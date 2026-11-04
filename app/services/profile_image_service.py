
import io
import logging

import cloudinary
import cloudinary.uploader

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.repositories.user_repository import UserRepository


logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_PIXELS = 20_000_000

ALLOWED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class ProfileImageService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)

        settings = get_settings()

        if not all([
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        ]):
            raise HTTPException(
                status_code=503,
                detail="Image storage is not configured",
            )

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    def validate_image(self, file: UploadFile) -> bytes:

        if file.content_type not in ALLOWED_FORMATS.values():
            raise HTTPException(
                status_code=415,
                detail="Only JPEG, PNG and WebP images are allowed",
            )

        # Read no more than the maximum size plus one byte.
        data = file.file.read(MAX_FILE_SIZE + 1)

        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Maximum image size is 5 MB",
            )

        if not data:
            raise HTTPException(
                status_code=400,
                detail="Image file is empty",
            )

        try:
            Image.MAX_IMAGE_PIXELS = MAX_PIXELS

            with Image.open(io.BytesIO(data)) as image:
                image_format = image.format
                width, height = image.size

                if (
                    image_format not in ALLOWED_FORMATS
                    or file.content_type != ALLOWED_FORMATS[image_format]
                ):
                    raise HTTPException(
                        status_code=415,
                        detail="Image content does not match its file type",
                    )

                if (
                    width <= 0
                    or height <= 0
                    or width * height > MAX_PIXELS
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Image dimensions are invalid or too large",
                    )

                image.verify()

        except HTTPException:
            raise

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid or corrupted image",
            )

        return data

    def _destroy_image(self, public_id: str) -> None:
        cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
            invalidate=True,
        )

    def upload(self, user: User, file: UploadFile) -> User:

        data = self.validate_image(file)

        old_public_id = user.profile_image_public_id

        image_stream = io.BytesIO(data)
        image_stream.name = "profile_image"

        try:
            result = cloudinary.uploader.upload(
                image_stream,
                folder=f"smart-hajj-guardian/users/{user.id}",
                resource_type="image",
                use_filename=False,
                unique_filename=True,
                overwrite=False,
            )

            new_url = result["secure_url"]
            new_public_id = result["public_id"]

        except Exception:
            logger.exception("Cloudinary profile image upload failed")
            raise HTTPException(
                status_code=502,
                detail="Unable to upload profile image",
            )

        try:
            updated_user = self.repository.update(
                user,
                {
                    "profile_image_url": new_url,
                    "profile_image_public_id": new_public_id,
                },
            )

        except Exception:
            self.db.rollback()

            # Remove newly uploaded asset if database update fails.
            try:
                self._destroy_image(new_public_id)
            except Exception:
                logger.exception(
                    "Failed to clean up uploaded image after DB error"
                )

            raise HTTPException(
                status_code=500,
                detail="Unable to save profile image",
            )

        # Delete the old asset only AFTER Neon has been updated.
        if old_public_id and old_public_id != new_public_id:
            try:
                self._destroy_image(old_public_id)
            except Exception:
                logger.exception(
                    "Old profile image cleanup failed"
                )

        return updated_user

    def delete(self, user: User) -> None:

        old_public_id = user.profile_image_public_id

        if not old_public_id and not user.profile_image_url:
            return

        try:
            self.repository.update(
                user,
                {
                    "profile_image_url": None,
                    "profile_image_public_id": None,
                },
            )

        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Unable to remove profile image",
            )

        if old_public_id:
            try:
                self._destroy_image(old_public_id)
            except Exception:
                logger.exception(
                    "Cloudinary profile image cleanup failed"
                )
