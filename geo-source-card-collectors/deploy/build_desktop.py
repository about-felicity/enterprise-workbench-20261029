"""Build the native Windows panel; keep build files outside the source tree."""

import os
import shutil
import tempfile
from pathlib import Path

import pefile
import PyInstaller.__main__


def main():
    repository = Path(__file__).resolve().parents[1]
    work = Path(tempfile.gettempdir()) / "geo-desktop-build"
    destination = repository.parent / "deliverables"
    work.mkdir(parents=True, exist_ok=True)
    PyInstaller.__main__.run(
        [
            "--noconfirm",
            "--onedir",
            "--windowed",
            "--name",
            "ContentWorkspace",
            "--distpath",
            str(destination),
            "--workpath",
            str(work / "work"),
            "--specpath",
            str(work),
            "--paths",
            str(repository),
            "--hidden-import",
            "paramiko",
            "--exclude-module",
            "PySide6.QtWebEngineWidgets",
            "--exclude-module",
            "PySide6.QtWebEngineCore",
            str(repository / "deploy/desktop_entry.py"),
        ]
    )
    internal = destination / "ContentWorkspace/_internal"
    if os.name == "nt":
        # Poppler on PATH can supply an ICU DLL with renamed exports. Qt uses
        # Windows' unversioned ICU ABI; do not bundle a different ICU ABI.
        icu = internal / "icuuc.dll"
        if icu.exists():
            library = pefile.PE(str(icu))
            exports = {item.name for item in library.DIRECTORY_ENTRY_EXPORT.symbols}
            library.close()
            if b"ucnv_open" not in exports:
                archive = work / "incompatible-libraries"
                archive.mkdir(exist_ok=True)
                for item in (icu, internal / "icudt78.dll"):
                    if item.exists():
                        shutil.move(str(item), str(archive / item.name))
        for name in ("VCRUNTIME140.dll", "VCRUNTIME140_1.dll"):
            supplied = internal / "PySide6" / name
            if supplied.exists():
                shutil.copy2(supplied, internal / name)
    print(destination / "ContentWorkspace/ContentWorkspace.exe")


if __name__ == "__main__":
    main()
