"""Carga secretos desde AWS Secrets Manager al entorno (solo si SECRETO_ID está definida).

El secreto es un JSON plano {"WHATSAPP_ACCESS_TOKEN": "...", "ANTHROPIC_API_KEY": "...", ...}.
Las variables que ya tengan valor en el entorno de la Lambda no se pisan.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)


def cargar_secretos_aws(secreto_id: str | None = None, cliente: Any = None) -> int:
    """Devuelve cuántas variables se cargaron (0 si no hay SECRETO_ID)."""
    secreto_id = (secreto_id or os.environ.get("SECRETO_ID", "")).strip()
    if not secreto_id:
        return 0
    if cliente is None:
        import boto3

        cliente = boto3.client("secretsmanager")
    datos = json.loads(cliente.get_secret_value(SecretId=secreto_id)["SecretString"])
    cargadas = 0
    for clave, valor in datos.items():
        if not os.environ.get(clave):
            os.environ[clave] = valor if isinstance(valor, str) else json.dumps(valor)
            cargadas += 1
    log.info("🔐 %d variables cargadas desde Secrets Manager", cargadas)
    return cargadas
