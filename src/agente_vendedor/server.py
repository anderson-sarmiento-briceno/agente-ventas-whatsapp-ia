"""Webhook HTTP de WhatsApp (Flask). Solo traduce HTTP <-> agente; la lógica vive en `agente.py`.

Uso local:  python -m agente_vendedor.server   (lee .env, usa servicios reales)
"""
from __future__ import annotations

import json
import logging
import os

from flask import Flask, Response, jsonify, request

from .agente import OK, procesar_mensaje, procesar_no_soportado
from .dependencias import Dependencias

log = logging.getLogger(__name__)


class PayloadInvalido(ValueError):
    pass


def extraer_mensaje(body: dict) -> dict | None:
    """Devuelve el primer mensaje del webhook, o None si es una notificación de estado."""
    if not isinstance(body, dict) or not body.get("entry"):
        raise PayloadInvalido("'entry' no encontrado")
    entry = body["entry"][0]
    if not entry.get("changes"):
        raise PayloadInvalido("'changes' no encontrado")
    value = entry["changes"][0].get("value")
    if not value:
        raise PayloadInvalido("'value' no encontrado")
    mensajes = value.get("messages")
    return mensajes[0] if mensajes else None


def texto_del_mensaje(mensaje: dict) -> str | None:
    """Texto del mensaje (texto libre, botón o lista). None si el tipo no está soportado."""
    tipo = mensaje.get("type")
    if tipo == "text":
        return str(mensaje.get("text", {}).get("body", "")).strip()
    if tipo == "interactive":
        interactivo = mensaje.get("interactive", {})
        for clave, campo in (("button_reply", "title"), ("list_reply", "title"), ("button", "text")):
            if campo in interactivo.get(clave, {}):
                return str(interactivo[clave][campo]).strip()
        return ""
    if tipo == "button":  # respuesta rápida de una plantilla
        return str(mensaje.get("button", {}).get("text", "")).strip()
    return None


def crear_app(deps: Dependencias) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def verificar_webhook():
        p = request.args
        token = deps.config.whatsapp_verify_token
        if token and p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == token:
            log.info("✅ Webhook verificado")
            return Response(p.get("hub.challenge", ""), mimetype="text/plain")
        log.warning("❌ Token de verificación inválido")
        return Response("Token inválido", status=403, mimetype="text/plain")

    @app.post("/")
    def recibir_mensaje():
        inicio = deps.reloj()
        try:
            body = request.get_json(silent=True)
            if body is None:
                body = json.loads(request.data.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            log.error("JSON inválido: %s", e)
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        try:
            mensaje = extraer_mensaje(body)
        except PayloadInvalido as e:
            log.warning("Payload de WhatsApp inválido: %s", e)
            return jsonify({"status": "error", "message": "Invalid WhatsApp payload"}), 400

        if mensaje is None or not mensaje.get("from"):
            return jsonify({"status": OK})  # notificación de estado (entregado, leído...)

        numero = mensaje["from"]
        texto = texto_del_mensaje(mensaje)
        if texto is None:
            log.info("Tipo de mensaje no soportado: %s", mensaje.get("type"))
            return jsonify({"status": procesar_no_soportado(deps, numero, inicio)})

        estado = procesar_mensaje(deps, numero, texto, inicio)
        log.info("✅ Solicitud completada en %.2f s", deps.reloj() - inicio)
        return jsonify({"status": estado})

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "modelo": deps.llm.modelo})

    return app


def main() -> None:
    from .config import Config, cargar_env_local
    from .dependencias import crear_dependencias_produccion

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(levelname)s %(name)s: %(message)s")
    cargar_env_local()
    config = Config.desde_entorno()
    if faltan := config.faltantes():
        raise SystemExit(f"Faltan variables de entorno: {', '.join(faltan)} (ver .env.example)")
    app = crear_app(crear_dependencias_produccion(config))
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


if __name__ == "__main__":
    main()
