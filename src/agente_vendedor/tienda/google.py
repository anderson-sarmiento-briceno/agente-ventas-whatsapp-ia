"""Tienda sobre Google Sheets (inventario y registro de ventas) y Google Drive (fotos, videos, catálogo)."""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable

from ..config import Config
from .adapter import Archivo, Producto

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


def filas_a_productos(valores: list[list[str]]) -> list[Producto]:
    """Convierte la salida de `get_all_values()` (encabezado + filas) en diccionarios limpios."""
    if not valores or len(valores) < 2:
        return []
    encabezados = [h.strip() for h in valores[0]]
    productos = []
    for fila in valores[1:]:
        completa = list(fila) + [""] * (len(encabezados) - len(fila))
        productos.append({encabezados[i]: str(v).strip() for i, v in enumerate(completa[: len(encabezados)])})
    return productos


def fila_desde_rango(rango: str) -> int | None:
    """'registro_ventas!A12:J12' -> 12"""
    m = re.search(r"![A-Z]+(\d+)", rango or "")
    return int(m.group(1)) if m else None


def escapar_query_drive(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace("'", "\\'")


class TiendaGoogle:
    def __init__(self, config: Config, reloj: Callable[[], float] = time.time):
        self._config = config
        self._reloj = reloj
        self._libro: Any = None
        self._drive: Any = None
        self._cache: list[Producto] | None = None
        self._cache_ts = 0.0

    # --- conexión (perezosa y reutilizada entre invocaciones "calientes" de Lambda) ---
    def _credenciales(self):
        from google.oauth2.service_account import Credentials

        return Credentials.from_service_account_file(self._config.google_credentials_file, scopes=SCOPES)

    def libro(self):
        if self._libro is None:
            import gspread

            self._libro = gspread.authorize(self._credenciales()).open_by_key(self._config.spreadsheet_id)
        return self._libro

    def drive(self):
        if self._drive is None:
            from googleapiclient.discovery import build

            self._drive = build("drive", "v3", credentials=self._credenciales(), cache_discovery=False)
        return self._drive

    def precalentar(self) -> None:
        self.libro()

    # --- inventario ---
    def inventario(self, forzar: bool = False) -> list[Producto]:
        ahora = self._reloj()
        vigente = self._cache is not None and (ahora - self._cache_ts) < self._config.cache_inventario_seg
        if vigente and not forzar:
            log.info("♻️ Inventario desde caché")
            return self._cache  # type: ignore[return-value]
        try:
            valores = self.libro().worksheet(self._config.hoja_inventario).get_all_values()
        except Exception as e:  # noqa: BLE001 - si falla la API se usa la caché vieja
            log.error("❌ Error leyendo inventario: %s", e)
            return self._cache or []
        productos = filas_a_productos(valores)
        if not productos:
            log.warning("⚠️ Hoja de inventario vacía")
            return self._cache or []
        self._cache, self._cache_ts = productos, ahora
        log.info("✅ Inventario actualizado: %d productos", len(productos))
        return productos

    def actualizar_unidades(self, fila: int, unidades: int) -> None:
        hoja = self.libro().worksheet(self._config.hoja_inventario)
        encabezados = [h.strip() for h in hoja.row_values(1)]
        columna = encabezados.index("unidades") + 1 if "unidades" in encabezados else 3
        hoja.update_cell(fila, columna, unidades)
        self._cache = None  # la próxima lectura trae el inventario actualizado

    # --- Drive ---
    def buscar_archivos(self, prefijo: str) -> list[Archivo]:
        if not prefijo:
            return []
        query = (
            f"name contains '{escapar_query_drive(prefijo)}' "
            f"and '{self._config.drive_carpeta_id}' in parents and trashed = false"
        )
        r = self.drive().files().list(q=query, spaces="drive", fields="files(id, name, mimeType)", pageSize=50).execute()
        return r.get("files", [])

    def catalogo_pdf(self) -> dict[str, str] | None:
        query = f"mimeType='application/pdf' and '{self._config.drive_carpeta_id}' in parents and trashed = false"
        r = (
            self.drive()
            .files()
            .list(q=query, spaces="drive", fields="files(id, name)", orderBy="createdTime desc", pageSize=1)
            .execute()
        )
        archivos = r.get("files", [])
        if not archivos:
            return None
        a = archivos[0]
        return {"id": a["id"], "nombre": a["name"], "url": f"https://drive.google.com/uc?id={a['id']}&export=download"}

    # --- registro de ventas ---
    def _hoja_ventas(self):
        return self.libro().worksheet(self._config.hoja_ventas)

    def registrar_venta(self, fila: list[Any]) -> int | None:
        respuesta = self._hoja_ventas().append_row(fila)
        try:
            return fila_desde_rango(respuesta["updates"]["updatedRange"])
        except (KeyError, TypeError):
            return None

    def leer_ventas(self) -> list[list[str]]:
        return self._hoja_ventas().get_all_values()

    def actualizar_venta(self, fila: int, columna: int, valor: Any) -> None:
        self._hoja_ventas().update_cell(fila, columna, valor)
