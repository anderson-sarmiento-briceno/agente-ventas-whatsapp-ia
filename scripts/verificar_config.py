"""Revisa que la configuración y los datos estén completos antes de desplegar.

    python scripts/verificar_config.py           # solo revisa archivos y variables
    python scripts/verificar_config.py --online  # además se conecta a Google Sheets/Drive

Muestra TODOS los problemas de una vez y termina con código 1 si hay errores.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from agente_vendedor.config import Config, cargar_env_local  # noqa: E402
from agente_vendedor.prompts import cargar_conocimiento, cargar_prompt  # noqa: E402

COLUMNAS_INVENTARIO = {"numero", "servicio", "unidades", "precio", "descripcion"}
errores = avisos = 0


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def error(msg: str) -> None:
    global errores
    errores += 1
    print(f"  ❌ {msg}")


def aviso(msg: str) -> None:
    global avisos
    avisos += 1
    print(f"  ⚠️  {msg}")


def revisar_variables(config: Config) -> None:
    print("\n=== Variables de entorno ===")
    faltan = config.faltantes()
    for nombre in faltan:
        error(f"{nombre} está vacía")
    if not faltan:
        ok("todas las obligatorias están definidas")
    if not config.asesores_autorizados:
        aviso("ASESORES_AUTORIZADOS vacío: cualquier cliente puede escribir 'cerrar venta'")


def revisar_archivos(config: Config) -> None:
    print("\n=== Archivos ===")
    cred = RAIZ / config.google_credentials_file
    if not cred.exists():
        error(f"{config.google_credentials_file} no existe")
    else:
        try:
            datos = json.loads(cred.read_text(encoding="utf-8"))
            ok(f"{config.google_credentials_file} (cuenta de servicio: {datos.get('client_email', '?')})")
        except json.JSONDecodeError as e:
            error(f"{config.google_credentials_file}: JSON inválido ({e})")
    for nombre in ("clasificador", "respuesta"):
        cargar_prompt(nombre)
        ok(f"prompts/{nombre}.md")
    ok(f"knowledge/negocio.md ({len(cargar_conocimiento())} caracteres)")


def revisar_fixtures() -> None:
    print("\n=== Fixtures ===")
    inventario = json.loads((RAIZ / "fixtures" / "inventario.json").read_text(encoding="utf-8"))
    for i, item in enumerate(inventario):
        faltan = COLUMNAS_INVENTARIO - item.keys()
        if faltan:
            error(f"inventario.json[{i}] sin columnas: {', '.join(sorted(faltan))}")
    ok(f"inventario.json ({len(inventario)} productos)")


def revisar_online(config: Config) -> None:
    print("\n=== Google (online) ===")
    from agente_vendedor.tienda.google import TiendaGoogle

    tienda = TiendaGoogle(config)
    try:
        productos = tienda.inventario(forzar=True)
        ok(f"hoja '{config.hoja_inventario}': {len(productos)} productos")
        if productos:
            faltan = COLUMNAS_INVENTARIO - productos[0].keys()
            if faltan:
                error(f"a la hoja de inventario le faltan columnas: {', '.join(sorted(faltan))}")
        ok(f"hoja '{config.hoja_ventas}': {len(tienda.leer_ventas())} filas")
        pdf = tienda.catalogo_pdf()
        ok(f"catálogo PDF: {pdf['nombre']}") if pdf else aviso("no hay PDF de catálogo en la carpeta de Drive")
    except Exception as e:  # noqa: BLE001
        error(f"no se pudo conectar a Google: {e}")


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()

    cargar_env_local(RAIZ / ".env")
    config = Config.desde_entorno()
    revisar_variables(config)
    revisar_archivos(config)
    revisar_fixtures()
    if args.online:
        revisar_online(config)
    print(f"\n=== Resumen: {errores} errores · {avisos} avisos ===")
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
