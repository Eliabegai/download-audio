"""Anexa o runtime (Python, FFmpeg, Node e scripts) ao final do executável."""

from __future__ import annotations

import shutil
import struct
import zipfile
from pathlib import Path

MAGIC = 0x31444E424F525044
FOOTER = 16

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "apps" / "desktop" / "src-tauri" / "resources"
SRC = ROOT / "src"
EXE = ROOT / "apps" / "desktop" / "src-tauri" / "target" / "release" / "downloader_pro_desktop.exe"
PORTABLE = (
    ROOT
    / "apps"
    / "desktop"
    / "src-tauri"
    / "target"
    / "release"
    / "bundle"
    / "portable"
    / "Downloader Pro.exe"
)


def strip_payload(path: Path) -> None:
    with path.open("r+b") as fh:
        fh.seek(0, 2)
        size = fh.tell()
        if size < FOOTER:
            return
        fh.seek(-FOOTER, 2)
        zip_len, magic = struct.unpack("<QQ", fh.read(FOOTER))
        if magic != MAGIC or zip_len == 0 or zip_len + FOOTER > size:
            return
        fh.truncate(size - FOOTER - zip_len)


def copy_scripts() -> None:
    dest = RESOURCES / "src"
    dest.mkdir(parents=True, exist_ok=True)
    for script in SRC.glob("*.py"):
        shutil.copy2(script, dest / script.name)


def build_zip(destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for file in RESOURCES.rglob("*"):
            if not file.is_file():
                continue
            if "__pycache__" in file.parts or file.suffix == ".pyc":
                continue
            archive.write(file, file.relative_to(RESOURCES).as_posix())


def append_payload(exe: Path, payload: Path) -> None:
    data = payload.read_bytes()
    with exe.open("ab") as fh:
        fh.write(data)
        fh.write(struct.pack("<QQ", len(data), MAGIC))


def main() -> None:
    if not EXE.is_file():
        raise SystemExit(f"Executável não encontrado: {EXE}")
    if not (RESOURCES / "python" / "python.exe").is_file():
        raise SystemExit(f"Runtime não preparado em {RESOURCES}. Rode o build de novo.")

    copy_scripts()
    strip_payload(EXE)
    payload = EXE.with_suffix(".runtime.zip")
    print("Compactando runtime...")
    build_zip(payload)
    print(f"Anexando {payload.stat().st_size / (1024 * 1024):.1f} MB ao executável")
    append_payload(EXE, payload)
    PORTABLE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EXE, PORTABLE)
    payload.unlink(missing_ok=True)
    print(f"Portátil pronto: {PORTABLE}")


if __name__ == "__main__":
    main()
