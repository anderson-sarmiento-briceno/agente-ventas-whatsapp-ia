"""Registro de pedidos, aviso al asesor y cierre de venta con descuento de inventario."""
from __future__ import annotations

import logging
import random
import string
from datetime import datetime

from .dependencias import Dependencias
from .inventario import a_entero, a_precio, producto_por_numero
from .tienda.adapter import COL_CANTIDAD, COL_CODIGO_VENTA, COL_ESTADO, COL_FECHA, COL_PRECIO_FINAL

log = logging.getLogger(__name__)

COMANDO_CIERRE = "cerrar venta"


def generar_codigo_unico(longitud: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=longitud))


def _ahora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def enviar_datos_a_asesor(deps: Dependencias, cliente_info: dict, producto: dict, numero_cliente: str, codigos_venta: dict) -> str:
    """Registra el pedido como 'pendiente', avisa al asesor y devuelve el código de cierre."""
    nombre = cliente_info.get("nombre", "Sin nombre")
    telefono = cliente_info.get("telefono", "Sin teléfono")
    direccion = cliente_info.get("direccion", "Sin dirección")
    producto_nombre = producto.get("item", {}).get("servicio", "Producto no especificado")
    producto_codigo = producto.get("numero", "N/A")
    cantidad = producto.get("cantidad", 1)
    asesor = deps.config.numero_asesor
    fecha = _ahora()
    codigo = generar_codigo_unico()

    fila = deps.tienda.registrar_venta(
        [
            fecha,
            cliente_info.get("nombre", "No indicado"),
            cliente_info.get("telefono", "No indicado"),
            cliente_info.get("direccion", "No indicada"),
            producto.get("item", {}).get("servicio", "No especificado"),
            producto_codigo,
            cantidad,
            asesor,
            codigo,
            "pendiente",
        ]
    )
    codigos_venta[codigo] = {
        "numero_producto": producto_codigo,
        "cantidad": cantidad,
        "codigo": codigo,
        "fila": fila,
        "cliente_info": cliente_info,
        "producto": producto,
    }

    deps.mensajero.enviar_texto(
        asesor,
        f"📦 *Nuevo pedido recibido:*\n"
        f"🕒 *Fecha y hora:* {fecha}\n"
        f"👤 *Nombre:* {nombre}\n"
        f"📱 *Celular (escrito por cliente):* {telefono}\n"
        f"📍 *Dirección:* {direccion}\n"
        f"🛒 *Producto:* {producto_nombre} (Cod: {producto_codigo})\n"
        f"📞 *WhatsApp real del cliente:* {numero_cliente}\n"
        f"🔐 *Código de cierre:* {codigo}",
    )
    return codigo


def manejar_cierre_venta(deps: Dependencias, numero: str, texto: str, estados: dict, codigos_venta: dict) -> bool:
    """Flujo del asesor: 'cerrar venta' -> código -> cantidad. Devuelve True si manejó el mensaje."""
    enviar = deps.mensajero.enviar_texto
    estado_actual = estados.get(numero, {}).get("estado")

    if texto.lower().strip() == COMANDO_CIERRE and deps.config.puede_cerrar_ventas(numero):
        estados[numero] = {"estado": "esperando_codigo"}
        enviar(numero, "🔐 Por favor, escribe el *código de venta* que deseas cerrar.")
        return True

    if estado_actual == "esperando_codigo":
        estados[numero] = {"estado": "esperando_cantidad", "codigo": texto.strip().upper()}
        enviar(numero, "✏️ Ingresa la *cantidad vendida*: ")
        return True

    if estado_actual != "esperando_cantidad":
        return False

    try:
        cantidad = int(texto.strip())
        if cantidad <= 0:
            raise ValueError
    except ValueError:
        enviar(numero, "⚠️ Por favor ingresa una cantidad válida (número entero positivo).")
        return True

    codigo = estados[numero].get("codigo", "")
    try:
        enviar(numero, _cerrar_venta(deps, codigo, cantidad))
    except Exception as e:  # noqa: BLE001
        log.exception("Error en cierre de venta")
        enviar(numero, f"❌ Error en el proceso: {e}")
    finally:
        estados.pop(numero, None)  # siempre se sale del flujo; para reintentar: "cerrar venta"
    return True


def _cerrar_venta(deps: Dependencias, codigo: str, cantidad: int) -> str:
    """Marca la venta como completada, descuenta inventario y devuelve el mensaje de resultado."""
    tienda = deps.tienda
    registros = tienda.leer_ventas()
    fila_venta = numero_producto = estado_venta = None
    for i, fila in enumerate(registros, start=1):
        if len(fila) >= COL_CODIGO_VENTA and fila[COL_CODIGO_VENTA - 1].strip() == codigo:
            fila_venta = i
            numero_producto = fila[5]
            estado_venta = fila[COL_ESTADO - 1] if len(fila) >= COL_ESTADO else ""
            break

    if not fila_venta:
        return "❌ Código no encontrado en el registro de ventas"
    if str(estado_venta).lower() == "completado":
        return "⚠️ Esta venta ya fue cerrada anteriormente"

    encontrado = producto_por_numero(tienda.inventario(forzar=True), numero_producto)
    if encontrado is None:
        return f"⚠️ No se encontró precio para el producto: {numero_producto}"
    fila_inventario, item = encontrado
    precio_unitario = a_precio(item.get("precio", 0))
    precio_final = cantidad * precio_unitario

    tienda.actualizar_unidades(fila_inventario, max(a_entero(item.get("unidades", 0)) - cantidad, 0))
    tienda.actualizar_venta(fila_venta, COL_CANTIDAD, cantidad)
    tienda.actualizar_venta(fila_venta, COL_ESTADO, "completado")
    tienda.actualizar_venta(fila_venta, COL_FECHA, _ahora())
    tienda.actualizar_venta(fila_venta, COL_PRECIO_FINAL, precio_final)

    return (
        f"✅ Venta cerrada correctamente!\n"
        f"🔐 Código: {codigo}\n"
        f"🛒 Producto: {numero_producto}\n"
        f"📦 Unidades: {cantidad}\n"
        f"💰 Precio Unitario: ${precio_unitario:,.2f}\n"
        f"💲 Precio Final: ${precio_final:,.2f}"
    )
