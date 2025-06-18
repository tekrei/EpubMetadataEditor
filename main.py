#!/usr/bin/env python3

import os
import utilities
import dialogs
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk # noqa

running_path = os.path.dirname(os.path.realpath(__file__))


class MainWindowGTK:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(running_path+"/main.glade")

        handlers = {
            "onDestroyWindow": self.quit_window,
            "onQuit": self.quit_window,
            "onClearList": self.clear,
            "onOpenFolder": self.load_table,
            "onAbout": dialogs.show_about,
            "onLstBooksRowActivated": self.row_activated,
            "onLstBooksChanged": self.selection_changed
        }

        self.builder.connect_signals(handlers)
        self.window = self.builder.get_object("mainWindow")

        self.prepare_table()

        self.window.show_all()
        Gtk.main()

    def prepare_table(self):
        self.columns = ["file name", "title", "creator",
                        "publisher", "date", "language", "description"]
        self.book_table = self.builder.get_object("lstBooks")

        for i, c in enumerate(self.columns):
            cell = Gtk.CellRendererText()
            cell.set_property("editable", i > 0)
            cell.connect("edited", self.text_edited, i)
            column = Gtk.TreeViewColumn(c, cell, text=i)
            column.set_resizable(True)
            column.set_sort_column_id(i)
            self.book_table.append_column(column)
        self.book_store = Gtk.ListStore(*[str]*len(self.columns))
        self.book_table.set_model(self.book_store)

    def update_book_metadata(self, file_name, key, value):
        utilities.update_book_metadata(
            self.folder+"/"+file_name, key, value)

    def text_edited(self, renderer, row, new_text, column):
        if new_text:
            iter = self.book_store.get_iter_from_string(row)
            if iter:
                self.book_store.set(iter, column, new_text)
                utilities.update_book_metadata(
                    self.folder+"/"+self.book_store[row][0],
                    self.columns[column],
                    new_text
                )

    def selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            print("selection changed", model[treeiter])

    def row_activated(self, widget, row, column):
        print("row activated", widget, row, column)

    def quit_window(self, widget):
        Gtk.main_quit()

    def clear(self, widget):
        self.book_store.clear()

    def load_table(self, widget):
        self.folder = dialogs.get_folder()
        if not self.folder:
            return
        self.clear(None)

        for epub_file in utilities.get_epub_files(self.folder):
            try:
                values = utilities.get_metadata(
                    epub_file, self.columns[1:])
                values.insert(0, utilities.get_filename(epub_file))
                self.book_store.append(values)
            except BaseException as e:
                print(e)
                dialogs.show_error_message(
                    "No metadata is found for %s (%s)" % (epub_file, e))


if __name__ == "__main__":
    hwg = MainWindowGTK()
