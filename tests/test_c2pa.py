from pathlib import Path

import pytest

from atloscli.file import File, MetadataError

DATA_DIR = Path(__file__).parent / "data"
SIGNED_IMAGES = ["party_bear_claude.png", "plain_white_claude.png"]


@pytest.mark.parametrize("name", SIGNED_IMAGES)
def test_get_c2pa_signed_image(name):
    info = File(DATA_DIR / name).get_c2pa()

    assert info is not None
    assert info.generator[0]["name"] == "Anthropic Claude.ai"
    assert info.signature_info["issuer"] == "Anthropic, PBC"
    assert info.signature_info["common_name"] == "Anthropic Claude Content Signing"
    assert info.signature_valid
    assert info.valid
    assert "assertion.dataHash.mismatch" not in {f["code"] for f in info.failures}


def test_get_c2pa_without_manifest():
    assert File(DATA_DIR / "party_bear_claude_cleaned.png").get_c2pa() is None


def test_get_c2pa_unsupported_format(tmp_path):
    text = tmp_path / "file.txt"
    text.write_text("hello")
    assert File(text).get_c2pa() is None


def test_get_c2pa_tampered_image(tmp_path):
    data = bytearray((DATA_DIR / "plain_white_claude.png").read_bytes())
    data[-100] ^= 0xFF
    tampered = tmp_path / "tampered.png"
    tampered.write_bytes(data)

    info = File(tampered).get_c2pa()

    assert info is not None
    # The signature still matches the claim, but the content does not
    assert info.signature_valid
    assert not info.valid
    assert info.validation_state == "Invalid"
    assert "assertion.dataHash.mismatch" in {f["code"] for f in info.failures}


def test_get_c2pa_missing_file(tmp_path):
    with pytest.raises(MetadataError):
        File(tmp_path / "missing.png").get_c2pa()
