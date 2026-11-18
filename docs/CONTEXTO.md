# Contexto del proyecto

> Documento vivo para quien llega al repositorio (persona o agente de IA): qué es el sistema, por qué está construido así, qué reglas no se negocian y qué queda pendiente.
> Las preguntas de planeación (problema, modelo, supuestos, riesgos, métricas) están en [PLANEACION.md](PLANEACION.md).

## 1. Qué es
**Agente de ventas por WhatsApp con IA** para *Accesorios MotoPro*, una tienda de accesorios para moto en Kennedy Tintal (Bogotá).

El cliente escribe por WhatsApp; el agente busca el producto en el inventario (Google Sheets), envía fotos/videos (Google Drive), resuelve dudas del negocio con Claude, toma los datos del pedido y avisa al asesor. El asesor confirma con el cliente y **cierra la venta desde el mismo chat**, lo que descuenta el inventario.

| Actor | Qué hace |
|---|---|
| 👤 Cliente | Busca productos, pregunta, hace el pedido |
| 👔 Asesor | Recibe el pedido con un código y cierra la venta (`cerrar venta`) |
| 🤖 Agente | Conversa, busca, valida datos y registra todo en Google Sheets |

## 2. Principios de diseño
1. **La lógica de negocio es código, no decisiones del modelo.** El LLM solo clasifica mensajes, redacta respuestas sobre el negocio y sugiere productos; stock, precios, validaciones y cierre de venta son deterministas.
2. **El LLM nunca inventa productos.** Sus sugerencias se mapean a nombres reales del catálogo (similitud ≥ 75) o se descartan.
3. **Arquitectura desacoplada.** WhatsApp, LLM, almacén de contexto y tienda están detrás de interfaces (`adapter.py`). Cambiar de proveedor = escribir otra implementación.
4. **Fallar con elegancia.** Un error externo nunca devuelve 500 al webhook (WhatsApp reintentaría el mensaje): se registra y el cliente recibe un mensaje claro.
5. **Sin secretos en el repositorio.** Todo va en variables de entorno.
6. **Probado sin red.** Los 170+ tests y `demo.py` usan dobles en memoria: no necesitan claves ni internet.

## 3. Reglas obligatorias
Las reglas de negocio (RV1–RV9) están en [`knowledge/proceso-ventas.md`](../src/agente_vendedor/knowledge/proceso-ventas.md) y las de respuesta en [`knowledge/negocio.md`](../src/agente_vendedor/knowledge/negocio.md). Para quien desarrolla:

| # | Regla |
|---|---|
| D1 | Ninguna clave, token o ID privado en código, tests o fixtures. |
| D2 | Nunca subir `.env`, `credentials.json`, `_respaldo_original/`, `.vscode/`, `build/`, `dist/`. |
| D3 | Cada corrección de comportamiento va con un test que fallaba antes. |
| D4 | Compatible con Python 3.11 (runtime de AWS Lambda). |
| D5 | Los textos para el LLM viven en `prompts/` y `knowledge/` (Markdown), no en el código. |
| D6 | La skill `.claude/skills/ventas-motopro` se genera con `scripts/generar_skill.py`; un test verifica que esté al día. |
| D7 | El contexto en DynamoDB conserva la forma `{"estado_usuarios_data", "codigos_venta_data"}` para no romper conversaciones en curso. |

## 4. Historia y decisiones

### Versión 1 (julio 2025)
Prototipo funcional en AWS Lambda: `servidor.py`, `funciones.py`, `filtro.py`, `respuesta_modelo.py` y `captura_enlace.py` en una sola carpeta, con OpenAI `gpt-4o-mini` y claves escritas en el código.

### Versión 2 (noviembre 2026): esta reestructuración
| Cambio | Motivo |
|---|---|
| Paquete `src/agente_vendedor/` por responsabilidad | Un archivo de 900 líneas mezclaba HTTP, estados, Sheets y WhatsApp |
| Adaptadores con versión real + en memoria | Poder probar todo sin servicios externos |
| Claves a variables de entorno | Estaban en el código (token de WhatsApp, clave de OpenAI) |
| **Claude Haiku 5.5** como LLM (`LLM_PROVIDER`) | La cuenta de OpenAI se quedó sin créditos; Haiku es rápido y barato (~USD 0.0008 por conversación) |
| Thinking desactivado y `effort: low` | El clasificador usa 5 tokens: con razonamiento la respuesta podía llegar vacía |
| Empaquetado con wheels de Linux | El zip anterior traía binarios `.pyd` de Windows y le faltaba `bs4/`: por eso los enlaces de Marketplace fallaban en AWS |
| Prompts y conocimiento en Markdown | Editables sin tocar Python; antes estaban en código y en un `.docx` |
| 169 tests + `demo.py` | No había pruebas |

### Errores heredados corregidos
| Error | Corrección |
|---|---|
| Función `obtener_datos_actualizados` duplicada: la caché del inventario nunca funcionaba | Una sola implementación con caché configurable |
| La búsqueda con LLM partía el catálogo en 8 trozos: con pocos productos devolvía cualquier cosa | Catálogo completo en bloques de 200 y opción `NINGUNO` |
| "sí" se aceptaba como nombre del cliente | Validación `parece_nombre` (RV4) |
| Un código de cierre inexistente dejaba al asesor atascado | Siempre se sale del flujo; se reintenta con `cerrar venta` |
| `"45.000"` se leía como 45 pesos al cerrar la venta | `a_precio` entiende el formato colombiano (RV9) |
| `registrar_venta` devolvía el total de filas de la hoja, no la fila insertada | Se lee la fila de la respuesta de la API |
| Los logs imprimían el token de WhatsApp | Los headers ya no se registran |
| Respuestas de botones (`button_reply`) se ignoraban | Se soportan texto, botones, listas y respuestas rápidas |

## 5. Estado actual y pendientes
- ✅ Funciona en local con Claude (verificado con la API real: clasificador 6/6, búsqueda semántica correcta).
- ⏳ **Desplegar la versión 2 en Lambda:** handler `agente_vendedor.lambda_handler.handler` + variables de `.env.example`.
- ⏳ **Rotar credenciales antiguas:** el token de WhatsApp y la clave de OpenAI estuvieron en el código de la versión 1.
- ⏳ Configurar `ASESORES_AUTORIZADOS` para que solo el asesor pueda cerrar ventas.
- ⚠️ Facebook suele bloquear la lectura de enlaces de Marketplace desde IPs de AWS; el agente pide entonces el nombre del producto.
- 💡 Futuro: zona horaria `America/Bogota` en las fechas del registro (hoy usa la hora del servidor), Workload Identity Federation en lugar de clave de API.

## 6. Glosario
| Término | Significado |
|---|---|
| Contexto | Estado de la conversación de cada número, guardado en DynamoDB 24 h |
| Código de cierre | 6 caracteres que identifican un pedido pendiente |
| Prefijo | 4 primeras letras del código del producto; agrupa sus archivos en Drive |
| Pregunta general | Mensaje sobre el negocio (horarios, envíos…), no una búsqueda |
| Doble en memoria | Implementación falsa de un adaptador para tests (`memoria.py`, `falso.py`) |
