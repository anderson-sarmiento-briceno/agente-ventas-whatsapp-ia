"""Configuración, cliente de WhatsApp y utilidades de Google Sheets (sin red)."""
import requests

from agente_vendedor.config import Config, cargar_env_local
from agente_vendedor.tienda.google import escapar_query_drive, fila_desde_rango, filas_a_productos
from agente_vendedor.tienda.memoria import TiendaMemoria
from agente_vendedor.whatsapp.cloud_api import ClienteWhatsApp


# --- config ---
def test_config_desde_entorno(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "abc")
    monkeypatch.setenv("ASESORES_AUTORIZADOS", "573001, 573002 ,")
    monkeypatch.setenv("PAUSA_MEDIA_SEG", "0.5")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    c = Config.desde_entorno()
    assert c.whatsapp_access_token == "abc"
    assert c.asesores_autorizados == {"573001", "573002"}
    assert c.pausa_media_seg == 0.5
    assert c.openai_model == "gpt-4o-mini"
    assert c.puede_cerrar_ventas("573001") and not c.puede_cerrar_ventas("999")


def test_faltantes():
    assert "OPENAI_API_KEY" in Config().faltantes()  # sin claves: se asume openai
    assert "ANTHROPIC_API_KEY" in Config(llm_provider="anthropic").faltantes()
    assert Config().puede_cerrar_ventas("cualquiera")


def test_cargar_env_local_no_pisa_variables(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('# comentario\nVAR_A=uno  # nota\nVAR_B="dos # no es comentario"\nVAR_C=tres\n', encoding="utf-8")
    monkeypatch.setenv("VAR_C", "existente")
    for v in ("VAR_A", "VAR_B"):
        monkeypatch.delenv(v, raising=False)
    assert cargar_env_local(env)
    import os

    assert os.environ["VAR_A"] == "uno"
    assert os.environ["VAR_B"] == "dos # no es comentario"
    assert os.environ["VAR_C"] == "existente"
    assert cargar_env_local(tmp_path / "no-existe") is False


# --- WhatsApp ---
class SesionFalsa:
    def __init__(self, status=200, error=None):
        self.status, self.error, self.llamadas = status, error, []

    def post(self, url, headers, json, timeout):
        self.llamadas.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if self.error:
            raise self.error
        r = requests.Response()
        r.status_code = self.status
        r._content = b'{"error": "x"}'
        return r


def test_whatsapp_payloads():
    sesion = SesionFalsa()
    c = ClienteWhatsApp(Config(whatsapp_access_token="tok", whatsapp_phone_number_id="123"), sesion)
    c.enviar_texto("573", "hola")
    c.enviar_media("573", "https://x/img", "video", "pie")
    c.enviar_documento("573", "https://x/doc.pdf", "doc.pdf", "catálogo")

    texto, media, doc = sesion.llamadas
    assert texto["url"] == "https://graph.facebook.com/v18.0/123/messages"
    assert texto["headers"]["Authorization"] == "Bearer tok"
    assert texto["json"]["text"] == {"body": "hola"}
    assert media["json"]["video"] == {"link": "https://x/img", "caption": "pie"}
    assert doc["json"]["document"]["filename"] == "doc.pdf" and doc["timeout"] == 15


def test_whatsapp_errores_no_se_propagan():
    config = Config(whatsapp_access_token="tok", whatsapp_phone_number_id="1")
    ClienteWhatsApp(config, SesionFalsa(status=401)).enviar_texto("1", "x")
    ClienteWhatsApp(config, SesionFalsa(error=requests.exceptions.Timeout())).enviar_texto("1", "x")
    ClienteWhatsApp(config, SesionFalsa(error=requests.exceptions.ConnectionError())).enviar_texto("1", "x")


# --- Google Sheets ---
def test_filas_a_productos():
    valores = [[" numero ", "servicio", "unidades"], ["A1", " Casco ", "2"], ["B2", "Guantes"], []]
    assert filas_a_productos(valores) == [
        {"numero": "A1", "servicio": "Casco", "unidades": "2"},
        {"numero": "B2", "servicio": "Guantes", "unidades": ""},
        {"numero": "", "servicio": "", "unidades": ""},
    ]
    assert filas_a_productos([["solo encabezado"]]) == []


def test_fila_desde_rango():
    assert fila_desde_rango("registro_ventas!A12:J12") == 12
    assert fila_desde_rango("'hoja con espacios'!A7:K7") == 7
    assert fila_desde_rango("") is None


def test_escapar_query_drive():
    assert escapar_query_drive("O'Neil") == "O\\'Neil"


def test_tienda_memoria_registro_y_actualizacion():
    t = TiendaMemoria([{"numero": "A", "unidades": "1"}])
    fila = t.registrar_venta(["fecha", "x"])
    assert fila == 2
    t.actualizar_venta(fila, 11, 500.0)
    assert t.ventas[1][10] == 500.0
    t.actualizar_unidades(2, 0)
    assert t.inventario()[0]["unidades"] == "0"
