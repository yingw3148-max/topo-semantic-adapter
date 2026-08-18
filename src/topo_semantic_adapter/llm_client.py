"""Lightweight local-LLM client for semantic enrichment.

Defaults to an OpenAI-compatible Ollama endpoint so that users can run the
analysis pipeline entirely locally. The client is optional: if ``openai`` is
not installed or the endpoint is unreachable, the analyzer falls back to
deterministic community labels and anomaly lists.
"""

from __future__ import annotations

import json
import os
from typing import Any


class LLMClient:
    """OpenAI-compatible chat client configured for local inference."""

    DEFAULT_BASE_URL = "http://localhost:11434/v1"
    DEFAULT_MODEL = "qwen2.5-coder:7b"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "LLM support requires the 'openai' package. "
                "Install it with: pip install -e '.[llm]'"
            ) from exc

        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL") or self.DEFAULT_BASE_URL
        self.model = model or os.environ.get("OPENAI_MODEL") or self.DEFAULT_MODEL
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or "ollama"
        self._client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=timeout,
        )

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str | None:
        """Send a chat request and return the assistant message content.

        Returns ``None`` when the endpoint is unreachable so callers can fall
        back to deterministic behavior.
        """
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:  # pragma: no cover
            print(f"[llm] warning: LLM call failed ({exc}); falling back.", flush=True)
            return None

    def label_communities(
        self, community_summaries: dict[int, str]
    ) -> dict[int, str] | None:
        """Ask the LLM to produce a short Chinese label for each community.

        ``community_summaries`` maps ``community_id`` to a newline-separated
        summary of that community's members (kind, label, key metadata).
        """
        if not community_summaries:
            return {}

        prompt_parts = [
            "你是一名网络拓扑分析专家。下面是若干个拓扑社区，每个社区包含一组节点。",
            "请为每个社区生成一个简洁的中文标签（最多 8 个汉字），反映该社区在网络中的角色。",
            "只输出 JSON 对象，key 为社区编号，value 为中文标签。不要输出解释。",
            "",
        ]
        for cid, summary in community_summaries.items():
            prompt_parts.append(f"社区 {cid}:\n{summary}\n")

        content = self.chat_completion(
            [
                {"role": "system", "content": "你是一个网络拓扑分析助手，只输出 JSON。"},
                {"role": "user", "content": "\n".join(prompt_parts)},
            ]
        )
        if content is None:
            return None

        return _extract_json_object(content)

    def summarize_anomalies(self, anomalies: list[dict[str, Any]]) -> str | None:
        """Ask the LLM to summarize a list of topology anomalies in Chinese."""
        if not anomalies:
            return "未发现明显异常。"

        prompt = (
            "你是一名网络运维专家。下面是从拓扑图中识别出的异常信号，"
            "请用一段简洁的中文总结关键风险和可能原因，不超过 200 字。\n\n"
            + json.dumps(anomalies, ensure_ascii=False, indent=2)
        )
        return self.chat_completion(
            [
                {"role": "system", "content": "你是一个网络运维分析助手。"},
                {"role": "user", "content": prompt},
            ]
        )


def _extract_json_object(text: str) -> dict[int, str] | None:
    """Best-effort JSON extraction from an LLM response."""
    text = text.strip()
    # Strip markdown fences.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first `{...}` block.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

    if not isinstance(parsed, dict):
        return None

    result: dict[int, str] = {}
    for key, value in parsed.items():
        try:
            cid = int(key)
        except (ValueError, TypeError):
            continue
        if isinstance(value, str):
            result[cid] = value.strip()
    return result
