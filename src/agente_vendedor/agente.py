"""Ciclo de conversación del vendedor (máquina de estados por usuario).

Estados:
    (sin estado)              -> bienvenida + catálogo
    esperando_busqueda        -> el cliente escribe qué busca
    seleccionando             -> eligió de una lista de varios resultados
    confirmando_producto      -> "¿Este es el producto?" sí/no
    confirmando_continuacion  -> tras una pregunta general: "¿continuar con la compra?"
    solicitando_nombre / solicitando_telefono / solicitando_direccion  (clientes.py)
    esperando_codigo / esperando_cantidad                              (ventas.py, asesor)

El contexto se guarda en `AlmacenContexto` con la forma
`{"estado_usuarios_data": {numero: {...}}, "codigos_venta_data": {...}}` (compatible con la versión anterior).
"""
from __future__ import annotations

import logging

from .clasificador import es_pregunta_general, responder_fuera_de_flujo
from .clientes import manejar_captura_datos_cliente
from .dependencias import Dependencias
from .inventario import (
    buscar_y_verificar_inventario,
    formatear_resultados,
    formatear_seleccion_whatsapp,
    obtener_archivos_asociados,
    url_descarga_drive,
)
from .marketplace import es_enlace_marketplace
from .ventas import manejar_cierre_venta

log = logging.getLogger(__name__)

OK = "ok"
PROCESANDO = "processing"

AFIRMACIONES = {"sí", "si", "s", "yes", "ok", "okay"}
NEGACIONES = {"no", "n"}

# Límites de tiempo (segundos) para no exceder el timeout del webhook
T_AVISO = 4.0  # si ya pasó este tiempo antes de empezar, solo se avisa "procesando"
T_ERROR = 2.8  # los mensajes de error solo se envían si aún hay margen
T_PREGUNTA = 7.0  # tiempo máximo para empezar a responder una pregunta general / selección
T_RESULTADOS = 15.0  # tiempo máximo para mostrar resultados de búsqueda

ESTADOS_CON_INVENTARIO = {"esperando_busqueda", "seleccionando", "confirmando_producto"}

MSG_PEDIR_NOMBRE = "📝 Por favor escribe tu *nombre completo* (nombre y apellido) para continuar con el pedido."
MSG_ES_ESTE = "❓ ¿Este es el producto que buscabas? Responde con *sí* o *no*."
MSG_SOLO_SI_NO = "❓ Por favor responde solo con *sí* o *no*."
MSG_ELEGIR = "Escribe el número del producto que deseas ver o *0* para cancelar búsqueda."
MSG_QUE_BUSCAS = "🛒 Por favor escribe qué producto deseas buscar."
MSG_ESPERA = "⌛ Continuaré con tu solicitud en un momento..."
MSG_ERROR = "⚠️ Ocurrió un error. Por favor intenta de nuevo."
MSG_NO_SOPORTADO = "Lo siento, solo puedo procesar mensajes de texto y selecciones."


def mensaje_bienvenida(nombre_tienda: str) -> str:
    return (
        f"👋 ¡Bienvenido a *{nombre_tienda}*!\n"
        "📦 Encuentra accesorios para moto fácilmente.\n"
        "🔎 Escribe lo que estás buscando, por ejemplo: *Guantes rojos talla M*.\n"
        "Si lo prefieres revisa nuestro catalogo y escribe el nombre del producto"
    )


def procesar_mensaje(deps: Dependencias, numero: str, texto: str, inicio: float | None = None) -> str:
    """Procesa un mensaje de texto del usuario. Devuelve "ok" o "processing"."""
    conversacion = Conversacion(deps, numero, deps.reloj() if inicio is None else inicio)
    try:
        return conversacion.procesar(texto)
    except Exception:  # noqa: BLE001 - nunca se devuelve un 500 a WhatsApp (reintentaría el mensaje)
        log.exception("❌ Error general procesando el mensaje de %s", numero)
        if conversacion.transcurrido() < T_ERROR:
            deps.mensajero.enviar_texto(numero, MSG_ERROR)
        conversacion.guardar_si_cargado()
        return OK


def procesar_no_soportado(deps: Dependencias, numero: str, inicio: float) -> str:
    if deps.reloj() - inicio < T_ERROR:
        deps.mensajero.enviar_texto(numero, MSG_NO_SOPORTADO)
    return OK


class Conversacion:
    def __init__(self, deps: Dependencias, numero: str, inicio: float):
        self.deps = deps
        self.numero = numero
        self.inicio = inicio
        self.contexto: dict | None = None
        self.estados: dict = {}
        self.codigos: dict = {}

    # --- utilidades ---
    def transcurrido(self) -> float:
        return self.deps.reloj() - self.inicio

    def enviar(self, mensaje: str) -> None:
        self.deps.mensajero.enviar_texto(self.numero, mensaje)

    @property
    def usuario(self) -> dict:
        return self.estados.get(self.numero, {})

    def guardar(self) -> str:
        assert self.contexto is not None
        self.contexto["estado_usuarios_data"] = self.estados
        self.contexto["codigos_venta_data"] = self.codigos
        self.deps.contexto.guardar(self.numero, self.contexto)
        return OK

    def guardar_si_cargado(self) -> None:
        if self.contexto is None:
            return
        try:
            self.guardar()
        except Exception:  # noqa: BLE001
            log.exception("❌ Error adicional al guardar contexto")

    # --- flujo principal ---
    def procesar(self, texto: str) -> str:
        deps, numero = self.deps, self.numero

        if es_enlace_marketplace(texto):
            log.info("🔗 Enlace de Marketplace detectado")
            titulo = deps.extraer_titulo(texto)
            if not titulo:
                self.enviar("⚠️ No pude obtener información del producto. Por favor, escribe el nombre del producto.")
                return OK
            texto = titulo
            self.enviar(f"🔍 Buscando producto: *{titulo}*")

        log.info("📥 Mensaje de %s: %r", numero, texto)
        if self.transcurrido() > T_AVISO:
            self.enviar("⏳ Estoy procesando tu mensaje...")
            return PROCESANDO

        self.contexto = deps.contexto.obtener(numero)
        self.estados = self.contexto.get("estado_usuarios_data", {})
        self.codigos = self.contexto.get("codigos_venta_data", {})
        self.estados.setdefault(numero, {})
        estado_actual = self.usuario.get("estado")
        log.debug("Estado actual de %s: %s", numero, estado_actual)

        datos = None
        if estado_actual in ESTADOS_CON_INVENTARIO:
            try:
                datos = deps.tienda.inventario()
            except Exception:  # noqa: BLE001
                log.exception("❌ Error al leer el inventario")
                if self.transcurrido() < T_ERROR:
                    self.enviar("⚠️ Error temporal al acceder al sistema. Por favor intenta en 1 minuto.")
                return OK

        if self.transcurrido() > T_AVISO:
            self.enviar("⏳ Buscando información...")
            return PROCESANDO

        # Flujos con prioridad: datos del cliente y cierre de venta del asesor
        if manejar_captura_datos_cliente(deps, numero, texto, self.estados, self.codigos):
            return self.guardar()
        if manejar_cierre_venta(deps, numero, texto, self.estados, self.codigos):
            return self.guardar()

        # Foto del estado antes de una posible interrupción (pregunta general)
        if "contexto_pre_interrupcion" not in self.estados[numero]:
            self.estados[numero]["contexto_pre_interrupcion"] = self._foto_estado(estado_actual)

        es_pregunta = es_pregunta_general(texto, deps.llm)
        log.debug("¿Pregunta general? %s", es_pregunta)

        if estado_actual and es_pregunta:
            resultado = self._pregunta_en_flujo(texto, estado_actual)
            if resultado:
                return resultado

        if estado_actual == "confirmando_continuacion":
            self._confirmar_continuacion(texto)
            return self.guardar()

        if self.usuario.get("estado") == "confirmando_producto":
            return self._confirmar_producto(texto)

        if self.usuario.get("estado") == "seleccionando":
            return self._seleccionar(texto)

        if "estado" not in self.usuario:
            return self._bienvenida()

        if self.usuario.get("estado") == "esperando_busqueda":
            if es_pregunta:
                if self.transcurrido() > T_PREGUNTA:
                    self.enviar(MSG_ESPERA)
                    return PROCESANDO
                respuesta = responder_fuera_de_flujo(texto, deps.llm, deps.config.nombre_tienda)
                if respuesta:
                    self.enviar(respuesta)
                    self.estados[numero] = {"estado": "esperando_busqueda"}
                    self.enviar(MSG_QUE_BUSCAS)
                return self.guardar()
            if len(texto) < 3:
                if self.transcurrido() < T_ERROR:
                    self.enviar("📝 Escribe al menos 3 caracteres para buscar un producto.")
                return OK

        return self._buscar(texto, datos)

    # --- pasos ---
    def _foto_estado(self, estado_actual: str | None) -> dict:
        u = self.usuario
        return {
            "estado": estado_actual,
            "resultados": u.get("resultados"),
            "ultimo_producto": u.get("ultimo_producto"),
            "termino_busqueda_actual": u.get("termino_busqueda_actual"),
            "producto": u.get("producto"),
        }

    def _pregunta_en_flujo(self, texto: str, estado_actual: str) -> str | None:
        """Responde una pregunta general en medio de un flujo y ofrece retomar la compra."""
        if self.transcurrido() > T_PREGUNTA:
            self.enviar(MSG_ESPERA)
            return PROCESANDO
        respuesta = responder_fuera_de_flujo(texto, self.deps.llm, self.deps.config.nombre_tienda)
        if not respuesta:
            return None
        self.enviar(respuesta)

        u = self.usuario
        pendiente = (
            "ultimo_producto" in u
            or "producto" in u
            or "termino_busqueda_actual" in u
            or u.get("estado") == "seleccionando"
        )
        if pendiente:
            anterior = u.get("contexto_pre_interrupcion")
            u["contexto_pre_interrupcion"] = {**self._foto_estado(estado_actual), "contexto_pre_interrupcion_anterior": anterior}

            nombre = u.get("termino_busqueda_actual", "estos productos")
            if "ultimo_producto" in u:
                nombre = (u["ultimo_producto"] or {}).get("item", {}).get("servicio", "este producto")
            elif "producto" in u:
                nombre = (u["producto"] or {}).get("item", {}).get("servicio", "este producto")
            self.enviar(f"¿Deseas continuar con la compra de {nombre}? Responde *sí* o *no*.")
            u["estado"] = "confirmando_continuacion"
        return self.guardar()

    def _pasar_a_datos_cliente(self, producto: dict) -> None:
        self.estados[self.numero] = {"estado": "solicitando_nombre", "producto": producto, "cliente_info": {}}
        self.enviar(MSG_PEDIR_NOMBRE)

    def _reiniciar_busqueda(self, mensaje: str) -> None:
        self.enviar(mensaje)
        self.estados[self.numero] = {"estado": "esperando_busqueda"}

    def _confirmar_continuacion(self, texto: str) -> None:
        respuesta = texto.lower()
        u = self.usuario
        if respuesta in NEGACIONES:
            u.pop("contexto_pre_interrupcion", None)
            self._reiniciar_busqueda("🔄 Puedes buscar otro producto escribiendo lo que necesitas")
            return
        if respuesta not in AFIRMACIONES:
            self.enviar(MSG_SOLO_SI_NO)
            return

        previo = u.get("contexto_pre_interrupcion")
        if not previo:
            producto = u.get("ultimo_producto") or u.get("producto")
            if producto:
                self._pasar_a_datos_cliente(producto)
            else:
                self._reiniciar_busqueda("🔄 Por favor escribe nuevamente lo que estás buscando.")
            return

        # Restaurar el estado anterior a la interrupción
        restaurado = previo.get("estado")
        u["estado"] = restaurado
        for clave in ("resultados", "ultimo_producto", "termino_busqueda_actual", "producto"):
            if clave in previo:
                u[clave] = previo[clave]
        if "contexto_pre_interrupcion_anterior" in previo:
            u["contexto_pre_interrupcion"] = previo["contexto_pre_interrupcion_anterior"]
        else:
            u.pop("contexto_pre_interrupcion", None)

        producto = previo.get("ultimo_producto") or previo.get("producto")
        if restaurado == "seleccionando":
            self.enviar(MSG_ELEGIR)
        elif restaurado == "esperando_busqueda":
            self.enviar(MSG_QUE_BUSCAS)
        elif producto:  # confirmando_producto u otro: decir "sí, continuar" confirma el producto
            self._pasar_a_datos_cliente(producto)
        elif restaurado == "confirmando_producto":
            self._reiniciar_busqueda("🔄 Por favor escribe nuevamente lo que estás buscando.")
        else:
            self._reiniciar_busqueda("🔄 Volviendo al inicio. ¿Qué producto buscas?")

    def _confirmar_producto(self, texto: str) -> str:
        respuesta = texto.lower()
        if respuesta in AFIRMACIONES:
            self._pasar_a_datos_cliente(self.usuario.get("ultimo_producto", {}))
            return self.guardar()
        if respuesta in NEGACIONES:
            self._reiniciar_busqueda("🔄 Por favor escribe nuevamente lo que estás buscando con más características.")
            return self.guardar()
        self.enviar(MSG_SOLO_SI_NO)
        return OK

    def _seleccionar(self, texto: str) -> str:
        resultados = self.usuario.get("resultados", [])
        if self.transcurrido() > T_PREGUNTA:
            self.enviar(MSG_ESPERA)
            return PROCESANDO
        if texto == "0":
            self.enviar("❌ Búsqueda cancelada")
            self.deps.contexto.eliminar(self.numero)
            return OK
        try:
            idx = int(texto) - 1
        except ValueError:
            self.enviar("⚠️ Por favor ingresa solo números.")
            return self.guardar()
        if 0 <= idx < len(resultados):
            self._mostrar_producto(resultados[idx])
        else:
            self.enviar("⚠️ Número inválido. Por favor elige un número de la lista.")
        return self.guardar()

    def _bienvenida(self) -> str:
        deps = self.deps
        self.enviar(mensaje_bienvenida(deps.config.nombre_tienda))
        try:
            pdf = deps.tienda.catalogo_pdf()
            if pdf:
                deps.mensajero.enviar_documento(self.numero, pdf["url"], pdf["nombre"], "📚 Catálogo completo de productos")
            else:
                self.enviar("🔍 Pronto tendremos nuestro catálogo disponible para ti.")
        except Exception:  # noqa: BLE001
            log.exception("Error al enviar el catálogo PDF")
        self.estados[self.numero] = {"estado": "esperando_busqueda"}
        return self.guardar()

    def _mostrar_producto(self, producto: dict) -> None:
        """Envía hasta 2 archivos (imágenes primero), la ficha del producto y pide confirmación."""
        deps = self.deps
        for archivo in obtener_archivos_asociados(producto["numero"], deps.tienda):
            mime, nombre = archivo.get("mimeType", ""), archivo.get("name", "")
            url = url_descarga_drive(archivo["id"])
            if "image" in mime:
                deps.mensajero.enviar_media(self.numero, url, tipo="image", caption=nombre)
            elif "video" in mime:
                deps.mensajero.enviar_media(self.numero, url, tipo="video", caption=nombre)
            else:
                self.enviar(f"📄 {nombre}: {url}")
        deps.dormir(deps.config.pausa_media_seg)  # que las fotos lleguen antes que el texto
        self.enviar(formatear_resultados([producto]))
        self.enviar(MSG_ES_ESTE)
        self.usuario["estado"] = "confirmando_producto"
        self.usuario["ultimo_producto"] = producto

    def _buscar(self, texto: str, datos: list | None) -> str:
        if datos is None:
            try:
                datos = self.deps.tienda.inventario()
            except Exception:  # noqa: BLE001
                log.exception("❌ Error al cargar inventario")
                if self.transcurrido() < T_ERROR:
                    self.enviar("⚠️ Error temporal al acceder al inventario. Por favor intenta en 1 minuto.")
                return OK

        resultados = buscar_y_verificar_inventario(texto, datos, self.deps.llm)
        if self.transcurrido() > T_RESULTADOS:
            self.enviar("⌛ Continuaré con tu búsqueda en un momento...")
            return PROCESANDO

        if not resultados:
            self._reiniciar_busqueda(
                "❌ No encontramos productos que coincidan con tu búsqueda. "
                "¿Podrías intentar con otro nombre o descripción? Estamos aquí para ayudarte."
            )
        elif "error" in resultados[0]:
            self._reiniciar_busqueda(resultados[0]["error"])
        elif len(resultados) == 1:
            self._mostrar_producto(resultados[0])
        else:
            self.enviar(formatear_seleccion_whatsapp(resultados))
            self.usuario.update({"estado": "seleccionando", "resultados": resultados, "termino_busqueda_actual": texto})
        return self.guardar()
