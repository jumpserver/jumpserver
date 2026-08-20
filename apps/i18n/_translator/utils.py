import os
from typing import Protocol

from openai import AsyncOpenAI


class Translator(Protocol):
    async def translate_text(self, text: str, target_lang: str = "English") -> str: ...


_TRANSLATION_SYSTEM_PROMPT = (
    "Translate the Chinese text in the input JSON array into {target_lang}. "
    "Return only a valid JSON array of translated strings in exactly the same order and with "
    "exactly the same number of items. Do not add Markdown fences or explanations. "
    "Translate naturally, smoothly, and authentically. "
    "Do NOT change placeholders or tokens; keep them exactly as-is, including but not limited to: "
    "%s, %d, %(name)s, {name}, {}, {{value}}, ${name}, $NAME, <tag>...</tag>, URLs, "
    "and line breaks. "
    "Translate '动作' as 'Action'. In short menu labels, omit '管理' when translating it would "
    "make the label unnecessarily long."
)


def _build_system_prompt(target_lang: str) -> str:
    # Do not use str.format(): the prompt intentionally contains translation
    # placeholders such as {name} and {} that must remain literal.
    return _TRANSLATION_SYSTEM_PROMPT.replace('{target_lang}', target_lang)


class OpenAITranslate:
    def __init__(
        self,
        key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        key = key or os.getenv("OPENAI_API_KEY")
        base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE_URL")
            or None
        )
        if base_url:
            base_url = base_url.rstrip("/")
            if base_url.endswith("/chat/completions"):
                base_url = base_url[:-len("/chat/completions")]
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.client = AsyncOpenAI(api_key=key, base_url=base_url)

    async def translate_text(self, text: str, target_lang: str = "English") -> str:
        response = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": _build_system_prompt(target_lang),
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            model=self.model,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError(
                f'OpenAI returned empty content (base_url={self.client.base_url}, '
                f'model={self.model})'
            )
        return content.strip()


class ClaudeTranslate:
    def __init__(self, key: str | None = None, model: str | None = None):
        # anthropic is optional at runtime; only required when provider=claude
        from anthropic import AsyncAnthropic  # type: ignore

        key = key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-latest"
        self.client = AsyncAnthropic(api_key=key)

    async def translate_text(self, text: str, target_lang: str = "English") -> str:
        msg = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=_build_system_prompt(target_lang),
            messages=[{"role": "user", "content": text}],
        )

        # anthropic SDK returns content blocks; we want the concatenated text
        parts: list[str] = []
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        content = "".join(parts).strip()
        if not content:
            raise RuntimeError(f'Claude returned empty content (model={self.model})')
        return content


def build_translator() -> Translator:
    provider = (os.getenv("I18N_PROVIDER") or "openai").lower()
    if provider in {"claude", "anthropic"}:
        return ClaudeTranslate()
    return OpenAITranslate()
