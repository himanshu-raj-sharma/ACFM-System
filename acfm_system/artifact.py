"""Securely prepare a local model artifact for application startup."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from urllib import request as urlrequest
from urllib.parse import urlparse

MAX_MODEL_BYTES = 250 * 1024 * 1024


class _HTTPSOnlyRedirectHandler(urlrequest.HTTPRedirectHandler):
    """Reject redirects that would downgrade the pinned download to HTTP."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme != "https":
            raise ValueError("a model URL redirect must stay HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_model(path: str) -> None:
    """Ensure a model exists locally, optionally downloading it securely."""
    destination = Path(path)
    expected_hash = os.environ.get("ACFM_MODEL_SHA256", "").strip().lower()
    model_url = os.environ.get("ACFM_MODEL_URL", "").strip()

    if expected_hash and len(expected_hash) != 64:
        raise ValueError("ACFM_MODEL_SHA256 must be a 64-character SHA-256 hash")

    if destination.exists():
        if expected_hash and _sha256(destination) != expected_hash:
            raise ValueError("the local model does not match ACFM_MODEL_SHA256")
        return

    if not model_url:
        return
    if urlparse(model_url).scheme != "https":
        raise ValueError("ACFM_MODEL_URL must use HTTPS")
    if not expected_hash:
        raise ValueError("ACFM_MODEL_SHA256 is required when downloading a model")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        opener = urlrequest.build_opener(_HTTPSOnlyRedirectHandler)
        with opener.open(model_url, timeout=60) as response:
            with tempfile.NamedTemporaryFile(
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = temporary.name
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_MODEL_BYTES:
                        raise ValueError("downloaded model exceeds the 250 MB limit")
                    temporary.write(chunk)
        downloaded = Path(temporary_path)
        if _sha256(downloaded) != expected_hash:
            raise ValueError("downloaded model does not match ACFM_MODEL_SHA256")
        os.replace(downloaded, destination)
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
