"""Proveedor LLM simulado para tests y para `demo.py`: responde sin red ni claves."""
from __future__ import annotations

from typing import Callable

from .adapter import ErrorLLM, Mensaje

RESPUESTA_DEFECTO = "¡Hola! 😊 Atendemos de lunes a viernes de 8:00 a 19:00 horas."


class ProveedorFalso:
    """Por defecto: el clasificador responde "False", la búsqueda GPT no sugiere nada
    y las preguntas generales reciben `RESPUESTA_DEFECTO`.

    Se puede pasar `responder(mensajes) -> str` para controlar cada respuesta.
    Todas las llamadas quedan en `self.llamadas`.
    """

    modelo = "falso"

    def __init__(self, responder: Callable[[list[Mensaje]], str] | None = None, *, fallar: bool = False):
        self._responder = responder
        self._fallar = fallar
        self.llamadas: list[list[Mensaje]] = []

    def completar(self, mensajes: list[Mensaje], *, max_tokens: int, temperature: float) -> str:
        self.llamadas.append(mensajes)
        if self._fallar:
            raise ErrorLLM("proveedor falso configurado para fallar")
        if self._responder is not None:
            return self._responder(mensajes)
        return respuesta_por_defecto(mensajes)


def es_clasificacion(mensajes: list[Mensaje]) -> bool:
    return any(m["role"] == "system" and "clasificador binario" in m["content"] for m in mensajes)


def es_busqueda_catalogo(mensajes: list[Mensaje]) -> bool:
    return any("Catálogo de productos:" in m["content"] for m in mensajes)


def respuesta_por_defecto(mensajes: list[Mensaje]) -> str:
    if es_clasificacion(mensajes):
        return "False"
    if es_busqueda_catalogo(mensajes):
        return ""
    return RESPUESTA_DEFECTO
