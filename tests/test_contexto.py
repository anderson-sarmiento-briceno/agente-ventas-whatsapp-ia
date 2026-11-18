from decimal import Decimal

from agente_vendedor.contexto.dynamodb import ContextoDynamoDB
from agente_vendedor.contexto.memoria import ContextoMemoria
from agente_vendedor.contexto.serializacion import deserializar, serializar


class TablaFalsa:
    def __init__(self):
        self.items = {}
        self.fallar = False

    def get_item(self, Key):
        if self.fallar:
            raise RuntimeError("DynamoDB caído")
        item = self.items.get(Key["whatsapp_number"])
        return {"Item": item} if item else {}

    def put_item(self, Item):
        if self.fallar:
            raise RuntimeError("DynamoDB caído")
        self.items[Item["whatsapp_number"]] = Item

    def delete_item(self, Key):
        self.items.pop(Key["whatsapp_number"], None)


class RecursoFalso:
    def __init__(self):
        self.tabla = TablaFalsa()

    def Table(self, nombre):
        self.nombre = nombre
        return self.tabla


def test_serializacion_con_decimales():
    contexto = {"precio": 12.5, "lista": [1.1, {"x": Decimal("2.5")}], "texto": "ñ"}
    recuperado = deserializar(serializar(contexto))
    assert recuperado == {"precio": Decimal("12.5"), "lista": [Decimal("1.1"), {"x": Decimal("2.5")}], "texto": "ñ"}


def test_deserializar_valores_invalidos():
    assert deserializar("{roto") == {}
    assert deserializar("[1, 2]") == {}
    assert deserializar(42) == {}
    assert deserializar({"a": 1.5}) == {"a": Decimal("1.5")}


def test_dynamodb_guarda_json_con_ttl():
    recurso = RecursoFalso()
    almacen = ContextoDynamoDB("tabla_prueba", ttl_seg=100, recurso=recurso, reloj=lambda: 1000.0)
    almacen.guardar("57300", {"estado_usuarios_data": {"57300": {"estado": "seleccionando"}}})

    item = recurso.tabla.items["57300"]
    assert recurso.nombre == "tabla_prueba"
    assert item["expire_at"] == 1100
    assert isinstance(item["context"], str)
    assert almacen.obtener("57300")["estado_usuarios_data"]["57300"]["estado"] == "seleccionando"

    almacen.eliminar("57300")
    assert almacen.obtener("57300") == {}


def test_dynamodb_errores_no_se_propagan():
    recurso = RecursoFalso()
    almacen = ContextoDynamoDB("t", recurso=recurso)
    recurso.tabla.fallar = True
    assert almacen.obtener("1") == {}
    almacen.guardar("1", {"a": 1})  # no lanza
    almacen.guardar("1", ["no", "dict"])  # se descarta


def test_memoria_estado():
    m = ContextoMemoria()
    m.guardar("1", {"estado_usuarios_data": {"1": {"estado": "x"}}})
    assert m.estado("1") == "x"
    assert m.estado("2") is None
