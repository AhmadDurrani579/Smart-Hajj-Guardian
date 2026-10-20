"""Generate DEVELOPMENT-ONLY Hajj/Umrah guidance using the existing GeminiService.

From Backend/:
    uv run python -m scripts.generate_guidance --journey UMRAH
    uv run python -m scripts.generate_guidance --journey HAJJ --variant TAMATTU

No database writes. Generated content must be verified before production use.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.services.gemini_service import GeminiService
from google.genai import types

class GeneratedStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_order: int = Field(ge=1)
    title: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    location_context: str | None = None
    adab: str | None = None
    dua: str | None = None
    safety_notes: str | None = None
    source_reference: str = Field(min_length=1)
    image_prompt: str = Field(min_length=1)
    image_caption: str = Field(min_length=1)
    image_alt_text: str = Field(min_length=1)


class GeneratedGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    journey_type: Literal["HAJJ", "UMRAH"]
    variant: Literal["STANDARD", "TAMATTU", "QIRAN", "IFRAD"]
    content_status: Literal["AI_GENERATED_UNVERIFIED"]
    steps: list[GeneratedStep] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_steps(self):
        orders = [step.step_order for step in self.steps]
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError("step_order values must be sequential, starting at 1")
        if self.journey_type == "UMRAH" and self.variant != "STANDARD":
            raise ValueError("UMRAH must use STANDARD")
        if self.journey_type == "HAJJ" and self.variant == "STANDARD":
            raise ValueError("HAJJ needs TAMATTU, QIRAN or IFRAD")
        return self


def build_prompt(journey: str, variant: str) -> str:
    return f"""You are drafting DEVELOPMENT-ONLY sample guidance for the Smart Hajj Guardian university project.
Journey: {journey}; variant: {variant}; language: English.

Produce a comprehensive, correctly ordered list of pilgrimage stages. Write readable guidance suitable for first-time and elderly users. Clearly distinguish required and optional practices when appropriate; flag material scholarly differences and avoid treating a disputed opinion as universal. Include safety considerations. Do NOT invent Quran verses, hadith numbers, citations or claims of scholarly approval. If a source has not been personally verified against an authoritative document, set source_reference to exactly 'UNVERIFIED'. Do not manufacture Arabic supplications; use null for dua if uncertain. This is sample data, not religious advice.

Each step must contain:
step_order (sequential integer starting at 1), title, instructions, location_context, adab, dua, safety_notes, source_reference, image_prompt, image_caption, image_alt_text.

image_prompt must describe an educational image or diagram appropriate to the step, respectful and factually cautious; images will be sourced or produced and checked separately. Do NOT include image URLs. image_caption and image_alt_text must be short, useful and accessible.
IMPORTANT OUTPUT REQUIREMENTS:

Every step MUST include ALL these fields:
- step_order
- title
- instructions
- location_context
- adab
- dua
- safety_notes
- source_reference
- image_prompt
- image_caption
- image_alt_text

The "instructions" field is MANDATORY.

For every step:
- Write clear, detailed instructions describing what the pilgrim does.
- Do not replace instructions with image_prompt.
- Do not omit instructions to save tokens.
- Keep image_prompt relatively short.
- Use null for optional information when unavailable.
- Use "UNVERIFIED" for unverified religious references.

Generate complete step descriptions, not just titles and image prompts.

Return only a JSON object with EXACT keys journey_type, variant, content_status, steps. Set content_status to 'AI_GENERATED_UNVERIFIED', journey_type to '{journey}', variant to '{variant}'. Do not include markdown or other fields. All optional textual fields may be null; required text fields cannot be empty.
"""


def parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def main():
    parser = argparse.ArgumentParser(description="Generate unverified guidance JSON with Gemini")
    parser.add_argument("--journey", choices=["HAJJ", "UMRAH"], required=True)
    parser.add_argument("--variant", choices=["STANDARD", "TAMATTU", "QIRAN", "IFRAD"])
    parser.add_argument("--output-dir", default="scripts/generated_guidance")
    args = parser.parse_args()

    variant = args.variant or ("STANDARD" if args.journey == "UMRAH" else None)
    if variant is None:
        parser.error("--variant is required for HAJJ")
    if args.journey == "UMRAH" and variant != "STANDARD":
        parser.error("UMRAH must use STANDARD")
    if args.journey == "HAJJ" and variant == "STANDARD":
        parser.error("HAJJ variant must be TAMATTU, QIRAN or IFRAD")

    print(f"Generating unverified {args.journey}/{variant} development guidance...")
    raw = GeminiService().generate(
        prompt=build_prompt(args.journey, variant),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=GeneratedGuidance.model_json_schema(),
            temperature=0.2,
            max_output_tokens=16000,
        ),
    )

    try:
        guidance = GeneratedGuidance.model_validate(parse_json(raw))
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        print("Gemini response did not pass validation. Nothing has been saved.")
        raise SystemExit(str(exc)) from exc

    if guidance.journey_type != args.journey or guidance.variant != variant:
        raise SystemExit("Generated guidance does not match the requested journey and variant")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{args.journey}_{variant}.json"
    # No database write. Subsequent runs overwrite the local file for this variant.
    path.write_text(guidance.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(guidance.steps)} steps to {path}")
    print("WARNING: AI-generated, unverified development content. Do not publish to pilgrims.")


if __name__ == "__main__":
    main()
