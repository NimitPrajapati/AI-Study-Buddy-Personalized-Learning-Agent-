"""
src/watsonx_client.py
Thin wrapper around the ibm-watsonx-ai Python SDK.
All feature modules call this instead of the SDK directly.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from src.exceptions import WatsonxAPIError

load_dotenv()

_DEFAULT_MODEL = "ibm/granite-3-8b-instruct"

_DEFAULT_PARAMS: Dict[str, Any] = {
    "max_new_tokens": 1024,
    "temperature": 0.3,
    "top_p": 0.9,
    "repetition_penalty": 1.1,
}


class WatsonxClient:
    """
    Singleton-style wrapper around ModelInference.
    Instantiate once and reuse across the application.
    """

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        self.model_id = model_id
        self._api_key = api_key or os.getenv("WATSONX_API_KEY", "")
        self._project_id = project_id or os.getenv("WATSONX_PROJECT_ID", "")
        self._url = url or os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self._model: Any = None  # Lazy-initialised on first call

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_model(self) -> Any:
        """Lazy-initialise the ModelInference object."""
        if self._model is None:
            try:
                from ibm_watsonx_ai import APIClient, Credentials
                from ibm_watsonx_ai.foundation_models import ModelInference

                credentials = Credentials(url=self._url, api_key=self._api_key)
                client = APIClient(credentials)
                self._model = ModelInference(
                    model_id=self.model_id,
                    api_client=client,
                    project_id=self._project_id,
                )
            except Exception as exc:
                raise WatsonxAPIError(
                    f"Failed to initialise watsonx ModelInference: {exc}"
                ) from exc
        return self._model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_text(
        self,
        prompt: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Call ModelInference.generate_text() and return the generated string.

        Raises WatsonxAPIError on any SDK failure.
        """
        merged = {**_DEFAULT_PARAMS, **(params or {})}
        try:
            model = self._get_model()
            response = model.generate_text(prompt=prompt, params=merged)
            return response.strip() if isinstance(response, str) else str(response)
        except WatsonxAPIError:
            raise
        except Exception as exc:
            raise WatsonxAPIError(f"generate_text failed: {exc}") from exc

    def chat(
        self,
        messages: List[Dict[str, str]],
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Call ModelInference.chat() with a list of message dicts and return
        the assistant's reply text.

        messages format: [{"role": "system"|"user"|"assistant", "content": "..."}]

        Raises WatsonxAPIError on any SDK failure.
        """
        merged = {**_DEFAULT_PARAMS, **(params or {})}
        try:
            model = self._get_model()
            response = model.chat(messages=messages, params=merged)
            # SDK returns a dict with choices[0].message.content
            if isinstance(response, dict):
                choices = response.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    return msg.get("content", "").strip()
                return str(response)
            return str(response).strip()
        except WatsonxAPIError:
            raise
        except Exception as exc:
            raise WatsonxAPIError(f"chat failed: {exc}") from exc

    def is_configured(self) -> bool:
        """Return True if the required environment variables are present."""
        return bool(self._api_key and self._project_id)
