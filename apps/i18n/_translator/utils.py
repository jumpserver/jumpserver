import os
from typing import Protocol

from openai import AsyncOpenAI


class Translator(Protocol):
    async def translate_text(self, text: str, target_lang: str = "English") -> str | None: ...


_TRANSLATION_SYSTEM_PROMPT = (
    "Now I ask you to be the translator. "
    "Your goal is to understand the Chinese I provided you and translate it into {target_lang}. "
    "Please translate naturally, smoothly and authentically (no translation accent). "
    "Do NOT change placeholders or tokens; keep them exactly as-is, including but not limited to: "
    "%s, %d, %(name)s, {name}, {}, {{value}}, <tag>...</tag>, URLs, and line breaks. "
    "If you found word '动作' please translate it to 'Action', because it's short. "
    "If you found word '管理' in menu, you can not translate it, because management is too long in menu."
)


class OpenAITranslate:
    def __init__(
        self,
        key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        key = key or os.getenv("OPENAI_API_KEY")
        base_url = base_url or os.getenv("OPENAI_BASE_URL") or None
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.client = AsyncOpenAI(api_key=key, base_url=base_url)

    async def translate_text(self, text: str, target_lang: str = "English") -> str | None:
        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": _TRANSLATION_SYSTEM_PROMPT.format(target_lang=target_lang),
                    },
                    {
                        "role": "user",
                        "content": text,
                    },
                ],
                model=self.model,
            )
        except Exception as e:
            print("OpenAI Error: ", e)
            return None
        return response.choices[0].message.content.strip()


class ClaudeTranslate:
    def __init__(self, key: str | None = None, model: str | None = None):
        # anthropic is optional at runtime; only required when provider=claude
        from anthropic import AsyncAnthropic  # type: ignore

        key = key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-latest"
        self.client = AsyncAnthropic(api_key=key)

    async def translate_text(self, text: str, target_lang: str = "English") -> str | None:
        try:
            msg = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=_TRANSLATION_SYSTEM_PROMPT.format(target_lang=target_lang),
                messages=[{"role": "user", "content": text}],
            )
        except Exception as e:
            print("Claude Error: ", e)
            return None

        # anthropic SDK returns content blocks; we want the concatenated text
        parts: list[str] = []
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts).strip() or None


def build_translator() -> Translator:
    provider = (os.getenv("I18N_PROVIDER") or "openai").lower()
    if provider in {"claude", "anthropic"}:
        return ClaudeTranslate()
    return OpenAITranslate()
