"""Image preprocessing pipeline."""

import base64
import io
import logging
from PIL import Image
import numpy as np

from app.config import settings
from app.exceptions import ImageValidationError, PreprocessingError

logger = logging.getLogger(__name__)


def validate_base64(data: str) -> bytes:
    """Validate and decode a base64 string."""
    try:
        # Remove data URI prefix if present
        if "," in data:
            data = data.split(",", 1)[1]
        return base64.b64decode(data, validate=True)
    except Exception as e:
        raise ImageValidationError(
            message="Invalid base64 encoding",
            detail=str(e),
        )


def validate_image_format(data: bytes) -> Image.Image:
    """Verify the data is a valid image and return a PIL Image."""
    try:
        buffer = io.BytesIO(data)
        img = Image.open(buffer)
        # Force load all image data to catch truncated/corrupt images early
        img.load()
    except Exception as e:
        raise ImageValidationError(
            message="Could not decode image data",
            detail=f"Unsupported or corrupt image format: {e}",
        )

    if img.format not in ("PNG", "JPEG", "JPG"):
        raise ImageValidationError(
            message="Unsupported image format",
            detail=f"Format '{img.format}' not supported. Use PNG or JPEG.",
        )

    return img


def validate_dimensions(img: Image.Image) -> None:
    """Check image dimensions are within bounds."""
    w, h = img.size
    max_dim = settings.image_max_px
    min_dim = settings.image_min_px

    if w > max_dim or h > max_dim:
        raise ImageValidationError(
            message="Image too large",
            detail=f"Image is {w}x{h}. Maximum dimensions: {max_dim}x{max_dim}px.",
        )

    if w < min_dim or h < min_dim:
        raise ImageValidationError(
            message="Image too small",
            detail=f"Image is {w}x{h}. Minimum dimensions: {min_dim}x{min_dim}px.",
        )


def detect_blank_canvas(img: Image.Image, threshold: float = 5.0) -> None:
    """
    Detect if the canvas is blank (all white or all black).
    Raises ImageValidationError if canvas appears empty.
    """
    # Convert to grayscale numpy array
    gray = img.convert("L")
    arr = np.array(gray, dtype=np.float64)

    # Compute standard deviation of pixel values
    # Blank white = std dev ~0, blank black = also ~0, real drawings have high std dev
    std_dev = float(np.std(arr))
    mean_val = float(np.mean(arr))

    # If std dev is very low AND mean is near 0 (black) or 255 (white), it's blank
    if std_dev < threshold:
        if mean_val > 245:
            raise ImageValidationError(
                message="Canvas appears to be blank (all white)",
                detail="Draw something on the canvas before submitting.",
            )
        elif mean_val < 10:
            raise ImageValidationError(
                message="Canvas appears to be blank (all black)",
                detail="Draw something on the canvas before submitting.",
            )


def normalize_background(img: Image.Image) -> Image.Image:
    """Convert to RGB with white background, black strokes."""
    # Convert to grayscale
    gray = img.convert("L")
    arr = np.array(gray)

    # Threshold: pixels above 200 become white (background), below become black
    threshold = 200
    arr = np.where(arr > threshold, 255, 0).astype(np.uint8)

    result = Image.fromarray(arr, mode="L").convert("RGB")
    return result


def auto_crop_with_padding(img: Image.Image, padding_percent: float = 0.15) -> Image.Image:
    """
    Crop to the bounding box of non-white content, then add padding.
    If the image is mostly white, returns the original.
    """
    arr = np.array(img.convert("L"))
    rows = np.any(arr < 240, axis=1)
    cols = np.any(arr < 240, axis=0)

    if not rows.any() or not cols.any():
        return img  # No content found, return as-is

    y_min, y_max = np.where(rows)[0][[0, -1]]
    x_min, x_max = np.where(cols)[0][[0, -1]]

    # Crop
    cropped = img.crop((x_min, y_min, x_max + 1, y_max + 1))

    # Add padding
    w, h = cropped.size
    pad_x = int(w * padding_percent)
    pad_y = int(h * padding_percent)

    new_w = w + 2 * pad_x
    new_h = h + 2 * pad_y

    padded = Image.new("RGB", (new_w, new_h), color=(255, 255, 255))
    padded.paste(cropped, (pad_x, pad_y))

    return padded


def resize_to_square(img: Image.Image, size: int = 512) -> Image.Image:
    """Resize image to a square, preserving aspect ratio with white padding."""
    w, h = img.size

    # Determine scale factor to fit within size x size
    scale = size / max(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    resized = img.resize((new_w, new_h), Image.LANCZOS)

    # Pad to square
    square = Image.new("RGB", (size, size), color=(255, 255, 255))
    x_offset = (size - new_w) // 2
    y_offset = (size - new_h) // 2
    square.paste(resized, (x_offset, y_offset))

    return square


def thicken_strokes(img: Image.Image, iterations: int = 1) -> Image.Image:
    """
    Thicken dark strokes using a maximum filter (dilation).
    Helps VLMs see thin air-drawn lines better.
    """
    from PIL import ImageFilter

    for _ in range(iterations):
        img = img.filter(ImageFilter.MaxFilter(size=3))

    return img


def preprocess_image(base64_string: str) -> str:
    """
    Full preprocessing pipeline.
    Takes a base64 image string, validates and processes it,
    returns a base64 PNG string ready for the VLM.
    """
    try:
        # Step 1: Validate base64
        raw_bytes = validate_base64(base64_string)

        # Step 2: Decode image
        img = validate_image_format(raw_bytes)

        # Step 3: Check dimensions
        validate_dimensions(img)

        # Step 4: Detect blank canvas
        detect_blank_canvas(img)

        # Step 5: Normalize to white bg, black strokes
        img = normalize_background(img)

        # Step 6: Crop to content + padding
        img = auto_crop_with_padding(img)

        # Step 7: Resize to 512x512
        img = resize_to_square(img)

        # Step 8: Thicken strokes
        img = thicken_strokes(img, iterations=1)

        # Step 9: Encode back to base64 PNG
        output = io.BytesIO()
        img.save(output, format="PNG")
        return base64.b64encode(output.getvalue()).decode()

    except ImageValidationError:
        raise
    except Exception as e:
        logger.exception("Preprocessing pipeline failed")
        raise PreprocessingError(
            message="Failed to process image",
            detail=str(e),
        )
