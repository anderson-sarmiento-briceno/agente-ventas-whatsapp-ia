# Arquitectura

## 1. Vista general

```mermaid
flowchart LR
    subgraph Clientes
        C([👤 Cliente])
        AS([👔 Asesor])
    end
    subgraph Meta
        W[📱 WhatsApp Cloud API]
    end
    subgraph AWS
        L[⚙️ Lambda<br/>Python 3.11]
        D[(🗄️ DynamoDB<br/>contexto_bot_will)]
    end
    subgraph Google
        S[(📊 Sheets<br/>inventario · registro_ventas)]
        G[(📁 Drive<br/>fotos · videos · catálogo)]
    end
    A[🧠 Claude Haiku 5.5]

    C & AS <--> W
    W -- webhook --> L
    L -- mensajes --> W
    L <--> D
    L <--> S
    L --> G
    L <--> A

    classDef ext fill:#E8F5E9,stroke:#2E7D32,color:#1B5E20
    classDef aws fill:#FFF3E0,stroke:#E65100,color:#BF360C
    classDef ggl fill:#E3F2FD,stroke:#1565C0,color:#0D47A1
    classDef ai fill:#FBE9E7,stroke:#D84315,color:#BF360C
    class C,AS,W ext
    class L,D aws
    class S,G ggl
    class A ai
```

## 2. Capas del código

```mermaid
flowchart TB
    subgraph Entrada
        LH[lambda_handler.py<br/>Mangum + arranque]
        SV[server.py<br/>webhook Flask]
    end
    subgraph Dominio
        AG[agente.py<br/>máquina de estados]
        BU[busqueda.py]
        CL[clasificador.py]
        IN[inventario.py]
        CI[clientes.py]
        VE[ventas.py]
        MK[marketplace.py]
    end
    subgraph Puertos["Interfaces (adapter.py)"]
        P1[ProveedorLLM]
        P2[Mensajero]
        P3[AlmacenContexto]
        P4[Tienda]
    end
    subgraph Adaptadores
        A1[anthropic · openai · falso]
        A2[cloud_api · memoria]
        A3[dynamodb · memoria]
        A4[google · memoria]
    end
    TX[(prompts/ · knowledge/<br/>Markdown)]

    LH --> SV --> AG
    AG --> BU & CL & IN & CI & VE & MK
    CL --> TX
    BU & CL --> P1
    AG & CI & VE --> P2
    AG --> P3
    AG & IN & VE --> P4
    P1 --- A1
    P2 --- A2
    P3 --- A3
    P4 --- A4
```

**Regla de dependencias:** el dominio solo conoce las interfaces. `dependencias.py` arma el objeto `Dependencias` con los adaptadores reales (producción) o en memoria (tests y `demo.py`).

## 3. Recorrido de un mensaje

```mermaid
sequenceDiagram
    autonumber
    participant C as 👤 Cliente
    participant W as WhatsApp API
    participant S as server.py
    participant A as agente.py
    participant D as DynamoDB
    participant T as Sheets / Drive
    participant L as Claude

    C->>W: "algo para proteger la cabeza"
    W->>S: POST / (webhook)
    S->>S: extraer número y texto
    S->>A: procesar_mensaje()
    A->>D: obtener contexto
    A->>T: inventario (caché 5 min)
    A->>L: ¿pregunta general o búsqueda?
    L-->>A: False (búsqueda)
    A->>A: búsqueda difusa → sin coincidencias
    A->>L: sugerir productos del catálogo
    L-->>A: "Casco integral negro mate, ..."
    A->>A: mapear a productos reales + filtrar stock
    A->>T: fotos del producto (Drive)
    A->>W: imagen + ficha + "¿Es este el producto?"
    A->>D: guardar estado confirmando_producto
    S-->>W: 200 {"status": "ok"}
    W->>C: mensajes
```

## 4. Estados de la conversación

```mermaid
stateDiagram-v2
    [*] --> esperando_busqueda: bienvenida + catálogo PDF
    esperando_busqueda --> seleccionando: varios resultados
    esperando_busqueda --> confirmando_producto: un resultado
    seleccionando --> confirmando_producto: elige número
    seleccionando --> [*]: 0 = cancelar
    confirmando_producto --> solicitando_nombre: sí
    confirmando_producto --> esperando_busqueda: no
    confirmando_producto --> confirmando_continuacion: pregunta general
    seleccionando --> confirmando_continuacion: pregunta general
    confirmando_continuacion --> solicitando_nombre: sí
    confirmando_continuacion --> esperando_busqueda: no
    solicitando_nombre --> solicitando_telefono: nombre válido
    solicitando_telefono --> solicitando_direccion: teléfono válido
    solicitando_direccion --> [*]: pedido pendiente → asesor

    state "Flujo del asesor" as asesor {
        [*] --> esperando_codigo: cerrar venta
        esperando_codigo --> esperando_cantidad
        esperando_cantidad --> [*]: venta completada y descuenta inventario
    }
```

## 5. Ciclo de vida de una venta

```mermaid
sequenceDiagram
    participant C as 👤 Cliente
    participant B as 🤖 Agente
    participant H as 📊 registro_ventas
    participant I as 📊 inventario
    participant AS as 👔 Asesor

    C->>B: nombre, celular, dirección
    B->>H: fila nueva · estado = pendiente · código ABC123
    B->>AS: 📦 Nuevo pedido · código ABC123
    B->>C: ✅ Gracias por tu pedido
    AS-->>C: confirma entrega (fuera del bot)
    AS->>B: cerrar venta → ABC123 → 2
    B->>H: ¿existe y no está completado?
    B->>I: unidades -= 2
    B->>H: cantidad = 2 · estado = completado · precio final
    B->>AS: ✅ Venta cerrada · $90,000.00
```

## 6. Datos

| Almacén | Clave | Contenido |
|---|---|---|
| DynamoDB `contexto_bot_will` | `whatsapp_number` | `context` (JSON con `estado_usuarios_data` y `codigos_venta_data`) y `expire_at` (TTL 24 h) |
| Sheets `inventario` | fila | `numero` · `servicio` · `unidades` · `precio` · `descripcion` |
| Sheets `registro_ventas` | fila | Fecha · Nombre · Teléfono · Dirección · Producto · CódigoProducto · Cantidad · Asesor · CódigoVenta · estado · PrecioFinal |
| Drive (carpeta) | nombre de archivo | `GPMR01-frente.jpg`, `GPMR01-video.mp4`… y el PDF del catálogo (el más reciente) |

## 7. Despliegue

```mermaid
flowchart LR
    DEV[💻 Repositorio] -->|scripts/empaquetar_lambda.py| ZIP[📦 dist/lambda.zip<br/>wheels manylinux + código + credentials.json]
    ZIP -->|subir| LAM[⚙️ AWS Lambda<br/>handler: agente_vendedor.lambda_handler.handler]
    ENV[🔐 Variables de entorno<br/>.env.example] --> LAM
    LAM -->|URL de la función| META[📱 Webhook en Meta]
```
