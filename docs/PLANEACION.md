# Planeación del agente

> Las preguntas que conviene responder **antes** de construir cualquier agente, aplicadas a este. Si vas a construir otro agente, copia los títulos y responde cada uno.
>
> El detalle técnico está en [ARQUITECTURA.md](ARQUITECTURA.md) y la historia de cambios en [CONTEXTO.md](CONTEXTO.md).

---

## 1. El problema en una frase
La tienda pierde ventas por WhatsApp porque nadie alcanza a responder rápido a cada cliente: buscar el producto, enviar fotos y precio, resolver dudas y anotar el pedido se hace a mano, y el inventario se desactualiza.

## 2. Quién lo usa y qué gana
| Usuario | Hoy | Con el agente |
|---|---|---|
| 👤 Cliente | Espera a que alguien le conteste | Respuesta inmediata, fotos y precio, a cualquier hora |
| 👔 Asesor | Busca productos y anota pedidos a mano | Recibe el pedido listo con un código y lo cierra con 3 mensajes |
| 🏪 Dueño | No sabe cuántos pedidos se pierden | Cada pedido queda registrado como *pendiente* o *completado* |

## 3. Qué hace el modelo y qué hace el código
La decisión más importante: **el modelo conversa, el código decide.**

| Lo hace el modelo (Claude) | Lo hace el código |
|---|---|
| Distinguir si el mensaje es una pregunta o una búsqueda | Revisar stock y precios |
| Responder dudas del negocio con el documento de entrenamiento | Validar nombre y teléfono |
| Sugerir productos cuando el cliente no usa el nombre exacto | Registrar el pedido y cerrar la venta |
| | Descontar el inventario |

Así el modelo nunca puede inventar un precio, vender algo agotado ni cerrar una venta.

## 4. Elección del modelo
- **Modelo:** `claude-haiku-5-5`, sin razonamiento previo y con `effort: low`.
- **Por qué:** las tareas del modelo son cortas (clasificar, responder en 2 líneas, sugerir nombres). Un modelo más grande no da respuestas más correctas, pero sí cuesta más y tarda más.
- **Costo medido** con la API real:

| Prueba | Llamadas | Tokens | Costo |
|---|---|---|---|
| Conversación completa (saludo, búsqueda, pregunta, pedido) | 6 | ~7.400 | ~USD 0,0008 |

Aproximadamente **USD 0,80 por cada 1.000 conversaciones**. Los tests y `demo.py` sin clave cuestan USD 0.

## 5. Reglas
Las reglas de negocio **RV1–RV9** (stock, nombre, teléfono, código de cierre, precio…) están en [proceso-ventas.md](../src/agente_vendedor/knowledge/proceso-ventas.md#reglas-de-negocio), y las reglas de respuesta del modelo en [negocio.md](../src/agente_vendedor/knowledge/negocio.md#reglas-de-respuesta). Todas son código o texto versionado, no "lo que el modelo recuerde".

## 6. Integraciones
| Sistema | Para qué | Si falla |
|---|---|---|
| WhatsApp Cloud API | Recibir y enviar mensajes | Se registra el error; la conversación sigue |
| Google Sheets | Inventario y registro de ventas | Se usa la caché del inventario; si no hay, se pide intentar en 1 minuto |
| Google Drive | Fotos, videos y catálogo PDF | Se envía la ficha sin fotos |
| DynamoDB | Recordar en qué paso va cada cliente (24 h) | La conversación empieza de nuevo |
| Claude | Clasificar, responder, sugerir | Se trata como búsqueda y se usa una respuesta genérica |

Cada sistema está detrás de una interfaz: cambiarlo (por ejemplo, Sheets por una base de datos) no toca la conversación.

## 7. Decisiones y alternativas
| # | Decisión | Alternativa descartada | Por qué |
|---|---|---|---|
| 1 | Máquina de estados en código | Un agente con herramientas que decide los pasos | El flujo de venta es fijo y conocido; un agente libre sería más caro y menos predecible |
| 2 | Búsqueda difusa primero y Claude solo si no hay resultados | Siempre buscar con Claude | La mayoría de búsquedas se resuelven gratis y en milisegundos |
| 3 | Google Sheets como inventario | Una base de datos | El dueño ya lo usa y lo edita sin ayuda. A cambio, no hay bloqueo si dos personas escriben al mismo tiempo |
| 4 | El asesor cierra la venta desde WhatsApp | Un panel web | No hay que construir ni aprender otra herramienta |
| 5 | Claude Haiku 5.5 | OpenAI `gpt-4o-mini` (versión 1) | La cuenta de OpenAI se quedó sin créditos; Haiku acertó 6/6 en el clasificador y es más barato |

## 8. Supuestos
1. Todos los clientes y asesores están en **Colombia** (validación de teléfonos `3XXXXXXXXX`, `60XXXXXXXX` o 7 dígitos).
2. Los precios están en **pesos colombianos** y pueden venir como `45000`, `45.000` o `$45.000`.
3. Las fotos de un producto se identifican por las **4 primeras letras** de su código (`GPMR01` → `GPMR01-frente.jpg`).
4. El pedido se registra con **1 unidad**: la cantidad real la indica el asesor al cerrar la venta.
5. Si un cliente no escribe en 24 horas, su conversación se olvida.
6. El catálogo PDF que se envía es el **más reciente** de la carpeta de Drive.
7. Las fechas del registro usan la hora del servidor (en Lambda, UTC).

## 9. Estado
| Funcionalidad | Estado | Nota |
|---|---|---|
| Búsqueda, fotos y ficha del producto | ✅ | Probado con Claude real |
| Preguntas generales y retomar la compra | ✅ | |
| Captura del pedido y aviso al asesor | ✅ | |
| Cierre de venta y descuento de inventario | ✅ | |
| Enlaces de Facebook Marketplace | 🟡 | Funciona en local; desde AWS Facebook suele bloquear la lectura |
| Despliegue de la versión 2 en Lambda | ⏳ | Paquete listo en `dist/lambda.zip` |
| Cantidad pedida por el cliente en el pedido | ❌ | Ver supuesto 4 |

## 10. Riesgos
| Riesgo | Mitigación |
|---|---|
| Un cliente escribe "cerrar venta" y cierra pedidos | Configurar `ASESORES_AUTORIZADOS` (hoy vacío = cualquiera) |
| WhatsApp reenvía un mensaje si la respuesta tarda, y se procesa dos veces | Hoy no se filtra; pendiente descartar mensajes repetidos por su `id` |
| Un cliente intenta manipular al modelo con instrucciones en el mensaje | El modelo no tiene herramientas: solo clasifica y responde con el documento del negocio. Stock, precios y ventas son código |
| El modelo responde algo que no está en el documento | Regla "no inventar" en [negocio.md](../src/agente_vendedor/knowledge/negocio.md); respuestas máximo de 2-3 líneas |
| Dos asesores cierran ventas al mismo tiempo en Sheets | Bajo volumen hoy; si crece, pasar el registro a una base de datos con transacciones |
| Uso abusivo (muchos mensajes) aumenta el costo | Costo bajo por mensaje; si hace falta, límite de mensajes por número |
| Datos personales de clientes (nombre, teléfono, dirección) | Solo en la hoja privada del negocio; tratarlos según la ley colombiana de protección de datos (Ley 1581 de 2012) |
| Credenciales de la versión 1 estuvieron en el código | Rotar el token de WhatsApp y la clave de OpenAI |

## 11. Cómo medir si funciona
Con el registro de ventas ya se puede medir:
- **Pedidos por día** y cuántos pasan de *pendiente* a *completado*.
- **Pedidos sin cerrar** después de 2 días (asesor que no hizo seguimiento).

Con poco esfuerzo adicional (registrar las búsquedas):
- **Búsquedas sin resultado**: qué productos piden los clientes y la tienda no tiene.
- **Conversión**: de cada 100 conversaciones, cuántas terminan en pedido.

## 12. Uso de IA en el desarrollo
- **Asistente:** Claude Code (Claude Opus 5.5) en VS Code.
- **Para qué:** reestructurar el código de la versión 1, escribir los tests, migrar de OpenAI a Claude, documentar y empaquetar para Lambda.
- **Qué detectó la IA:** el paquete de Lambda sin `bs4` y con binarios de Windows (causa de que Marketplace fallara en AWS), la caché de inventario que nunca funcionaba y la búsqueda con LLM que devolvía siempre los mismos productos.
- **Rol humano:** definir el negocio, las reglas y el alcance; probar los flujos y decidir qué se despliega.
