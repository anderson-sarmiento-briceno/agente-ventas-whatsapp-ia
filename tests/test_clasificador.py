import pytest

from agente_vendedor.clasificador import RESPUESTA_RESPALDO, es_pregunta_general, responder_fuera_de_flujo
from agente_vendedor.llm.falso import ProveedorFalso


@pytest.mark.parametrize("texto", ["1", "12", "0", "sí", "No", "ok", "gracias", "3101234567", "mi numero es 6011234"])
def test_atajos_no_llaman_al_llm(texto):
    llm = ProveedorFalso(lambda _m: "True")
    assert es_pregunta_general(texto, llm) is False
    assert llm.llamadas == []


@pytest.mark.parametrize("salida, esperado", [("True", True), (" true\n", True), ("False", False), ("quizá", False)])
def test_interpreta_la_salida_del_llm(salida, esperado):
    llm = ProveedorFalso(lambda _m: salida)
    assert es_pregunta_general("¿Dónde están ubicados?", llm) is esperado


def test_el_prompt_incluye_el_mensaje_en_minusculas():
    llm = ProveedorFalso(lambda _m: "False")
    es_pregunta_general("Tienen Envíos", llm)
    sistema, usuario = llm.llamadas[0]
    assert "clasificador binario" in sistema["content"]
    assert '"tienen envíos"' in usuario["content"]
    assert "{{texto}}" not in usuario["content"]


def test_error_del_llm_se_trata_como_busqueda():
    assert es_pregunta_general("¿tienen envíos?", ProveedorFalso(fallar=True)) is False


def test_respuesta_usa_el_documento_del_negocio():
    llm = ProveedorFalso(lambda _m: "Atendemos hasta las 19:00 horas ⏰")
    assert responder_fuera_de_flujo("¿horario?", llm) == "Atendemos hasta las 19:00 horas ⏰"
    prompt = llm.llamadas[0][0]["content"]
    assert "Calle 6 #94A-26" in prompt
    assert "¿horario?" in prompt
    assert "{{" not in prompt


def test_respuesta_de_respaldo_si_el_llm_falla():
    assert responder_fuera_de_flujo("¿horario?", ProveedorFalso(fallar=True)) == RESPUESTA_RESPALDO
