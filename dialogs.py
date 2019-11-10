import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk # noqa


def get_folder():
    dialog = Gtk.FileChooserDialog(title="Please choose Epub folder",
                                   action=Gtk.FileChooserAction.SELECT_FOLDER
                                   )
    dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
    dialog.add_buttons(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
    response = dialog.run()
    folder = None
    if response == Gtk.ResponseType.OK:
        folder = dialog.get_filename()

    dialog.destroy()
    return folder


def show_error_message(message):
    dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=message)
    dialog.run()
    dialog.destroy()


def show_about(widget):
    dialog = Gtk.AboutDialog()
    dialog.set_program_name("EpubMetadata Editor")
    dialog.set_copyright("GNU General Public License version 3")
    dialog.set_authors(["T. E. Kalayci"])
    dialog.set_website("https://github.com/tekrei/EpubMetadataEditor")
    dialog.set_website_label("PythonExamples")
    dialog.set_logo_icon_name("accessories-dictionary")
    dialog.connect("response", close_dialog)
    dialog.show()


def close_dialog(action, parameter):
    action.destroy()
