# Proceso de venta por WhatsApp

## Flujo correcto
Saludo → búsqueda del producto → confirmación del producto → datos del cliente (nombre, celular, dirección) → **pedido pendiente al asesor** → el asesor confirma con el cliente → **cierre de venta** (descuenta inventario).
El inventario **solo** se descuenta al cerrar la venta, nunca al tomar el pedido.

## Estados de la conversación
| Estado | Qué espera el bot | Siguiente paso |
|---|---|---|
| *(sin estado)* | Cualquier mensaje | Bienvenida + catálogo PDF → `esperando_busqueda` |
| `esperando_busqueda` | Qué producto busca | 1 resultado → `confirmando_producto`; varios → `seleccionando` |
| `seleccionando` | Número de la lista (`0` cancela) | `confirmando_producto` |
| `confirmando_producto` | sí / no | sí → `solicitando_nombre`; no → `esperando_busqueda` |
| `confirmando_continuacion` | sí / no tras una pregunta general | sí → retoma la compra; no → `esperando_busqueda` |
| `solicitando_nombre` | Nombre (1 a 3 palabras, solo letras) | `solicitando_telefono` |
| `solicitando_telefono` | Celular o fijo de Colombia | `solicitando_direccion` |
| `solicitando_direccion` | Dirección de entrega | Pedido al asesor y fin |
| `esperando_codigo` | Código de cierre (asesor) | `esperando_cantidad` |
| `esperando_cantidad` | Unidades vendidas (asesor) | Venta completada y fin |

## Reglas de negocio
| Regla | Qué verifica | Si no se cumple |
|---|---|---|
| RV1 | El producto tiene unidades > 0 | No se ofrece: "registrado pero sin unidades" |
| RV2 | Todas las palabras de la búsqueda coinciden con el nombre (tolerando errores de tipeo) | Se piden sugerencias al LLM sobre el catálogo |
| RV3 | El LLM solo sugiere nombres que existen en el catálogo (similitud ≥ 75) | La sugerencia se descarta |
| RV4 | El nombre del cliente no es "sí/no/ok", no tiene números y tiene de 1 a 3 palabras | Se vuelve a pedir |
| RV5 | Celular `3XXXXXXXXX`, fijo de 7 dígitos o `60XXXXXXXX` | Se vuelve a pedir con un ejemplo |
| RV6 | El código de cierre existe en `registro_ventas` | "Código no encontrado"; se sale del flujo |
| RV7 | La venta no está `completado` | No se descuenta dos veces |
| RV8 | Si `ASESORES_AUTORIZADOS` tiene números, solo ellos cierran ventas | El mensaje se trata como búsqueda normal |
| RV9 | Precio final = cantidad × precio unitario (acepta `45.000`, `$45.000`, `45000`) | Error claro al asesor |

## Preguntas generales
- Se detectan con el clasificador (pregunta general vs. búsqueda). Números de opción, sí/no y teléfonos se resuelven **sin** llamar al LLM.
- Se responden solo con el documento de entrenamiento del negocio.
- Si hay una compra en curso, después de responder se pregunta: "¿Deseas continuar con la compra de …?".

## Glosario
- **Inventario**: hoja `inventario` (numero, servicio, unidades, precio, descripcion).
- **Registro de ventas**: hoja `registro_ventas`; cada pedido entra como `pendiente` y pasa a `completado` al cerrarse.
- **Código de cierre**: 6 caracteres que recibe el asesor con cada pedido.
- **Prefijo de archivos**: las 4 primeras letras del `numero` del producto identifican sus fotos y videos en Drive.
