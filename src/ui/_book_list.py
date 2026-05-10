import logging
import threading
from pathlib import Path

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, GLib, Gtk

from data import AppEvent
from services import BookError, FileService

from ._dialogs import Dialogs

logger = logging.getLogger(__name__)


class BookListView:
    def __init__(self, builder, config_manager, book_service, event_bus):
        self.config_manager = config_manager
        self.book_service = book_service
        self.event_bus = event_bus
        self.builder = builder
        self.folder = None
        self.folder_rows = {}
        self.rows_data = {} # Map of row widget to metadata
        self.expanded_folders = set() # Set of relative path strings
        self.last_selected_row = None # Anchor for range selection

        self.list_box = builder.get_object("lstBooks")
        self.search_entry = builder.get_object("searchEntry")
        self.progressbar = builder.get_object("progressbar")

        self.list_box.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.list_box.set_filter_func(self.filter_func)
        self.list_box.set_sort_func(self.sort_func)
        self.list_box.connect("button-press-event", self.on_button_press)
        self.list_box.connect("selected-rows-changed", lambda _: self.event_bus.emit(AppEvent.SELECTION_CHANGED, self.get_selected_file_info()))

    def get_handlers(self):
        return {
            "onSearchChanged": lambda *a: self.list_box.invalidate_filter(),
            "onLstBooksRowActivated": self.on_row_activated,
        }

    def on_row_activated(self, listbox, row):
        meta = self.rows_data.get(row)
        if not meta:
            return

        if meta['is_folder']:
            rel_path = str(Path(meta['path']).relative_to(self.folder))
            if rel_path in self.expanded_folders:
                self.expanded_folders.remove(rel_path)
            else:
                self.expanded_folders.add(rel_path)

            self._update_row_widget(row)
            self.list_box.invalidate_filter()
        else:
            self.event_bus.emit(AppEvent.FOCUS_DETAILS)

    def filter_func(self, row):
        query = self.search_entry.get_text().lower()
        meta = self.rows_data.get(row)
        if not meta:
            return True

        # 1. Search Logic: If searching, show all matches flat
        if query:
            text_to_search = f"{meta['title']} {meta['author']} {meta['name']}".lower()
            return query in text_to_search

        # 2. Expansion Logic: Hide if any ancestor folder is not expanded
        return not self._is_ancestor_collapsed(meta)

    def sort_func(self, row1, row2):
        meta1 = self.rows_data.get(row1)
        meta2 = self.rows_data.get(row2)
        if not meta1 or not meta2:
            return 0

        # Sort by full path to maintain the folder structure in the flat list
        p1 = meta1['path'].lower()
        p2 = meta2['path'].lower()
        return (p1 > p2) - (p1 < p2)

    def on_button_press(self, listbox, event):
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            row = listbox.get_row_at_y(event.y)
            if not row:
                return False

            # 1. Shift + Click: Range Selection
            if (event.state & Gdk.ModifierType.SHIFT_MASK) and self.last_selected_row:
                all_rows = listbox.get_children()
                try:
                    idx1 = all_rows.index(self.last_selected_row)
                    idx2 = all_rows.index(row)
                    start, end = (idx1, idx2) if idx1 < idx2 else (idx2, idx1)

                    listbox.unselect_all()
                    for i in range(start, end + 1):
                        child = all_rows[i]
                        if child.get_visible():
                            listbox.select_row(child)
                    row.grab_focus()
                    return True
                except ValueError:
                    pass

            # 2. Control + Click: Toggle Selection (Default behavior)
            if event.state & Gdk.ModifierType.CONTROL_MASK:
                self.last_selected_row = row
                return False  # Let Gtk handle the toggle

            # 3. Standard Click: Single Selection
            # Toggle expansion if it's a folder
            meta = self.rows_data.get(row)
            if meta and meta['is_folder']:
                self.on_row_activated(listbox, row)

            listbox.unselect_all()
            listbox.select_row(row)
            self.last_selected_row = row
            row.grab_focus()
            return True

        if event.button == 3:
            row = self.list_box.get_row_at_y(event.y)
            if row:
                # Select on right-click if not already selected
                if row not in self.list_box.get_selected_rows():
                    self.list_box.unselect_all()
                    self.list_box.select_row(row)

                meta = self.rows_data.get(row)
                if meta:
                    self._show_context_menu(event, row)
            return True
        return False

    def _show_context_menu(self, event, row):
        menu = Gtk.Menu()
        items = [
            ("Rename File", lambda _: self.on_rename_file(row)),
            ("Batch Rename", lambda _: self.on_batch_rename()),
            ("Move to Trash", lambda _: self.on_delete_files()),
            ("Open containing folder", lambda _: self._on_open_containing_folder(row))
        ]
        for label, callback in items:
            m_item = Gtk.MenuItem(label=label)
            m_item.connect("activate", callback)
            menu.append(m_item)
        menu.show_all()
        menu.popup_at_pointer(event)

    def on_rename_file(self, row):
        meta = self.rows_data[row]
        old_path = Path(meta['path'])
        # Using refactored Dialogs
        new_name = Dialogs.get_text_input(self.builder.get_object("mainWindow"), "Rename File", "New filename:", old_path.name)

        if new_name and new_name != old_path.name:
            try:
                new_path = FileService.rename(old_path, new_name)
                meta['name'] = new_name
                meta['path'] = str(new_path)
                self._update_row_widget(row)
            except OSError as e:
                Dialogs.show_error_message(self.builder.get_object("mainWindow"), str(e))
                logger.error(f"Rename error: {e}")

    def on_batch_rename(self):
        selected_rows = self.list_box.get_selected_rows()
        template = self.config_manager.get("naming_template", "{year} - {title} ({author})")
        changes, preview = [], []

        for row in selected_rows:
            meta = self.rows_data.get(row)
            if not meta or meta['is_folder']:
                continue

            old_path = Path(meta['path'])

            n_name = self.book_service.format_filename(template, meta)
            if n_name and old_path.name != n_name:
                changes.append((old_path, n_name, row))
                preview.append((old_path.name, n_name))

        if changes and Dialogs.show_rename_preview(self.builder.get_object("mainWindow"), preview):
            for old, n_name, row in changes:
                try:
                    new_path = FileService.rename(old, n_name)
                    meta = self.rows_data[row]
                    meta['name'] = n_name
                    meta['path'] = str(new_path)
                    self._update_row_widget(row)
                except OSError:
                    continue
            self.event_bus.emit(AppEvent.STATUS_MESSAGE, "Batch rename complete.")

    def on_delete_files(self):
        selected_rows = self.list_box.get_selected_rows()
        parent = self.builder.get_object("mainWindow")
        if not selected_rows or not Dialogs.ask_confirmation(parent, "Delete", f"Trash {len(selected_rows)} item(s)?"):
            return

        for row in selected_rows:
            meta = self.rows_data.get(row)
            if not meta or meta['is_folder']:
                continue
            try:
                FileService.trash(meta['path'])
                self.list_box.remove(row)
                del self.rows_data[row]
            except OSError as e:
                logger.error(f"Trash error: {e}")
                self.event_bus.emit(AppEvent.STATUS_MESSAGE, f"Failed to trash {meta['name']}")

    def _on_open_containing_folder(self, row):
        meta = self.rows_data.get(row)
        if meta:
            FileService.open_containing_folder(meta['path'])

    def open_folder_dialog(self, _=None):
        folder_selected = Dialogs.get_folder()
        if folder_selected:
            self.folder = Path(folder_selected)
            self.refresh()

    def refresh(self, _=None):
        if not self.folder: # E701
            return
        self.clear()
        self.folder_rows = {}
        self.rows_data = {}
        self.expanded_folders = set()

        def run_scan():
            epubs = self.book_service.find_books(self.folder)
            GLib.idle_add(self._start_loading, epubs)

        threading.Thread(target=run_scan, daemon=True).start()

    def _start_loading(self, epubs):
        if not epubs:
            self.event_bus.emit(AppEvent.STATUS_MESSAGE, "No EPUBs found.")
            return
        self.progressbar.show()
        self.progressbar.set_fraction(0.0)
        load_gen = self._load_books_generator(epubs)
        GLib.idle_add(lambda: next(load_gen, False))

    def _get_or_create_folder_row(self, relative_path):
        """Recursively ensures rows for parent folders exist."""
        if not relative_path.parts:
            return

        path_str = str(relative_path)
        if path_str in self.folder_rows:
            return

        # Ensure the parent of this folder exists first
        self._get_or_create_folder_row(relative_path.parent)

        meta = {
            'name': relative_path.name,
            'title': '',
            'author': '',
            'path': str(self.folder / relative_path),
            'is_folder': True,
            'depth': len(relative_path.parts) - 1
        }

        row = self._create_row_widget(meta)
        self.rows_data[row] = meta
        self.folder_rows[path_str] = row
        self.list_box.add(row)

    def _create_row_widget(self, meta):
        """Creates a simple horizontal box for the ListBox row."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Add indentation based on nesting depth
        depth = meta.get('depth', 0)
        box.set_margin_start(10 + (depth * 20))

        box.set_margin_end(10)
        box.set_margin_top(5)
        box.set_margin_bottom(5)

        if meta['is_folder']:
            rel_path = str(Path(meta['path']).relative_to(self.folder))
            is_expanded = rel_path in self.expanded_folders
            icon_name = "pan-down-symbolic" if is_expanded else "pan-end-symbolic"
        else:
            icon_name = "text-x-generic"

        img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
        box.pack_start(img, False, False, 0)

        lbl_name = Gtk.Label(label=meta['name'])
        lbl_name.set_ellipsize(3) # Pango.EllipsizeMode.END
        box.pack_start(lbl_name, False, False, 0)

        if not meta['is_folder']:
            lbl_details = Gtk.Label(label=f" - {meta['title']} ({meta['author']})")
            lbl_details.get_style_context().add_class("dim-label")
            box.pack_start(lbl_details, False, False, 0)

        box.show_all()
        row = Gtk.ListBoxRow()
        row.add(box)
        row.show()
        return row

    def _is_ancestor_collapsed(self, meta):
        """Checks if any parent folder in the hierarchy is collapsed."""
        rel_path = Path(meta['path']).relative_to(self.folder).parent
        while str(rel_path) != ".":
            if str(rel_path) not in self.expanded_folders:
                return True
            rel_path = rel_path.parent
        return False

    def _update_row_widget(self, row):
        """Refreshes the internal widget of a row when metadata changes."""
        meta = self.rows_data[row]
        old_child = row.get_child()
        if old_child:
            old_child.destroy()

        temp_row = self._create_row_widget(meta)
        new_box = temp_row.get_child()
        temp_row.remove(new_box)
        row.add(new_box)
        temp_row.destroy()

    def _load_books_generator(self, epubs):
        total = len(epubs)
        for i, epub_file in enumerate(epubs):
            try:
                rel_path = epub_file.relative_to(self.folder)
                # Ensure folders leading to this file are in the list
                self._get_or_create_folder_row(rel_path.parent)

                meta = self.book_service.get_metadata(epub_file)
                meta['name'] = epub_file.name
                meta['is_folder'] = False
                meta['depth'] = len(rel_path.parts) - 1

                row = self._create_row_widget(meta)
                self.rows_data[row] = meta
                self.list_box.add(row)
            except BookError as e:
                logger.error(f"Failed to load {epub_file.name}: {e}")

            self.progressbar.set_fraction((i + 1) / total) # Update progress bar
            if (i + 1) % 5 == 0 or (i + 1) == total: # Update status text less frequently
                self.event_bus.emit(AppEvent.STATUS_MESSAGE, f"Loading: {i+1}/{total}...")
            yield True
        self.progressbar.hide()
        self.event_bus.emit(AppEvent.STATUS_MESSAGE, f"Successfully loaded {total} books.")
        yield False

    def get_selected_file_info(self):
        """Returns metadata if exactly one book is selected; otherwise None."""
        selected = self.list_box.get_selected_rows()
        if len(selected) != 1:
            return None
        row = selected[0]
        meta = self.rows_data.get(row)
        if not meta or meta['is_folder']:
            return None
        return meta

    def update_selected_metadata(self, metadata: dict):
        selected = self.list_box.get_selected_rows()
        if selected:
            row = selected[0]
            self.rows_data[row].update(metadata)
            self._update_row_widget(row)

    def clear(self):
        self.list_box.foreach(lambda row: self.list_box.remove(row))
        self.rows_data = {}
        self.folder_rows = {}
        self.expanded_folders = set()
        self.last_selected_row = None

    def select_all(self, _=None):
        # Only select rows currently visible (matching the filter)
        self.list_box.foreach(lambda row: self.list_box.select_row(row) if row.get_visible() else None)

    def unselect_all(self, _=None):
        self.list_box.unselect_all()
