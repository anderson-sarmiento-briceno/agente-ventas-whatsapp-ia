"""Piezas del despliegue en AWS: secretos, conversión del .env y eventos de Lambda (sin AWS real)."""
import json

import pytest
from asgiref.wsgi import WsgiToAsgi
from mangum import Mangum

from agente_vendedor.config import Config, leer_env
from agente_vendedor.secretos import cargar_secretos_aws
from agente_vendedor.server import crear_app
from scripts.env_a_aws import LIMITE_VARIABLES_LAMBDA, secreto, variables_lambda

from .conftest import leer_fixture


# --- Secrets Manager ---
class SecretsFalso:
    def __init__(self, datos):
        self.datos, self.pedidos = datos, []

    def get_secret_value(self, SecretId):
        self.pedidos.append(SecretId)
        return {"SecretString": json.dumps(self.datos)}


def test_sin_secreto_id_no_hace_nada(monkeypatch):
    monkeypatch.delenv("SECRETO_ID", raising=False)
    assert cargar_secretos_aws(cliente=SecretsFalso({"X": "1"})) == 0


def test_carga_secretos_sin_pisar_variables(monkeypatch):
    monkeypatch.setenv("SECRETO_ID", "agente-ventas/prod")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "de-la-lambda")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CREDENTIALS_JSON", raising=False)
    cliente = SecretsFalso({"WHATSAPP_ACCESS_TOKEN": "del-secreto", "ANTHROPIC_API_KEY": "sk-x", "GOOGLE_CREDENTIALS_JSON": {"a": 1}})

    assert cargar_secretos_aws(cliente=cliente) == 2
    import os

    assert cliente.pedidos == ["agente-ventas/prod"]
    assert os.environ["WHATSAPP_ACCESS_TOKEN"] == "de-la-lambda"
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-x"
    assert json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"]) == {"a": 1}
    assert Config.desde_entorno().google_credentials_json == '{"a": 1}'


# --- Conversión del .env ---
ENV = {
    "WHATSAPP_ACCESS_TOKEN": "tok",
    "ANTHROPIC_API_KEY": "sk",
    "NUMERO_ASESOR": "573",
    "LLM_PROVIDER": "anthropic",
    "PORT": "5000",
    "AWS_REGION": "us-east-1",
    "OPENAI_API_KEY": "",
}


def test_variables_lambda_plan_gratuito():
    assert variables_lambda(ENV, sin_secretos=False, secreto_id=None) == {
        "WHATSAPP_ACCESS_TOKEN": "tok",
        "ANTHROPIC_API_KEY": "sk",
        "NUMERO_ASESOR": "573",
        "LLM_PROVIDER": "anthropic",
    }


def test_variables_lambda_plan_de_pago():
    assert variables_lambda(ENV, sin_secretos=True, secreto_id="agente-ventas/prod") == {
        "NUMERO_ASESOR": "573",
        "LLM_PROVIDER": "anthropic",
        "SECRETO_ID": "agente-ventas/prod",
    }


def test_secreto_incluye_credenciales_de_google(tmp_path):
    cred = tmp_path / "credentials.json"
    cred.write_text('{\n  "type": "service_account"\n}', encoding="utf-8")
    datos = secreto(ENV, cred)
    assert datos == {"WHATSAPP_ACCESS_TOKEN": "tok", "ANTHROPIC_API_KEY": "sk", "GOOGLE_CREDENTIALS_JSON": '{"type": "service_account"}'}


def test_env_de_ejemplo_cabe_en_lambda():
    env = {k: "x" * 210 for k in leer_env(".env.example")}  # cada valor del tamaño del token de WhatsApp
    variables = variables_lambda(env, sin_secretos=False, secreto_id=None)
    assert sum(len(k) + len(v) for k, v in variables.items()) < LIMITE_VARIABLES_LAMBDA * 2  # referencia de tamaño


# --- Eventos de Lambda (Function URL / API Gateway HTTP API, formato 2.0) ---
@pytest.fixture
def handler(deps):
    return Mangum(WsgiToAsgi(crear_app(deps)), lifespan="off")


def test_evento_health(handler):
    r = handler(leer_fixture("lambda/evento_health.json"), None)
    assert r["statusCode"] == 200
    assert json.loads(r["body"]) == {"ok": True, "modelo": "falso"}


def test_evento_verificacion_webhook(handler):
    evento = leer_fixture("lambda/evento_health.json")
    evento["rawPath"] = evento["requestContext"]["http"]["path"] = "/"
    evento["rawQueryString"] = "hub.mode=subscribe&hub.verify_token=token-prueba&hub.challenge=777"
    r = handler(evento, None)
    assert r["statusCode"] == 200 and r["body"] == "777"


def test_evento_mensaje_de_whatsapp(handler, deps):
    evento = leer_fixture("lambda/evento_health.json")
    evento["rawPath"] = evento["requestContext"]["http"]["path"] = "/"
    evento["requestContext"]["http"]["method"] = "POST"
    evento["body"] = json.dumps(leer_fixture("webhooks/texto.json"))
    # AWS siempre manda content-length en los POST; sin él Flask leería un cuerpo vacío
    evento["headers"]["content-length"] = str(len(evento["body"].encode("utf-8")))
    r = handler(evento, None)
    assert r["statusCode"] == 200
    assert "Bienvenido" in deps.mensajero.textos()[0]
