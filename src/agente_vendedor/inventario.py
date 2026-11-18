"""Verificación de stock, formato de mensajes de producto y archivos asociados."""
from __future__ import annotations

import logging
import re

from .busqueda import buscar_producto_fuzzy
from .llm import ProveedorLLM
from .tienda import Archivo, Producto, Tienda

log = logging.getLogger(__name__)

ERROR_INVENTARIO = "❌ Error temporal al acceder al inventario. Por favor intenta más tarde."
ERROR_SIN_COINCIDENCIAS = "❌ No encontré productos que coincidan. Escribe *nombre de otro producto*"
ERROR_SIN_STOCK = "⚠️ El producto está registrado pero no hay unidades disponibles."


def a_entero(valor: object, defecto: int = 0) -> int:
    try:
        texto = str(valor).strip()
        return int(float(texto)) if texto else defecto
    except (TypeError, ValueError):
        return defecto


def a_precio(valor: object) -> float:
    """Convierte precios como '45000', '45.000', '$45.000' o '1.250,50' a float. Lanza ValueError si no puede."""
    texto = re.sub(r"[$\s]", "", str(valor))
    if not texto:
        raise ValueError("precio vacío")
    if "," in texto and "." in texto:  # 1.250,50 -> 1250.50
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", texto):  # 45.000 -> 45000 (miles en pesos)
        texto = texto.replace(".", "")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+", texto):  # 45,000 -> 45000
        texto = texto.replace(",", "")
    else:
        texto = texto.replace(",", ".")
    return float(texto)


def buscar_y_verificar_inventario(consulta: str, datos: list, llm: ProveedorLLM | None = None) -> list[dict]:
    """Busca productos y deja solo los que tienen unidades.

    Devuelve `[{"item", "unidades", "precio", "numero"}]` o `[{"error": mensaje}]`.
    """
    if not datos or not isinstance(datos, list):
        return [{"error": ERROR_INVENTARIO}]

    if isinstance(datos[0], dict):
        inventario = datos
    else:  # filas crudas: la primera es el encabezado
        encabezados = datos[0]
        inventario = [dict(zip(encabezados, fila)) for fila in datos[1:] if len(fila) == len(encabezados)]

    encontrados = buscar_producto_fuzzy(consulta, inventario, llm)
    if not encontrados:
        return [{"error": ERROR_SIN_COINCIDENCIAS}]

    disponibles = []
    for r in encontrados:
        item = r.get("item", {})
        if not isinstance(item, dict):
            continue
        unidades = a_entero(item.get("unidades", "0"))
        if unidades <= 0:
            continue
        disponibles.append(
            {"item": item, "unidades": unidades, "precio": item.get("precio", "N/A"), "numero": str(item.get("numero", ""))}
        )

    return disponibles or [{"error": ERROR_SIN_STOCK}]


def formatear_resultados(resultados: list[dict]) -> str:
    if not resultados:
        return "❌ No se encontraron resultados"
    if "error" in resultados[0]:
        return resultados[0]["error"]

    mensajes = []
    for r in resultados:
        if "item" not in r:
            continue
        nombre = r["item"].get("servicio", "Producto sin nombre")
        descripcion = r["item"].get("descripcion", "Sin descripción disponible.")
        if r.get("unidades", 0) > 0:
            mensajes.append(f"✅ {nombre} tiene un precio unitario de: ${r.get('precio', 'N/A')}\n📝 {descripcion}")
        else:
            mensajes.append(f"❌ '{nombre}' - Agotado\n📝 Descripción: {descripcion}")
    return "\n".join(mensajes) if mensajes else "❌ No se encontraron productos disponibles."


def formatear_seleccion_whatsapp(resultados: list[dict]) -> str:
    mensaje = (
        "🔢 Escribe el número del producto que deseas ver o *0* para cancelar búsqueda.\n\n"
        "🔽 Se encontraron varios productos en el catalogo:\n"
    )
    for i, r in enumerate(resultados, 1):
        nombre = r["item"].get("servicio", f"Producto {i}")
        estado = "✅ Disponible" if r["unidades"] > 0 else "❌ Agotado"
        mensaje += f"{i}. {nombre} - {estado}\n"
    return mensaje + "0. Cancelar búsqueda"


def _orden_tipo(archivo: Archivo) -> int:
    mime = archivo.get("mimeType", "")
    return 0 if "image" in mime else 1 if "video" in mime else 2


def obtener_archivos_asociados(numero_producto: str, tienda: Tienda, max_archivos: int = 2) -> list[Archivo]:
    """Archivos de Drive del producto (prefijo = 4 primeras letras del código), imágenes primero."""
    if not numero_producto or numero_producto == "0":
        return []
    archivos = tienda.buscar_archivos(numero_producto[:4])
    return sorted(archivos, key=_orden_tipo)[:max_archivos]


def url_descarga_drive(file_id: str) -> str:
    return f"https://drive.google.com/uc?id={file_id}&export=download"


def producto_por_numero(inventario: list[Producto], numero_producto: str) -> tuple[int, Producto] | None:
    """(fila en la hoja, producto). La fila 1 es el encabezado."""
    for fila, item in enumerate(inventario, start=2):
        if str(item.get("numero", "")).strip() == str(numero_producto).strip():
            return fila, item
    return None
