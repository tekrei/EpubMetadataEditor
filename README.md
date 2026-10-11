# A simple Epub Metadata Editor

A lightweight tool for viewing and editing EPUB metadata, built with Python and PySide6.

## Features

- View and edit EPUB2/EPUB3 metadata (Title, Author, etc.).
- Fetch metadata from the web via ISBN (Google Books & Open Library providers).
- Side-by-side metadata comparison and selective merging.
- Cover image management: view, update, clear, or download from the internet.
- Batch renaming of files based on metadata using customizable templates.
- Hierarchical folder structure with search filtering and range selection (Shift+Click).
- Integrated file actions: Move to Trash and Open containing folder.
- Fully responsive UI using background threading for network and I/O operations.
- Efficient manipulation using `zipfile` and `lxml` instead of full re-writes.
- Built with modern Python tooling (`uv`, `hatch`).
- Recursive directory scanning for EPUB files.
- Native Qt interface with PySide6.

## Libraries

- **Package Manager:** uv
- **UI Framework:** PySide6 (Qt)
- **XML Processing:** `lxml`
- **Archive Handling:** Built-in `zipfile`

## Installation & Setup

This project is primarily tested on GNU/Linux and uses PySide6 for its desktop UI.

### Linux system dependencies (Ubuntu/Debian, X11)

PySide6 includes Qt, but the X11 platform plugin also needs system libraries:

```bash
sudo apt install libgl1 libegl1 libxkbcommon0 libxkbcommon-x11-0 \
	libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-xkb1
```

Running the desktop UI also requires an active X11 or Wayland display. Headless
containers need display forwarding or a virtual desktop; installing these
libraries alone does not provide a display server.

### Install Dependencies

Using `uv` to manage the virtual environment and dependencies:

```bash
uv sync
uv run pre-commit install
```

## Running the Application

- **Standard Run:** `uv run epub-editor`
- **Development Run:** `uv run python -m epub_metadata_editor.main`

## Development

This project uses `ruff` for linting and formatting via `pre-commit`.

- **Install hooks:** `uv run pre-commit install`
- **Run manually:** `uv run pre-commit run --all-files`

## Possible improvements

- Add unit tests for metadata extraction and ISBN detection logic.
- Implement a persistent SQLite cache for faster library loading.
- Package standalone builds for Linux, Windows, and macOS.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](https://github.com/tekrei/EpubMetadataEditor/blob/main/LICENSE) file for details.
