from pathlib import Path

from PIL import Image

from app.services.avatar_storage import AvatarStorageService


def test_save_company_avatar_converts_to_webp(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (140, 90), "#224466").save(source, format="PNG")

    service = AvatarStorageService(base_dir=tmp_path / "avatars")
    saved_path = service.save_company_avatar(company_id=7, source_path=str(source))

    target = Path(saved_path)
    assert target.exists()
    assert target.suffix == ".webp"
    assert "company_7" in target.as_posix()


def test_delete_avatar_removes_only_inside_storage(tmp_path: Path) -> None:
    service = AvatarStorageService(base_dir=tmp_path / "avatars")
    source = tmp_path / "input.png"
    Image.new("RGB", (120, 120), "#775533").save(source, format="PNG")
    managed = Path(
        service.save_company_avatar(
            company_id=1,
            source_path=str(source),
        )
    )

    service.delete_avatar(str(managed))
    assert not managed.exists()

    external = tmp_path / "external.webp"
    external.write_bytes(b"x")
    service.delete_avatar(str(external))
    assert external.exists()
