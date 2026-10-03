"""File handling: validation, streaming SHA-256, local save, tamper demo.

The SHA-256 computed here must match the browser's Web Crypto digest on the
public verify page byte for byte, so it is always computed over the raw
uploaded bytes, nothing else.
"""

import hashlib
import uuid

from fastapi import HTTPException, UploadFile

from ..config import get_settings
from ..states import ErrorCode
from .storage import get_storage

CHUNK = 1024 * 1024  # 1 MiB


class FileRejected(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=422, detail=message)
        self.details = {"code": ErrorCode.VALIDATION_ERROR.value}


def validate_upload(file: UploadFile) -> str:
    """Raise FileRejected unless the upload is allowed. Returns the extension."""
    settings = get_settings()
    name = file.filename or ""
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in settings.allowed_extension_list:
        allowed = ", ".join(settings.allowed_extension_list)
        raise FileRejected(f"File type '{ext or 'unknown'}' not allowed. Allowed: {allowed}")
    return ext


def save_upload(file: UploadFile) -> dict:
    """Stream the upload to storage, computing SHA-256 and enforcing the size
    cap mid-stream (never trust Content-Length). Returns file metadata."""
    settings = get_settings()
    ext = validate_upload(file)
    key = f"{uuid.uuid4().hex}{ext}"
    digest = hashlib.sha256()
    size = 0

    storage = get_storage()
    stored_path = storage.root / key  # written directly for streaming; key is app-generated
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stored_path, "wb") as out:
        while True:
            chunk = file.file.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_upload_bytes:
                out.close()
                stored_path.unlink(missing_ok=True)
                raise FileRejected(
                    f"File exceeds the {settings.max_upload_mb} MB limit"
                )
            digest.update(chunk)
            out.write(chunk)

    if size == 0:
        stored_path.unlink(missing_ok=True)
        raise FileRejected("Empty file")

    return {
        "file_name": file.filename or key,
        "stored_path": str(stored_path),
        "storage_key": key,
        "mime_type": file.content_type or "application/octet-stream",
        "file_size": size,
        "sha256": digest.hexdigest(),
    }


def compute_file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def make_tampered_copy(stored_path: str) -> str:
    """Create a copy with exactly one byte flipped (the demo 'Tamper with this
    file' button). The change breaks the hash but keeps the file plausible."""
    src = open(stored_path, "rb").read()
    if not src:
        raise FileRejected("Cannot tamper an empty file")
    # Flip a byte near the middle: past PDF/image headers, inside real content.
    idx = len(src) // 2
    tampered = bytearray(src)
    tampered[idx] ^= 0x01
    out_path = f"{stored_path}.tampered"
    with open(out_path, "wb") as fh:
        fh.write(bytes(tampered))
    return out_path
