from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PIL import Image


class AvatarStorageService:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.cwd() / "storage" / "avatars"

    def save_company_avatar(self, *, company_id: int, source_path: str) -> str:
        source = Path(source_path)
        if not source.exists():
            raise ValueError("Файл фото не знайдено.")

        target_dir = self.base_dir / f"company_{company_id}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{uuid4().hex}.webp"

        with Image.open(source) as image:
            rgb = image.convert("RGB")
            rgb.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            rgb.save(target_path, format="WEBP", quality=85, method=6)

        return str(target_path.as_posix())

    def delete_avatar(self, path: str | None) -> None:
        if not path:
            return
        avatar_path = Path(path)
        try:
            resolved_avatar = avatar_path.resolve()
            resolved_base = self.base_dir.resolve()
        except FileNotFoundError:
            return
        if resolved_base not in resolved_avatar.parents:
            return
        if resolved_avatar.exists():
            resolved_avatar.unlink()

