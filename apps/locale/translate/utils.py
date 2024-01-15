from openai import AsyncOpenAI


class OpenAITranslate:
    def __init__(self, key: str | None = None):
        self.client = AsyncOpenAI(api_key=key)

    async def translate_text(self, text, target_lang="English") -> str | None:
        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": f"Now I ask you to be the translator. "
                                   f"Your goal is to understand the Chinese "
                                   f"I provided you and translate it into {target_lang}. "
                                   f"Please do not use a translation accent when translating, "
                                   f"but translate naturally, smoothly and authentically, "
                                   f"using beautiful and elegant words. way of expression.",
                    },
                    {
                        "role": "user",
                        "content": text,
                    },
                ],
                model="gpt-4",
            )
        except Exception as e:
            print("Open AI Error: ", e)
            return
        return response.choices[0].message.content.strip()
