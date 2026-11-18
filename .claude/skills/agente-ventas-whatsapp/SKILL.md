---
name: agente-ventas-whatsapp
description: Cómo trabajar en este repositorio (bot de ventas por WhatsApp en Python sobre AWS Lambda) - ejecutar tests y demo, cambiar el conocimiento o los prompts, agregar un proveedor, empaquetar y desplegar. Úsalo antes de modificar código, prompts o la configuración del bot.
---

# Desarrollo del agente de ventas por WhatsApp

## Antes de cambiar algo
1. Lee [docs/CONTEXTO.md](../../../docs/CONTEXTO.md): decisiones, reglas y estado actual.
2. La lógica vive en `src/agente_vendedor/`; `server.py` solo traduce HTTP y `agente.py` es la máquina de estados.
3. Todo servicio externo está detrás de una interfaz (`adapter.py`) con una versión en memoria para tests. **No** llames servicios reales desde los tests.

## Comandos
| Tarea | Comando |
|---|---|
| Instalar | `python -m venv .venv` y `.venv\Scripts\pip install -r requirements-dev.txt` |
| Tests | `.venv\Scripts\python -m pytest` |
| Cobertura | `.venv\Scripts\python -m pytest --cov` |
| Demo sin servicios | `.venv\Scripts\python demo.py --guion` |
| Verificar configuración | `.venv\Scripts\python scripts\verificar_config.py [--online]` |
| Regenerar skill de negocio | `.venv\Scripts\python scripts\generar_skill.py` |
| Empaquetar Lambda | `.venv\Scripts\python scripts\empaquetar_lambda.py` → `dist/lambda.zip` |

## Recetas
**Cambiar datos del negocio (horarios, garantía, envíos…)**
Edita `src/agente_vendedor/knowledge/negocio.md`, ejecuta `scripts/generar_skill.py` y los tests.

**Cambiar cómo responde o clasifica el LLM**
Edita `src/agente_vendedor/prompts/respuesta.md` o `clasificador.md`. Los marcadores `{{...}}` deben seguir existiendo (lo verifica `tests/test_prompts.py`).

**Agregar un estado a la conversación**
Agrégalo en `agente.py` (o `clientes.py` / `ventas.py`), documenta la transición en `knowledge/proceso-ventas.md` y escribe una conversación de prueba en `tests/test_agente.py` usando el fixture `chat`.

**Cambiar de proveedor LLM**
`LLM_PROVIDER=anthropic|openai`. Para uno nuevo: implementa `ProveedorLLM.completar()` en `llm/`, regístralo en `llm/__init__.py` y agrega tests con un cliente falso (ver `tests/test_llm.py`).

## Reglas obligatorias
1. **Nunca** escribas claves, tokens ni IDs privados en el código, en los tests ni en los fixtures: van en `.env` (local) o en las variables de entorno de Lambda.
2. **Nunca** hagas commit de `.env`, `credentials.json`, `_respaldo_original/`, `.vscode/`, `build/` ni `dist/`.
3. Toda corrección de comportamiento lleva un test que fallaba antes.
4. El código debe correr en **Python 3.11** (runtime de Lambda): nada de sintaxis 3.12+.
5. Con Claude Haiku 5.5 no se envía `temperature` (da 400) y el thinking va desactivado con `effort: low` para respuestas cortas.
6. Un error de WhatsApp, DynamoDB, Google o del LLM nunca debe devolver 500 al webhook: se registra y la conversación continúa.
