
import json
import os
from typing import Literal

from google import genai
from app.core.config import get_settings
from google.genai import types
from pydantic import BaseModel

from app.schemas.guidance import GuidanceStepResponse
from app.core.config import get_settings


class GeneratedGuidanceContent(BaseModel):
    title: str
    instructions: str
    location_context: str | None = None
    adab: str | None = None
    safety_notes: str | None = None


class GuidanceGenerationService:


    def __init__(self):
        settings = get_settings()

        api_keys = [
            settings.GEMINI_API_KEY_1,
            settings.GEMINI_API_KEY_2,
            settings.GEMINI_API_KEY_3,
            settings.GEMINI_API_KEY_4,
            settings.GEMINI_API_KEY_5,
        ]

        api_key = next(
            (key for key in api_keys if key and key.strip()),
            None,
        )

        if not api_key:
            raise RuntimeError("No Gemini API key configured")

        self.client = genai.Client(api_key=api_key)
        self.model = settings.GEMINI_MODEL

    def generate_steps(
        self,
        steps: list[GuidanceStepResponse],
        language: Literal["en", "ur"],
    ) -> list[dict]:

        language_name = {
            "en": "English",
            "ur": "Urdu",
        }[language]

        results = []

        for step in steps:
            original = step.model_dump(mode="json")

            prompt = f"""
You are preparing Hajj and Umrah guidance for pilgrims.

Generate the guidance directly in {language_name}.

Rules:
1. Write all explanatory content in {language_name}.
2. For Urdu, use Urdu script, not Roman Urdu.
3. Use the supplied guidance as the authoritative
   content boundary for this generation task.
4. Preserve the ritual sequence and meaning.
5. Do not invent additional rituals, religious rulings,
   Quran verses, hadith or references.
6. Write clearly for first-time and elderly pilgrims.
7. Preserve safety instructions and important details.
8. Do not include unsupported religious claims.
9. Do not generate a new dua.
10. Do not claim unverified material is verified.

Existing guidance context:
{json.dumps(original, ensure_ascii=False)}
"""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeneratedGuidanceContent,
                    temperature=0,
                ),
            )

            if not response.text:
                raise RuntimeError(
                    "Gemini returned an empty response"
                )

            generated = (
                GeneratedGuidanceContent.model_validate_json(
                    response.text
                )
            )

            content = generated.model_dump()

            # Reject missing generated fields.
            for field in (
                "title",
                "instructions",
                "location_context",
                "adab",
                "safety_notes",
            ):
                if original.get(field) and not content.get(field):
                    raise ValueError(
                        f"Missing generated field: {field}"
                    )

            result = original.copy()
            result.update(content)

            # Identity and source metadata come from the DB.
            # Never let Gemini create these values.
            result["dua"] = original.get("dua")
            result["source_reference"] = original.get(
                "source_reference"
            )

            results.append(result)

        return results
