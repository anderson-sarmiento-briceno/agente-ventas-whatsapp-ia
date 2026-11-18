"""Selección del proveedor LLM con LLM_PROVIDER (anthropic | openai)."""
from __future__ import annotations

from ..config import Config
from .adapter import ErrorLLM, Mensaje, ProveedorLLM


def crear_proveedor_llm(config: Config) -> ProveedorLLM:
    proveedor = config.proveedor_llm
    if proveedor == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("Falta ANTHROPIC_API_KEY")
        from .anthropic_provider import ProveedorAnthropic

        return ProveedorAnthropic(config.anthropic_api_key, config.anthropic_model)
    if proveedor == "openai":
        if not config.openai_api_key:
            raise ValueError("Falta OPENAI_API_KEY")
        from .openai_provider import ProveedorOpenAI

        return ProveedorOpenAI(config.openai_api_key, config.openai_model)
    raise ValueError(f"LLM_PROVIDER no soportado: {proveedor!r} (usa 'anthropic' u 'openai')")


__all__ = ["ErrorLLM", "Mensaje", "ProveedorLLM", "crear_proveedor_llm"]
