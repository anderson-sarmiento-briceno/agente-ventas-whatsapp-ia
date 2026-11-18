"""Cliente de la WhatsApp Cloud API (Graph API de Meta).

Los errores de red o HTTP se registran y no se propagan: un mensaje que no sale
no debe tumbar el resto de la conversación (mismo comportamiento que la versión original).
"""
from __future__ import annotations

import logging
from typing import Any

import requests

from ..config import Config

log = logging.getLogger(__name__)


class ClienteWhatsApp:
    def __init__(self, config: Config, sesion: Any = None):
        self._url = (
            f"https://graph.facebook.com/{config.whatsapp_api_version}/{config.whatsapp_phone_number_id}/messages"
        )
        self._headers = {
            "Authorization": f"Bearer {config.whatsapp_access_token}",
            "Content-Type": "application/json",
        }
        self._http = sesion or requests

    def enviar_texto(self, numero: str, mensaje: str) -> None:
        payload = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": mensaje}}
        self._post(payload, "mensaje", timeout=10)

    def enviar_media(self, numero: str, url: str, tipo: str = "image", caption: str = "") -> None:
        payload = {"messaging_product": "whatsapp", "to": numero, "type": tipo, tipo: {"link": url, "caption": caption}}
        self._post(payload, tipo, timeout=10)

    def enviar_documento(self, numero: str, url: str, nombre_archivo: str, caption: str = "") -> None:
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "document",
            "document": {"link": url, "filename": nombre_archivo, "caption": caption},
        }
        self._post(payload, "documento", timeout=15)

    def _post(self, payload: dict, descripcion: str, timeout: float) -> bool:
        # Nunca se registran los headers: contienen el token de acceso.
        log.debug("Enviando %s: %s", descripcion, payload)
        try:
            respuesta = self._http.post(self._url, headers=self._headers, json=payload, timeout=timeout)
            respuesta.raise_for_status()
            log.info("✅ %s enviado a %s", descripcion.capitalize(), payload.get("to"))
            return True
        except requests.exceptions.Timeout:
            log.error("❌ Timeout al enviar %s (revisar conectividad de la Lambda)", descripcion)
        except requests.exceptions.ConnectionError as e:
            log.error("❌ Fallo de conexión al enviar %s: %s", descripcion, e)
        except requests.exceptions.HTTPError as e:
            r = e.response
            log.error("❌ Error HTTP al enviar %s: %s %s - %s", descripcion, r.status_code, r.reason, r.text)
        except Exception as e:  # noqa: BLE001
            log.error("❌ Error inesperado al enviar %s: %s", descripcion, e)
        return False
