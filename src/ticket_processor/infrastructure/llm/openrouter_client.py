"""Free-model LLM client with OpenRouter primary and optional Groq fallback."""

from __future__ import annotations

from dataclasses import dataclass

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from ticket_processor.config import LlmProvider, Settings
from ticket_processor.domain.exceptions import LlmError
from ticket_processor.domain.ports import LlmPort


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    provider: LlmProvider
    model: str
    base_url: str
    api_key: str


class OpenRouterClient(LlmPort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = requests.Session()
        self._providers = self._build_provider_chain(settings)

    def _build_provider_chain(self, settings: Settings) -> list[ProviderConfig]:
        providers: list[ProviderConfig] = []
        if (
            settings.llm_provider == LlmProvider.OPENROUTER
            and settings.openrouter_api_key is not None
        ):
            providers.append(
                ProviderConfig(
                    provider=LlmProvider.OPENROUTER,
                    model=settings.llm_model,
                    base_url=str(settings.openrouter_base_url).rstrip("/"),
                    api_key=settings.openrouter_api_key.get_secret_value(),
                )
            )
        elif settings.llm_provider == LlmProvider.GROQ and settings.groq_api_key is not None:
            providers.append(
                ProviderConfig(
                    provider=LlmProvider.GROQ,
                    model=settings.llm_model,
                    base_url=str(settings.groq_base_url).rstrip("/"),
                    api_key=settings.groq_api_key.get_secret_value(),
                )
            )

        if (
            settings.llm_fallback_provider == LlmProvider.OPENROUTER
            and settings.openrouter_api_key is not None
            and settings.llm_fallback_model is not None
        ):
            providers.append(
                ProviderConfig(
                    provider=LlmProvider.OPENROUTER,
                    model=settings.llm_fallback_model,
                    base_url=str(settings.openrouter_base_url).rstrip("/"),
                    api_key=settings.openrouter_api_key.get_secret_value(),
                )
            )
        elif (
            settings.llm_fallback_provider == LlmProvider.GROQ
            and settings.groq_api_key is not None
            and settings.llm_fallback_model is not None
        ):
            providers.append(
                ProviderConfig(
                    provider=LlmProvider.GROQ,
                    model=settings.llm_fallback_model,
                    base_url=str(settings.groq_base_url).rstrip("/"),
                    api_key=settings.groq_api_key.get_secret_value(),
                )
            )
        return providers

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        errors: list[str] = []
        for provider in self._providers:
            try:
                return self._complete_with_provider(provider, prompt, system_prompt)
            except Exception as exc:
                errors.append(f"{provider.provider}:{provider.model}:{exc}")
        raise LlmError("All configured free LLM providers failed", context={"errors": errors})

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((requests.RequestException, LlmError)),
    )
    def _complete_with_provider(
        self,
        provider: ProviderConfig,
        prompt: str,
        system_prompt: str | None,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }
        if provider.provider == LlmProvider.OPENROUTER:
            headers["HTTP-Referer"] = "https://localhost/ticket-processor-refactored"
            headers["X-Title"] = "ticket-processor-refactored"

        response = self._session.post(
            f"{provider.base_url}/chat/completions",
            headers=headers,
            json={
                "model": provider.model,
                "messages": messages,
                "temperature": self._settings.llm_temperature,
            },
            timeout=self._settings.llm_timeout_seconds,
        )

        if response.status_code >= 400:
            raise LlmError(
                "LLM request failed",
                context={
                    "provider": provider.provider,
                    "model": provider.model,
                    "status_code": response.status_code,
                    "body": response.text[:500],
                },
            )

        payload = response.json()
        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError(
                "Invalid LLM response payload",
                context={
                    "provider": provider.provider,
                    "model": provider.model,
                    "payload": payload,
                },
            ) from exc
