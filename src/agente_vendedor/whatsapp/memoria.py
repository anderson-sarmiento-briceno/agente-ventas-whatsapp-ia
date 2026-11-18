"""Mensajero en memoria: guarda lo que se habría enviado por WhatsApp (tests y demo)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Enviado:
    tipo: str  # "text" | "image" | "video" | "document"
    numero: str
    contenido: str  # texto del mensaje o URL del archivo
    caption: str = ""
    nombre_archivo: str = ""


@dataclass
class MensajeroMemoria:
    enviados: list[Enviado] = field(default_factory=list)

    def enviar_texto(self, numero: str, mensaje: str) -> None:
        self.enviados.append(Enviado("text", numero, mensaje))

    def enviar_media(self, numero: str, url: str, tipo: str = "image", caption: str = "") -> None:
        self.enviados.append(Enviado(tipo, numero, url, caption=caption))

    def enviar_documento(self, numero: str, url: str, nombre_archivo: str, caption: str = "") -> None:
        self.enviados.append(Enviado("document", numero, url, caption=caption, nombre_archivo=nombre_archivo))

    def textos(self, numero: str | None = None) -> list[str]:
        return [e.contenido for e in self.enviados if e.tipo == "text" and (numero is None or e.numero == numero)]

    def ultimo_texto(self, numero: str | None = None) -> str:
        textos = self.textos(numero)
        return textos[-1] if textos else ""

    def limpiar(self) -> None:
        self.enviados.clear()
