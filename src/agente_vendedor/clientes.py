"""Captura de datos del cliente: nombre -> teléfono -> dirección -> pedido al asesor."""
from __future__ import annotations

import re

from .clasificador import RESPUESTAS_SIMPLES, es_pregunta_general, responder_fuera_de_flujo
from .dependencias import Dependencias
from .ventas import enviar_datos_a_asesor

PATRON_MOVIL_CO = re.compile(r"^3\d{9}$")
PATRON_FIJO_7 = re.compile(r"^\d{7}$")
PATRON_FIJO_60 = re.compile(r"^(?:60)\d{8}$")
PATRON_NUMERICO = re.compile(r"^\d+$|^\d+[\s\-\.]?\d+$")


def es_telefono_valido(digitos: str) -> bool:
    return any(p.fullmatch(digitos) for p in (PATRON_MOVIL_CO, PATRON_FIJO_7, PATRON_FIJO_60))


def parece_nombre(texto: str) -> bool:
    """1 a 3 palabras, solo letras (se permiten tildes, guion y apóstrofo), y no una respuesta tipo sí/no/ok."""
    palabras = texto.strip().split()
    if not 1 <= len(palabras) <= 3 or texto.strip().lower() in RESPUESTAS_SIMPLES:
        return False
    return all(len(p) > 1 and p.replace("-", "").replace("'", "").isalpha() for p in palabras)


def manejar_captura_datos_cliente(deps: Dependencias, numero: str, texto: str, estados: dict, codigos_venta: dict) -> bool:
    """Devuelve True si el mensaje pertenecía a la captura de datos."""
    enviar = deps.mensajero.enviar_texto
    usuario = estados.get(numero, {})
    estado = usuario.get("estado")
    cliente_info = usuario.get("cliente_info", {})
    producto = usuario.get("producto", {})

    if estado == "solicitando_nombre":
        if parece_nombre(texto):
            cliente_info["nombre"] = texto.strip().title()
            estados[numero]["cliente_info"] = cliente_info
            estados[numero]["estado"] = "solicitando_telefono"
            enviar(numero, f"✅ Gracias {texto.split()[0]}. Ahora, por favor escribe tu *número de celular*.")
            return True
        if es_pregunta_general(texto, deps.llm) and not texto.strip().isalpha():
            enviar(numero, responder_fuera_de_flujo(texto, deps.llm, deps.config.nombre_tienda))
            enviar(numero, "📝 Por favor escribe tu *nombre completo* para continuar con el pedido.")
            return True
        enviar(numero, "📝 Por favor escribe tu *nombre completo* (nombre y apellido) para continuar.")
        return True

    if estado == "solicitando_telefono":
        nombre = cliente_info.get("nombre", "")
        entrada = texto.strip()
        if PATRON_NUMERICO.match(entrada):
            digitos = re.sub(r"\D", "", entrada)
            if es_telefono_valido(digitos):
                cliente_info["telefono"] = digitos
                estados[numero]["cliente_info"] = cliente_info
                estados[numero]["estado"] = "solicitando_direccion"
                enviar(numero, "📍 Finalmente, escribe tu *dirección de entrega*.")
            else:
                enviar(
                    numero,
                    f"⚠️ Lo siento {nombre}, el número *{entrada}* no parece ser un número de celular o fijo válido. "
                    "Por favor, asegúrate de escribirlo correctamente (ej. 3101234567 o 6011234567).",
                )
            return True
        if es_pregunta_general(texto, deps.llm):
            enviar(numero, responder_fuera_de_flujo(texto, deps.llm, deps.config.nombre_tienda))
            enviar(numero, f"📞 Por favor escribe tu *número de celular*, {nombre}.")
        else:
            enviar(
                numero,
                f"🤔 No entendí tu respuesta, {nombre}. Por favor, escribe tu *número de celular* "
                "o haz una pregunta general sobre horarios, ubicación, etc.",
            )
        return True

    if estado == "solicitando_direccion":
        cliente_info["direccion"] = texto.strip()
        enviar_datos_a_asesor(deps, cliente_info, producto, numero, codigos_venta)
        enviar(
            numero,
            f"✅ ¡Gracias por tu pedido, {cliente_info.get('nombre', '')}! 🛵\n"
            "📞 Un asesor se comunicará contigo pronto para confirmar la hora de entrega.",
        )
        estados.pop(numero, None)
        return True

    return False
