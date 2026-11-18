"""Genera la skill de negocio para Claude Code a partir del conocimiento del agente.

    python scripts/generar_skill.py           # escribe .claude/skills/ventas-motopro/SKILL.md
    python scripts/generar_skill.py --check   # falla si la skill está desactualizada (usado en tests)

Fuente única de verdad: src/agente_vendedor/knowledge/*.md. La skill no se edita a mano.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
KNOWLEDGE = RAIZ / "src" / "agente_vendedor" / "knowledge"
DESTINO = RAIZ / ".claude" / "skills" / "ventas-motopro" / "SKILL.md"

ENCABEZADO = """---
name: ventas-motopro
description: Conocimiento del negocio Accesorios MotoPro y de su proceso de venta por WhatsApp (estados, reglas RV1–RV9, datos oficiales, tallas, glosario). Úsalo al responder dudas del negocio, revisar conversaciones del bot o cambiar sus reglas.
---
<!-- Generado por scripts/generar_skill.py. No editar a mano: editar src/agente_vendedor/knowledge/ y volver a generar. -->
"""

FUENTES = ["proceso-ventas.md", "negocio.md"]


def generar() -> str:
    partes = [ENCABEZADO]
    for nombre in FUENTES:
        texto = (KNOWLEDGE / nombre).read_text(encoding="utf-8").strip()
        partes.append(f"\n<!-- fuente: src/agente_vendedor/knowledge/{nombre} -->\n{texto}\n")
    return "".join(partes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    contenido = generar()
    actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
    if args.check:
        if actual != contenido:
            sys.exit("La skill está desactualizada: ejecuta python scripts/generar_skill.py")
        print("Skill al día")
        return
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(contenido, encoding="utf-8", newline="\n")
    print(f"Generada {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
