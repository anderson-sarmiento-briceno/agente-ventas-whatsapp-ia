"""Proveedores LLM y su selección (sin red: el cliente de Anthropic se reemplaza por uno falso)."""
from types import SimpleNamespace

import pytest

from agente_vendedor.clasificador import es_pregunta_general
from agente_vendedor.config import Config
from agente_vendedor.llm import ErrorLLM, crear_proveedor_llm
from agente_vendedor.llm.anthropic_provider import ProveedorAnthropic, separar_sistema


def respuesta(*textos, stop_reason="end_turn"):
    bloques = [SimpleNamespace(type="thinking", thinking="")] + [SimpleNamespace(type="text", text=t) for t in textos]
    return SimpleNamespace(content=bloques, stop_reason=stop_reason)


class ClienteFalso:
    def __init__(self, resultado=None, error=None):
        self.resultado, self.error, self.llamadas = resultado, error, []
        self.messages = self

    def create(self, **parametros):
        self.llamadas.append(parametros)
        if self.error:
            raise self.error
        return self.resultado


def test_separar_sistema():
    sistema, conversacion = separar_sistema(
        [{"role": "system", "content": "A"}, {"role": "user", "content": "hola"}, {"role": "system", "content": "B"}]
    )
    assert sistema == "A\n\nB"
    assert conversacion == [{"role": "user", "content": "hola"}]


def test_parametros_enviados_a_claude():
    cliente = ClienteFalso(respuesta(" True "))
    llm = ProveedorAnthropic("clave", cliente=cliente)
    texto = llm.completar(
        [{"role": "system", "content": "clasificador"}, {"role": "user", "content": "¿horario?"}],
        max_tokens=5,
        temperature=0.0,
    )
    assert texto == "True"
    [p] = cliente.llamadas
    assert p["model"] == "claude-haiku-5-5"
    assert p["system"] == "clasificador"
    assert p["messages"] == [{"role": "user", "content": "¿horario?"}]
    assert p["max_tokens"] == 5
    assert p["thinking"] == {"type": "disabled"}
    assert p["output_config"] == {"effort": "low"}
    assert "temperature" not in p  # Haiku 5.5 la rechaza


def test_sin_mensaje_de_sistema_no_envia_system():
    cliente = ClienteFalso(respuesta("hola"))
    ProveedorAnthropic("clave", cliente=cliente).completar([{"role": "user", "content": "x"}], max_tokens=10, temperature=0.7)
    assert "system" not in cliente.llamadas[0]


def test_une_varios_bloques_de_texto():
    llm = ProveedorAnthropic("clave", cliente=ClienteFalso(respuesta("Hola ", "mundo")))
    assert llm.completar([{"role": "user", "content": "x"}], max_tokens=10, temperature=0) == "Hola mundo"


def test_negativa_del_modelo_es_error():
    llm = ProveedorAnthropic("clave", cliente=ClienteFalso(respuesta(stop_reason="refusal")))
    with pytest.raises(ErrorLLM, match="refusal"):
        llm.completar([{"role": "user", "content": "x"}], max_tokens=10, temperature=0)


def test_errores_del_sdk_se_traducen():
    anthropic = pytest.importorskip("anthropic")
    import httpx2

    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    llm = ProveedorAnthropic("clave", cliente=ClienteFalso(error=error))
    with pytest.raises(ErrorLLM, match="error de conexión"):
        llm.completar([{"role": "user", "content": "x"}], max_tokens=10, temperature=0)


def test_clasificador_funciona_con_claude():
    llm = ProveedorAnthropic("clave", cliente=ClienteFalso(respuesta("True")))
    assert es_pregunta_general("¿dónde están ubicados?", llm) is True


# --- selección del proveedor ---
@pytest.mark.parametrize(
    "config, esperado",
    [
        (Config(anthropic_api_key="a", openai_api_key="o"), "anthropic"),
        (Config(openai_api_key="o"), "openai"),
        (Config(llm_provider="openai", anthropic_api_key="a", openai_api_key="o"), "openai"),
        (Config(llm_provider="anthropic", anthropic_api_key="a"), "anthropic"),
    ],
)
def test_proveedor_elegido(config, esperado):
    assert config.proveedor_llm == esperado
    assert crear_proveedor_llm(config).modelo == ("claude-haiku-5-5" if esperado == "anthropic" else "gpt-4o-mini")


def test_falta_la_clave_del_proveedor_elegido():
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        crear_proveedor_llm(Config(llm_provider="anthropic", openai_api_key="o"))
    assert "ANTHROPIC_API_KEY" in Config(llm_provider="anthropic").faltantes()
    assert "OPENAI_API_KEY" not in Config(llm_provider="anthropic").faltantes()


def test_proveedor_desconocido():
    with pytest.raises(ValueError, match="no soportado"):
        crear_proveedor_llm(Config(llm_provider="gemini"))
