import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtWidgets import QLineEdit, QMainWindow, QSplitter, QToolBar

from data import AppEvent
from services import BookService, ConfigManager, EventBus

from ._qt_dialogs import Dialogs
from ._qt_views import BookDetailsView, BookListView

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "epub-metadata-editor"
CONFIG_FILE = CONFIG_DIR / "settings.json"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EpubMetadata Editor")
        self.resize(1024, 768)

        self.config_manager = ConfigManager(CONFIG_FILE)
        self.book_service = BookService()
        self.event_bus = EventBus()
        self.book_list = BookListView(
            self.config_manager, self.book_service, self.event_bus, self
        )
        self.book_details = BookDetailsView(
            self.config_manager, self.book_service, self.event_bus, self
        )

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.book_list)
        splitter.addWidget(self.book_details)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

        self._create_actions()
        self.status = self.statusBar()
        self.status.showMessage("Ready")
        self.event_bus.subscribe(AppEvent.STATUS_MESSAGE, self.status.showMessage)
        self.event_bus.subscribe(AppEvent.REQUEST_SHOW_SETTINGS, self.on_settings)
        self.event_bus.subscribe(
            AppEvent.REQUEST_SHOW_ABOUT, lambda _=None: Dialogs.show_about(self)
        )
        self.event_bus.subscribe(AppEvent.REQUEST_APP_QUIT, lambda _=None: self.close())
        self._restore_window_state()

    def _create_actions(self):
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        file_menu = self.menuBar().addMenu("&File")
        edit_menu = self.menuBar().addMenu("&Edit")
        help_menu = self.menuBar().addMenu("&Help")

        def add_action(menu, label, callback, toolbar_button=False):
            action = QAction(label, self)
            action.triggered.connect(callback)
            menu.addAction(action)
            if toolbar_button:
                toolbar.addAction(action)
            return action

        add_action(
            file_menu,
            "Open Folder...",
            lambda: self.event_bus.emit(AppEvent.REQUEST_FOLDER_OPEN),
            True,
        )
        add_action(
            file_menu,
            "Refresh",
            lambda: self.event_bus.emit(AppEvent.REQUEST_LIST_REFRESH),
            True,
        ).setShortcut("F5")
        add_action(
            file_menu,
            "Clear List",
            lambda: self.event_bus.emit(AppEvent.REQUEST_LIST_CLEAR),
            True,
        )
        file_menu.addSeparator()
        add_action(file_menu, "Quit", lambda: self.close())

        add_action(
            edit_menu,
            "Select All Books",
            lambda: self.event_bus.emit(AppEvent.REQUEST_LIST_SELECT_ALL),
            True,
        )
        add_action(
            edit_menu,
            "Deselect All",
            lambda: self.event_bus.emit(AppEvent.REQUEST_LIST_DESELECT_ALL),
            True,
        )
        edit_menu.addSeparator()
        add_action(
            edit_menu,
            "Settings...",
            lambda: self.event_bus.emit(AppEvent.REQUEST_SHOW_SETTINGS),
        )
        add_action(
            help_menu,
            "About",
            lambda: self.event_bus.emit(AppEvent.REQUEST_SHOW_ABOUT),
        )

    def _restore_window_state(self):
        self.resize(
            self.config_manager.get("width", 1024),
            self.config_manager.get("height", 768),
        )
        self.move(
            self.config_manager.get("x", 0),
            self.config_manager.get("y", 0),
        )
        if self.config_manager.get("maximized"):
            self.showMaximized()

    def on_settings(self, _=None):
        current_template = self.config_manager.get(
            "naming_template", "{year} - {title} ({author})"
        )
        current_provider = self.config_manager.get("metadata_provider", "google")
        result = Dialogs.show_settings(self, current_template, current_provider)
        if result:
            template, provider = result
            self.config_manager.set("naming_template", template)
            self.config_manager.set("metadata_provider", provider)
            self.config_manager.save()
            self.status.showMessage("Settings saved.", 3000)

    def keyPressEvent(self, event: QKeyEvent):
        modifiers = event.modifiers()
        if event.key() == Qt.Key.Key_F5:
            self.book_list.refresh()
            event.accept()
            return
        if (
            event.key() == Qt.Key.Key_A
            and modifiers & Qt.KeyboardModifier.ControlModifier
            and not modifiers & Qt.KeyboardModifier.ShiftModifier
            and not isinstance(self.focusWidget(), QLineEdit)
        ):
            self.book_list.select_all()
            event.accept()
            return
        if event.key() == Qt.Key.Key_A and modifiers & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        ) == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            self.book_list.unselect_all()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.book_list.stop_scan()
        self.book_details.wait_for_operation()
        if self.isMaximized():
            self.config_manager.save({"maximized": True})
        else:
            geometry = self.geometry()
            self.config_manager.save(
                {
                    "width": geometry.width(),
                    "height": geometry.height(),
                    "x": geometry.x(),
                    "y": geometry.y(),
                    "maximized": False,
                }
            )
        event.accept()
