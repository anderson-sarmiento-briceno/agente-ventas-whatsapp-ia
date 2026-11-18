"""Conversaciones completas contra la máquina de estados, con dobles en memoria."""
from agente_vendedor.agente import MSG_ES_ESTE, MSG_PEDIR_NOMBRE, PROCESANDO, procesar_mensaje
from agente_vendedor.llm.falso import ProveedorFalso, es_clasificacion, respuesta_por_defecto

from .conftest import CLIENTE


def test_usuario_nuevo_recibe_bienvenida_y_catalogo(chat, deps):
    respuestas = chat("hola")
    assert "Bienvenido a *Accesorios MotoPro*" in respuestas[0]
    [documento] = [e for e in deps.mensajero.enviados if e.tipo == "document"]
    assert documento.nombre_archivo == "Catalogo_MotoPro.pdf"
    assert chat.estado == "esperando_busqueda"


def test_sin_catalogo_avisa(chat, tienda):
    tienda.catalogo = None
    assert chat("hola")[-1] == "🔍 Pronto tendremos nuestro catálogo disponible para ti."


def test_un_resultado_muestra_fotos_ficha_y_pregunta(chat, deps):
    chat("hola")
    deps.mensajero.limpiar()
    respuestas = chat("guantes rojos")

    tipos = [e.tipo for e in deps.mensajero.enviados]
    assert tipos == ["image", "video", "text", "text"]
    assert deps.mensajero.enviados[0].contenido == "https://drive.google.com/uc?id=drv-gpmr-foto&export=download"
    assert respuestas[0].startswith("✅ Guantes protección moto rojos talla M")
    assert respuestas[1] == MSG_ES_ESTE
    assert chat.estado == "confirmando_producto"
    assert chat.usuario["ultimo_producto"]["numero"] == "GPMR01"


def test_varios_resultados_y_seleccion(chat):
    chat("hola")
    [lista] = chat("guantes")
    assert "1. Guantes protección moto rojos talla M" in lista
    assert chat.estado == "seleccionando"
    assert chat.usuario["termino_busqueda_actual"] == "guantes"

    assert chat("9") == ["⚠️ Número inválido. Por favor elige un número de la lista."]
    assert chat("dos") == ["⚠️ Por favor ingresa solo números."]
    assert chat.estado == "seleccionando"

    respuestas = chat("2")
    assert respuestas[0].startswith("✅ Guantes protección moto negros talla L")
    assert chat.estado == "confirmando_producto"


def test_cancelar_seleccion_borra_el_contexto(chat, deps):
    chat("hola")
    chat("guantes")
    assert chat("0") == ["❌ Búsqueda cancelada"]
    assert CLIENTE not in deps.contexto.datos


def test_producto_agotado_y_sin_resultados(chat):
    chat("hola")
    assert chat("casco abatible") == ["⚠️ El producto está registrado pero no hay unidades disponibles."]
    assert chat("botas de cuero") == ["❌ No encontré productos que coincidan. Escribe *nombre de otro producto*"]
    assert chat.estado == "esperando_busqueda"


def test_texto_corto_pide_mas_caracteres(chat):
    chat("hola")
    assert chat("ab") == ["📝 Escribe al menos 3 caracteres para buscar un producto."]


def test_no_es_el_producto_vuelve_a_buscar(chat):
    chat("hola")
    chat("guantes rojos")
    assert chat("tal vez") == ["❓ Por favor responde solo con *sí* o *no*."]
    assert chat("no") == ["🔄 Por favor escribe nuevamente lo que estás buscando con más características."]
    assert chat.estado == "esperando_busqueda"


def test_compra_completa_y_cierre_por_el_asesor(chat, chat_asesor, deps, tienda):
    chat("hola")
    chat("guantes rojos")
    assert chat("sí") == [MSG_PEDIR_NOMBRE]
    assert chat("juan pérez") == ["✅ Gracias juan. Ahora, por favor escribe tu *número de celular*."]
    assert chat("12345")[0].startswith("⚠️ Lo siento Juan Pérez, el número *12345*")
    assert chat("310 1234567") == ["📍 Finalmente, escribe tu *dirección de entrega*."]
    [confirmacion] = chat("Calle 1 # 2-3")
    assert "¡Gracias por tu pedido, Juan Pérez!" in confirmacion
    assert chat.estado is None

    # El asesor recibe el pedido con el código y queda registrado como pendiente
    aviso = deps.mensajero.ultimo_texto(chat_asesor.numero)
    assert "*Nombre:* Juan Pérez" in aviso and "*Celular (escrito por cliente):* 3101234567" in aviso
    codigo = aviso.rsplit("*Código de cierre:* ", 1)[1]
    venta = tienda.ventas[-1]
    assert venta[1:9] == ["Juan Pérez", "3101234567", "Calle 1 # 2-3", "Guantes protección moto rojos talla M", "GPMR01", 1, chat_asesor.numero, codigo]
    assert venta[9] == "pendiente"
    assert codigo in deps.contexto.obtener(CLIENTE)["codigos_venta_data"]

    # Cierre de venta
    assert chat_asesor("Cerrar venta") == ["🔐 Por favor, escribe el *código de venta* que deseas cerrar."]
    assert chat_asesor(codigo.lower()) == ["✏️ Ingresa la *cantidad vendida*: "]
    assert chat_asesor("cero") == ["⚠️ Por favor ingresa una cantidad válida (número entero positivo)."]
    [cierre] = chat_asesor("2")
    assert cierre.startswith("✅ Venta cerrada correctamente!")
    assert "💲 Precio Final: $90,000.00" in cierre
    assert tienda.productos[0]["unidades"] == "3"
    assert tienda.ventas[-1][6] == 2 and tienda.ventas[-1][9] == "completado" and tienda.ventas[-1][10] == 90000.0

    # Repetir el cierre no descuenta dos veces
    chat_asesor("cerrar venta")
    chat_asesor(codigo)
    assert chat_asesor("1") == ["⚠️ Esta venta ya fue cerrada anteriormente"]
    assert tienda.productos[0]["unidades"] == "3"
    assert chat_asesor.estado is None


def test_cierre_con_codigo_inexistente_sale_del_flujo(chat_asesor):
    chat_asesor("cerrar venta")
    chat_asesor("XXXXXX")
    assert chat_asesor("1") == ["❌ Código no encontrado en el registro de ventas"]
    assert chat_asesor.estado is None


def test_cierre_restringido_a_asesores_autorizados(deps, chat):
    from dataclasses import replace

    deps.config = replace(deps.config, asesores_autorizados=frozenset({"573000000099"}))
    chat("hola")
    assert "código de venta" not in " ".join(chat("cerrar venta"))
    assert chat.estado != "esperando_codigo"


def test_pregunta_general_en_medio_de_la_compra_y_retomar(deps, chat):
    preguntas = {"¿tienen envíos a medellín?"}

    def responder(mensajes):
        if es_clasificacion(mensajes):
            return "True" if any(p in mensajes[1]["content"] for p in preguntas) else "False"
        return respuesta_por_defecto(mensajes)

    deps.llm = ProveedorFalso(responder)
    chat("hola")
    chat("guantes rojos")

    respuesta, oferta = chat("¿Tienen envíos a Medellín?")
    assert respuesta.startswith("¡Hola! 😊")
    assert oferta == "¿Deseas continuar con la compra de Guantes protección moto rojos talla M? Responde *sí* o *no*."
    assert chat.estado == "confirmando_continuacion"

    assert chat("si") == [MSG_PEDIR_NOMBRE]
    assert chat.estado == "solicitando_nombre"
    assert chat.usuario["producto"]["numero"] == "GPMR01"


def test_pregunta_general_sin_compra_en_curso(deps, chat):
    deps.llm = ProveedorFalso(lambda m: "True" if es_clasificacion(m) else respuesta_por_defecto(m))
    chat("hola")
    respuestas = chat("¿dónde están ubicados?")
    # Igual que la versión original: se responde la pregunta y se sigue esperando la búsqueda.
    assert respuestas == ["¡Hola! 😊 Atendemos de lunes a viernes de 8:00 a 19:00 horas."]
    assert chat.estado == "esperando_busqueda"


def test_rechazar_continuacion(deps, chat):
    def responder(m):
        if es_clasificacion(m):
            return "True" if '"¿cuál es el horario?"' in m[1]["content"] else "False"
        return respuesta_por_defecto(m)

    deps.llm = ProveedorFalso(responder)
    chat("hola")
    chat("guantes")
    chat("¿cuál es el horario?")
    assert chat.estado == "confirmando_continuacion"
    assert chat("quizás") == ["❓ Por favor responde solo con *sí* o *no*."]
    assert chat("no") == ["🔄 Puedes buscar otro producto escribiendo lo que necesitas"]
    assert chat.estado == "esperando_busqueda"


def test_enlace_de_marketplace_busca_por_titulo(deps, chat):
    deps.extraer_titulo = lambda url: "Casco integral negro mate"
    chat("hola")
    respuestas = chat("https://www.facebook.com/marketplace/item/123/")
    assert respuestas[0] == "🔍 Buscando producto: *Casco integral negro mate*"
    assert respuestas[1].startswith("✅ Casco integral negro mate tiene un precio unitario de: $280.000")


def test_enlace_de_marketplace_ilegible(chat):
    assert chat("https://m.facebook.com/marketplace/item/1") == [
        "⚠️ No pude obtener información del producto. Por favor, escribe el nombre del producto."
    ]


def test_mensaje_tardio_solo_avisa(deps):
    deps.reloj = lambda: 10.0
    assert procesar_mensaje(deps, CLIENTE, "hola", inicio=0.0) == PROCESANDO
    assert deps.mensajero.textos() == ["⏳ Estoy procesando tu mensaje..."]


def test_error_inesperado_responde_y_no_lanza(deps, chat):
    chat("hola")

    def romper(*_a, **_k):
        raise RuntimeError("Sheets caído")

    deps.tienda.inventario = romper
    assert chat("guantes") == ["⚠️ Error temporal al acceder al sistema. Por favor intenta en 1 minuto."]


def test_contexto_viejo_corrupto_reinicia(deps, chat):
    deps.contexto.datos[CLIENTE] = "{no es json"
    assert "Bienvenido" in chat("hola")[0]
