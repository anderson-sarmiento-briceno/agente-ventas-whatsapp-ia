"""Clasifica mensajes (pregunta general vs. búsqueda de producto) y responde las preguntas generales."""
from __future__ import annotations

import logging
import re

from .llm import ErrorLLM, ProveedorLLM
from .prompts import cargar_conocimiento, cargar_prompt, renderizar

log = logging.getLogger(__name__)

RESPUESTAS_SIMPLES = {"si", "sí", "no", "s", "n", "ok", "yes", "okay", "gracias", "de nada", "listo", "claro"}
PATRON_OPCION = re.compile(r"^\d{1,3}$")
PATRON_CELULAR = re.compile(r"\b(?:\d{7}|\d{10})\b")
PATRON_CELULAR_CO = re.compile(r"\b3(?:0[0-9]|1[0-9]|2[0-9]|5[0-9])\d{7}\b")

SISTEMA_CLASIFICADOR = "Eres un clasificador binario. Responde solo 'True' o 'False'."
RESPUESTA_RESPALDO = "¡Hola! 😊 Estoy aquí para ayudarte. ¿Tienes alguna pregunta sobre nuestros productos?"


def es_pregunta_general(texto: str, llm: ProveedorLLM) -> bool:
    """True si el mensaje es una consulta general (horarios, envíos, colores...), False si busca un producto.

    Opciones de lista, respuestas sí/no y números de teléfono se resuelven sin llamar al LLM.
    """
    texto = texto.lower().strip()
    if PATRON_OPCION.fullmatch(texto) or texto in RESPUESTAS_SIMPLES:
        return False
    if PATRON_CELULAR_CO.search(texto) or PATRON_CELULAR.search(texto):
        return False

    prompt = renderizar(cargar_prompt("clasificador"), texto=texto)
    try:
        salida = llm.completar(
            [{"role": "system", "content": SISTEMA_CLASIFICADOR}, {"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0.0,
        )
    except ErrorLLM as e:
        log.error("Error al clasificar mensaje: %s", e)
        return False
    return salida.strip().lower() == "true"


def responder_fuera_de_flujo(mensaje: str, llm: ProveedorLLM, nombre_tienda: str = "Accesorios MotoPro") -> str:
    """Responde con la información del negocio (`knowledge/negocio.md`)."""
    prompt = renderizar(
        cargar_prompt("respuesta"),
        tienda=nombre_tienda,
        documento=cargar_conocimiento("negocio"),
        pregunta=mensaje,
    )
    try:
        return llm.completar([{"role": "user", "content": prompt}], max_tokens=150, temperature=0.7) or RESPUESTA_RESPALDO
    except ErrorLLM as e:
        log.error("❌ Error en LLM: %s", e)
        return RESPUESTA_RESPALDO
