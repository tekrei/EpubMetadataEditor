from enum import IntEnum, Enum

# Common EPUB Namespaces
NAMESPACES = {
    'n': 'urn:oasis:names:tc:opendocument:xmlns:container',
    'opf': 'http://www.idpf.org/2007/opf',
    'dc': 'http://purl.org/dc/elements/1.1/'
}

class BookColumn(IntEnum):
    """TreeStore Column Indices"""
    ICON = 0
    NAME = 1
    TITLE = 2
    AUTHOR = 3
    PUBLISHER = 4
    DATE = 5
    PATH = 6
    IS_FOLDER = 7

class AppEvent(str, Enum):
    SELECTION_CHANGED = "selection-changed"
    FOCUS_DETAILS = "focus-details"
    METADATA_INLINE_EDITED = "metadata-inline-edited"
    REQUEST_APP_QUIT = "request-app-quit"
    REQUEST_LIST_CLEAR = "request-list-clear"
    REQUEST_FOLDER_OPEN = "request-folder-open"
    REQUEST_LIST_REFRESH = "request-list-refresh"
    REQUEST_LIST_SELECT_ALL = "request-list-select-all"
    REQUEST_LIST_DESELECT_ALL = "request-list-deselect-all"
    REQUEST_SHOW_SETTINGS = "request-show-settings"
    REQUEST_SHOW_ABOUT = "request-show-about"
    STATUS_MESSAGE = "status-message"