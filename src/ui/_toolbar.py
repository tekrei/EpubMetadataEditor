import gi

gi.require_version("Gtk", "3.0")
from data import AppEvent


class ToolbarView:
    def __init__(self, builder, event_bus):
        self.builder = builder
        self.event_bus = event_bus
        self.toolbar = builder.get_object("toolbar")

    def get_handlers(self):
        """Returns a mapping of Glade signal names to action callbacks."""
        return {
            "onQuit": lambda _: self.event_bus.emit(AppEvent.REQUEST_APP_QUIT),
            "onClearList": lambda _: self.event_bus.emit(AppEvent.REQUEST_LIST_CLEAR),
            "onOpenFolder": lambda _: self.event_bus.emit(AppEvent.REQUEST_FOLDER_OPEN),
            "onRefresh": lambda _: self.event_bus.emit(AppEvent.REQUEST_LIST_REFRESH),
            "onAbout": lambda _: self.event_bus.emit(AppEvent.REQUEST_SHOW_ABOUT),
            "onSelectAll": lambda _: self.event_bus.emit(
                AppEvent.REQUEST_LIST_SELECT_ALL
            ),
            "onSettings": lambda _: self.event_bus.emit(AppEvent.REQUEST_SHOW_SETTINGS),
            "onDeselectAll": lambda _: self.event_bus.emit(
                AppEvent.REQUEST_LIST_DESELECT_ALL
            ),
        }
