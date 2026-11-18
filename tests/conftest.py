"""Piezas compartidas: el agente se arma con dobles en memoria (sin red, sin claves)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agente_vendedor.agente import procesar_mensaje
from agente_vendedor.config import Config
from agente_vendedor.contexto.memoria import ContextoMemoria
from agente_vendedor.dependencias import Dependencias
from agente_vendedor.llm.falso import ProveedorFalso
from agente_vendedor.tienda.memoria import TiendaMemoria
from agente_vendedor.whatsapp.memoria import MensajeroMemoria

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
CLIENTE = "573000000001"
ASESOR = "573000000099"


def leer_fixture(ruta: str):
    texto = (FIXTURES / ruta).read_text(encoding="utf-8")
    return json.loads(texto) if ruta.endswith(".json") else texto


@pytest.fixture
def config() -> Config:
    return Config(
        whatsapp_verify_token="token-prueba",
        whatsapp_access_token="acceso-prueba",
        whatsapp_phone_number_id="000",
        openai_api_key="sk-prueba",
        spreadsheet_id="hoja",
        drive_carpeta_id="carpeta",
        numero_asesor=ASESOR,
        pausa_media_seg=0,
    )


@pytest.fixture
def tienda() -> TiendaMemoria:
    return TiendaMemoria.desde_fixtures(FIXTURES)


@pytest.fixture
def llm() -> ProveedorFalso:
    return ProveedorFalso()


@pytest.fixture
def deps(config, tienda, llm) -> Dependencias:
    return Dependencias(
        config=config,
        mensajero=MensajeroMemoria(),
        contexto=ContextoMemoria(),
        tienda=tienda,
        llm=llm,
        reloj=lambda: 0.0,
        dormir=lambda _s: None,
        extraer_titulo=lambda _url: None,
    )


class Chat:
    """Conversación de prueba: `chat("hola")` devuelve los textos que respondió el bot."""

    def __init__(self, deps: Dependencias, numero: str = CLIENTE):
        self.deps = deps
        self.numero = numero

    def __call__(self, texto: str) -> list[str]:
        mensajero = self.deps.mensajero
        antes = len(mensajero.enviados)
        procesar_mensaje(self.deps, self.numero, texto)
        return [e.contenido for e in mensajero.enviados[antes:] if e.tipo == "text" and e.numero == self.numero]

    @property
    def estado(self) -> str | None:
        return self.deps.contexto.estado(self.numero)

    @property
    def usuario(self) -> dict:
        return self.deps.contexto.obtener(self.numero).get("estado_usuarios_data", {}).get(self.numero, {})


@pytest.fixture
def chat(deps) -> Chat:
    return Chat(deps)


@pytest.fixture
def chat_asesor(deps) -> Chat:
    return Chat(deps, ASESOR)
