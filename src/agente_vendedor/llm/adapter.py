"""Interfaz propia del proveedor LLM: el agente solo conoce estos tipos.

Cambiar de proveedor (OpenAI, Claude, etc.) = escribir otra implementación de `ProveedorLLM`.
"""
from __future__ import annotations

from typing import Protocol

Mensaje = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": "..."}


class ProveedorLLM(Protocol):
    modelo: str

    def completar(self, mensajes: list[Mensaje], *, max_tokens: int, temperature: float) -> str:
        """Devuelve el texto de la respuesta. Lanza `ErrorLLM` si el proveedor falla."""
        ...


class ErrorLLM(Exception):
    """Error del proveedor LLM ya traducido a un mensaje claro."""
