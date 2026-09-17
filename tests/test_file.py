import shutil
from pathlib import Path

import pytest

from atloscli.file import File, MetadataError

DATA_DIR = Path(__file__).parent / "data"
IMAGE = DATA_DIR / "party_bear_claude.png"

pytestmark = pytest.mark.skipif(
    shutil.which("exiftool") is None, reason="exiftool is not installed"
)


def test_init_accepts_str_and_path():
    assert File(str(IMAGE)).path == IMAGE
    assert File(IMAGE).path == IMAGE


def test_get_metadata_png():
    f = File(IMAGE)
    f.get_metadata()

    metadata = f._all_metadata
    assert metadata["FileName"] == IMAGE.name
    assert metadata["FileType"] == "PNG"
    assert metadata["MIMEType"] == "image/png"
    assert metadata["ImageWidth"] == 2760
    assert metadata["ImageHeight"] == 2280


def test_get_metadata_sets_mime_type():
    f = File(IMAGE)
    f.get_metadata()
    assert f._mime_type == "image/png"


def test_get_metadata_missing_file(tmp_path):
    with pytest.raises(MetadataError):
        File(tmp_path / "missing.png").get_metadata()


def test_get_metadata_invalid_file(tmp_path):
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(bytes(range(256)) * 4)
    with pytest.raises(MetadataError):
        File(corrupt).get_metadata()
