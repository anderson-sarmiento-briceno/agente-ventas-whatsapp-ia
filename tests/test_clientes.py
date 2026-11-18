import pytest

from agente_vendedor.clientes import es_telefono_valido, manejar_captura_datos_cliente, parece_nombre
from agente_vendedor.llm.falso import ProveedorFalso

from .conftest import CLIENTE


@pytest.mark.parametrize("digitos", ["3101234567", "6011234567", "4123456"])
def test_telefonos_validos(digitos):
    assert es_telefono_valido(digitos)


@pytest.mark.parametrize("digitos", ["44444", "2101234567", "31012345678", "601123456"])
def test_telefonos_invalidos(digitos):
    assert not es_telefono_valido(digitos)


@pytest.mark.parametrize("texto", ["Juan", "juan pérez", "María José Gómez", "Ana-María O'Neil"])
def test_nombres_validos(texto):
    assert parece_nombre(texto)


@pytest.mark.parametrize("texto", ["sí", "si", "ok", "no", "2", "juan 2", "a b", "", "me llamo juan pablo perez", "3101234567"])
def test_no_son_nombres(texto):
    assert not parece_nombre(texto)


def test_si_no_se_acepta_como_nombre(deps):
    e = estados("solicitando_nombre")
    manejar_captura_datos_cliente(deps, CLIENTE, "sí", e, {})
    assert e[CLIENTE]["estado"] == "solicitando_nombre"
    assert "nombre" not in e[CLIENTE]["cliente_info"]


def estados(estado, **extra):
    return {CLIENTE: {"estado": estado, "cliente_info": {}, "producto": {}, **extra}}


def test_ignora_estados_ajenos(deps):
    assert manejar_captura_datos_cliente(deps, CLIENTE, "hola", {CLIENTE: {"estado": "esperando_busqueda"}}, {}) is False


def test_nombre_demasiado_largo_se_vuelve_a_pedir(deps):
    e = estados("solicitando_nombre")
    assert manejar_captura_datos_cliente(deps, CLIENTE, "me llamo juan pablo perez", e, {})
    assert e[CLIENTE]["estado"] == "solicitando_nombre"
    assert "nombre completo" in deps.mensajero.ultimo_texto()


def test_pregunta_mientras_se_pide_el_telefono(deps):
    deps.llm = ProveedorFalso(lambda m: "True" if m[0]["role"] == "system" else "Abrimos a las 8:00 ⏰")
    e = estados("solicitando_telefono", cliente_info={"nombre": "Ana"})
    manejar_captura_datos_cliente(deps, CLIENTE, "¿a qué hora abren?", e, {})
    assert deps.mensajero.textos() == ["Abrimos a las 8:00 ⏰", "📞 Por favor escribe tu *número de celular*, Ana."]
    assert e[CLIENTE]["estado"] == "solicitando_telefono"


def test_texto_no_numerico_en_telefono(deps):
    e = estados("solicitando_telefono", cliente_info={"nombre": "Ana"})
    manejar_captura_datos_cliente(deps, CLIENTE, "mañana te lo paso", e, {})
    assert deps.mensajero.ultimo_texto().startswith("🤔 No entendí tu respuesta, Ana.")
