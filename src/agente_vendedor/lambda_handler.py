"""Punto de entrada de AWS Lambda.

Handler a configurar en la función:  agente_vendedor.lambda_handler.handler
Las dependencias se crean una sola vez por contenedor y se reutilizan en invocaciones "calientes".
"""
from __future__ import annotations

import logging
import os

from asgiref.wsgi import WsgiToAsgi
from mangum import Mangum

from .config import Config
from .dependencias import crear_dependencias_produccion
from .secretos import cargar_secretos_aws
from .server import crear_app

logging.getLogger().setLevel(os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger(__name__)

cargar_secretos_aws()  # solo actúa si SECRETO_ID está definida (solución de pago)
config = Config.desde_entorno()
if faltan := config.faltantes():
    log.error("🚨 Faltan variables de entorno: %s", ", ".join(faltan))

deps = crear_dependencias_produccion(config)


def _precalentar() -> None:
    """Abre las conexiones a DynamoDB y Google Sheets durante el arranque en frío."""
    try:
        deps.contexto.obtener("0000000000")
        precalentar = getattr(deps.tienda, "precalentar", None)
        if precalentar:
            precalentar()
        log.info("✅ Dependencias listas")
    except Exception:  # noqa: BLE001
        log.exception("⚠️ No se pudieron precalentar las dependencias")


_precalentar()
app = crear_app(deps)
handler = Mangum(WsgiToAsgi(app), lifespan="off")
