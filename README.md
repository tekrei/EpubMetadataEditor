# A simple Epub Metadata Editor

A lightweight tool for viewing and editing EPUB metadata, built as a learning project for [GTK](https://www.gtk.org/) with Python.

## Features

- View and edit EPUB2/EPUB3 metadata (Title, Author, etc.).
- Fetch metadata from the web via ISBN (Google Books & Open Library providers).
- Side-by-side metadata comparison and selective merging.
- Cover image management: view, update, clear, or download from the internet.
- Hierarchical folder structure in book list with expand/collapse support.
- Fully responsive UI using background threading for network and I/O operations.
- Efficient manipulation using `zipfile` and `lxml` instead of full re-writes.
- Built with modern Python tooling (`uv`, `hatch`).
- Recursive directory scanning for EPUB files.
- Native GTK3 interface.

## Libraries

- **Package Manager:** uv
- **UI Framework:** PyGObject (GTK3)
- **XML Processing:** `lxml`
- **Archive Handling:** Built-in `zipfile`

## Installation & Setup

This project is primarily tested on GNU/Linux.

### 1. System Dependencies (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0 gobject-introspection libgirepository-2.0-dev appmenu-gtk3-module libcanberra-gtk3-module
```

### 2. Python Dependencies

Using `uv` to manage the virtual environment and dependencies:

```bash
uv sync
```

## Running the Application

- **Standard Run:** `uv run epub-editor`
- **Development Run:** `uv run python -m epub_metadata_editor.main`

## Possible improvements

- Add unit tests for metadata extraction and ISBN detection logic.
- Implement a persistent SQLite cache for faster library loading.
- Migrate to [GTK 4.0](https://docs.gtk.org/gtk4/).

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](https://github.com/tekrei/EpubMetadataEditor/blob/main/LICENSE) file for details.
