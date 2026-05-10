#!/usr/bin/env python3

import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from ui import MainWindowGTK


def main():
    hwg = MainWindowGTK()
    hwg.window.show_all()
    Gtk.main()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
