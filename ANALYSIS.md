# Análisis del Código Actual - Ticket Processor

## Resumen Ejecutivo

El código actual (`ticket_processor.py`) es un **monolito de ~400 líneas** en un solo archivo que viola principios fundamentales de ingeniería de software. Funciona pero no es mantenible, testeable ni seguro para producción.

---

## Problemas Críticos Encontrados

### 🔴 Seguridad - Secrets Hardcodeados
| Archivo | Secret | Riesgo |
|---------|--------|--------|
| `ticket_processor.py:17-20` | `SUPABASE_URL`, `SUPABASE_KEY` (service role key completo) | Acceso total a BD |
| `ticket_processor.py:22` | `OPENROUTER_API_KEY` | Uso no autorizado de créditos LLM |
| `gog_wrapper.sh:5-7` | `REFRESH_TOKEN`, `CLIENT_ID`, `CLIENT_SECRET` | Acceso total a Gmail/Drive |
| `deploy_via_api.py:13-17` | Mismos secrets de Google OAuth | Duplicación de credenciales |
| `setup_gcloud.sh:8-13` | Mismos secrets | Triplicación |

### 🔴 Arquitectura - Acoplamiento Extremo
- **Single Responsibility Principle violado**: Una clase/función hace parsing, clasificación, Sheets, Supabase, Gmail, PDF extraction
- **No Dependency Injection**: Dependencias hardcodeadas (`requests`, `subprocess`, `gog_wrapper.sh`)
- **No interfaces/abstracciones**: Imposible mockear para tests
- **Código procedural**: No hay dominio modelado

### 🔴 Calidad de Código
| Aspecto | Estado |
|---------|--------|
| Type hints | ❌ Ausentes (solo 1 función tiene annotation) |
| Tests unitarios | ❌ 0 tests |
| Logging estructurado | ❌ Solo `print()` |
| Manejo de errores | ❌ `except Exception: pass`, bare except |
| Configuración | ❌ Mezcla `os.environ.get()` con defaults hardcodeados |
| Validación de entrada | ❌ Ninguna |
| Documentación | ⚠️ README describe arquitectura que no existe |

### 🔴 Problemas Técnicos Específicos

1. **`main.py` rota**: Importa `get_access_token` que no existe en `ticket_processor.py`
2. **`gog_wrapper.sh` como dependencia runtime**: Llamadas `subprocess` frágiles, parsing de salida JSON sin validación
3. **PDF parsing frágil**: Try/except en cascada sin logging de qué librería falló
4. **Clasificador hardcodeado**: Keywords en `if/elif` chain, no extensible
5. **LLM prompt en string literal**: No versionable, no testeable
6. **Sin retry/backoff**: Llamadas a APIs externas sin resiliencia
7. **Sin idempotencia**: Procesar mismo email dos veces crea duplicados

---

## Deuda Técnica Cuantificada

- **Cyclomatic complexity**: `parse_ticket_with_llm` ~15, `classify_product` ~20
- **Coupling**: 8 dependencias externas directas en un módulo
- **Test coverage**: 0%
- **Security issues**: 5+ secrets expuestos en repo (aunque .gitignore los ignore, están en history)

---

## Conclusión

**Requiere reescritura completa** aplicando:
1. Clean Architecture / Hexagonal Architecture
2. Dependency Injection container
3. Pydantic Settings para configuración
4. Structured logging (structlog)
5. Custom exceptions + error handling
6. Unit tests + integration tests con mocks
7. Secret management externo (no en código)
8. CI/CD pipeline con quality gates