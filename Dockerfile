# Imagen del agente para AWS Lambda (solución de pago: "Lambda con imagen de contenedor").
#
# Construir (siempre para linux/amd64 y sin "provenance", que Lambda no acepta):
#   docker buildx build --platform linux/amd64 --provenance=false -t agente-ventas-whatsapp:latest --load .
#
# Probar en local (la imagen trae el emulador de Lambda en el puerto 8080):
#   docker run --rm -p 9000:8080 --env-file .env -v "$PWD/credentials.json:/var/task/credentials.json:ro" agente-ventas-whatsapp:latest

# Imagen oficial de AWS con el mismo sistema y Python que usa Lambda
FROM public.ecr.aws/lambda/python:3.11

# 1) Dependencias primero: Docker reutiliza esta capa si requirements.txt no cambió
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt --target "${LAMBDA_TASK_ROOT}" \
    && rm ${LAMBDA_TASK_ROOT}/requirements.txt

# 2) Código del agente (prompts y conocimiento van dentro del paquete)
COPY src/agente_vendedor ${LAMBDA_TASK_ROOT}/agente_vendedor

# Las claves NO van en la imagen: llegan por Secrets Manager (SECRETO_ID) o variables de entorno.

# Función que Lambda ejecuta en cada mensaje
CMD ["agente_vendedor.lambda_handler.handler"]
