import logging
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data import AppEvent
from services import BookError, FileService

from ._qt_dialogs import Dialogs

logger = logging.getLogger(__name__)


class _ScanWorker(QThread):
    progress = Signal(int, int, int, str)
    completed = Signal(int, list)
    failed = Signal(int, str)

    def __init__(self, folder, book_service, generation, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.book_service = book_service
        self.generation = generation

    def run(self):
        try:
            paths = self.book_service.find_books(self.folder)
            books = []
            for index, path in enumerate(paths, 1):
                if self.isInterruptionRequested():
                    return
                metadata = self.book_service.get_metadata(path)
                metadata.update({"name": path.name, "is_folder": False})
                books.append((path, metadata))
                self.progress.emit(self.generation, index, len(paths), path.name)
            self.completed.emit(self.generation, books)
        except Exception as error:
            logger.exception("Failed to scan EPUB folder")
            self.failed.emit(self.generation, str(error))


class _OperationWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.completed.emit(self.operation())
        except Exception as error:
            logger.exception("Background operation failed")
            self.failed.emit(str(error))


class BookListView(QWidget):
    def __init__(self, config_manager, book_service, event_bus, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.book_service = book_service
        self.event_bus = event_bus
        self.folder = None
        self.folder_items = {}
        self._scan_worker = None
        self._scan_workers = []
        self._scan_generation = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search title, author, or filename...")
        self.search_entry.textChanged.connect(self._filter_items)
        layout.addWidget(self.search_entry)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Book / Folder", "Title and author"])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemSelectionChanged.connect(self._selection_changed)
        self.tree.itemDoubleClicked.connect(self._item_activated)
        self.tree.setUniformRowHeights(True)
        layout.addWidget(self.tree, 1)

        self.progressbar = QProgressBar()
        self.progressbar.setRange(0, 100)
        self.progressbar.hide()
        layout.addWidget(self.progressbar)

        self.event_bus.subscribe(AppEvent.REQUEST_LIST_CLEAR, self.clear)
        self.event_bus.subscribe(AppEvent.REQUEST_LIST_REFRESH, self.refresh)
        self.event_bus.subscribe(AppEvent.REQUEST_LIST_SELECT_ALL, self.select_all)
        self.event_bus.subscribe(AppEvent.REQUEST_LIST_DESELECT_ALL, self.unselect_all)
        self.event_bus.subscribe(AppEvent.REQUEST_FOLDER_OPEN, self.open_folder_dialog)

    def open_folder_dialog(self, _=None):
        folder = Dialogs.get_folder(self.window())
        if folder:
            self.folder = Path(folder)
            self.refresh()

    def refresh(self, _=None):
        if not self.folder:
            return
        self.clear()
        self.folder_items.clear()
        self.progressbar.setValue(0)
        self.progressbar.show()
        self.event_bus.emit(AppEvent.STATUS_MESSAGE, "Scanning for EPUB files...")
        generation = self._scan_generation
        worker = _ScanWorker(self.folder, self.book_service, generation, self)
        worker.progress.connect(self._scan_progress)
        worker.completed.connect(self._scan_completed)
        worker.failed.connect(self._scan_failed)
        worker.finished.connect(self._scan_worker_finished)
        worker.finished.connect(worker.deleteLater)
        self._scan_worker = worker
        self._scan_workers.append(worker)
        worker.start()

    def _scan_progress(self, generation, current, total, filename):
        if generation != self._scan_generation:
            return
        if total:
            self.progressbar.setValue(int(current * 100 / total))
        if current % 5 == 0 or current == total:
            self.event_bus.emit(
                AppEvent.STATUS_MESSAGE, f"Loading: {current}/{total}..."
            )

    def _scan_completed(self, generation, books):
        if generation != self._scan_generation:
            return
        self.progressbar.hide()
        if not books:
            self.event_bus.emit(AppEvent.STATUS_MESSAGE, "No EPUBs found.")
            return

        for path, metadata in books:
            relative_path = path.relative_to(self.folder)
            parent = self._ensure_folder(relative_path.parent)
            item = QTreeWidgetItem([metadata["name"], _book_summary(metadata)])
            item.setData(0, Qt.ItemDataRole.UserRole, metadata)
            if parent:
                parent.addChild(item)
            else:
                self.tree.addTopLevelItem(item)
        self._filter_items(self.search_entry.text())
        self.event_bus.emit(
            AppEvent.STATUS_MESSAGE, f"Successfully loaded {len(books)} books."
        )

    def _scan_failed(self, generation, message):
        if generation != self._scan_generation:
            return
        self.progressbar.hide()
        Dialogs.show_error_message(self.window(), f"Failed to scan folder: {message}")

    def _scan_worker_finished(self):
        worker = self.sender()
        if worker in self._scan_workers:
            self._scan_workers.remove(worker)
        if self._scan_worker is worker:
            self._scan_worker = None

    def _ensure_folder(self, relative_path):
        if not relative_path.parts:
            return None
        key = relative_path.as_posix()
        if key in self.folder_items:
            return self.folder_items[key]
        parent = self._ensure_folder(relative_path.parent)
        path = self.folder / relative_path
        metadata = {
            "name": relative_path.name,
            "title": "",
            "author": "",
            "path": str(path),
            "is_folder": True,
        }
        item = QTreeWidgetItem([relative_path.name, ""])
        item.setData(0, Qt.ItemDataRole.UserRole, metadata)
        if parent:
            parent.addChild(item)
        else:
            self.tree.addTopLevelItem(item)
        self.folder_items[key] = item
        return item

    def _filter_items(self, query):
        query = query.strip().casefold()

        def visit(item):
            metadata = item.data(0, Qt.ItemDataRole.UserRole) or {}
            own_match = (
                not query
                or query
                in " ".join(
                    str(metadata.get(key, "")) for key in ("title", "author", "name")
                ).casefold()
            )
            child_match = False
            for index in range(item.childCount()):
                child_match = visit(item.child(index)) or child_match
            visible = own_match or child_match
            item.setHidden(not visible)
            if query and child_match:
                item.setExpanded(True)
            return visible

        for index in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(index))

    def _selection_changed(self):
        self.event_bus.emit(AppEvent.SELECTION_CHANGED, self.get_selected_file_info())

    def get_selected_file_info(self):
        selected = self.tree.selectedItems()
        if len(selected) != 1:
            return None
        metadata = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not metadata or metadata.get("is_folder"):
            return None
        return metadata

    def _item_activated(self, item, _column):
        metadata = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if metadata.get("is_folder"):
            item.setExpanded(not item.isExpanded())
        else:
            self.event_bus.emit(AppEvent.FOCUS_DETAILS)

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
        if item not in self.tree.selectedItems():
            self.tree.setCurrentItem(item)
        metadata = item.data(0, Qt.ItemDataRole.UserRole) or {}

        menu = QMenu(self)
        if not metadata.get("is_folder"):
            menu.addAction("Rename File", lambda: self._rename_file(item))
        menu.addAction("Batch Rename", self.on_batch_rename)
        if not metadata.get("is_folder"):
            menu.addAction("Move to Trash", self.on_delete_files)
        menu.addAction(
            "Open Containing Folder",
            lambda: FileService.open_containing_folder(metadata["path"]),
        )
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _rename_file(self, item):
        metadata = item.data(0, Qt.ItemDataRole.UserRole)
        old_path = Path(metadata["path"])
        new_name = Dialogs.get_text_input(
            self.window(), "Rename File", "New filename:", old_path.name
        )
        if not new_name or new_name == old_path.name:
            return
        try:
            new_path = FileService.rename(old_path, new_name)
            metadata.update({"name": new_name, "path": str(new_path)})
            item.setText(0, new_name)
            item.setData(0, Qt.ItemDataRole.UserRole, metadata)
        except OSError as error:
            Dialogs.show_error_message(self.window(), str(error))
            logger.error("Rename error: %s", error)

    def on_batch_rename(self):
        selected = self.tree.selectedItems()
        template = self.config_manager.get(
            "naming_template", "{year} - {title} ({author})"
        )
        changes = []
        for item in selected:
            metadata = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if metadata.get("is_folder"):
                continue
            old_path = Path(metadata["path"])
            new_name = self.book_service.format_filename(template, metadata)
            if new_name and new_name != old_path.name:
                changes.append((item, old_path, new_name))
        if not changes:
            return
        preview = [(old.name, new) for _, old, new in changes]
        if not Dialogs.show_rename_preview(self.window(), preview):
            return
        for item, old_path, new_name in changes:
            try:
                new_path = FileService.rename(old_path, new_name)
                metadata = item.data(0, Qt.ItemDataRole.UserRole)
                metadata.update({"name": new_name, "path": str(new_path)})
                item.setText(0, new_name)
                item.setData(0, Qt.ItemDataRole.UserRole, metadata)
            except OSError as error:
                logger.error("Batch rename failed for %s: %s", old_path, error)
        self.event_bus.emit(AppEvent.STATUS_MESSAGE, "Batch rename complete.")

    def on_delete_files(self):
        items = [
            item
            for item in self.tree.selectedItems()
            if not (item.data(0, Qt.ItemDataRole.UserRole) or {}).get("is_folder")
        ]
        if not items or not Dialogs.ask_confirmation(
            self.window(), "Delete", f"Trash {len(items)} item(s)?"
        ):
            return
        for item in items:
            metadata = item.data(0, Qt.ItemDataRole.UserRole)
            try:
                FileService.trash(metadata["path"])
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))
            except OSError as error:
                logger.error("Trash error: %s", error)
                self.event_bus.emit(
                    AppEvent.STATUS_MESSAGE, f"Failed to trash {metadata['name']}"
                )
        self._selection_changed()

    def update_selected_metadata(self, metadata):
        selected = self.tree.selectedItems()
        if len(selected) != 1:
            return
        item = selected[0]
        current = item.data(0, Qt.ItemDataRole.UserRole) or {}
        current.update(metadata)
        item.setData(0, Qt.ItemDataRole.UserRole, current)
        item.setText(1, _book_summary(current))

    def clear(self, _=None):
        self._scan_generation += 1
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.requestInterruption()
        self._scan_worker = None
        self.tree.clear()
        self.folder_items.clear()
        self.progressbar.hide()
        self._selection_changed()

    def select_all(self, _=None):
        self.tree.selectAll()

    def unselect_all(self, _=None):
        self.tree.clearSelection()

    def stop_scan(self):
        workers = tuple(self._scan_workers)
        for worker in workers:
            if worker.isRunning():
                worker.requestInterruption()
        for worker in workers:
            worker.wait()
        self._scan_workers.clear()
        self._scan_worker = None


def _book_summary(metadata):
    title = metadata.get("title") or "Unknown Title"
    author = metadata.get("author") or "Unknown Author"
    return f"{title} ({author})"


class BookDetailsView(QWidget):
    def __init__(self, config_manager, book_service, event_bus, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.book_service = book_service
        self.event_bus = event_bus
        self.current_path = None
        self._worker = None
        self._operation_success = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(QLabel("Book Details"))

        content = QHBoxLayout()
        cover_column = QVBoxLayout()
        self.img_cover = QLabel("No cover")
        self.img_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_cover.setFixedSize(150, 210)
        self.img_cover.setStyleSheet("border: 1px solid palette(mid);")
        cover_column.addWidget(self.img_cover, 0, Qt.AlignmentFlag.AlignTop)
        self.btn_change = QPushButton("Change Cover...")
        self.btn_clear = QPushButton("Clear Cover")
        cover_column.addWidget(self.btn_change)
        cover_column.addWidget(self.btn_clear)
        content.addLayout(cover_column)

        form_column = QVBoxLayout()
        form = QFormLayout()
        self.fields = {
            key: QLineEdit() for key in ("title", "author", "publisher", "date", "isbn")
        }
        for key, label in (
            ("title", "Title"),
            ("author", "Author"),
            ("publisher", "Publisher"),
            ("date", "Date"),
            ("isbn", "ISBN"),
        ):
            form.addRow(f"{label}:", self.fields[key])
        form_column.addLayout(form)

        actions = QHBoxLayout()
        self.btn_fetch = QPushButton("Fetch from Web")
        self.btn_open = QPushButton("Open EPUB")
        self.btn_save = QPushButton("Save Changes")
        actions.addWidget(self.btn_fetch)
        actions.addStretch(1)
        actions.addWidget(self.btn_open)
        actions.addWidget(self.btn_save)
        form_column.addLayout(actions)
        self.activity = QLabel()
        form_column.addWidget(self.activity)
        form_column.addStretch(1)
        content.addLayout(form_column, 1)
        layout.addLayout(content)

        self.btn_save.clicked.connect(self.on_save_clicked)
        self.btn_open.clicked.connect(self.on_open_epub)
        self.btn_change.clicked.connect(self.on_change_cover)
        self.btn_clear.clicked.connect(lambda: self.on_change_cover(True))
        self.btn_fetch.clicked.connect(self.on_fetch_metadata)
        self.event_bus.subscribe(AppEvent.SELECTION_CHANGED, self.update)
        self.event_bus.subscribe(AppEvent.FOCUS_DETAILS, self._focus_title)
        self.update(None)

    def _focus_title(self, _=None):
        self.fields["title"].setFocus()

    def update(self, info):
        self.current_path = info.get("path") if info else None
        for key, field in self.fields.items():
            field.setText((info.get(key) or "") if info else "")
            field.setEnabled(bool(info))
        for button in (self.btn_open, self.btn_change, self.btn_clear, self.btn_save):
            button.setEnabled(bool(info))
        self.btn_fetch.setEnabled(bool(info))
        self._load_cover()

    def _load_cover(self):
        self.img_cover.clear()
        self.img_cover.setText("No cover")
        if not self.current_path:
            return
        data = self.book_service.get_cover(self.current_path)
        image = QImage.fromData(data) if data else QImage()
        if not image.isNull():
            pixmap = QPixmap.fromImage(image).scaled(
                self.img_cover.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.img_cover.setPixmap(pixmap)

    def on_save_clicked(self):
        if not self.current_path:
            return
        metadata = {key: field.text() for key, field in self.fields.items()}
        try:
            self.book_service.update_metadata(self.current_path, metadata)
            self.event_bus.emit(AppEvent.STATUS_MESSAGE, "Saved.")
            self.event_bus.emit(
                AppEvent.SELECTION_CHANGED, metadata | {"path": self.current_path}
            )
        except BookError as error:
            Dialogs.show_error_message(self.window(), f"Update failed: {error}")

    def on_open_epub(self):
        if self.current_path:
            FileService.open_file(self.current_path)

    def on_change_cover(self, is_clear=False):
        if not self.current_path:
            return
        image_path = None if is_clear else Dialogs.get_image_file(self.window())
        if not is_clear and not image_path:
            return
        if self.book_service.update_cover(self.current_path, image_path):
            self._load_cover()

    def on_fetch_metadata(self, _=None):
        isbn = self.fields["isbn"].text().strip()
        if not isbn:
            Dialogs.show_error_message(self.window(), "Please enter an ISBN first.")
            return
        path = self.current_path
        provider = self.config_manager.get("metadata_provider", "google")
        self._set_busy(True, "Fetching metadata...")
        self._run_operation(
            lambda: self.book_service.fetch_metadata_by_isbn(isbn, provider),
            lambda results: self._metadata_fetch_complete(path, results),
        )

    def _metadata_fetch_complete(self, path, results):
        self._set_busy(False)
        if path != self.current_path:
            return
        if not results:
            provider = self.config_manager.get("metadata_provider", "google")
            Dialogs.show_error_message(
                self.window(), f"No metadata found via {provider.title()}."
            )
            return
        current_meta = {key: field.text() for key, field in self.fields.items()}
        current_cover = self.book_service.get_cover(path)
        applied = Dialogs.show_metadata_diff(
            self.window(), current_meta, results, current_cover
        )
        if not applied:
            return
        for key, value in applied.items():
            if key != "_apply_cover" and key in self.fields:
                self.fields[key].setText(value)
        if applied.get("_apply_cover") and results.get("cover_url"):
            self._download_cover(path, results["cover_url"])

    def _download_cover(self, path, url):
        self._set_busy(True, "Downloading cover...")

        def download():
            temporary_path = None
            try:
                with urllib.request.urlopen(url, timeout=20) as response:
                    data = response.read()
                with tempfile.NamedTemporaryFile(
                    suffix=".jpg", delete=False
                ) as temporary:
                    temporary.write(data)
                    temporary_path = Path(temporary.name)
                self.book_service.update_cover(path, str(temporary_path))
            finally:
                if temporary_path and temporary_path.exists():
                    temporary_path.unlink()

        self._run_operation(
            download,
            lambda _result: self._cover_download_complete(path),
        )

    def _cover_download_complete(self, path):
        self._set_busy(False)
        if path == self.current_path:
            self._load_cover()
            self.event_bus.emit(AppEvent.STATUS_MESSAGE, "Cover updated from web.")

    def _run_operation(self, operation, on_success):
        worker = _OperationWorker(operation, self)
        worker.completed.connect(self._operation_completed)
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(self._operation_finished)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        self._operation_success = on_success
        worker.start()

    def _operation_completed(self, result):
        callback = self._operation_success
        self._operation_success = None
        if callback:
            callback(result)

    def _operation_failed(self, message):
        self._operation_success = None
        self._set_busy(False)
        Dialogs.show_error_message(self.window(), message)

    def _operation_finished(self):
        if self._worker is self.sender():
            self._worker = None

    def wait_for_operation(self):
        if self._worker and self._worker.isRunning():
            self._worker.wait()
        self._worker = None

    def _set_busy(self, busy, message=""):
        self.activity.setText(message)
        self.btn_fetch.setEnabled(not busy and self.current_path is not None)
        self.btn_change.setEnabled(not busy and self.current_path is not None)
        self.btn_clear.setEnabled(not busy and self.current_path is not None)
