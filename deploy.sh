#!/bin/bash
# Despliegue en Google Cloud Functions

# CONFIGURAR ESTO:
PROJECT_ID="TU_PROYECTO_GCP_AQUI"  # <-- REEMPLAZAR

# Configurar proyecto
gcloud config set project $PROJECT_ID

# Habilitar APIs necesarias
gcloud services enable cloudfunctions.googleapis.com gmail.googleapis.com

# Desplegar función
gcloud functions deploy gmail-webhook \
  --gen2 \
  --runtime=python311 \
  --region=europe-west1 \
  --source=. \
  --entry-point=gmail_webhook \
  --trigger-http \
  --allow-unauthenticated

echo "Webhook deployado. URL:"
gcloud functions describe gmail-webhook --region=europe-west1 --format='value(httpsTrigger.url)'