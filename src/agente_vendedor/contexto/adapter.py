"""Interfaz del almacén del contexto de conversación de cada usuario."""
from __future__ import annotations

from typing import Protocol


class AlmacenContexto(Protocol):
    def obtener(self, numero: str) -> dict:
        """Devuelve el contexto guardado o `{}` si no existe o está corrupto."""
        ...

    def guardar(self, numero: str, contexto: dict) -> None: ...

    def eliminar(self, numero: str) -> None: ...
