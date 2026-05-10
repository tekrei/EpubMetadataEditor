import urllib.request

from gi.repository import GdkPixbuf, GLib, Gtk


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent, current_template, current_provider):
        super().__init__(title="Settings", transient_for=parent, modal=True)
        self.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_OK", Gtk.ResponseType.OK)

        content = self.get_content_area()
        content.set_spacing(10)
        content.set_border_width(12)

        content.add(Gtk.Label(label="Naming Template (e.g. {year} - {title})", xalign=0))
        self.entry = Gtk.Entry()
        self.entry.set_text(current_template)
        self.entry.set_activates_default(True)
        content.add(self.entry)

        content.add(Gtk.Label(label="Metadata Provider", xalign=0))
        self.provider_combo = Gtk.ComboBoxText()
        self.provider_combo.append("google", "Google Books")
        self.provider_combo.append("openlibrary", "Open Library")
        self.provider_combo.set_active_id(current_provider)
        content.add(self.provider_combo)

        self.set_default_response(Gtk.ResponseType.OK)
        content.show_all()

    def get_value(self):
        return self.entry.get_text()

    def get_provider(self):
        return self.provider_combo.get_active_id()


class MetadataDiffDialog(Gtk.Dialog):
    def __init__(self, parent, current_meta, fetched_meta, current_cover_data, remote_cover_data):
        super().__init__(title="Compare Metadata", transient_for=parent, modal=True)
        self.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Apply", Gtk.ResponseType.OK)
        self.set_default_size(600, -1)

        content = self.get_content_area()
        content.set_spacing(10)
        content.set_border_width(12)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        select_all_btn = Gtk.Button(label="Select All")
        deselect_all_btn = Gtk.Button(label="Deselect All")
        select_all_btn.connect("clicked", self._on_select_all)
        deselect_all_btn.connect("clicked", self._on_deselect_all)
        btn_box.pack_start(select_all_btn, False, False, 0)
        btn_box.pack_start(deselect_all_btn, False, False, 0)
        content.pack_start(btn_box, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(15)
        grid.set_row_spacing(10)

        self.fetched_meta = fetched_meta
        self.checks = {}

        # Headers
        grid.attach(Gtk.Label(label="<b>Apply?</b>", use_markup=True), 0, 0, 1, 1)
        grid.attach(Gtk.Label(label="<b>Field</b>", use_markup=True, xalign=1), 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="<b>Current</b>", use_markup=True, xalign=0), 2, 0, 1, 1)
        grid.attach(Gtk.Label(label="<b>Fetched</b>", use_markup=True, xalign=0), 3, 0, 1, 1)

        fields = [
            ("title", "Title"),
            ("author", "Author"),
            ("publisher", "Publisher"),
            ("date", "Date"),
            ("isbn", "ISBN")
        ]

        for i, (key, label) in enumerate(fields, 1):
            fetch_val = fetched_meta.get(key, "") or "-"
            curr_val = current_meta.get(key, "") or "-"

            # Checkbox: auto-select if fetched value is new/different
            check = Gtk.CheckButton()
            is_diff = fetch_val != "-" and fetch_val != curr_val
            check.set_active(is_diff)
            self.checks[key] = check
            grid.attach(check, 0, i, 1, 1)

            grid.attach(Gtk.Label(label=f"{label}:", xalign=1), 1, i, 1, 1)

            grid.attach(Gtk.Label(label=curr_val, xalign=0, ellipsize=3, max_width_chars=35), 2, i, 1, 1)

            fetch_lbl = Gtk.Label(xalign=0, ellipsize=3, max_width_chars=35)
            if is_diff:
                escaped_val = GLib.markup_escape_text(fetch_val)
                fetch_lbl.set_markup(f"<span foreground='blue'><b>{escaped_val}</b></span>")
            else:
                fetch_lbl.set_text(fetch_val)
            grid.attach(fetch_lbl, 3, i, 1, 1)

        # Add Cover Preview Row
        row_idx = len(fields) + 1

        # Checkbox for cover
        cover_check = Gtk.CheckButton()
        # Auto-select if remote cover exists and is different or no current cover
        is_cover_diff = remote_cover_data and (not current_cover_data or remote_cover_data != current_cover_data)
        cover_check.set_active(is_cover_diff)
        self.checks["_apply_cover"] = cover_check # Special key for cover
        grid.attach(cover_check, 0, row_idx, 1, 1)

        grid.attach(Gtk.Label(label="Cover Preview:", xalign=1), 1, row_idx, 1, 1)
        grid.attach(self._get_image_widget(current_cover_data), 2, row_idx, 1, 1)
        grid.attach(self.get_remote_cover_widget(remote_cover_data), 3, row_idx, 1, 1)

        content.pack_start(grid, True, True, 0)
        content.show_all()

    def get_remote_cover_widget(self, remote_cover_data):
        return self._get_image_widget(remote_cover_data)

    def _on_select_all(self, widget):
        for check in self.checks.values():
            check.set_active(True)

    def _on_deselect_all(self, widget):
        for check in self.checks.values():
            check.set_active(False)

    def get_selected_metadata(self):
        """Returns only the fetched metadata values that were checked."""
        return {key: self.fetched_meta[key] for key, check in self.checks.items() if check.get_active()}

    def _get_image_widget(self, data):
        img = Gtk.Image()
        if not data:
            img.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
            return img
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(data)
            loader.close()
            pb = loader.get_pixbuf()
            h = pb.get_height()
            w = pb.get_width()
            scale = 120 / h
            scaled = pb.scale_simple(int(w * scale), 120, GdkPixbuf.InterpType.BILINEAR)
            img.set_from_pixbuf(scaled)
        except GLib.Error:
            img.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        return img



class RenamePreviewDialog(Gtk.Dialog):
    def __init__(self, parent, renames):
        super().__init__(title="Confirm Batch Rename", transient_for=parent, modal=True)
        self.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_OK", Gtk.ResponseType.OK)
        self.set_default_size(700, 450)

        content = self.get_content_area()
        content.set_border_width(12)
        content.set_spacing(10)

        content.add(Gtk.Label(label=f"Review the following {len(renames)} changes:", xalign=0))

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        ls = Gtk.ListStore(str, str)
        for old, new in renames:
            ls.append([old, new])

        tv = Gtk.TreeView(model=ls)
        for i, title in enumerate(["Current Name", "New Name"]):
            res = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(title, res, text=i)
            col.set_resizable(True)
            tv.append_column(col)

        scrolled.add(tv)
        content.add(scrolled)
        content.show_all()


class Dialogs:
    """Factory-like utility to run refactored Dialog classes."""

    @staticmethod
    def get_folder(parent=None):
        dialog = Gtk.FileChooserDialog(
            title="Please choose Epub folder",
            transient_for=parent,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_buttons("_Open", Gtk.ResponseType.OK)

        response = dialog.run()
        folder = dialog.get_filename() if response == Gtk.ResponseType.OK else None
        dialog.destroy()
        return folder

    @staticmethod
    def get_image_file(parent=None):
        dialog = Gtk.FileChooserDialog(
            title="Select Cover Image",
            transient_for=parent,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_buttons("_Open", Gtk.ResponseType.OK)

        filter_img = Gtk.FileFilter()
        filter_img.set_name("Images")
        for mt in ["image/jpeg", "image/png"]:
            filter_img.add_mime_type(mt)
        dialog.add_filter(filter_img)

        response = dialog.run()
        filename = dialog.get_filename() if response == Gtk.ResponseType.OK else None
        dialog.destroy()
        return filename

    @staticmethod
    def show_error_message(parent, message):
        dialog = Gtk.MessageDialog(
            transient_for=parent,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message)
        dialog.run()
        dialog.destroy()

    @staticmethod
    def ask_confirmation(parent, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=parent,
            title=title,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=message)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    @staticmethod
    def show_settings(parent, current_template, current_provider):
        dialog = SettingsDialog(parent, current_template, current_provider)
        result = None
        while True:
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                template = dialog.get_value()
                provider = dialog.get_provider()
                try:
                    template.format(year="2024", title="Title", author="Author", publisher="Pub", date="Date")
                    result = (template, provider)
                    break
                except ValueError:
                    Dialogs.show_error_message(dialog, "Invalid Template format.")
            else:
                break
        dialog.destroy()
        return result

    @staticmethod
    def show_rename_preview(parent, renames):
        dialog = RenamePreviewDialog(parent, renames)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    @staticmethod
    def show_metadata_diff(parent, current_meta, fetched_meta, current_cover_data):
        # Fetch remote cover bytes synchronously for the preview
        remote_cover_data = None
        url = fetched_meta.get("cover_url")
        if url:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    remote_cover_data = resp.read()
            except urllib.error.URLError:
                pass

        dialog = MetadataDiffDialog(parent, current_meta, fetched_meta, current_cover_data, remote_cover_data)
        response = dialog.run()
        result = dialog.get_selected_metadata() if response == Gtk.ResponseType.OK else None
        dialog.destroy()
        return result

    @staticmethod
    def get_text_input(parent, title, label_text, default_text=""):
        dialog = Gtk.MessageDialog(
            transient_for=parent,
            title=title,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=label_text)

        entry = Gtk.Entry()
        entry.set_text(default_text)
        entry.show()
        dialog.get_content_area().pack_end(entry, True, True, 0)

        response = dialog.run()
        text = entry.get_text() if response == Gtk.ResponseType.OK else None
        dialog.destroy()
        return text

    @staticmethod
    def show_about(_):
        # AboutDialog is already a subclass, we just instantiate it
        dialog = Gtk.AboutDialog()
        dialog.set_program_name("EpubMetadata Editor")
        dialog.set_copyright("Apache License Version 2.0")
        dialog.set_authors(["T. E. Kalayci"])
        dialog.set_website("https://github.com/tekrei/EpubMetadataEditor")
        dialog.set_website_label("PythonExamples")
        dialog.set_logo_icon_name("accessories-dictionary")
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show()
