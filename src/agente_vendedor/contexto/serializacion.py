"""Conversión del contexto a/desde JSON con números `Decimal` (lo que exige DynamoDB)."""
from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

log = logging.getLogger(__name__)


def decimal_serializer(o: Any) -> float:
    """Permite a `json.dumps` serializar `Decimal`."""
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")


def floats_a_decimal(obj: Any) -> Any:
    if isinstance(obj, float):
        return Decimal(str(obj))  # vía str para no perder precisión
    if isinstance(obj, dict):
        return {k: floats_a_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [floats_a_decimal(v) for v in obj]
    return obj


def serializar(contexto: dict) -> str:
    return json.dumps(floats_a_decimal(contexto), default=decimal_serializer)


def deserializar(valor: Any) -> dict:
    """Acepta el string JSON guardado (o un dict de formatos antiguos). Si es inválido devuelve `{}`."""
    if isinstance(valor, dict):
        return json.loads(json.dumps(valor, default=decimal_serializer), parse_float=Decimal)
    if not isinstance(valor, str):
        log.warning("🚨 Formato de contexto inválido: %s. Se reinicia.", type(valor).__name__)
        return {}
    try:
        contexto = json.loads(valor, parse_float=Decimal)
    except json.JSONDecodeError:
        log.warning("⚠️ Contexto corrupto (JSON inválido). Se reinicia.")
        return {}
    if not isinstance(contexto, dict):
        log.warning("⚠️ El contexto no es un diccionario (%s). Se reinicia.", type(contexto).__name__)
        return {}
    return contexto
