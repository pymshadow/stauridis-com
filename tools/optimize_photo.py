"""Create the two WebP sizes used by the Stauridis portfolio.

Requires Pillow: python -m pip install Pillow
Example: python tools/optimize_photo.py original.jpg --name kart_track_03
"""

import argparse
import os
import re
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageCms, ImageOps


SITE_ROOT = Path(__file__).resolve().parents[1]


def prepared_image(source: Path) -> Image.Image:
    with Image.open(source) as opened:
        if getattr(opened, "n_frames", 1) != 1:
            raise ValueError("Only single-frame photos are supported")
        icc = opened.info.get("icc_profile")
        oriented = ImageOps.exif_transpose(opened)
        if icc:
            source_profile = ImageCms.ImageCmsProfile(BytesIO(icc))
            srgb_profile = ImageCms.createProfile("sRGB")
            return ImageCms.profileToProfile(
                oriented, source_profile, srgb_profile, outputMode="RGB"
            )
        return oriented.convert("RGB")


def save_temp(
    image: Image.Image, destination: Path, max_side: int, quality: int
) -> tuple[Path, tuple[int, int]]:
    resized = image.copy()
    resized.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".webp", delete=False
    ) as temporary:
        temp_path = Path(temporary.name)
    try:
        # Pillow writes no EXIF, GPS, or source ICC unless explicitly supplied.
        resized.save(temp_path, format="WEBP", quality=quality, method=6)
        return temp_path, resized.size
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original JPEG photo")
    parser.add_argument("--name", help="Output filename without extension")
    parser.add_argument("--output-root", type=Path, default=SITE_ROOT)
    parser.add_argument(
        "--replace", action="store_true", help="Replace both existing WebP files"
    )
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"Source photo does not exist: {args.source}")
    name = args.name or args.source.stem
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]*", name):
        parser.error("Use --name with only letters, digits, underscores, or hyphens")

    full_path = args.output_root / "photos" / f"{name}.webp"
    small_path = args.output_root / "photos" / "sm" / f"{name}.webp"
    if not args.replace and (full_path.exists() or small_path.exists()):
        parser.error("Output already exists; use --replace to update both sizes")

    image = prepared_image(args.source)
    temp_files = []
    try:
        full_temp, full_size = save_temp(image, full_path, 2000, 82)
        temp_files.append(full_temp)
        small_temp, small_size = save_temp(image, small_path, 1200, 80)
        temp_files.append(small_temp)
        os.replace(full_temp, full_path)
        os.replace(small_temp, small_path)
    finally:
        for temp_path in temp_files:
            temp_path.unlink(missing_ok=True)

    print(f"{full_path} {full_size[0]}x{full_size[1]} {full_path.stat().st_size / 1024:.0f} KB")
    print(f"{small_path} {small_size[0]}x{small_size[1]} {small_path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
