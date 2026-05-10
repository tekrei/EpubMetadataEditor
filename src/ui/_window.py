import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk # noqa
from pathlib import Path
import signal
import logging

from data import AppEvent
from ._book_list import BookListView
from ._book_details import BookDetailsView
from ._toolbar import ToolbarView
from ._dialogs import Dialogs
from services import ConfigManager, BookService, EventBus

logger = logging.getLogger(__name__)

ASSET_PATH = Path(__file__).parent.parent.resolve()
CONFIG_DIR = Path.home() / ".config" / "epub-metadata-editor"
CONFIG_FILE = CONFIG_DIR / "settings.json"

class MainWindowGTK:
    def __init__(self):
        # Initialize Services
        self.config_manager = ConfigManager(CONFIG_FILE)
        self.book_service = BookService()
        self.event_bus = EventBus()

        self.builder = Gtk.Builder()
        self.builder.add_from_file(str(ASSET_PATH / "assets" / "main.glade"))

        self.window = self.builder.get_object("mainWindow")
        self.statusbar = self.builder.get_object("statusbar")

        # Initialize Components with DI
        self.book_list = BookListView(self.builder, self.config_manager, self.book_service, self.event_bus)
        self.book_details = BookDetailsView(self.builder, self.config_manager, self.book_service, self.event_bus)
        self.toolbar = ToolbarView(self.builder, self.event_bus)

        self._setup_event_subscriptions()
        
        handlers = self._get_signal_handlers()
        self.builder.connect_signals(handlers)
        
        self._set_sensible_default_size()
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
        self.window.connect("key-press-event", self.on_window_key_press)

    def _setup_event_subscriptions(self):
        """Wires up the event bus subscriptions."""
        self.event_bus.subscribe(AppEvent.REQUEST_APP_QUIT, self.quit_window)
        self.event_bus.subscribe(AppEvent.REQUEST_LIST_CLEAR, self.book_list.clear)
        self.event_bus.subscribe(AppEvent.REQUEST_FOLDER_OPEN, self.book_list.open_folder_dialog)
        self.event_bus.subscribe(AppEvent.REQUEST_LIST_REFRESH, self.book_list.refresh)
        self.event_bus.subscribe(AppEvent.REQUEST_LIST_SELECT_ALL, self.book_list.select_all)
        self.event_bus.subscribe(AppEvent.REQUEST_LIST_DESELECT_ALL, self.book_list.unselect_all)
        self.event_bus.subscribe(AppEvent.REQUEST_SHOW_SETTINGS, self.on_settings)
        self.event_bus.subscribe(AppEvent.REQUEST_SHOW_ABOUT, lambda _: Dialogs.show_about(self.window))
        self.event_bus.subscribe(AppEvent.STATUS_MESSAGE, self.push_status)

    def _get_signal_handlers(self):
        """Aggregates all signal handlers for Gtk.Builder."""
        handlers = {
            "onDestroyWindow": self.quit_window,
            "onSaveClicked": self.on_save_clicked,
        }
        handlers.update(self.toolbar.get_handlers())
        handlers.update(self.book_list.get_handlers())
        handlers.update(self.book_details.get_handlers())
        return handlers

    def _save_config(self):
        """Save current window settings."""
        size = self.window.get_size()
        pos = self.window.get_position()
        self.config_manager.save({
            "width": size[0],
            "height": size[1],
            "x": pos[0],
            "y": pos[1],
            "maximized": self.window.is_maximized()
        })

    def _set_sensible_default_size(self):
        self.window.set_default_size(self.config_manager.get("width", 1024), self.config_manager.get("height", 768))
        self.window.move(self.config_manager.get("x", 0), self.config_manager.get("y", 0))
        if self.config_manager.get("maximized"):
            self.window.maximize()

    def on_save_clicked(self, widget):
        new_meta = self.book_details.on_save()
        if new_meta:
            self.book_list.update_selected_metadata(new_meta)
            self.push_status("Saved.")

    def on_window_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_F5:
            self.book_list.refresh()
            return True
        if (event.state & Gdk.ModifierType.CONTROL_MASK) and event.keyval == Gdk.KEY_a:
            if not isinstance(self.window.get_focus(), Gtk.Entry):
                self.book_list.select_all()
                return True
        if (event.state & Gdk.ModifierType.CONTROL_MASK) and (event.state & Gdk.ModifierType.SHIFT_MASK) and event.keyval == Gdk.KEY_A:
            self.book_list.unselect_all()
            return True
        return False

    def on_settings(self, _=None):
        current_template = self.config_manager.get("naming_template", "{year} - {title} ({author})")
        current_provider = self.config_manager.get("metadata_provider", "google")
        result = Dialogs.show_settings(self.window, current_template, current_provider)
        if result is not None:
            new_template, new_provider = result
            self.config_manager.set("naming_template", new_template)
            self.config_manager.set("metadata_provider", new_provider)
            self.config_manager.save()
            self.push_status("Settings saved.")

    def quit_window(self, _=None):
        self._save_config()
        Gtk.main_quit()

    def push_status(self, message: str):
        """Pushes a message to the status bar."""
        self.statusbar.push(0, message)