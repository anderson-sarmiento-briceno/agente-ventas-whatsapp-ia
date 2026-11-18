"""Genera dist/lambda.zip listo para subir a AWS Lambda (Python 3.11, x86_64).

    python scripts/empaquetar_lambda.py
    python scripts/empaquetar_lambda.py --arm64    # si la función usa arquitectura arm64

Instala las dependencias con wheels de *Linux* (aunque se ejecute en Windows): la versión
anterior incluía binarios .pyd de Windows y le faltaba la carpeta bs4/, por eso fallaba en AWS.

Handler a configurar en Lambda:  agente_vendedor.lambda_handler.handler
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUILD = RAIZ / "build" / "lambda"
DIST = RAIZ / "dist"
PAQUETE = RAIZ / "src" / "agente_vendedor"
# boto3/botocore ya vienen en el runtime de Lambda: no se empaquetan (el zip pesa ~20 MB menos).
EXCLUIR = {"boto3", "botocore", "s3transfer", "jmespath"}


def instalar_dependencias(plataforma: str) -> None:
    requisitos = [
        linea.split("#")[0].strip()
        for linea in (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if linea.split("#")[0].strip() and not linea.lower().startswith(tuple(EXCLUIR))
    ]
    comando = [
        sys.executable, "-m", "pip", "install",
        "--target", str(BUILD),
        "--platform", plataforma,
        "--implementation", "cp",
        "--python-version", "3.11",
        "--only-binary=:all:",
        "--upgrade",
        *requisitos,
    ]
    print("📦 Instalando dependencias para", plataforma)
    subprocess.run(comando, check=True)


def limpiar_build() -> None:
    for patron in ("**/__pycache__", "**/*.dist-info/RECORD"):
        for ruta in BUILD.glob(patron):
            shutil.rmtree(ruta) if ruta.is_dir() else ruta.unlink()
    binarios_windows = list(BUILD.rglob("*.pyd"))
    if binarios_windows:
        raise SystemExit(f"❌ Quedaron binarios de Windows en el paquete: {binarios_windows[:3]}")


def copiar_codigo() -> None:
    shutil.copytree(PAQUETE, BUILD / "agente_vendedor", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    credenciales = RAIZ / "credentials.json"
    if credenciales.exists():
        shutil.copy2(credenciales, BUILD / "credentials.json")
    else:
        print("⚠️  No hay credentials.json: el zip no podrá conectarse a Google Sheets/Drive")


def comprimir() -> Path:
    DIST.mkdir(exist_ok=True)
    destino = DIST / "lambda.zip"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for ruta in sorted(BUILD.rglob("*")):
            if ruta.is_file():
                z.write(ruta, ruta.relative_to(BUILD).as_posix())
    return destino


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")  # emojis en la consola de Windows
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm64", action="store_true", help="arquitectura arm64 (Graviton)")
    args = parser.parse_args()

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    instalar_dependencias("manylinux2014_aarch64" if args.arm64 else "manylinux2014_x86_64")
    limpiar_build()
    copiar_codigo()
    destino = comprimir()
    print(f"✅ {destino.relative_to(RAIZ)} ({destino.stat().st_size / 1_048_576:.1f} MB)")
    print("   Handler: agente_vendedor.lambda_handler.handler")


if __name__ == "__main__":
    main()
