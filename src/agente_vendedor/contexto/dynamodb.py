"""Contexto de conversación en DynamoDB (tabla con clave `whatsapp_number` y TTL `expire_at`)."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from .serializacion import deserializar, serializar

log = logging.getLogger(__name__)


class ContextoDynamoDB:
    def __init__(self, tabla: str, ttl_seg: int = 86400, recurso: Any = None, reloj: Callable[[], float] = time.time):
        if recurso is None:
            import boto3

            recurso = boto3.resource("dynamodb")
        self._tabla = recurso.Table(tabla)
        self._ttl = ttl_seg
        self._reloj = reloj

    def obtener(self, numero: str) -> dict:
        try:
            item = self._tabla.get_item(Key={"whatsapp_number": numero}).get("Item", {})
            return deserializar(item.get("context", "{}"))
        except Exception as e:  # noqa: BLE001 - un fallo de lectura reinicia la conversación
            log.error("🔥 Error DynamoDB al obtener contexto de %s: %s", numero, e)
            return {}

    def guardar(self, numero: str, contexto: dict) -> None:
        if not isinstance(contexto, dict):
            log.error("❌ Contexto no-dict para %s (%s). No se guarda.", numero, type(contexto).__name__)
            return
        try:
            self._tabla.put_item(
                Item={
                    "whatsapp_number": numero,
                    "context": serializar(contexto),
                    "expire_at": int(self._reloj() + self._ttl),
                }
            )
            log.info("✅ Contexto guardado para %s", numero)
        except Exception as e:  # noqa: BLE001
            log.error("🔥 Error DynamoDB al guardar contexto de %s: %s", numero, e)

    def eliminar(self, numero: str) -> None:
        try:
            self._tabla.delete_item(Key={"whatsapp_number": numero})
            log.info("🗑️ Contexto eliminado para %s", numero)
        except Exception as e:  # noqa: BLE001
            log.error("⚠️ Error DynamoDB al eliminar contexto de %s: %s", numero, e)
