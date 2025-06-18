# A simple Epub Metadata Editor

Just a simple Epub Metadata editor for learning [GTK](https://www.gtk.org/) in Python.

## Libraries

- This project is using [uv](https://docs.astral.sh/uv/getting-started/) and dependencies are defined in [pyproject.toml](./pyproject.toml) file.
- It is developed using Python and [PyGobject](https://pygobject.readthedocs.io/en/latest/index.html).
- Using [ebooklib](https://github.com/aerkalov/ebooklib) for handle EPUB2/EPUB3 format.

## Running

It is tested only in GNU/Linux operating system.

- Install dependencies:
  1. [install the following packages using package manager](https://pygobject.readthedocs.io/en/latest/getting_started.html#ubuntu-getting-started): `sudo apt get install libcairo2-dev libgirepository-2.0-dev pkg-config gcc python3-dev gir1.2-gtk-3.0`
  2. install remaining dependencies: `uv lock && uv sync`
  3. You can also directly run using: `uv run python main.py`

## Possible improvements

- If it is possible: just updating the metadata of the file instead of reading the epub file, changing the metadata and writing the file again
- Updating all metadata of selected book using a form instead of updating each metadata value separately
- Recursively finding and listing all epub files of the selected folder

## LICENSE

This program is free software: you can redistribute them and/or modify them under the terms of the [GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.en.html) as published by the [Free Software Foundation](https://www.fsf.org), either version 3 of the License, or any later version.

It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU General Public License](./LICENSE) for more details.

## Package management

We are using [uv](https://docs.astral.sh/uv/getting-started/) Python package and dependency
manager.

- Init interactively `uv init`
- Add package `uv add package-name`
- Remove package `uv remove package-name`
- Create lockfile `uv lock`
- Update dependencies `uv sync`
- Show available packages `uv show`
- Run a command in the virtualenv `uv run command`
