"""Unit tests for the preprocessing pipeline."""

import base64
import io
import pytest
from PIL import Image

from app.services.preprocess import (
    validate_base64,
    validate_image_format,
    validate_dimensions,
    detect_blank_canvas,
    normalize_background,
    auto_crop_with_padding,
    resize_to_square,
    thicken_strokes,
    preprocess_image,
)
from app.exceptions import ImageValidationError


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_png_base64(pixels: list[list[int]], size: int = 256) -> str:
    """Create a grayscale PNG from a 2D pixel array (0=black, 255=white)."""
    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        import zlib, struct
        chunk = chunk_type + data
        crc = zlib.crc32(chunk) & 0xffffffff
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', crc)

    raw_data = b''
    for row in pixels:
        raw_data += b'\x00' + bytes(row)

    import zlib, struct
    signature = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 0, 0, 0, 0)
    compressed = zlib.compress(raw_data, 6)
    png = signature + png_chunk(b'IHDR', ihdr) + png_chunk(b'IDAT', compressed) + png_chunk(b'IEND', b'')
    return base64.b64encode(png).decode()


def make_blank_white(size: int = 256) -> str:
    return make_png_base64([[255] * size for _ in range(size)], size)


def make_black_circle(size: int = 256, radius: int = 80, cx: int = 128, cy: int = 128) -> str:
    pixels = [[0 if ((x - cx)**2 + (y - cy)**2)**0.5 < radius else 255 for x in range(size)] for y in range(size)]
    return make_png_base64(pixels, size)


def make_rectangle(size: int = 256, margin: int = 50) -> str:
    pixels = []
    for y in range(size):
        row = []
        for x in range(size):
            in_rect = margin <= x < size - margin and margin <= y < size - margin
            row.append(0 if in_rect else 255)
        pixels.append(row)
    return make_png_base64(pixels, size)


# ── validate_base64 ──────────────────────────────────────────────────────────

class TestValidateBase64:
    def test_valid_base64(self):
        b64 = base64.b64encode(b"hello").decode()
        result = validate_base64(b64)
        assert result == b"hello"

    def test_strips_data_uri_prefix(self):
        b64 = "data:image/png;base64," + base64.b64encode(b"hello").decode()
        result = validate_base64(b64)
        assert result == b"hello"

    def test_invalid_base64_raises(self):
        with pytest.raises(ImageValidationError) as exc_info:
            validate_base64("not!!valid@@base64!!!")
        assert "Invalid base64" in exc_info.value.message


# ── validate_image_format ─────────────────────────────────────────────────────

class TestValidateImageFormat:
    def test_valid_png(self):
        b64 = make_blank_white(64)
        img = validate_image_format(base64.b64decode(b64))
        assert img.size == (64, 64)
        assert img.format == "PNG"

    def test_corrupt_data_raises(self):
        with pytest.raises(ImageValidationError) as exc_info:
            validate_image_format(b"not an image at all")
        assert "Could not decode" in exc_info.value.message


# ── validate_dimensions ───────────────────────────────────────────────────────

class TestValidateDimensions:
    def test_valid_dimensions(self):
        img = Image.new("RGB", (100, 100))
        validate_dimensions(img)  # Should not raise

    def test_too_large_raises(self):
        img = Image.new("RGB", (3000, 3000))
        with pytest.raises(ImageValidationError) as exc_info:
            validate_dimensions(img)
        assert "too large" in exc_info.value.message

    def test_too_small_raises(self):
        img = Image.new("RGB", (5, 5))
        with pytest.raises(ImageValidationError) as exc_info:
            validate_dimensions(img)
        assert "too small" in exc_info.value.message


# ── detect_blank_canvas ───────────────────────────────────────────────────────

class TestDetectBlankCanvas:
    def test_blank_white_raises(self):
        img = Image.new("RGB", (256, 256), color="white")
        with pytest.raises(ImageValidationError) as exc_info:
            detect_blank_canvas(img)
        assert "blank" in exc_info.value.message.lower()

    def test_blank_black_raises(self):
        img = Image.new("RGB", (256, 256), color="black")
        with pytest.raises(ImageValidationError) as exc_info:
            detect_blank_canvas(img)
        assert "blank" in exc_info.value.message.lower()

    def test_drawing_passes(self):
        from PIL import ImageDraw
        img = Image.new("RGB", (256, 256), color="white")
        draw = ImageDraw.Draw(img)
        draw.ellipse([100, 100, 156, 156], outline="black")
        detect_blank_canvas(img)  # Should not raise


# ── Full pipeline ─────────────────────────────────────────────────────────────

class TestPreprocessPipeline:
    def test_blank_canvas_rejected(self):
        with pytest.raises(ImageValidationError) as exc_info:
            preprocess_image(make_blank_white(256))
        assert "blank" in exc_info.value.message.lower()

    def test_circle_image_processed(self):
        b64 = make_black_circle(256)
        result = preprocess_image(b64)
        # Result should be base64-encoded PNG
        decoded = base64.b64decode(result)
        img = Image.open(io.BytesIO(decoded))
        assert img.size == (512, 512)  # Resized to square
        assert img.format == "PNG"

    def test_rectangle_processed(self):
        b64 = make_rectangle(256)
        result = preprocess_image(b64)
        decoded = base64.b64decode(result)
        img = Image.open(io.BytesIO(decoded))
        assert img.size == (512, 512)
