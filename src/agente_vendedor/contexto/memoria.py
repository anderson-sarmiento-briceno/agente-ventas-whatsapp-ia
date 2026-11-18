"""Contexto en memoria. Guarda el JSON serializado, igual que DynamoDB, para que los tests
detecten cualquier dato que no se pueda serializar."""
from __future__ import annotations

from .serializacion import deserializar, serializar


class ContextoMemoria:
    def __init__(self) -> None:
        self.datos: dict[str, str] = {}

    def obtener(self, numero: str) -> dict:
        return deserializar(self.datos.get(numero, "{}"))

    def guardar(self, numero: str, contexto: dict) -> None:
        self.datos[numero] = serializar(contexto)

    def eliminar(self, numero: str) -> None:
        self.datos.pop(numero, None)

    def estado(self, numero: str) -> str | None:
        """Atajo para tests: estado actual del usuario."""
        return self.obtener(numero).get("estado_usuarios_data", {}).get(numero, {}).get("estado")
