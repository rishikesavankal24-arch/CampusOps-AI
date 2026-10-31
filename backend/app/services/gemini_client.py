"""Asynchronous Google Gemini REST API client for embeddings and generation."""

import logging
from typing import Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiConfigError(Exception):
    """Raised when Gemini API key or model configuration is missing or invalid."""
    pass


class GeminiApiError(Exception):
    """Raised when the Gemini REST API returns an unexpected error."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class GeminiRateLimitError(GeminiApiError):
    """Raised when Gemini API quota or rate limits are exceeded (HTTP 429)."""
    def __init__(self, message: str = "Gemini API rate limit exceeded"):
        super().__init__(message, status_code=429)


class GeminiClient:
    """Async client communicating with Google Gemini REST endpoints.
    
    SECURITY:
    - Never logs API keys, raw query tokens, or sensitive context in error messages.
    - Enforces configured 768-dimensional embeddings to match pgvector schema.
    """

    def __init__(self):
        self.timeout = httpx.Timeout(connect=10.0, read=25.0, write=10.0, pool=10.0)

    def _ensure_configured(self) -> str:
        """Validate presence of configured API key without exposing its value."""
        if not settings.is_gemini_configured:
            raise GeminiConfigError("Gemini API key is not configured on this server")
        return settings.gemini_api_key.strip()

    async def get_embedding(self, text: str) -> list[float]:
        """Generate a 768-dimensional embedding vector for the provided text.
        
        Uses models/gemini-embedding-001 with output_dimensionality=768.
        """
        api_key = self._ensure_configured()
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Cannot generate embedding for empty text")

        model_name = settings.gemini_embedding_model
        url = f"{GEMINI_API_BASE_URL}/models/{model_name}:embedContent?key={api_key}"
        payload: dict[str, Any] = {
            "content": {
                "parts": [{"text": cleaned_text}]
            },
            "output_dimensionality": settings.gemini_embedding_dimension,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.TimeoutException:
                raise GeminiApiError("Gemini embedding service request timed out", status_code=504)
            except httpx.RequestError as exc:
                raise GeminiApiError(f"Network error connecting to Gemini embedding service: {exc.__class__.__name__}")

        if response.status_code == 429:
            raise GeminiRateLimitError("Gemini embedding quota exceeded or rate limited")
        if response.status_code != 200:
            error_data = response.json().get("error", {}) if response.headers.get("content-type", "").startswith("application/json") else {}
            err_msg = error_data.get("message", "Embedding generation failed")
            logger.error("Gemini embedding error: status=%d, code=%s", response.status_code, error_data.get("code"))
            raise GeminiApiError(f"Gemini embedding API error: {err_msg}", status_code=response.status_code)

        data = response.json()
        embedding_values = data.get("embedding", {}).get("values", [])
        if not embedding_values:
            raise GeminiApiError("Gemini embedding response contained no vector values")

        if len(embedding_values) != settings.gemini_embedding_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {settings.gemini_embedding_dimension}, "
                f"received {len(embedding_values)}"
            )

        return embedding_values

    async def generate_content(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> str:
        """Generate grounded text using Gemini with automatic fallback on service errors."""
        api_key = self._ensure_configured()

        models_to_try = [settings.gemini_model]
        if settings.gemini_model_fallback and settings.gemini_model_fallback != settings.gemini_model:
            models_to_try.append(settings.gemini_model_fallback)

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }

        last_error: Exception | None = None

        for model in models_to_try:
            url = f"{GEMINI_API_BASE_URL}/models/{model}:generateContent?key={api_key}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    response = await client.post(url, json=payload)
                except httpx.TimeoutException:
                    last_error = GeminiApiError(f"Gemini model '{model}' timed out", status_code=504)
                    continue
                except httpx.RequestError as exc:
                    last_error = GeminiApiError(f"Network error with model '{model}': {exc.__class__.__name__}")
                    continue

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise GeminiApiError("Gemini returned empty response candidates")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts or "text" not in parts[0]:
                    raise GeminiApiError("Gemini response missing text content")
                return parts[0]["text"]

            if response.status_code == 429:
                raise GeminiRateLimitError("Gemini generation quota exceeded or rate limited")

            error_data = response.json().get("error", {}) if response.headers.get("content-type", "").startswith("application/json") else {}
            err_msg = error_data.get("message", "Model generation failed")
            logger.warning("Gemini model %s failed with status %d: %s", model, response.status_code, err_msg)
            last_error = GeminiApiError(f"Gemini model '{model}' error: {err_msg}", status_code=response.status_code)

        if last_error:
            raise last_error
        raise GeminiApiError("All configured Gemini models failed to generate a response")


gemini_client = GeminiClient()

