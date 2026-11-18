"""Tienda en memoria, cargada desde `fixtures/`. Se usa en tests y en `demo.py`."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .adapter import Archivo, Producto

ENCABEZADO_VENTAS = [
    "Fecha", "Nombre", "Teléfono", "Dirección", "Producto",
    "CódigoProducto", "Cantidad", "Asesor", "CódigoVenta", "estado", "PrecioFinal",
]


class TiendaMemoria:
    def __init__(
        self,
        inventario: list[Producto],
        archivos: list[Archivo] | None = None,
        catalogo: dict[str, str] | None = None,
        ventas: list[list[Any]] | None = None,
    ):
        self.productos = copy.deepcopy(inventario)
        self.archivos = list(archivos or [])
        self.catalogo = catalogo
        self.ventas: list[list[Any]] = ventas if ventas is not None else [list(ENCABEZADO_VENTAS)]

    @classmethod
    def desde_fixtures(cls, directorio: str | Path) -> "TiendaMemoria":
        d = Path(directorio)
        leer = lambda nombre: json.loads((d / nombre).read_text(encoding="utf-8"))  # noqa: E731
        return cls(
            inventario=leer("inventario.json"),
            archivos=leer("archivos_drive.json"),
            catalogo=leer("catalogo.json") if (d / "catalogo.json").exists() else None,
        )

    def inventario(self, forzar: bool = False) -> list[Producto]:
        return copy.deepcopy(self.productos)

    def actualizar_unidades(self, fila: int, unidades: int) -> None:
        self.productos[fila - 2]["unidades"] = str(unidades)

    def buscar_archivos(self, prefijo: str) -> list[Archivo]:
        return [a for a in self.archivos if prefijo and prefijo in a["name"]]

    def catalogo_pdf(self) -> dict[str, str] | None:
        return self.catalogo

    def registrar_venta(self, fila: list[Any]) -> int | None:
        self.ventas.append(list(fila))
        return len(self.ventas)

    def leer_ventas(self) -> list[list[str]]:
        return [[str(v) for v in fila] for fila in self.ventas]

    def actualizar_venta(self, fila: int, columna: int, valor: Any) -> None:
        registro = self.ventas[fila - 1]
        registro.extend([""] * (columna - len(registro)))
        registro[columna - 1] = valor
