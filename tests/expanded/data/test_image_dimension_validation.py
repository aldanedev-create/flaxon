"""Image dimension validation behavior and boundary cases."""

from io import BytesIO

import pytest
from PIL import Image

from flaxon.files.upload import UploadedFile
from flaxon.files.validation import ImageValidator


@pytest.mark.parametrize(
    "size,valid",
    [
        ((10, 10), True),
        ((9, 10), False),
        ((10, 9), False),
        ((21, 10), False),
        ((10, 21), False),
        ((20, 20), True),
    ],
)
def test_dimension_boundaries(size, valid):
    stream = BytesIO()
    Image.new("RGB", size).save(stream, format="PNG")
    stream.seek(0)
    file = UploadedFile("image.png", "image/png", len(stream.getvalue()), stream)
    errors = ImageValidator(min_width=10, min_height=10, max_width=20, max_height=20).validate_image(file)
    assert (not errors) == valid


def test_invalid_image_bytes_are_rejected():
    file = UploadedFile("image.png", "image/png", 4, BytesIO(b"fake"))
    assert "Invalid image file" in ImageValidator().validate_image(file)
