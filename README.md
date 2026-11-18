<div align="center">

# 🛵 Agente de Ventas por WhatsApp con IA

**Agente conversacional que vende por WhatsApp: encuentra productos en el inventario aunque el cliente no use el nombre exacto, muestra fotos y precios, resuelve dudas del negocio, toma el pedido y deja que el asesor cierre la venta desde el mismo chat.**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Haiku_5.5-D97757?style=flat-square&logo=anthropic&logoColor=white)
![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=flat-square&logo=awslambda&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?style=flat-square&logo=amazondynamodb&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp_Cloud_API-25D366?style=flat-square&logo=whatsapp&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google_Sheets-34A853?style=flat-square&logo=googlesheets&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3-000000?style=flat-square&logo=flask&logoColor=white)
![Tests](https://img.shields.io/badge/tests-171_passing-2ea44f?style=flat-square&logo=pytest&logoColor=white)

[Contexto](docs/CONTEXTO.md) · [Arquitectura](docs/ARQUITECTURA.md) · [Proceso de venta](src/agente_vendedor/knowledge/proceso-ventas.md) · [Conocimiento del negocio](src/agente_vendedor/knowledge/negocio.md)

</div>

---

## ✨ Qué hace

| | Característica | Detalle |
|:-:|---|---|
| 🔎 | **Búsqueda semántica** | "algo para proteger la cabeza" → cascos; "retrovisor" → espejos. Primero coincidencia difusa (tolera errores de tipeo) y, si no hay resultados, Claude sugiere productos **reales** del catálogo. |
| 📦 | **Stock en tiempo real** | Lee el inventario de Google Sheets (con caché) y solo ofrece productos con unidades. |
| 🖼️ | **Fotos y videos** | Envía las imágenes y videos del producto desde Google Drive antes de la ficha con precio. |
| 💬 | **Dudas del negocio** | Horarios, envíos, garantía, tallas… se responden con el [documento de entrenamiento](src/agente_vendedor/knowledge/negocio.md); luego ofrece retomar la compra. |
| 📝 | **Captura del pedido** | Nombre, celular (validado para Colombia) y dirección; el pedido queda *pendiente* y le llega al asesor con un código. |
| 🔐 | **Cierre por el asesor** | `cerrar venta` → código → cantidad: descuenta inventario, calcula el total y evita cerrar dos veces. |
| 🛡️ | **Reglas deterministas** | Stock, precios y validaciones son código ([RV1–RV9](src/agente_vendedor/knowledge/proceso-ventas.md#reglas-de-negocio)); el modelo nunca inventa productos ni precios. |
| 🔌 | **Arquitectura desacoplada** | LLM, WhatsApp, contexto y tienda detrás de interfaces: cambiar Claude ↔ OpenAI es una variable de entorno. |
| 💰 | **Bajo costo** | ~**USD 0,0008** por conversación completa con Claude Haiku 5.5 (medido). |

---

## 🏗️ Arquitectura

```mermaid
flowchart LR
    C([👤 Cliente]) -->|WhatsApp| W[📱 Meta Cloud API]
    W -->|webhook| L[⚙️ AWS Lambda<br/>lambda_handler.py]
    L --> S[🌐 Flask<br/>server.py]
    S --> A[🔄 Máquina de estados<br/>agente.py]
    A --> B[🔎 Búsqueda<br/>busqueda.py]
    A --> K[💬 Clasificador<br/>clasificador.py]
    A --> V[🧾 Pedidos y cierre<br/>clientes.py · ventas.py]
    A <-->|AlmacenContexto| D[(🗄️ DynamoDB)]
    B & K <-->|ProveedorLLM| O[🧠 Claude Haiku 5.5]
    A & V <-->|Tienda| G[(📊 Sheets + 📁 Drive)]
    A -->|Mensajero| W
    T[🧪 tests/ · demo.py<br/>dobles en memoria] -.-> A

    classDef ext fill:#E8F5E9,stroke:#2E7D32,color:#1B5E20
    classDef core fill:#E3F2FD,stroke:#1565C0,color:#0D47A1
    classDef ai fill:#FBE9E7,stroke:#D84315,color:#BF360C
    classDef data fill:#FFF8E1,stroke:#F9A825,color:#7A5A00
    class C,W ext
    class L,S,A,B,K,V core
    class O ai
    class D,G,T data
```

**Principio de diseño:** el modelo clasifica, redacta y sugiere; **la lógica de negocio vive en el código**. Por eso `demo.py` y los tests recorren conversaciones completas sin ningún servicio externo.

Más diagramas (capas, recorrido de un mensaje, estados, ciclo de una venta, despliegue) en **[docs/ARQUITECTURA.md](docs/ARQUITECTURA.md)**.

### 🔄 Estados de la conversación

```mermaid
stateDiagram-v2
    [*] --> esperando_busqueda: bienvenida + catálogo PDF
    esperando_busqueda --> seleccionando: varios resultados
    esperando_busqueda --> confirmando_producto: un resultado
    seleccionando --> confirmando_producto: elige número
    confirmando_producto --> solicitando_nombre: sí
    confirmando_producto --> confirmando_continuacion: pregunta general
    confirmando_continuacion --> solicitando_nombre: sí
    solicitando_nombre --> solicitando_telefono
    solicitando_telefono --> solicitando_direccion
    solicitando_direccion --> [*]: pedido al asesor
```

---

## 📁 Estructura

```
.
├── src/agente_vendedor/
│   ├── agente.py              # máquina de estados de la conversación
│   ├── server.py              # webhook Flask (verificación + mensajes)
│   ├── lambda_handler.py      # entrada de AWS Lambda (Mangum)
│   ├── config.py · dependencias.py
│   ├── busqueda.py            # búsqueda difusa + sugerencias del LLM
│   ├── clasificador.py        # pregunta general vs. búsqueda, y respuestas
│   ├── inventario.py          # stock, formatos de mensaje, archivos de Drive
│   ├── clientes.py · ventas.py  # captura del pedido y cierre de venta
│   ├── marketplace.py         # enlaces de Facebook Marketplace
│   ├── prompts/               # clasificador.md · respuesta.md
│   ├── knowledge/             # negocio.md · proceso-ventas.md
│   ├── llm/                   # ProveedorLLM: anthropic · openai · falso
│   ├── whatsapp/              # Mensajero: cloud_api · memoria
│   ├── contexto/              # AlmacenContexto: dynamodb · memoria
│   └── tienda/                # Tienda: google · memoria
├── .claude/skills/            # skills para Claude Code (desarrollo y negocio)
├── docs/                      # CONTEXTO.md · ARQUITECTURA.md
├── tests/                     # 171 tests, sin red ni claves
├── fixtures/                  # inventario, Drive y webhooks de ejemplo
├── scripts/                   # empaquetar_lambda · verificar_config · generar_skill
└── demo.py                    # conversación en consola
```

---

## 🚀 Inicio rápido

> Requiere **Python 3.11+**.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements-dev.txt
cp .env.example .env              # completar ANTHROPIC_API_KEY y demás valores
```

### 🧪 Tests (no requieren claves)

```bash
pytest            # 171 tests
pytest --cov      # con cobertura
```

### 💬 Demo en consola

Usa el inventario de `fixtures/`. Con `ANTHROPIC_API_KEY` en `.env` conversa con Claude real; sin ella, con un LLM simulado.

```bash
python demo.py --guion    # compra completa + cierre de venta
python demo.py            # interactivo ("!texto" para hablar como asesor)
```

### 🔍 Verificar configuración

```bash
python scripts/verificar_config.py            # variables, credenciales, prompts
python scripts/verificar_config.py --online   # además se conecta a Google Sheets/Drive
```

---

## ☁️ Despliegue en AWS Lambda

1. **Empaquetar** (desde cualquier sistema operativo; descarga wheels de Linux):
   ```bash
   python scripts/empaquetar_lambda.py          # x86_64   (--arm64 para Graviton)
   ```
2. **Subir** `dist/lambda.zip` a una función con runtime **Python 3.11**.
3. **Handler:** `agente_vendedor.lambda_handler.handler`
4. **Variables de entorno:** las de [`.env.example`](.env.example) (`LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, WhatsApp, Google…).
5. **Permisos:** el rol necesita `dynamodb:GetItem`, `PutItem` y `DeleteItem` sobre `contexto_bot_will` (TTL en `expire_at`).
6. **Webhook:** registra la URL de la función en Meta con tu `WHATSAPP_VERIFY_TOKEN`.

---

## 🤖 Trabajar con Claude Code

El repositorio incluye dos skills en `.claude/skills/`:

| Skill | Para qué |
|---|---|
| `agente-ventas-whatsapp` | Comandos, recetas (cambiar conocimiento, agregar estados o proveedores) y reglas de desarrollo |
| `ventas-motopro` | Conocimiento del negocio y del proceso de venta; **se genera** desde `knowledge/` con `scripts/generar_skill.py` |

---

## 🧰 Stack tecnológico

| Capa | Tecnología | Uso |
|---|---|---|
| **Runtime** | ![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white) ![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=flat-square&logo=awslambda&logoColor=white) | Función sin servidor detrás del webhook |
| **Web** | ![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white) | Webhook de WhatsApp, adaptado a Lambda con Mangum |
| **IA** | ![Claude](https://img.shields.io/badge/Claude_Haiku_5.5-D97757?style=flat-square&logo=anthropic&logoColor=white) | Clasificación, respuestas del negocio y búsqueda semántica (OpenAI como alternativa) |
| **Mensajería** | ![WhatsApp](https://img.shields.io/badge/WhatsApp_Cloud_API-25D366?style=flat-square&logo=whatsapp&logoColor=white) | Texto, imágenes, videos y documentos |
| **Datos** | ![Google Sheets](https://img.shields.io/badge/Sheets-34A853?style=flat-square&logo=googlesheets&logoColor=white) ![Google Drive](https://img.shields.io/badge/Drive-4285F4?style=flat-square&logo=googledrive&logoColor=white) | Inventario, registro de ventas, fotos y catálogo |
| **Estado** | ![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?style=flat-square&logo=amazondynamodb&logoColor=white) | Contexto de cada conversación con expiración de 24 h |
| **Búsqueda** | fuzzywuzzy + Levenshtein | Coincidencia difusa de nombres de producto |
| **Tests** | ![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white) | Unitarios y conversaciones completas |

---

<div align="center">

Hecho por **Anderson Sarmiento Briceño**

</div>
