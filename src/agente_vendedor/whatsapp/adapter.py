"""Interfaz del canal de mensajería (WhatsApp Cloud API o un doble de pruebas)."""
from __future__ import annotations

from typing import Protocol


class Mensajero(Protocol):
    def enviar_texto(self, numero: str, mensaje: str) -> None: ...

    def enviar_media(self, numero: str, url: str, tipo: str = "image", caption: str = "") -> None: ...

    def enviar_documento(self, numero: str, url: str, nombre_archivo: str, caption: str = "") -> None: ...
