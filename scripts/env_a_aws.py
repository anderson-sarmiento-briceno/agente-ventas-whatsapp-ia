"""Convierte el .env al formato que pide AWS, para no copiar variables a mano.

    # Plan gratuito: todas las variables van en la Lambda
    python3 scripts/env_a_aws.py lambda > /tmp/variables.json

    # Plan de pago: los secretos van a Secrets Manager y la Lambda solo guarda lo no sensible
    python3 scripts/env_a_aws.py secreto > /tmp/secreto.json
    python3 scripts/env_a_aws.py lambda --sin-secretos --secreto-id agente-ventas/prod > /tmp/variables.json

Solo usa la librería estándar de Python. Los archivos generados contienen secretos: bórralos al terminar.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from agente_vendedor.config import leer_env  # noqa: E402

# Lo que va a Secrets Manager en el plan de pago
SECRETOS = {
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_ACCESS_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "SPREADSHEET_ID",
    "DRIVE_CARPETA_ID",
    "GOOGLE_CREDENTIALS_JSON",
}
# Lambda reserva estos nombres o no aplican en la nube
EXCLUIR_LAMBDA = {"PORT", "GOOGLE_CREDENTIALS_FILE"}
LIMITE_VARIABLES_LAMBDA = 4096  # bytes: límite de AWS para todas las variables de una función


def variables_lambda(env: dict[str, str], sin_secretos: bool, secreto_id: str | None) -> dict[str, str]:
    variables = {
        k: v for k, v in env.items()
        if v and k not in EXCLUIR_LAMBDA and not k.startswith("AWS_") and not (sin_secretos and k in SECRETOS)
    }
    if secreto_id:
        variables["SECRETO_ID"] = secreto_id
    return variables


def secreto(env: dict[str, str], credenciales: Path) -> dict[str, str]:
    datos = {k: v for k, v in env.items() if v and k in SECRETOS}
    if credenciales.is_file():
        # Se guarda compacto (una línea) para que quepa en un solo valor
        datos["GOOGLE_CREDENTIALS_JSON"] = json.dumps(json.loads(credenciales.read_text(encoding="utf-8")))
    else:
        print(f"⚠️  No existe {credenciales}: el secreto no tendrá las credenciales de Google", file=sys.stderr)
    return datos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("modo", choices=["lambda", "secreto"])
    parser.add_argument("--env", default=str(RAIZ / ".env"))
    parser.add_argument("--credenciales", default=str(RAIZ / "credentials.json"))
    parser.add_argument("--sin-secretos", action="store_true", help="omite las variables que van a Secrets Manager")
    parser.add_argument("--secreto-id", help="nombre del secreto en Secrets Manager (agrega SECRETO_ID)")
    args = parser.parse_args()

    env = leer_env(args.env)
    if not env:
        sys.exit(f"❌ No se encontró {args.env} o está vacío")

    if args.modo == "secreto":
        print(json.dumps(secreto(env, Path(args.credenciales)), ensure_ascii=False))
        return

    variables = variables_lambda(env, args.sin_secretos, args.secreto_id)
    tamano = sum(len(k) + len(v) for k, v in variables.items())
    if tamano > LIMITE_VARIABLES_LAMBDA:
        sys.exit(f"❌ Las variables suman {tamano} bytes y Lambda permite {LIMITE_VARIABLES_LAMBDA}: usa el plan con Secrets Manager")
    print(json.dumps({"Variables": variables}, ensure_ascii=False))


if __name__ == "__main__":
    main()
