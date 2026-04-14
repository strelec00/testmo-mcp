import io
import mimetypes
from pathlib import Path
from typing import Any

from PIL import Image

from ..server import mcp
from ..client import _request, _upload

MAX_IMAGE_SIZE = 1_000_000  # 1 MB — compress images larger than this
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def _prepare_file(file_path: str) -> tuple[str, bytes, str]:
    """Read a file and compress it if it's a large image. Returns (filename, content, content_type)."""
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    file_content = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS and len(file_content) > MAX_IMAGE_SIZE:
        img = Image.open(io.BytesIO(file_content))
        img = img.convert("RGB")
        buf = io.BytesIO()
        quality = 85
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        while buf.tell() > MAX_IMAGE_SIZE and quality > 20:
            quality -= 10
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
        file_content = buf.getvalue()
        filename = path.stem + ".jpg"
        content_type = "image/jpeg"
    else:
        filename = path.name
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return filename, file_content, content_type


@mcp.tool()
async def testmo_list_case_attachments(
    case_id: int,
    page: int = 1,
    per_page: int = 100,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List all attachments for a test case.

    Args:
        case_id: The test case ID.
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if expands:
        params["expands"] = ",".join(expands)
    return await _request("GET", f"/cases/{case_id}/attachments", params=params)


@mcp.tool()
async def testmo_upload_case_attachment(
    case_id: int,
    file_path: str,
) -> dict[str, Any]:
    """Upload a single file attachment to a test case. Large images are auto-compressed.

    IMPORTANT: file_path must be an absolute path to a file saved on disk (e.g. /Users/jan/Desktop/screenshot.png).
    Pasted images or image data from the conversation cannot be uploaded — the user must save the file first and provide its path.
    If no path is provided or the user has not saved the file yet, ask them to save it and share the full file path.

    Args:
        case_id: The test case ID.
        file_path: Absolute path to the local file to upload (e.g. /Users/jan/Desktop/screenshot.png).
    """
    if not file_path or not file_path.strip():
        raise ValueError("file_path is required. Ask the user to save the file to disk and provide the full path (e.g. /Users/jan/Desktop/screenshot.png).")
    filename, file_content, content_type = _prepare_file(file_path)
    return await _upload(
        f"/cases/{case_id}/attachments/single",
        [("file", (filename, file_content, content_type))],
    )


@mcp.tool()
async def testmo_upload_case_attachments(
    case_id: int,
    file_paths: list[str],
) -> dict[str, Any]:
    """Upload up to 20 file attachments to a test case in one request. Large images are auto-compressed.

    IMPORTANT: Each path must be an absolute path to a file saved on disk.
    Pasted images or image data from the conversation cannot be uploaded — the user must save the files first.
    If no paths are provided, ask the user to save the files and share their full paths.

    Args:
        case_id: The test case ID.
        file_paths: List of absolute paths to local files to upload (max 20).
    """
    if not file_paths:
        raise ValueError("file_paths must not be empty")
    if len(file_paths) > 20:
        file_paths = file_paths[:20]
    files = []
    for fp in file_paths:
        filename, file_content, content_type = _prepare_file(fp)
        files.append(("file", (filename, file_content, content_type)))
    return await _upload(f"/cases/{case_id}/attachments", files)


@mcp.tool()
async def testmo_delete_case_attachments(
    case_id: int,
    attachment_ids: list[int],
) -> dict[str, Any]:
    """Delete one or more attachments from a test case.

    Args:
        case_id: The test case ID.
        attachment_ids: Array of attachment IDs to delete.
    """
    return await _request(
        "DELETE", f"/cases/{case_id}/attachments", data={"ids": attachment_ids}
    )
