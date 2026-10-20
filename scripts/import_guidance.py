
import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.guidance import GuidanceStep, GuidanceVersion


GUIDANCE_DIR = Path(__file__).resolve().parent / "generated_guidance"

FILES = {
    "UMRAH_STANDARD.json": ("UMRAH", "STANDARD"),
    "HAJJ_TAMATTU.json": ("HAJJ", "TAMATTU"),
    "HAJJ_QIRAN.json": ("HAJJ", "QIRAN"),
    "HAJJ_IFRAD.json": ("HAJJ", "IFRAD"),
}


class ImportedStep(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    step_order: int = Field(gt=0)
    title: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    location_context: str | None = None
    adab: str | None = None
    dua: str | None = None
    safety_notes: str | None = None
    source_reference: str = Field(min_length=1)


class ImportedGuidance(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    journey_type: Literal["HAJJ", "UMRAH"]
    variant: Literal["STANDARD", "TAMATTU", "QIRAN", "IFRAD"]
    content_status: Literal["AI_GENERATED_UNVERIFIED"]
    steps: list[ImportedStep] = Field(min_length=1)


def load_guidance(filename, expected_type, expected_variant):
    path = GUIDANCE_DIR / filename

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    guidance = ImportedGuidance.model_validate(data)

    if (
        guidance.journey_type != expected_type
        or guidance.variant != expected_variant
    ):
        raise ValueError(f"Journey mismatch in {filename}")

    orders = [step.step_order for step in guidance.steps]

    if orders != list(range(1, len(orders) + 1)):
        raise ValueError(
            f"Step numbers must start at 1 and be sequential: {filename}"
        )

    return guidance


def import_guidance(filename, guidance, apply_changes=False):
    with SessionLocal() as db:
        try:
            existing = db.scalar(
                select(GuidanceVersion).where(
                    GuidanceVersion.journey_type == guidance.journey_type,
                    GuidanceVersion.variant == guidance.variant,
                )
            )

            if existing:
                guidance_id = existing.id

                existing_step = db.scalar(
                    select(GuidanceStep.id)
                    .where(
                        GuidanceStep.guidance_version_id == guidance_id
                    )
                    .limit(1)
                )

                if existing_step is not None:
                    print(
                        f"SKIPPED: {filename} — "
                        "guidance already contains steps"
                    )
                    return
            else:
                guidance_id = None

            if not apply_changes:
                print(
                    f"DRY RUN: {filename} — "
                    f"{len(guidance.steps)} steps validated"
                )
                return

            if existing is None:
                record = GuidanceVersion(
                    journey_type=guidance.journey_type,
                    variant=guidance.variant,
                    is_active=False,
                )
                db.add(record)
                db.flush()
                guidance_id = record.id

            for step in guidance.steps:
                record = GuidanceStep(
                    guidance_version_id=guidance_id,
                    step_order=step.step_order,
                    title=step.title,
                    instructions=step.instructions,
                    location_context=step.location_context,
                    adab=step.adab,
                    dua=step.dua,
                    safety_notes=step.safety_notes,
                    source_reference=step.source_reference,
                )
                db.add(record)

            db.commit()

            print(
                f"IMPORTED: {filename} — "
                f"{len(guidance.steps)} steps; "
                f"guidance ID {guidance_id}; inactive"
            )

        except Exception:
            db.rollback()
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually insert data into Neon PostgreSQL",
    )
    args = parser.parse_args()

    # Validate every JSON file before making any database changes.
    validated = []

    for filename, (journey_type, variant) in FILES.items():
        guidance = load_guidance(
            filename,
            journey_type,
            variant,
        )
        validated.append((filename, guidance))

    print(f"Validated {len(validated)} guidance files.")

    for filename, guidance in validated:
        import_guidance(
            filename,
            guidance,
            apply_changes=args.apply,
        )

    if not args.apply:
        print("Dry run complete. No database records changed.")


if __name__ == "__main__":
    main()
