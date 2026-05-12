from pathlib import Path
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
    files = [f for f in files if not f.name.startswith(".") and not f.name.startswith("~$")]
    return files

