"""File handling and hashing edge cases.

The SHA-256 computed by the backend must byte-match the browser's Web Crypto
digest on the public verify page, so these tests pin the hashing behavior.
"""

import hashlib

import pytest
from fastapi import UploadFile

from app.config import get_settings
from app.services.files import (
    FileRejected,
    compute_file_sha256,
    make_tampered_copy,
    save_upload,
    validate_upload,
)
from app.services.storage import LocalStorage


def _upload_file(name: str, content: bytes, mime: str = "application/pdf") -> UploadFile:
    import io

    return UploadFile(filename=name, file=io.BytesIO(content), headers={"content-type": mime})


def test_compute_file_sha256_matches_hashlib(tmp_path):
    payload = b"attesta" * 1000
    path = tmp_path / "doc.pdf"
    path.write_bytes(payload)
    assert compute_file_sha256(str(path)) == hashlib.sha256(payload).hexdigest()


def test_validate_upload_extension_rules():
    assert validate_upload(_upload_file("a.pdf", b"x")) == ".pdf"
    assert validate_upload(_upload_file("A.PNG", b"x")) == ".png"  # case-insensitive
    with pytest.raises(FileRejected):
        validate_upload(_upload_file("a.txt", b"x"))
    with pytest.raises(FileRejected):
        validate_upload(_upload_file("noext", b"x"))


def test_save_upload_streams_and_hashes_exactly(tmp_path):
    content = bytes(range(256)) * 4096  # 1 MiB, crosses chunk boundaries
    meta = save_upload(_upload_file("blob.pdf", content))
    assert meta["sha256"] == hashlib.sha256(content).hexdigest()
    assert meta["file_size"] == len(content)
    with open(meta["stored_path"], "rb") as fh:
        assert fh.read() == content


def test_save_upload_rejects_oversize_mid_stream(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    content = b"x" * (1 * 1024 * 1024 + 1)
    with pytest.raises(FileRejected) as excinfo:
        save_upload(_upload_file("big.pdf", content))
    assert "1 MB" in str(excinfo.value.detail)


def test_make_tampered_copy_flips_exactly_one_byte(tmp_path):
    src = tmp_path / "real.pdf"
    payload = b"%PDF-1.4 attesta original document bytes" * 10
    src.write_bytes(payload)
    original_hash = hashlib.sha256(payload).hexdigest()

    tampered_path = make_tampered_copy(str(src))
    tampered = open(tampered_path, "rb").read()

    assert len(tampered) == len(payload)
    assert sum(a != b for a, b in zip(tampered, payload, strict=True)) == 1
    assert hashlib.sha256(tampered).hexdigest() != original_hash
    # The original file is untouched.
    assert compute_file_sha256(str(src)) == original_hash


def test_local_storage_refuses_path_traversal(tmp_path):
    storage = LocalStorage(str(tmp_path / "uploads"))
    with pytest.raises(ValueError):
        storage._path("../escape.pdf")
