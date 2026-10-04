import json
import logging
import re
import time
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings


logger = logging.getLogger(__name__)


class LLMConfigurationError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


class ModelArkClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def read_prompt(self, filename: str) -> str:
        path = self.settings.prompts_dir / filename
        return path.read_text(encoding="utf-8")

    async def generate_json(
        self,
        prompt: str,
        response_model: type[BaseModel],
        *,
        temperature: float = 0.2,
        max_tokens: int = 6000,
        system_prompt: Optional[str] = None,
    ) -> BaseModel:
        if not self.settings.llm_ready:
            raise LLMConfigurationError(
                "ModelArk is not configured. Set MODELARK_API_KEY and MAIN_AGENT_ENDPOINT."
            )

        system = system_prompt or self.read_prompt("system_debate_coach.md")
        schema = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        full_prompt = (
            f"{prompt}\n\n"
            "Return one valid JSON object only. Do not use Markdown fences.\n"
            f"The JSON must follow this schema:\n{schema}"
        )
        headers = {
            "Authorization": f"Bearer {self.settings.modelark_api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.modelark_base_url.rstrip('/')}/chat/completions"

        last_error: Optional[Exception] = None
        max_attempts = 3
        for attempt in range(max_attempts):
            retry_note = (
                "\n\nYour previous response was not valid JSON. Carefully check every "
                "comma, quote, bracket, and required field before returning the object."
                if attempt
                else ""
            )
            payload = {
                "model": self.settings.main_agent_endpoint,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": full_prompt + retry_note},
                ],
                "temperature": temperature if attempt == 0 else 0,
                "max_tokens": self.settings.llm_max_tokens,
                "response_format": {"type": "json_object"},
                "thinking": {"type": self.settings.llm_thinking_mode},
                "reasoning_effort": self.settings.llm_reasoning_effort,
            }
            try:
                started_at = time.perf_counter()
                async with httpx.AsyncClient(
                    timeout=self.settings.llm_timeout_seconds
                ) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    body = response.json()
                choice = body.get("choices", [{}])[0]
                usage = body.get("usage", {})
                logger.info(
                    "ModelArk structured call model=%s elapsed=%.2fs "
                    "prompt_tokens=%s completion_tokens=%s reasoning_tokens=%s "
                    "finish_reason=%s attempt=%s",
                    response_model.__name__,
                    time.perf_counter() - started_at,
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                    usage.get("completion_tokens_details", {}).get(
                        "reasoning_tokens"
                    ),
                    choice.get("finish_reason"),
                    attempt + 1,
                )
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:500]
                logger.error("ModelArk returned HTTP %s", exc.response.status_code)
                raise LLMResponseError(
                    f"ModelArk request failed with HTTP {exc.response.status_code}: {detail}"
                ) from exc
            except (httpx.HTTPError, ValueError) as exc:
                raise LLMResponseError(f"ModelArk request failed: {exc}") from exc

            try:
                choice = body["choices"][0]
                if choice.get("finish_reason") == "length":
                    usage = body.get("usage", {})
                    reasoning_tokens = usage.get(
                        "completion_tokens_details", {}
                    ).get("reasoning_tokens")
                    raise LLMResponseError(
                        "ModelArk truncated the structured response at "
                        f"{self.settings.llm_max_tokens} tokens"
                        + (
                            f" ({reasoning_tokens} reasoning tokens)."
                            if reasoning_tokens is not None
                            else "."
                        )
                    )
                content = choice["message"]["content"]
                data = self._parse_json(content)
                return response_model.model_validate(data)
            except (
                KeyError,
                IndexError,
                TypeError,
                ValidationError,
                json.JSONDecodeError,
            ) as exc:
                last_error = exc
                logger.warning(
                    "ModelArk returned invalid structured data (attempt %s/%s): %s",
                    attempt + 1,
                    max_attempts,
                    exc,
                )

        raise LLMResponseError(
            f"The AI returned an invalid structured response after {max_attempts} attempts."
        ) from last_error

    @staticmethod
    def _parse_json(content: Any) -> Dict[str, Any]:
        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise TypeError("Expected string or object content")

        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1:
                raise
            return json.loads(cleaned[start : end + 1])
