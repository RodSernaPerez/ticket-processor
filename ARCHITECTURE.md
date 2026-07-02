# Nueva Arquitectura Propuesta - Ticket Processor

## Principios de Diseño

1. **Clean Architecture** - Separación clara: Domain → Application → Infrastructure
2. **Dependency Inversion** - Interfaces en dominio, implementaciones en infraestructura
3. **Configuration as Code** - Pydantic Settings + .env (nunca en código)
4. **Structured Logging** - structlog con JSON output
5. **Type Safety** - Type hints obligatorios, mypy strict
6. **Testability** - 100% coverage en domain/application, mocks en infra

---

## Estructura de Directorios

```
ticket-processor/
├── src/
│   └── ticket_processor/
│       ├── __init__.py
│       ├── config.py                 # Pydantic Settings
│       ├── domain/                   # Capa de Dominio (sin dependencias externas)
│       │   ├── __init__.py
│       │   ├── models.py             # Entidades: Ticket, Product, Purchase
│       │   ├── ports.py              # Interfaces/Puertos (abstract base classes)
│       │   ├── exceptions.py         # Excepciones de dominio
│       │   └── classifiers/          # Clasificador de productos (estrategia)
│       │       ├── __init__.py
│       │       ├── base.py
│       │       ├── keyword_classifier.py
│       │       └── llm_classifier.py
│       ├── application/              # Casos de uso / Servicios de aplicación
│       │   ├── __init__.py
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   ├── ticket_processor_service.py
│       │   │   ├── email_processor_service.py
│       │   │   └── classification_service.py
│       │   ├── dtos.py               # Data Transfer Objects
│       │   └── use_cases/
│       │       ├── __init__.py
│       │       ├── process_email_use_case.py
│       │       ├── process_webhook_use_case.py
│       │       └── sync_purchases_use_case.py
│       └── infrastructure/           # Adaptadores concretos
│           ├── __init__.py
│           ├── config/               # Factory de configuración
│           ├── email/
│           │   ├── __init__.py
│           │   ├── gog_client.py
│           │   └── gmail_adapter.py
│           ├── parser/
│           │   ├── __init__.py
│           │   ├── pdf_parser.py
│           │   ├── text_parser.py
│           │   └── llm_parser.py
│           ├── storage/
│           │   ├── __init__.py
│           │   ├── sheets_adapter.py
│           │   └── supabase_adapter.py
│           ├── llm/
│           │   ├── __init__.py
│           │   └── openrouter_client.py
│           └── logging/
│               ├── __init__.py
│               └── setup.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Fixtures compartidos
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── test_models.py
│   │   │   ├── test_classifiers.py
│   │   │   └── test_exceptions.py
│   │   ├── application/
│   │   │   ├── test_ticket_processor_service.py
│   │   │   └── test_use_cases.py
│   │   └── infrastructure/
│   │       ├── test_parsers.py
│   │       └── test_classifiers.py
│   └── integration/
│       ├── test_gmail_integration.py
│       ├── test_sheets_integration.py
│       └── test_supabase_integration.py
├── scripts/
│   ├── run_processor.py              # Entry point CLI
│   ├── run_webhook.py                # Entry point Cloud Function
│   └── setup_secrets.py              # Helper para secrets
├── configs/
│   ├── config.yaml.example           # Template de configuración
│   └── logging.yaml                  # Configuración de logging
├── pyproject.toml                    # Configuración moderna Python
├── .env.example                      # Template de variables de entorno
├── .github/
│   └── workflows/
│       ├── ci.yml                    # CI pipeline
│       └── cd.yml                    # CD pipeline
├── Dockerfile                        # Container para Cloud Run
├── docker-compose.yml                # Desarrollo local
├── Makefile                          # Comandos comunes
└── README.md                         # Documentación técnica
```

---

## Diagrama de Dependencias

```
┌─────────────────────────────────────────────────────────────┐
│                      SCRIPTS / ENTRY POINTS                 │
│  (run_processor.py, run_webhook.py)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ depends on
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                        │
│  Use Cases → Services → DTOs                                │
│  (Orquesta el flujo, sin lógica de negocio)                 │
└─────────────────────┬───────────────────────────────────────┘
                      │ depends on (interfaces)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                           │
│  Models, Ports (Interfaces), Exceptions, Classifiers        │
│  (Cero dependencias externas - Pure Python)                 │
└─────────────────────┬───────────────────────────────────────┘
                      ▲ implements (interfaces)
                      │
┌─────────────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                        │
│  Adapters: Gmail, Sheets, Supabase, PDF, LLM, Logging       │
│  (Implementaciones concretas de los Ports)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Inyección de Dependencias (Container Simple)

```python
# src/ticket_processor/infrastructure/config/container.py
class Container:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._email_port = None
        self._parser_port = None
        self._sheets_port = None
        self._supabase_port = None
        self._classifier_port = None
        self._llm_port = None

    @property
    def email_port(self) -> EmailPort:
        if self._email_port is None:
            self._email_port = GmailAdapter(
                GogClient(self.settings.gog_refresh_token, ...)
            )
        return self._email_port

    @property
    def parser_port(self) -> ParserPort:
        if self._parser_port is None:
            self._parser_port = LlmParser(
                OpenRouterClient(self.settings.openrouter_api_key),
                self.classifier_port
            )
        return self._parser_port
    # ... resto de ports
```

---

## Flujo Principal (Procesar Email)

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐     ┌──────────────┐
│  Gmail      │────▶│  Email       │────▶│  Parser    │────▶│  Classifier  │
│  Adapter    │     │  Processor   │     │  (LLM)     │     │  (Keyword)   │
└─────────────┘     └──────────────┘     └────────────┘     └──────────────┘
                           │                                        │
                           ▼                                        ▼
                    ┌──────────────┐                         ┌──────────────┐
                    │  Sheets      │                         │  Supabase    │
                    │  Adapter     │                         │  Adapter     │
                    └──────────────┘                         └──────────────┘
```

---

## Configuración (Pydantic Settings)

```python
# src/ticket_processor/config.py
class Settings(BaseSettings):
    # Google / Gog
    gog_refresh_token: str
    gog_client_id: str
    gog_client_secret: str
    gog_account: str = "rosepe94oclaw@gmail.com"

    # Supabase
    supabase_url: HttpUrl
    supabase_service_key: SecretStr
    supabase_table: str = "tickets_gastos"

    # Google Sheets
    sheet_id: str

    # OpenRouter LLM
    openrouter_api_key: SecretStr
    openrouter_model: str = "openai/gpt-oss-120b:free"
    openrouter_timeout: int = 60

    # App
    log_level: str = "INFO"
    log_format: str = "json"  # json | console
    environment: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
```

---

## Manejo de Errores (Custom Exceptions)

```python
# domain/exceptions.py
class TicketProcessorError(Exception): pass

class ConfigurationError(TicketProcessorError): pass
class AuthenticationError(TicketProcessorError): pass
class ParsingError(TicketProcessorError): pass
class ClassificationError(TicketProcessorError): pass
class StorageError(TicketProcessorError): pass
class ExternalServiceError(TicketProcessorError):
    def __init__(self, service: str, original: Exception):
        self.service = service
        super().__init__(f"{service} error: {original}")
```

---

## Testing Strategy

| Capa | Tipo | Cobertura Objetivo | Herramientas |
|------|------|-------------------|--------------|
| Domain | Unit | 100% | pytest, hypothesis |
| Application | Unit | 95% | pytest, pytest-mock |
| Infrastructure | Integration | 80% | pytest, testcontainers (opcional) |
| E2E | Manual/CI | Critical paths | playwright, real APIs |

---

## Despliegue

### Local Development
```bash
make dev          # docker-compose up con hot reload
make test         # pytest con coverage
make lint         # ruff + mypy
```

### Cloud Run (Producción)
```bash
# Build
docker build -t gcr.io/PROJECT/ticket-processor .

# Deploy
gcloud run deploy ticket-processor \
  --image gcr.io/PROJECT/ticket-processor \
  --region europe-west1 \
  --set-secrets=GOG_REFRESH_TOKEN=gog-token:latest,...
```

### Secrets Management
- **NUNCA** en código ni .env en repo
- **Secret Manager** (GCP) / Vault / 1Password CLI
- Inyección en runtime via `--set-secrets` o env vars en Cloud Run

---

## Métricas de Calidad (Quality Gates)

```yaml
# .github/workflows/ci.yml - checks requeridos
- ruff check .           # linting
- mypy --strict src/     # type checking
- pytest --cov=90        # coverage mínimo 90%
- bandit -r src/         # security scan
- pip-audit              # dependency vulnerabilities
```