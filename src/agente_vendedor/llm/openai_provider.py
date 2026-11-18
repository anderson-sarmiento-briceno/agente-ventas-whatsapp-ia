"""Implementación de `ProveedorLLM` con OpenAI.

Funciona con la librería `openai==0.28` (la que usa hoy la Lambda) y también con `openai>=1`,
para poder actualizar la dependencia sin tocar el resto del agente.
"""
from __future__ import annotations

from .adapter import ErrorLLM, Mensaje


class ProveedorOpenAI:
    def __init__(self, api_key: str, modelo: str = "gpt-4o-mini", timeout: float = 20.0):
        import openai  # import diferido: los tests no necesitan la librería

        self.modelo = modelo
        self._openai = openai
        self._api_key = api_key
        self._timeout = timeout
        self._cliente = openai.OpenAI(api_key=api_key, timeout=timeout) if hasattr(openai, "OpenAI") else None

    def completar(self, mensajes: list[Mensaje], *, max_tokens: int, temperature: float) -> str:
        try:
            if self._cliente is not None:  # openai >= 1
                r = self._cliente.chat.completions.create(
                    model=self.modelo, messages=mensajes, max_tokens=max_tokens, temperature=temperature
                )
                return (r.choices[0].message.content or "").strip()
            r = self._openai.ChatCompletion.create(  # openai 0.28
                api_key=self._api_key,
                model=self.modelo,
                messages=mensajes,
                max_tokens=max_tokens,
                temperature=temperature,
                request_timeout=self._timeout,
            )
            return r["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001 - se traduce a un error propio
            raise ErrorLLM(f"OpenAI falló: {e}") from e
