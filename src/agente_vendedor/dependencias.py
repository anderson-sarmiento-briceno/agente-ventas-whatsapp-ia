"""Contenedor de dependencias del agente. Producción y tests arman el mismo objeto con piezas distintas."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from .config import Config
from .contexto import AlmacenContexto
from .llm import ProveedorLLM
from .marketplace import extraer_titulo_marketplace
from .tienda import Tienda
from .whatsapp import Mensajero


@dataclass
class Dependencias:
    config: Config
    mensajero: Mensajero
    contexto: AlmacenContexto
    tienda: Tienda
    llm: ProveedorLLM
    reloj: Callable[[], float] = time.time
    dormir: Callable[[float], None] = time.sleep
    extraer_titulo: Callable[[str], str | None] = field(default=extraer_titulo_marketplace)


def crear_dependencias_produccion(config: Config | None = None) -> Dependencias:
    """WhatsApp Cloud API + DynamoDB + Google Sheets/Drive + OpenAI."""
    from .contexto.dynamodb import ContextoDynamoDB
    from .llm import crear_proveedor_llm
    from .tienda.google import TiendaGoogle
    from .whatsapp.cloud_api import ClienteWhatsApp

    config = config or Config.desde_entorno()
    return Dependencias(
        config=config,
        mensajero=ClienteWhatsApp(config),
        contexto=ContextoDynamoDB(config.dynamodb_tabla, config.contexto_ttl_seg),
        tienda=TiendaGoogle(config),
        llm=crear_proveedor_llm(config),
    )
