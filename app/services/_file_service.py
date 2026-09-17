import logging
import os
import sys
from pathlib import Path

from gi.repository import Gio

logger = logging.getLogger(__name__)


class FileService:
    @staticmethod
    def rename(old_path: Path, new_name: str) -> Path:
        new_path = old_path.parent / new_name
        if new_path.exists():
            raise FileExistsError(f"A file named {new_name} already exists.")
        old_path.rename(new_path)
        return new_path

    @staticmethod
    def trash(file_path: str):
        gfile = Gio.File.new_for_path(file_path)
        gfile.trash(None)

    @staticmethod
    def open_containing_folder(file_path: str):
        folder = str(Path(file_path).parent)
        if sys.platform == "linux" or sys.platform == "linux2":
            import subprocess

            subprocess.Popen(["xdg-open", folder])
        elif sys.platform == "darwin":
            import subprocess

            subprocess.Popen(["open", folder])
        elif sys.platform == "win32":
            os.startfile(folder)

    @staticmethod
    def open_file(file_path: str):
        if sys.platform == "win32":
            os.startfile(file_path)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            import subprocess

            subprocess.Popen([opener, file_path])

    @staticmethod
    def find_files(
        directory: str | Path, pattern: str, recursive: bool = True
    ) -> list[Path]:
        """Generic method to find files matching a pattern in a directory."""
        root = Path(directory)

        if recursive:
            files = list(root.rglob(pattern, case_sensitive=False))
        else:
            files = list(root.glob(pattern, case_sensitive=False))

        files.sort(key=lambda p: p.name.lower())
        return files
