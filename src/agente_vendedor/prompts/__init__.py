"""Plantillas de prompt en Markdown. Se editan sin tocar código Python."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_DIR_PROMPTS = Path(__file__).parent
_DIR_KNOWLEDGE = _DIR_PROMPTS.parent / "knowledge"


@lru_cache(maxsize=None)
def cargar_prompt(nombre: str) -> str:
    return (_DIR_PROMPTS / f"{nombre}.md").read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def cargar_conocimiento(nombre: str = "negocio") -> str:
    texto = (_DIR_KNOWLEDGE / f"{nombre}.md").read_text(encoding="utf-8")
    return "\n".join(linea for linea in texto.splitlines() if linea.strip())


def renderizar(plantilla: str, **valores: str) -> str:
    """Reemplaza marcadores `{{clave}}` (no usa str.format para no chocar con llaves del texto)."""
    for clave, valor in valores.items():
        plantilla = plantilla.replace("{{" + clave + "}}", valor)
    return plantilla
