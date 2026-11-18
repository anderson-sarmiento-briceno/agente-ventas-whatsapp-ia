import pytest

from agente_vendedor.busqueda import (
    buscar_producto_fuzzy,
    buscar_producto_gpt,
    es_palabra_irrelevante,
    extraer_cantidad_y_limpiar_keyword,
)
from agente_vendedor.llm.falso import ProveedorFalso, es_busqueda_catalogo

from .conftest import leer_fixture

INVENTARIO = leer_fixture("inventario.json")


def nombres(resultados):
    return [r["item"]["servicio"] for r in resultados]


@pytest.mark.parametrize(
    "consulta, esperado",
    [
        ("quiero 2 guantes rojos", (2, "guantes rojos")),
        ("necesito por favor un casco integral", (1, "casco integral")),
        ("Buenas tardes, espejos", (1, "espejos")),  # "tardes," se reconoce como saludo aunque tenga coma
        ("10 rodilleras", (10, "rodilleras")),
        ("quiero", (1, "")),
    ],
)
def test_extraer_cantidad_y_limpiar_keyword(consulta, esperado):
    assert extraer_cantidad_y_limpiar_keyword(consulta) == esperado


@pytest.mark.parametrize("palabra", ["quiero", "necesito", "necesit", "precio", "cuanto"])
def test_palabras_de_relleno_son_irrelevantes(palabra):
    assert es_palabra_irrelevante(palabra)


@pytest.mark.parametrize("palabra", ["guantes", "casco", "rojo", "negro", "espejos"])
def test_palabras_de_producto_y_colores_son_relevantes(palabra):
    assert not es_palabra_irrelevante(palabra)


def test_busqueda_exige_todas_las_palabras():
    assert nombres(buscar_producto_fuzzy("guantes rojos", INVENTARIO)) == ["Guantes protección moto rojos talla M"]


def test_busqueda_tolera_errores_de_tipeo():
    assert nombres(buscar_producto_fuzzy("cazco integral", INVENTARIO)) == ["Casco integral negro mate"]


def test_busqueda_devuelve_varios_resultados():
    assert len(buscar_producto_fuzzy("guantes", INVENTARIO)) == 2


def test_consulta_vacia_no_busca():
    assert buscar_producto_fuzzy("quiero por favor", INVENTARIO) == []


def test_sin_llm_y_sin_coincidencias_devuelve_vacio():
    assert buscar_producto_fuzzy("botas", INVENTARIO) == []


def test_sin_coincidencias_usa_sugerencias_del_llm():
    def responder(mensajes):
        catalogo = mensajes[0]["content"]
        return "Casco abatible blanco, Producto Inventado" if "Casco abatible blanco" in catalogo else ""

    llm = ProveedorFalso(responder)
    resultados = buscar_producto_fuzzy("protección para la cabeza", INVENTARIO, llm)

    assert nombres(resultados) == ["Casco abatible blanco"]
    assert all(es_busqueda_catalogo(m) for m in llm.llamadas)


def test_busqueda_gpt_no_duplica_y_respeta_top_n():
    llm = ProveedorFalso(lambda _m: "Espejos retrovisores redondos, espejos retrovisores redondos")
    resultados = buscar_producto_gpt("retrovisor", INVENTARIO, llm, top_n=1)
    assert nombres(resultados) == ["Espejos retrovisores redondos"]


def test_busqueda_gpt_envia_el_catalogo_completo_en_una_llamada():
    llm = ProveedorFalso(lambda _m: "Espejos retrovisores redondos")
    buscar_producto_gpt("retrovisor", INVENTARIO, llm)
    assert len(llm.llamadas) == 1
    prompt = llm.llamadas[0][0]["content"]
    assert all(item["servicio"] in prompt for item in INVENTARIO)


def test_busqueda_gpt_respeta_ninguno():
    assert buscar_producto_gpt("pizza", INVENTARIO, ProveedorFalso(lambda _m: "NINGUNO")) == []


def test_busqueda_gpt_sobrevive_a_errores_del_llm():
    assert buscar_producto_fuzzy("botas", INVENTARIO, ProveedorFalso(fallar=True)) == []
