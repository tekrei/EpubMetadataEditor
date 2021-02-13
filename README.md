# A simple Epub Metadata Editor

Just a simple Epub Metadata editor for learning [GTK](https://www.gtk.org/) in Python.

## Libraries

- This project is using [poetry](https://python-poetry.org/) and dependencies are defined in [pyproject.toml](./pyproject.toml) file.
- It is developed using Python v3 and [PyGobject](https://pygobject.readthedocs.io/en/latest/index.html).
- Using [ebooklib](https://github.com/aerkalov/ebooklib) for handle EPUB2/EPUB3 format.

## Running

It is tested only in GNU/Linux operating system.

- Install dependencies:
  1. [install the following packages using package manager](https://pygobject.readthedocs.io/en/latest/getting_started.html#ubuntu-getting-started): `sudo apt get install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0`
  2. install remaining dependencies: `poetry update`
- Open the Python environment: `poetry shell`
- Run the main program: `python main.py`
- You can also directly run using: `poetry run python main.py`

## Possible improvements

- If it is possible: just updating the metadata of the file instead of reading the epub file, changing the metadata and writing the file again
- Updating all metadata of selected book using a form instead of updating each metadata value separately
- Recursively finding and listing all epub files of the selected folder

## LICENSE

This program is free software: you can redistribute them and/or modify them under the terms of the [GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.en.html) as published by the [Free Software Foundation](https://www.fsf.org), either version 3 of the License, or any later version.

It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU General Public License](./LICENSE) for more details.

## Package management

This project uses [poetry](https://python-poetry.org/) Python package and dependency manager.

- Init interactively `poetry init`
- Add package `poetry add package-name`
- Remove package `poetry remove package-name`
- Install dependencies `poetry install`
- Update dependencies `poetry update`
- Show available packages `poetry show`
- Run a command in the virtualenv `poetry run command`
- Open virtualenv `poetry shell`
