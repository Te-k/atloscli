"""Local file helpers."""

import functools
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import c2pa


class MetadataError(Exception):
    """Raised when exiftool cannot extract metadata from a file."""


@dataclass
class C2PAInfo:
    """C2PA provenance information of the active manifest of a file."""

    # claim_generator_info entries, e.g. [{"name": "Anthropic Claude.ai", ...}]
    generator: list[dict[str, Any]]
    # Signer details: alg, issuer, common_name, cert_serial_number...
    signature_info: dict[str, Any]
    # "Invalid", "Valid" (signature and hashes check out) or "Trusted" (the
    # signing certificate is also on a configured trust list)
    validation_state: str
    # True if the claim signature is cryptographically valid, even if the
    # content was modified after signing or the certificate is not trusted
    signature_valid: bool
    # Validation failures, e.g. {"code": "assertion.dataHash.mismatch", ...}
    failures: list[dict[str, Any]] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.validation_state in ("Valid", "Trusted")

    @property
    def trusted(self) -> bool:
        return self.validation_state == "Trusted"


@functools.cache
def _get_exiftool_path() -> str:  # pragma: no cover
    """
    From MAT2
    https://github.com/tpet/mat2/blob/master/libmat2/exiftool.py
    """
    possible_pathes = {
        "/usr/bin/exiftool",  # debian/fedora
        "/usr/bin/vendor_perl/exiftool",  # archlinux
    }

    for possible_path in possible_pathes:
        if os.path.isfile(possible_path):
            if os.access(possible_path, os.X_OK):
                return possible_path

    path = shutil.which("exiftool")
    if path is not None:
        return path

    raise RuntimeError("Unable to find exiftool")


class File:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._all_metadata: dict[str, Any] | None = None
        self._mime_type: str | None = None

    def get_metadata(self) -> None:
        """
        Get metadata
        """
        result = subprocess.run(
            [_get_exiftool_path(), "-json", "--", str(self.path)],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            metadata = json.loads(result.stdout)[0]
        except (json.JSONDecodeError, IndexError) as e:
            raise MetadataError(
                f"exiftool failed on {self.path}: {result.stderr.strip()}"
            ) from e
        if "Error" in metadata:
            raise MetadataError(f"exiftool failed on {self.path}: {metadata['Error']}")
        if result.returncode != 0:
            raise MetadataError(
                f"exiftool failed on {self.path}: {result.stderr.strip()}"
            )
        self._all_metadata = metadata
        self._mime_type = metadata.get("MIMEType")

    def get_c2pa(self) -> C2PAInfo | None:
        """Return C2PA information of the file, or None if it has none.

        The signature and content hashes are verified with the C2PA SDK.
        """
        try:
            with c2pa.Reader(self.path) as reader:
                store = json.loads(reader.json())
        except (c2pa.C2paError.ManifestNotFound, c2pa.C2paError.NotSupported):
            return None
        except c2pa.C2paError as e:
            raise MetadataError(f"cannot read C2PA data of {self.path}: {e}") from e

        manifest = store["manifests"][store["active_manifest"]]
        generator = manifest.get("claim_generator_info") or []
        if not generator and manifest.get("claim_generator"):
            generator = [{"name": manifest["claim_generator"]}]

        results = store.get("validation_results", {}).get("activeManifest", {})
        successes = {s["code"] for s in results.get("success", [])}
        failures = results.get("failure", [])
        signature_valid = "claimSignature.validated" in successes and not any(
            f["code"].startswith("claimSignature") for f in failures
        )

        return C2PAInfo(
            generator=generator,
            signature_info=manifest.get("signature_info", {}),
            validation_state=store.get("validation_state", "Invalid"),
            signature_valid=signature_valid,
            failures=failures,
        )
