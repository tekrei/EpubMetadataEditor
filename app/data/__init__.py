from enum import StrEnum

NAMESPACES = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "n": "urn:oasis:names:tc:opendocument:xmlns:container",
}


class AppEvent(StrEnum):
    SELECTION_CHANGED = "selection-changed"
    FOCUS_DETAILS = "focus-details"
    REQUEST_APP_QUIT = "request-app-quit"
    REQUEST_LIST_CLEAR = "request-list-clear"
    REQUEST_FOLDER_OPEN = "request-folder-open"
    REQUEST_LIST_REFRESH = "request-list-refresh"
    REQUEST_LIST_SELECT_ALL = "request-list-select-all"
    REQUEST_LIST_DESELECT_ALL = "request-list-deselect-all"
    REQUEST_SHOW_SETTINGS = "request-show-settings"
    REQUEST_SHOW_ABOUT = "request-show-about"
    STATUS_MESSAGE = "status-message"
