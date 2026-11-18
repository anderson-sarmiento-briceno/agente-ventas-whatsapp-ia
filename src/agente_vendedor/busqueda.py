"""Búsqueda de productos: coincidencia difusa por palabras y, si no hay resultados, sugerencias del LLM."""
from __future__ import annotations

import logging
import re
import warnings

from fuzzywuzzy import fuzz, process

from .llm import ErrorLLM, ProveedorLLM
from .tienda import Producto

warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher")

log = logging.getLogger(__name__)

PALABRAS_RELEVANTES = {"verde", "rojo", "azul", "amarillo", "naranja", "morado", "negro", "blanco", "gris"}

PALABRAS_IGNORADAS = {
    "necesito", "quiero", "busco", "por", "favor", "de", "el", "los", "las",
    "un", "una", "unos", "unas", "me", "gustaría", "saber", "precio", "cuánto",
    "vale", "coste", "cuesta", "podría", "dame", "muéstrame", "mostrar", "tienes",
    "hay", "ofreces", "oferta", "barato", "caro", "que", "valen", "tambien", "cuanto",
    "galon", "galones", "metro", "metros", "pulgada", "pulgadas", "litro", "litros",
    "kg", "kilo", "kilos", "kilogramo", "kilogramos", "unidad", "unidades", "m2", "mts",
    "caneca", "canecas", "buenas", "tardes", "buenos", "dias", "noches", "al",
}

UMBRAL_TOKEN = 75  # similitud mínima entre una palabra de la consulta y una del nombre del producto
UMBRAL_GPT = 75  # similitud mínima entre el nombre sugerido por el LLM y el del catálogo


def es_palabra_irrelevante(palabra: str, palabras_ignoradas: set[str] = PALABRAS_IGNORADAS, umbral: int = 85) -> bool:
    if palabra.lower() in PALABRAS_RELEVANTES:
        return False
    if palabra in palabras_ignoradas:
        return True
    # Variantes truncadas o con errores de tipeo ("necesit", "porfa")
    for ignorada in palabras_ignoradas:
        if abs(len(palabra) - len(ignorada)) <= 2 and fuzz.partial_ratio(palabra, ignorada) >= 90:
            return True
    umbral_final = umbral if len(palabra) < 6 else 95
    _, puntaje = process.extractOne(palabra, palabras_ignoradas)
    return puntaje >= umbral_final


def extraer_cantidad_y_limpiar_keyword(consulta: str) -> tuple[int, str]:
    """'quiero 2 guantes rojos' -> (2, 'guantes rojos')"""
    encontrada = re.search(r"\b\d+\b", consulta)
    cantidad = int(encontrada.group()) if encontrada else 1
    sin_cantidad = re.sub(rf"\b{cantidad}\b", "", consulta).lower()
    palabras = [p for p in sin_cantidad.split() if not es_palabra_irrelevante(p)]
    return cantidad, " ".join(palabras).strip()


def buscar_producto_fuzzy(consulta: str, datos: list[Producto], llm: ProveedorLLM | None = None) -> list[dict]:
    """Devuelve `[{"item", "score", "cantidad"}]`. Todas las palabras de la consulta deben aparecer en el nombre."""
    _, consulta_limpia = extraer_cantidad_y_limpiar_keyword(consulta)
    if not consulta_limpia:
        return []

    tokens = consulta_limpia.split()
    resultados = []
    for item in datos:
        tokens_producto = item.get("servicio", "").lower().split()
        if all(any(fuzz.ratio(t, p) > UMBRAL_TOKEN for p in tokens_producto) for t in tokens):
            resultados.append({"item": item, "score": 100, "cantidad": 1})

    if resultados or llm is None:
        return resultados

    log.info("🤖 Sin coincidencias directas; consultando al LLM")
    try:
        return buscar_producto_gpt(consulta, datos, llm, top_n=5)
    except Exception as e:  # noqa: BLE001
        log.error("Error al consultar el LLM: %s", e)
        return []


PRODUCTOS_POR_CONSULTA = 200  # el catálogo se envía en bloques de este tamaño
SIN_COINCIDENCIAS = "NINGUNO"


def _prompt_busqueda(consulta: str, catalogo: str) -> str:
    return (
        "Eres un asistente que ayuda a encontrar productos en un almacén. "
        "Dado el siguiente catálogo de productos, responde con una lista separada por comas de hasta 10 productos del catálogo "
        "que realmente correspondan a la siguiente consulta del cliente. "
        "La consulta puede usar sinónimos o términos alternativos para referirse a los productos, incluyendo género, uso o tipo "
        "(por ejemplo, 'retrovisor' = espejo, 'proteger la cabeza' = casco). "
        "Da prioridad a coincidencias de género (por ejemplo, 'para niña' o 'de mujer') sobre otras características como color o tamaño. "
        "No incluyas productos que sirvan para otra cosa.\n\n"
        f"Consulta del cliente: {consulta}\n"
        f"Catálogo de productos: {catalogo}\n\n"
        "Responde solo con los nombres exactos de los productos del catálogo, separados por comas, "
        f"del más al menos relevante. Si ninguno corresponde, responde solo {SIN_COINCIDENCIAS}."
    )


def buscar_producto_gpt(consulta: str, datos: list[Producto], llm: ProveedorLLM, top_n: int = 10) -> list[dict]:
    """Pide al LLM nombres del catálogo (en bloques de PRODUCTOS_POR_CONSULTA) y los mapea a productos reales."""
    cantidad, consulta_limpia = extraer_cantidad_y_limpiar_keyword(consulta)
    if not consulta_limpia or not datos:
        return []

    catalogo = sorted({item["servicio"] for item in datos if item.get("servicio")})
    tam = PRODUCTOS_POR_CONSULTA
    partes = [catalogo[i : i + tam] for i in range(0, len(catalogo), tam)]
    resultados: list[dict] = []

    for parte in partes:
        try:
            respuesta = llm.completar(
                [{"role": "user", "content": _prompt_busqueda(consulta_limpia, ", ".join(parte))}],
                max_tokens=150,
                temperature=0.8,
            )
        except ErrorLLM as e:
            log.error("Error en búsqueda con LLM: %s", e)
            respuesta = ""

        for nombre in (n.strip() for n in respuesta.split(",")):
            if not nombre or nombre.upper() == SIN_COINCIDENCIAS:
                continue
            mejor = max(datos, key=lambda it: fuzz.token_set_ratio(nombre.lower(), it.get("servicio", "").lower()))
            score = fuzz.token_set_ratio(nombre.lower(), mejor.get("servicio", "").lower())
            ya_esta = any(r["item"]["servicio"].lower() == mejor["servicio"].lower() for r in resultados)
            if score >= UMBRAL_GPT and not ya_esta:
                resultados.append({"item": mejor, "score": score, "cantidad": cantidad})

        if len(resultados) >= top_n:
            break

    return resultados[:top_n]
