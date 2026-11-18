"""Extrae el título de una publicación de Facebook Marketplace para buscarla en el inventario.

Nota: desde AWS, Facebook suele responder con una página de login/"checkpoint" a las IPs
de centros de datos; en ese caso se devuelve None y el bot pide escribir el nombre del producto.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import requests

log = logging.getLogger(__name__)

PREFIJOS_MARKETPLACE = ("https://www.facebook.com/marketplace/", "https://m.facebook.com/marketplace/")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

CLASES_TITULO = ["x1lliihq", "x1heor9g", "x1qlqyl8"]
TITULOS_GENERICOS = {"facebook", "marketplace", "facebook marketplace", "log in or sign up to view", "inicia sesión"}


def es_enlace_marketplace(texto: str) -> bool:
    return texto.startswith(PREFIJOS_MARKETPLACE)


def titulo_desde_html(html: str) -> str | None:
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # sin bs4 la Lambda no debe caerse completa
        log.error("❌ beautifulsoup4 no está instalado: no se pueden leer enlaces de Marketplace")
        return None

    soup = BeautifulSoup(html, "html.parser")
    candidatos: list[str] = []

    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        candidatos.append(og["content"])
    if soup.title:
        candidatos.append(soup.title.get_text().replace(" | Facebook Marketplace", ""))
    span = soup.find("span", {"data-testid": "marketplace_pdp_title"})
    if span:
        candidatos.append(span.get_text(strip=True))
    for clase in CLASES_TITULO:
        el = soup.find(class_=re.compile(clase))
        if el:
            candidatos.append(el.get_text(strip=True))

    for c in candidatos:
        c = c.strip()
        if c and c.lower() not in TITULOS_GENERICOS:
            return c
    return None


def extraer_titulo_marketplace(url: str, reportar_error: bool = False, http: Any = None) -> str | None:
    http = http or requests
    try:
        r = http.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        if "checkpoint" in r.url or "login" in r.url or "content is not available" in r.text:
            log.warning("⚠️ Facebook bloqueó la lectura del enlace (checkpoint/login)")
            return None
        return titulo_desde_html(r.text)
    except Exception as e:  # noqa: BLE001
        log.error("Error al extraer título de Marketplace: %s", e)
        return f"❌ Error al extraer título: {e}" if reportar_error else None
