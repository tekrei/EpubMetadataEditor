import json
import logging
import tempfile
import threading
import urllib.request
from pathlib import Path

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import GdkPixbuf, GLib

from data import AppEvent
from services import BookError, FileService

from ._dialogs import Dialogs

logger = logging.getLogger(__name__)

class BookDetailsView:
    def __init__(self, builder, config_manager, book_service, event_bus):
        self.builder = builder
        self.config_manager = config_manager
        self.book_service = book_service
        self.event_bus = event_bus
        self.fields = {
            "title": builder.get_object("entTitle"),
            "author": builder.get_object("entAuthor"),
            "publisher": builder.get_object("entPublisher"),
            "date": builder.get_object("entDate"),
            "isbn": builder.get_object("entISBN")
        }
        self.img_cover = builder.get_object("imgCover")
        self.btn_open = builder.get_object("btnOpenEpub")
        self.btn_change = builder.get_object("btnChangeCover")
        self.btn_clear = builder.get_object("btnClearCover")
        self.btn_fetch = builder.get_object("btnFetchMetadata")
        self.spin_fetch = builder.get_object("spinFetch")
        self.current_path = None

        self.event_bus.subscribe(AppEvent.SELECTION_CHANGED, self.update)
        self.event_bus.subscribe(AppEvent.FOCUS_DETAILS, lambda _: self.fields["title"].grab_focus())

    def get_handlers(self):
        return {
            "onChangeCover": lambda _: self.on_change_cover(),
            "onClearCover": lambda _: self.on_change_cover(True),
            "onOpenEpub": lambda _: self.on_open_epub(),
            "onFetchMetadata": self.on_fetch_metadata,
        }

    def update(self, info):
        if not info:
            self.current_path = None
            for f in self.fields.values():
                f.set_text("")
                f.set_sensitive(False)
            for b in [self.btn_open, self.btn_change, self.btn_clear]:
                b.set_sensitive(False)
            self.btn_fetch.set_sensitive(False)
            self.img_cover.clear()
            return

        self.current_path = info["path"]
        self.fields["title"].set_text(info["title"] or "")
        self.fields["author"].set_text(info["author"] or "")
        self.fields["publisher"].set_text(info["publisher"] or "")
        self.fields["date"].set_text(info["date"] or "")
        self.fields["isbn"].set_text(info.get("isbn") or "")

        for f in self.fields.values():
            f.set_sensitive(True)
        for b in [self.btn_open, self.btn_change, self.btn_clear]:
            b.set_sensitive(True)
        self.btn_fetch.set_sensitive(True)
        self._load_cover()

    def _load_cover(self):
        self.img_cover.clear()
        if not self.current_path:
            return
        data = self.book_service.get_cover(self.current_path)
        if data:
            try:
                loader = GdkPixbuf.PixbufLoader()
                loader.write(data)
                loader.close()
                pb = loader.get_pixbuf()
                h = pb.get_height()
                w = pb.get_width()
                scale = 200 / h
                scaled = pb.scale_simple(
                    int(w * scale), 200, GdkPixbuf.InterpType.BILINEAR)
                self.img_cover.set_from_pixbuf(scaled)
            except GLib.Error as e:
                logger.error(f"Cover render error: {e}")

    def on_save(self):
        if not self.current_path:
            return None
        meta = {k: v.get_text() for k, v in self.fields.items()}
        try:
            self.book_service.update_metadata(self.current_path, meta)
            return meta
        except BookError as e:
            Dialogs.show_error_message(self.builder.get_object("mainWindow"), f"Update failed: {e}")
            return None

    def on_open_epub(self):
        if not self.current_path:
            return
        FileService.open_file(self.current_path)

    def on_change_cover(self, is_clear=False):
        if not self.current_path:
            return False
        img_path = None if is_clear else Dialogs.get_image_file()
        if not is_clear and not img_path:
            return False

        if self.book_service.update_cover(self.current_path, img_path):
            self._load_cover()
            return True
        return False

    def on_fetch_metadata(self, _=None):
        """Initiates fetching metadata from the web in a background thread."""
        isbn = self.fields["isbn"].get_text()
        if not isbn:
            Dialogs.show_error_message(self.builder.get_object("mainWindow"), "Please enter an ISBN first.")
            return

        provider = self.config_manager.get("metadata_provider", "google")

        self.btn_fetch.set_sensitive(False)
        self.spin_fetch.show()
        self.spin_fetch.start()

        def do_fetch():
            try:
                results = self.book_service.fetch_metadata_by_isbn(isbn, provider)
                GLib.idle_add(self._on_metadata_fetch_complete, results, None)
            except BookError as e:
                GLib.idle_add(self._on_metadata_fetch_complete, None, str(e))
            except (urllib.error.URLError, json.JSONDecodeError) as e:
                GLib.idle_add(self._on_metadata_fetch_complete, None, f"Unexpected error: {e}")

        threading.Thread(target=do_fetch, daemon=True).start()

    def _on_metadata_fetch_complete(self, results, error_msg):
        """Callback after metadata fetch thread completes."""
        self.spin_fetch.stop()
        self.spin_fetch.hide()
        self.btn_fetch.set_sensitive(True)

        if error_msg:
            Dialogs.show_error_message(self.builder.get_object("mainWindow"), f"Error fetching metadata: {error_msg}")
            return

        if not results:
            provider = self.config_manager.get("metadata_provider", "google")
            Dialogs.show_error_message(self.builder.get_object("mainWindow"), f"No metadata found via {provider.title()}.")
            return

        current_meta = {k: v.get_text() for k, v in self.fields.items()}
        current_cover_data = self.book_service.get_cover(self.current_path)

        applied_meta = Dialogs.show_metadata_diff(self.builder.get_object("mainWindow"), current_meta, results, current_cover_data)

        if applied_meta:
            for key, value in applied_meta.items():
                if key != "_apply_cover": # Special key for cover
                    self.fields[key].set_text(value)

            if applied_meta.get("_apply_cover"):
                cover_url = results.get("cover_url")
                if cover_url:
                    self._start_cover_download(cover_url)
                else:
                    self.event_bus.emit(AppEvent.STATUS_MESSAGE, "No remote cover URL available.")

    def _start_cover_download(self, url):
        """Initiates downloading and applying the cover in a background thread."""
        self.btn_change.set_sensitive(False)
        self.btn_clear.set_sensitive(False)
        self.btn_fetch.set_sensitive(False)
        self.spin_fetch.show()
        self.spin_fetch.start()

        def do_download():
            try:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    temp_path = Path(tmp.name)

                urllib.request.urlretrieve(url, temp_path)
                self.book_service.update_cover(self.current_path, str(temp_path))
                if temp_path.exists():
                    temp_path.unlink()
                GLib.idle_add(self._on_cover_download_complete, None)
            except (urllib.error.URLError, OSError) as e:
                GLib.idle_add(self._on_cover_download_complete, str(e))
        threading.Thread(target=do_download, daemon=True).start()

    def _on_cover_download_complete(self, error_msg):
        """Callback after cover download thread completes."""
        self.spin_fetch.stop()
        self.spin_fetch.hide()
        self.btn_change.set_sensitive(True)
        self.btn_clear.set_sensitive(True)
        self.btn_fetch.set_sensitive(True)

        if error_msg:
            logger.error(f"Failed to download remote cover: {error_msg}")
            Dialogs.show_error_message(self.builder.get_object("mainWindow"), f"Failed to download cover image: {error_msg}")
        else:
            self._load_cover()
            self.event_bus.emit(AppEvent.STATUS_MESSAGE, "Cover updated from web.")
