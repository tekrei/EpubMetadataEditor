#!/usr/bin/env python3

import logging

from PySide6.QtWidgets import QApplication

from ui import MainWindow


def main():
    app = QApplication([])
    app.setApplicationName("EpubMetadata Editor")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
