"""Configuración del agente leída desde variables de entorno.

Ningún secreto vive en el código: en local se cargan desde `.env` (ver `.env.example`)
y en AWS Lambda desde las variables de entorno de la función.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def leer_env(ruta: str | Path = ".env") -> dict[str, str]:
    """Lee un archivo `.env` sencillo (CLAVE=valor). Soporta comentarios (`#`) y valores entre comillas."""
    ruta = Path(ruta)
    if not ruta.is_file():
        return {}
    valores: dict[str, str] = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        clave, valor = clave.strip(), valor.strip()
        if valor[:1] in {'"', "'"} and valor[-1:] == valor[:1] and len(valor) >= 2:
            valor = valor[1:-1]
        elif " #" in valor:
            valor = valor.split(" #", 1)[0].strip()
        valores[clave] = valor
    return valores


def cargar_env_local(ruta: str | Path = ".env") -> bool:
    """Carga el `.env` en el entorno sin pisar variables ya definidas. Devuelve True si el archivo existía."""
    if not Path(ruta).is_file():
        return False
    for clave, valor in leer_env(ruta).items():
        os.environ.setdefault(clave, valor)
    return True


def _texto(nombre: str, defecto: str = "") -> str:
    return os.environ.get(nombre, "").strip() or defecto


def _entero(nombre: str, defecto: int) -> int:
    valor = _texto(nombre)
    return int(valor) if valor else defecto


def _decimal(nombre: str, defecto: float) -> float:
    valor = _texto(nombre)
    return float(valor) if valor else defecto


def _lista(nombre: str) -> frozenset[str]:
    return frozenset(v.strip() for v in _texto(nombre).split(",") if v.strip())


@dataclass(frozen=True)
class Config:
    # WhatsApp Cloud API
    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v18.0"
    # LLM: "anthropic" (Claude) u "openai". Vacío = anthropic si hay ANTHROPIC_API_KEY, si no openai.
    llm_provider: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-5-5"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # DynamoDB (contexto de conversación)
    dynamodb_tabla: str = "contexto_bot_will"
    contexto_ttl_seg: int = 86400
    # Google Sheets / Drive
    google_credentials_file: str = "credentials.json"
    google_credentials_json: str = ""  # contenido del JSON (alternativa al archivo, p. ej. desde Secrets Manager)
    spreadsheet_id: str = ""
    hoja_inventario: str = "inventario"
    hoja_ventas: str = "registro_ventas"
    drive_carpeta_id: str = ""
    # Negocio
    nombre_tienda: str = "Accesorios MotoPro"
    numero_asesor: str = ""
    asesores_autorizados: frozenset[str] = frozenset()
    # Ajustes de comportamiento
    cache_inventario_seg: int = 300
    pausa_media_seg: float = 1.8

    @classmethod
    def desde_entorno(cls) -> "Config":
        return cls(
            whatsapp_verify_token=_texto("WHATSAPP_VERIFY_TOKEN"),
            whatsapp_access_token=_texto("WHATSAPP_ACCESS_TOKEN"),
            whatsapp_phone_number_id=_texto("WHATSAPP_PHONE_NUMBER_ID"),
            whatsapp_api_version=_texto("WHATSAPP_API_VERSION", cls.whatsapp_api_version),
            llm_provider=_texto("LLM_PROVIDER").lower(),
            anthropic_api_key=_texto("ANTHROPIC_API_KEY"),
            anthropic_model=_texto("ANTHROPIC_MODEL", cls.anthropic_model),
            openai_api_key=_texto("OPENAI_API_KEY"),
            openai_model=_texto("OPENAI_MODEL", cls.openai_model),
            dynamodb_tabla=_texto("DYNAMODB_TABLA", cls.dynamodb_tabla),
            contexto_ttl_seg=_entero("CONTEXTO_TTL_SEG", cls.contexto_ttl_seg),
            google_credentials_file=_texto("GOOGLE_CREDENTIALS_FILE", cls.google_credentials_file),
            google_credentials_json=_texto("GOOGLE_CREDENTIALS_JSON"),
            spreadsheet_id=_texto("SPREADSHEET_ID"),
            hoja_inventario=_texto("HOJA_INVENTARIO", cls.hoja_inventario),
            hoja_ventas=_texto("HOJA_VENTAS", cls.hoja_ventas),
            drive_carpeta_id=_texto("DRIVE_CARPETA_ID"),
            nombre_tienda=_texto("NOMBRE_TIENDA", cls.nombre_tienda),
            numero_asesor=_texto("NUMERO_ASESOR"),
            asesores_autorizados=_lista("ASESORES_AUTORIZADOS"),
            cache_inventario_seg=_entero("CACHE_INVENTARIO_SEG", cls.cache_inventario_seg),
            pausa_media_seg=_decimal("PAUSA_MEDIA_SEG", cls.pausa_media_seg),
        )

    @property
    def proveedor_llm(self) -> str:
        if self.llm_provider:
            return self.llm_provider
        return "anthropic" if self.anthropic_api_key else "openai"

    def faltantes(self) -> list[str]:
        """Variables obligatorias para producción que están vacías."""
        clave_llm = (
            ("ANTHROPIC_API_KEY", self.anthropic_api_key)
            if self.proveedor_llm == "anthropic"
            else ("OPENAI_API_KEY", self.openai_api_key)
        )
        obligatorias = {
            "WHATSAPP_VERIFY_TOKEN": self.whatsapp_verify_token,
            "WHATSAPP_ACCESS_TOKEN": self.whatsapp_access_token,
            "WHATSAPP_PHONE_NUMBER_ID": self.whatsapp_phone_number_id,
            clave_llm[0]: clave_llm[1],
            "SPREADSHEET_ID": self.spreadsheet_id,
            "DRIVE_CARPETA_ID": self.drive_carpeta_id,
            "NUMERO_ASESOR": self.numero_asesor,
        }
        return [nombre for nombre, valor in obligatorias.items() if not valor]

    def puede_cerrar_ventas(self, numero: str) -> bool:
        """Si ASESORES_AUTORIZADOS está vacío, cualquiera puede (comportamiento original)."""
        return not self.asesores_autorizados or numero in self.asesores_autorizados
