"""Interfaz de la tienda: inventario, archivos de producto, catálogo y registro de ventas.

La implementación real usa Google Sheets + Google Drive (`google.py`);
la de pruebas guarda todo en memoria (`memoria.py`).
"""
from __future__ import annotations

from typing import Any, Protocol

Producto = dict[str, str]  # una fila de la hoja de inventario: numero, servicio, unidades, precio, descripcion
Archivo = dict[str, str]  # {"id", "name", "mimeType"}

# Columnas de la hoja de ventas (base 1, como en Google Sheets)
COL_FECHA = 1
COL_CANTIDAD = 7
COL_CODIGO_VENTA = 9
COL_ESTADO = 10
COL_PRECIO_FINAL = 11


class Tienda(Protocol):
    def inventario(self, forzar: bool = False) -> list[Producto]:
        """Productos del inventario (con caché salvo `forzar=True`)."""
        ...

    def actualizar_unidades(self, fila: int, unidades: int) -> None:
        """Actualiza las unidades del producto en la fila `fila` de la hoja (la 1 es el encabezado)."""
        ...

    def buscar_archivos(self, prefijo: str) -> list[Archivo]:
        """Archivos de Drive cuyo nombre contiene `prefijo`."""
        ...

    def catalogo_pdf(self) -> dict[str, str] | None:
        """PDF más reciente del catálogo: {"id", "nombre", "url"}."""
        ...

    def registrar_venta(self, fila: list[Any]) -> int | None:
        """Agrega una fila al registro de ventas y devuelve su número de fila (si se conoce)."""
        ...

    def leer_ventas(self) -> list[list[str]]:
        """Todas las filas del registro de ventas, incluido el encabezado."""
        ...

    def actualizar_venta(self, fila: int, columna: int, valor: Any) -> None: ...
