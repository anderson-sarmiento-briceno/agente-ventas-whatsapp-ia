"""Implementación de `ProveedorLLM` con Claude (Anthropic SDK).

Notas para Claude Haiku 5.5:
- `temperature` no se envía: el modelo la rechaza (400). El parámetro `temperature` de la
  interfaz se ignora aquí.
- El razonamiento (thinking) viene activo por defecto y consume `max_tokens`. Las tareas del bot
  son cortas (clasificar con 5 tokens, responder en 2-3 líneas), así que se desactiva y se usa
  esfuerzo bajo: respuestas más rápidas y baratas, importante dentro del timeout del webhook.
- Los mensajes con rol "system" de la interfaz se envían en el parámetro `system`.
"""
from __future__ import annotations

from .adapter import ErrorLLM, Mensaje

MODELO_DEFECTO = "claude-haiku-5-5"


def separar_sistema(mensajes: list[Mensaje]) -> tuple[str, list[dict]]:
    """Separa los mensajes de sistema (van en `system`) de los de usuario/asistente."""
    sistema = "\n\n".join(m["content"] for m in mensajes if m["role"] == "system")
    conversacion = [{"role": m["role"], "content": m["content"]} for m in mensajes if m["role"] != "system"]
    return sistema, conversacion


def texto_de_respuesta(respuesta) -> str:
    """Une los bloques de texto. Una negativa del modelo se trata como error."""
    if respuesta.stop_reason == "refusal":
        raise ErrorLLM("Claude rechazó la solicitud (refusal)")
    return "".join(b.text for b in respuesta.content if b.type == "text").strip()


class ProveedorAnthropic:
    def __init__(
        self,
        api_key: str,
        modelo: str = MODELO_DEFECTO,
        timeout: float = 20.0,
        max_retries: int = 1,
        esfuerzo: str = "low",
        cliente=None,
    ):
        if cliente is None:
            import anthropic  # import diferido: los tests no necesitan la librería

            cliente = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.modelo = modelo
        self._cliente = cliente
        self._esfuerzo = esfuerzo

    def completar(self, mensajes: list[Mensaje], *, max_tokens: int, temperature: float) -> str:
        sistema, conversacion = separar_sistema(mensajes)
        parametros = {
            "model": self.modelo,
            "max_tokens": max_tokens,
            "messages": conversacion,
            "thinking": {"type": "disabled"},
            "output_config": {"effort": self._esfuerzo},
        }
        if sistema:
            parametros["system"] = sistema
        try:
            respuesta = self._cliente.messages.create(**parametros)
        except ErrorLLM:
            raise
        except Exception as e:  # noqa: BLE001 - se traduce a un error propio con un mensaje claro
            raise ErrorLLM(_describir_error(e)) from e
        return texto_de_respuesta(respuesta)


def _describir_error(e: Exception) -> str:
    try:
        import anthropic
    except ImportError:
        return f"Claude falló: {e}"
    if isinstance(e, anthropic.AuthenticationError):
        return "Claude: ANTHROPIC_API_KEY inválida"
    if isinstance(e, anthropic.RateLimitError):
        return "Claude: límite de uso alcanzado (429)"
    if isinstance(e, anthropic.APITimeoutError):
        return "Claude: tiempo de espera agotado"
    if isinstance(e, anthropic.APIConnectionError):
        return "Claude: error de conexión"
    if isinstance(e, anthropic.APIStatusError):
        return f"Claude: error HTTP {e.status_code} - {e.message}"
    return f"Claude falló: {e}"
