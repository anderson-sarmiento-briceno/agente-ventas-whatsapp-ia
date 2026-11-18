"""Webhook HTTP: verificación de Meta, parseo de payloads y tipos de mensaje."""
import pytest

from agente_vendedor.agente import MSG_NO_SOPORTADO
from agente_vendedor.server import crear_app, texto_del_mensaje

from .conftest import CLIENTE, leer_fixture


@pytest.fixture
def cliente(deps):
    return crear_app(deps).test_client()


def test_verificacion_del_webhook(cliente):
    r = cliente.get("/?hub.mode=subscribe&hub.verify_token=token-prueba&hub.challenge=12345")
    assert r.status_code == 200 and r.data == b"12345"


def test_verificacion_con_token_incorrecto(cliente):
    assert cliente.get("/?hub.mode=subscribe&hub.verify_token=otro&hub.challenge=1").status_code == 403


def test_token_vacio_nunca_verifica(cliente, deps):
    from dataclasses import replace

    deps.config = replace(deps.config, whatsapp_verify_token="")
    assert cliente.get("/?hub.mode=subscribe&hub.verify_token=&hub.challenge=1").status_code == 403


def test_mensaje_de_texto(cliente, deps):
    r = cliente.post("/", json=leer_fixture("webhooks/texto.json"))
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}
    assert "Bienvenido" in deps.mensajero.textos(CLIENTE)[0]


def test_notificacion_de_estado_se_ignora(cliente, deps):
    r = cliente.post("/", json=leer_fixture("webhooks/estado.json"))
    assert r.get_json() == {"status": "ok"}
    assert deps.mensajero.enviados == []


def test_tipo_no_soportado(cliente, deps):
    cliente.post("/", json=leer_fixture("webhooks/imagen.json"))
    assert deps.mensajero.textos() == [MSG_NO_SOPORTADO]


def test_respuesta_de_lista(cliente, deps):
    cliente.post("/", json=leer_fixture("webhooks/texto.json"))
    deps.mensajero.limpiar()
    cliente.post("/", json=leer_fixture("webhooks/lista.json"))
    assert deps.mensajero.textos()[0].startswith("✅ Casco integral negro mate")


@pytest.mark.parametrize("cuerpo", [b"no json", b"{}", b'{"entry": [{}]}', b'{"entry": [{"changes": [{}]}]}'])
def test_payload_invalido(cliente, cuerpo):
    r = cliente.post("/", data=cuerpo, content_type="application/json")
    assert r.status_code == 400


def test_health(cliente):
    assert cliente.get("/health").get_json() == {"ok": True, "modelo": "falso"}


@pytest.mark.parametrize(
    "mensaje, esperado",
    [
        ({"type": "text", "text": {"body": " hola "}}, "hola"),
        ({"type": "interactive", "interactive": {"button_reply": {"title": "Sí"}}}, "Sí"),
        ({"type": "interactive", "interactive": {"list_reply": {"title": "Casco"}}}, "Casco"),
        ({"type": "interactive", "interactive": {"button": {"text": "No"}}}, "No"),
        ({"type": "interactive", "interactive": {}}, ""),
        ({"type": "button", "button": {"text": "Ver catálogo"}}, "Ver catálogo"),
        ({"type": "audio"}, None),
    ],
)
def test_texto_del_mensaje(mensaje, esperado):
    assert texto_del_mensaje(mensaje) == esperado
