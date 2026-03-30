import logging
import json
import re
from typing import Any

import requests

from config.settings import get_settings


logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.last_error: str | None = None
        if self.is_ready:
            logger.info("LLM client configured for Ark via %s", self.settings.ark_base_url)
        else:
            logger.warning("LLM client is not ready. Configure ARK_API_KEY, ARK_BASE_URL, and MODEL_NAME before running analysis.")

    @property
    def is_ready(self) -> bool:
        return bool(
            self.settings.ark_api_key.strip()
            and self.settings.ark_base_url.strip()
            and self.settings.model_name.strip()
        )

    def generate_report(self, prompt: str, evidence: list[dict[str, Any]]) -> str:
        return self._call_ark(prompt)

    def answer_question(self, prompt: str, evidence: list[dict[str, Any]]) -> str:
        return self._call_ark(prompt)

    def generate_json(self, prompt: str) -> dict[str, Any]:
        content = self._call_ark(prompt)
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise RuntimeError("model did not return a JSON object")
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise RuntimeError("model returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("model JSON response must be an object")
        return payload

    def _call_ark(self, prompt: str) -> str:
        self._ensure_ready()

        url = f"{self.settings.ark_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.ark_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.settings.ark_timeout_seconds)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            if not content:
                raise RuntimeError("真实模型返回了空内容。")
            self.last_error = None
            return content
        except Exception as exc:
            self.last_error = str(exc)
            logger.exception("Ark request failed: %s", exc)
            raise RuntimeError(f"真实模型调用失败：{self.last_error}") from exc

    def _ensure_ready(self) -> None:
        missing: list[str] = []
        if not self.settings.ark_api_key.strip():
            missing.append("ARK_API_KEY")
        if not self.settings.ark_base_url.strip():
            missing.append("ARK_BASE_URL")
        if not self.settings.model_name.strip():
            missing.append("MODEL_NAME")

        if missing:
            message = f"真实模型尚未完成配置，请补充：{', '.join(missing)}"
            self.last_error = message
            raise RuntimeError(message)
