"""Tests for pulse.intake.storage module."""

from io import BytesIO
from PIL import Image
from pulse.intake.storage import R2StorageClient, generate_issue_key, make_web_version


def test_generate_issue_key():
    key_hires = generate_issue_key("2026-08-07", is_web=False)
    key_web = generate_issue_key("2026-08-07", is_web=True)

    assert key_hires == "issues/2026/08/2026-08-07-hires.png"
    assert key_web == "issues/2026/08/2026-08-07-web.jpg"


def test_make_web_version_resizes_large_image():
    # Create large 3000x4000 test image in memory
    img = Image.new("RGB", (3000, 4000), color=(255, 200, 100))
    buf = BytesIO()
    img.save(buf, format="PNG")
    raw_data = buf.getvalue()

    web_data = make_web_version(raw_data, max_long_edge=2048, quality=88)
    assert len(web_data) > 0

    web_img = Image.open(BytesIO(web_data))
    w, h = web_img.size
    assert max(w, h) == 2048
    assert web_img.format == "JPEG"


def test_r2_upload(mock_s3):
    storage = R2StorageClient(s3_client=mock_s3)
    url = storage.upload(b"test data", "issues/2026/08/test.png")

    assert url == "https://assets.pulse.art/issues/2026/08/test.png"
    mock_s3.put_object.assert_called_once_with(
        Bucket="pulse-assets",
        Key="issues/2026/08/test.png",
        Body=b"test data",
        ContentType="image/png",
    )
