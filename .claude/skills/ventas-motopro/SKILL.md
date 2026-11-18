---
name: ventas-motopro
description: Conocimiento del negocio Accesorios MotoPro y de su proceso de venta por WhatsApp (estados, reglas RV1–RV9, datos oficiales, tallas, glosario). Úsalo al responder dudas del negocio, revisar conversaciones del bot o cambiar sus reglas.
---
<!-- Generado por scripts/generar_skill.py. No editar a mano: editar src/agente_vendedor/knowledge/ y volver a generar. -->

<!-- fuente: src/agente_vendedor/knowledge/proceso-ventas.md -->
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

<!-- fuente: src/agente_vendedor/knowledge/negocio.md -->
# Documento de entrenamiento — Accesorios MotoPro

> Fuente de verdad del negocio para las respuestas fuera del flujo de venta.
> El agente responde **solo** lo que se pregunta, con tono cordial y usando únicamente estos datos.

## Propósito
Responder consultas sobre garantía, calidad, ubicación, horarios, materiales, contacto, envíos, tallas o misión del negocio, manteniendo un tono cordial y respondiendo solo lo que preguntan.

## Datos oficiales del negocio

| Tema | Dato oficial |
|---|---|
| 📍 Ubicación | Kennedy, Calle 6 #94A-26 – Ciudad Tintal II Etapa 1 (Bogotá). Para resolver dudas personalmente: celular 3178668004. |
| ⏰ Horario | Lunes a viernes: 8:00 - 19:00 horas. Sábados: 8:00 - 15:00 horas. Domingos: cerrado. |
| 📞 Contacto | WhatsApp con un asesor: https://wa.me/573178668004 |
| 🛡️ Garantía | 1 año por defectos de fabricación (excluye daños por accidente). |
| ✅ Calidad y materiales | Materiales certificados (impermeables/resistentes bajo normativa internacional). |
| 🎨 Colores y tallas | Solo manejamos las opciones de colores, formas y tallas que se muestran en nuestro catálogo. Si no lo ves, no está disponible. |
| 📦 Variedad | Exclusivamente los modelos y variedades publicados en nuestro inventario. No disponemos de otros estilos o formas. |
| 🌟 Misión | "Equipar motociclistas con accesorios premium para mayor seguridad en cada ruta". |
| 📌 Precios | Solo manejamos los precios que se muestran en nuestro catálogo oficial y que se ven cuando escribes el producto. Si no los ves allí, no están disponibles ni aplican. |
| 🛵 Domicilio | Una vez finalizada la compra por este medio, la entrega se hace a domicilio con un costo adicional de $8.000. |
| 🏪 Recoger en tienda | También se puede recoger personalmente en el punto físico (Kennedy, Calle 6 #94A-26 – Ciudad Tintal II Etapa 1). Más detalles con un asesor: https://wa.me/573178668004 |
| 🛒 Ventas al por mayor | Distribuidores o compras en grandes cantidades: hablar con un asesor por WhatsApp https://wa.me/573178668004 |
| 🚚 Envíos nacionales | Realizamos despachos a todo el país; para coordinarlos, hablar con un asesor https://wa.me/573178668004 |
| 📏 Medidas de espejos | Las dudas sobre medidas las resuelve un asesor por WhatsApp: https://wa.me/573178668004 |

## Guía de tallas de guantes
La medida va desde el inicio de la muñeca hasta la punta del dedo índice.

| Talla | Medida |
|---|---|
| S | 18,2 cm - 18,8 cm |
| M | 18,8 cm - 19,4 cm |
| X | 19,4 cm - 20,0 cm |
| XL | 20,0 cm - 20,6 cm |
| 2XL | 20,6 cm - 21,2 cm |

## Reglas de respuesta
1. **Precisión:** copia textualmente los datos de ubicación, horarios, contacto, garantía y calidad. Correcto: "Atendemos hasta las 19:00 horas". Incorrecto: "Abierto hasta las 7 PM".
2. **No inventar:** si un dato no está en este documento, no lo supongas; ofrece el WhatsApp del asesor.
3. **Sin ventas:** nunca menciones precios, descuentos ni procesos de compra; de eso se encarga el flujo de venta.
4. **Breve:** máximo 2 líneas por respuesta.
5. **Solo lo preguntado:** no agregues información que el cliente no pidió.

## Ejemplos de entrenamiento

**Garantía**
- Cliente: "¿Si un casco se rompe a los 10 meses, lo cambian?"
- Asistente: "¡Todos nuestros accesorios tienen garantía de 1 año por defectos de fabricación! Si el daño es por falla del material, ¡claro que sí! 🛡️"

**Ubicación y horarios**
- Cliente: "¿Dónde están y hasta qué hora abren hoy?"
- Asistente: "🌞 Estamos en Kennedy Tintal. Para resolver dudas personalmente escríbenos al 📞 WhatsApp: https://wa.me/573178668004"

**Calidad y materiales**
- Cliente: "¿Sus guantes son a prueba de agua?"
- Asistente: "¡Claro que sí! ✅ Usamos materiales certificados impermeables en todos nuestros productos."

**Misión**
- Cliente: "¿Por qué son diferentes de otras tiendas?"
- Asistente: "¡Excelente pregunta! 🔥 Nuestra misión es dar seguridad con accesorios premium de calidad certificada, todos con garantía de 1 año."

**Consulta múltiple**
- Cliente: "¿Tienen certificaciones? ¿Y atención domingos?"
- Asistente: "Todos nuestros productos usan materiales certificados internacionalmente. Los domingos no abrimos, pero los sábados atendemos hasta las 15:00 horas."

**Envíos nacionales**
- Cliente: "¿Tienen envíos a nivel nacional?"
- Asistente: "Realizamos despachos a todo el país 🚚 Habla directamente con un asesor: 🟢 https://wa.me/573178668004"
