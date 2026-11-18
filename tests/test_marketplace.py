import pytest
import requests

from agente_vendedor.marketplace import es_enlace_marketplace, extraer_titulo_marketplace, titulo_desde_html

from .conftest import leer_fixture


class RespuestaFalsa:
    def __init__(self, texto, url="https://www.facebook.com/marketplace/item/1", status=200):
        self.text, self.url, self.status_code = texto, url, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


class HttpFalso:
    def __init__(self, respuesta=None, error=None):
        self.respuesta, self.error = respuesta, error

    def get(self, url, headers, timeout):
        if self.error:
            raise self.error
        return self.respuesta


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("https://www.facebook.com/marketplace/item/1", True),
        ("https://m.facebook.com/marketplace/item/1", True),
        ("https://facebook.com/otra", False),
        ("guantes", False),
    ],
)
def test_es_enlace_marketplace(texto, esperado):
    assert es_enlace_marketplace(texto) is esperado


def test_titulo_desde_og_title():
    assert titulo_desde_html(leer_fixture("marketplace/publicacion.html")) == "Casco integral negro mate"


def test_titulo_desde_etiqueta_title():
    html = "<html><head><title>Espejos retrovisores | Facebook Marketplace</title></head></html>"
    assert titulo_desde_html(html) == "Espejos retrovisores"


def test_pagina_de_login_no_da_titulo():
    assert titulo_desde_html(leer_fixture("marketplace/login.html")) is None


def test_extraer_titulo_ok():
    http = HttpFalso(RespuestaFalsa(leer_fixture("marketplace/publicacion.html")))
    assert extraer_titulo_marketplace("https://www.facebook.com/marketplace/item/1", http=http) == "Casco integral negro mate"


def test_redireccion_a_checkpoint():
    http = HttpFalso(RespuestaFalsa("<html></html>", url="https://www.facebook.com/checkpoint/123"))
    assert extraer_titulo_marketplace("https://www.facebook.com/marketplace/item/1", http=http) is None


def test_error_de_red():
    http = HttpFalso(error=requests.exceptions.ConnectionError("sin red"))
    assert extraer_titulo_marketplace("u", http=http) is None
    assert extraer_titulo_marketplace("u", reportar_error=True, http=http).startswith("❌ Error al extraer título")
