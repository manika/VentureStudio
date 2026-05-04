from pathlib import Path
import hashlib
import shutil


def save_uploaded_file(uploaded_file, data_dir: Path) -> str:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / uploaded_file.name
    with open(out_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return str(out_path)


SUPPORTED_EXTENSIONS = ("*.pdf", "*.txt", "*.docx", "*.md", "*.csv", "*.xlsx", "*.rtf", "*.pptx")


def list_files(data_dir: Path, patterns=SUPPORTED_EXTENSIONS):
    data_dir = Path(data_dir)
    files = []
    for p in patterns:
        files.extend(list(data_dir.rglob(p)))
    # Filter out hidden/system files
    files = [f for f in files if not f.name.startswith(".")]
    return files


def get_file_hash(file_path: str) -> str:
    """Return MD5 hex digest of a file."""
    file_path = Path(file_path)
    hasher = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, IOError):
        return ""


def should_reprocess(file_path: str, hash_cache: dict) -> bool:
    """Return True if file has changed since last processed (or was never processed)."""
    current_hash = get_file_hash(file_path)
    stored_hash = hash_cache.get(str(file_path), "")
    return current_hash != stored_hash
