# GastoTracker - Automatización de tickets de supermercado

Sistema automatizado para procesar tickets de supermercado y registrarlos en Google Sheets y Supabase.

## Arquitectura

```
ticket-processor/
├── cmd/
│   └── server/          # Punto de entrada main
├── internal/
│   ├── email/           # Gmail integration (gog)
│   ├── parser/          # PDF/text/image parsing
│   ├── classifier/      # AI clasificación productos
│   ├── sheets/          # Google Sheets integration
│   └── supabase/        # Supabase client
├── configs/
│   └── config.yaml      # Configuración
└── pkg/
    └── models/          # Modelos de datos
```

## Configuración

Variables de entorno requeridas:
- `GOG_REFRESH_TOKEN` - OAuth refresh token
- `GOG_CLIENT_ID` - Google OAuth client ID
- `GOG_CLIENT_SECRET` - Google OAuth client secret
- `SUPABASE_URL` - URL del proyecto Supabase
- `SUPABASE_KEY` - API key de Supabase
- `SHEET_ID` - ID de la hoja de Google Sheets

## Deployment (Google Cloud Run)

```bash
gcloud run deploy ticket-processor \
  --source . \
  --region europe-west1 \
  --set-secrets GOG_REFRESH_TOKEN=gog-token:latest
```

## Funcionalidades

- [x] Detección automática de emails con tickets
- [x] Parsing de PDFs adjuntos
- [x] Parsing de texto plano
- [ ] Parsing de imágenes (OCR)
- [x] Clasificación automática de productos (2 niveles)
- [x] Registro en Google Sheets
- [ ] Registro en Supabase
- [x] Etiquetado automático de emails
- [ ] Respuesta automática de confirmación