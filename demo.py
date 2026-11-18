"""Demo del agente en la consola, sin WhatsApp, DynamoDB ni Google (usa fixtures/).

    python demo.py            # conversación interactiva
    python demo.py --guion    # recorre una compra completa y el cierre de venta

Usa el LLM real de LLM_PROVIDER (Claude u OpenAI) si su clave está en .env; si no, uno simulado.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

from agente_vendedor.agente import procesar_mensaje  # noqa: E402
from agente_vendedor.config import Config, cargar_env_local  # noqa: E402
from agente_vendedor.contexto.memoria import ContextoMemoria  # noqa: E402
from agente_vendedor.dependencias import Dependencias  # noqa: E402
from agente_vendedor.llm.falso import ProveedorFalso  # noqa: E402
from agente_vendedor.tienda.memoria import TiendaMemoria  # noqa: E402

CLIENTE = "573000000001"
ASESOR = "573000000099"


class MensajeroConsola:
    def enviar_texto(self, numero: str, mensaje: str) -> None:
        quien = "🤖→asesor" if numero == ASESOR else "🤖"
        print(f"\n{quien} {mensaje}")

    def enviar_media(self, numero: str, url: str, tipo: str = "image", caption: str = "") -> None:
        print(f"\n🤖 [{tipo}] {caption} ({url})")

    def enviar_documento(self, numero: str, url: str, nombre_archivo: str, caption: str = "") -> None:
        print(f"\n🤖 [documento] {nombre_archivo} — {caption}")


def crear_deps() -> Dependencias:
    cargar_env_local(RAIZ / ".env")
    config = Config.desde_entorno()
    config = Config(**{**config.__dict__, "numero_asesor": ASESOR, "pausa_media_seg": 0})
    try:
        from agente_vendedor.llm import crear_proveedor_llm

        llm = crear_proveedor_llm(config)
        print(f"🧠 LLM: {config.proveedor_llm} {llm.modelo}")
    except ValueError as e:
        llm = ProveedorFalso()
        print(f"🧠 LLM: simulado ({e})")
    return Dependencias(
        config=config,
        mensajero=MensajeroConsola(),
        contexto=ContextoMemoria(),
        tienda=TiendaMemoria.desde_fixtures(RAIZ / "fixtures"),
        llm=llm,
    )


def decir(deps: Dependencias, numero: str, texto: str) -> None:
    print(f"\n{'👔' if numero == ASESOR else '👤'} {texto}")
    procesar_mensaje(deps, numero, texto)


def guion(deps: Dependencias) -> None:
    for texto in ["hola", "guantes", "1", "sí", "Juan Pérez", "3101234567", "Calle 1 # 2-3"]:
        decir(deps, CLIENTE, texto)
    venta = deps.tienda.ventas[-1]
    codigo = venta[8]
    for texto in ["cerrar venta", codigo, "1"]:
        decir(deps, ASESOR, texto)
    print(f"\n📦 Unidades restantes de {venta[5]}: {deps.tienda.productos[0]['unidades']}")


def interactivo(deps: Dependencias) -> None:
    print("Escribe como cliente. Prefijo '!' para hablar como asesor (ej. '!cerrar venta'). Ctrl+C para salir.")
    while True:
        try:
            texto = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if texto:
            numero, texto = (ASESOR, texto[1:].strip()) if texto.startswith("!") else (CLIENTE, texto)
            procesar_mensaje(deps, numero, texto)


if __name__ == "__main__":
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")  # emojis en la consola de Windows
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--guion", action="store_true", help="ejecuta una conversación de ejemplo completa")
    args = parser.parse_args()
    deps = crear_deps()
    guion(deps) if args.guion else interactivo(deps)
