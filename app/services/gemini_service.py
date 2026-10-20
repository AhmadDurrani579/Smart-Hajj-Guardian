
import random
import time

from google import genai
from google.genai import errors, types

from app.core.config import get_settings


class GeminiService:

    def __init__(self):
        settings = get_settings()

        self.api_keys = [
            settings.GEMINI_API_KEY_1,
            settings.GEMINI_API_KEY_2,
            settings.GEMINI_API_KEY_3,
            settings.GEMINI_API_KEY_4,
            settings.GEMINI_API_KEY_5,
        ]

        self.model = settings.GEMINI_MODEL

    def generate(
        self,
        prompt: str,
        key_index: int = 0,
        config: types.GenerateContentConfig | None = None,
    ) -> str:

        client = genai.Client(
            api_key=self.api_keys[key_index]
        )

        try:
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config,
                    )

                    if not response.text:
                        raise ValueError(
                            "Gemini returned an empty response"
                        )

                    return response.text

                except errors.ClientError as exc:
                    if exc.code != 429 or attempt == 2:
                        raise

                except errors.ServerError:
                    if attempt == 2:
                        raise

                time.sleep(
                    min(2 ** attempt, 8)
                    + random.uniform(0, 0.5)
                )

        finally:
            client.close()
