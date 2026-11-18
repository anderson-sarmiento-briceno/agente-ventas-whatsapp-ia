import pytest

from agente_vendedor.inventario import (
    ERROR_INVENTARIO,
    ERROR_SIN_COINCIDENCIAS,
    ERROR_SIN_STOCK,
    a_entero,
    a_precio,
    buscar_y_verificar_inventario,
    formatear_resultados,
    formatear_seleccion_whatsapp,
    obtener_archivos_asociados,
    producto_por_numero,
)

from .conftest import leer_fixture

INVENTARIO = leer_fixture("inventario.json")


def test_producto_con_stock():
    [r] = buscar_y_verificar_inventario("guantes rojos", INVENTARIO)
    assert r["numero"] == "GPMR01"
    assert r["unidades"] == 5
    assert r["precio"] == "45000"


def test_producto_agotado():
    assert buscar_y_verificar_inventario("casco abatible", INVENTARIO) == [{"error": ERROR_SIN_STOCK}]


def test_unidades_vacias_cuentan_como_agotado():
    assert buscar_y_verificar_inventario("impermeable dos piezas", INVENTARIO) == [{"error": ERROR_SIN_STOCK}]


def test_sin_coincidencias():
    assert buscar_y_verificar_inventario("botas", INVENTARIO) == [{"error": ERROR_SIN_COINCIDENCIAS}]


def test_inventario_vacio():
    assert buscar_y_verificar_inventario("guantes", []) == [{"error": ERROR_INVENTARIO}]


def test_acepta_filas_crudas_con_encabezado():
    filas = [["numero", "servicio", "unidades", "precio"], ["X1", "Casco rojo", "1", "10"]]
    [r] = buscar_y_verificar_inventario("casco rojo", filas)
    assert r["numero"] == "X1"


def test_formatear_resultados():
    [r] = buscar_y_verificar_inventario("guantes rojos", INVENTARIO)
    assert formatear_resultados([r]) == (
        "✅ Guantes protección moto rojos talla M tiene un precio unitario de: $45000\n"
        "📝 Guantes con protección en nudillos, transpirables."
    )
    assert formatear_resultados([{"error": "x"}]) == "x"
    assert formatear_resultados([]) == "❌ No se encontraron resultados"


def test_formatear_seleccion():
    resultados = buscar_y_verificar_inventario("guantes", INVENTARIO)
    mensaje = formatear_seleccion_whatsapp(resultados)
    assert "1. Guantes protección moto rojos talla M - ✅ Disponible" in mensaje
    assert "2. Guantes protección moto negros talla L - ✅ Disponible" in mensaje
    assert mensaje.endswith("0. Cancelar búsqueda")


def test_archivos_asociados_imagenes_primero(tienda):
    archivos = obtener_archivos_asociados("GPMR01", tienda)
    assert [a["name"] for a in archivos] == ["GPMR01-frente.jpg", "GPMR01-video.mp4"]
    assert obtener_archivos_asociados("0", tienda) == []
    assert obtener_archivos_asociados("", tienda) == []


@pytest.mark.parametrize(
    "valor, esperado",
    [("45000", 45000), ("45.000", 45000), ("$ 280.000", 280000), ("1.250,50", 1250.5), ("45,000", 45000), ("12.5", 12.5), (60000, 60000)],
)
def test_a_precio(valor, esperado):
    assert a_precio(valor) == esperado


def test_a_precio_invalido():
    with pytest.raises(ValueError):
        a_precio("")


@pytest.mark.parametrize("valor, esperado", [("5", 5), ("", 0), (None, 0), ("abc", 0), ("3.0", 3)])
def test_a_entero(valor, esperado):
    assert a_entero(valor) == esperado


def test_producto_por_numero_devuelve_fila_de_la_hoja():
    fila, item = producto_por_numero(INVENTARIO, "CINT01")
    assert fila == 4  # encabezado en la fila 1
    assert item["servicio"] == "Casco integral negro mate"
    assert producto_por_numero(INVENTARIO, "NOEXISTE") is None
