---
title: Basit EPub Editörü
emoji: 📖
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "6.27.0"
python_version: "3.13"
app_file: main.py
pinned: false
---
# EPUB Metadata Editor

[![Basit EPub Editörü](https://huggingface.co/datasets/huggingface/badges/resolve/main/open-in-hf-spaces-sm.svg)](https://huggingface.co/spaces/tekrei/epubeditor)

A lightweight web-based tool for viewing and editing EPUB metadata, originally built as a GTK application and converted to a **Gradio** web interface. Managed using **`uv`**.

---

## 🚀 Features

- **View & Edit EPUB Metadata:** Title, Author, Publisher, Language, and Cover Image.
- **Modern Web Interface:** Built with Gradio (`gr.Blocks`), runs directly in your browser.
- **Fast Package Management:** Uses `uv` for lightning-fast dependency management and environment execution.
- **Efficient Archive Handling:** Lightweight EPUB XML/zip metadata updating via `lxml` and `zipfile`.

---

## 🛠️ Prerequisites & Installation

Ensure you have **`uv`** installed on your system. If not, install it via:

```bash
# On macOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell):
powershell -c "irm https://astral.sh/uv/install.sh | iex"
```

### 1. Project Setup & Dependencies

Add Gradio and sync environment dependencies using `uv`:

```bash
# Add Gradio dependency
uv add gradio

# Synchronize virtual environment dependencies
uv sync
```

---

## 🏃 Running the Application

You can launch the application directly through `uv` without manually activating the virtual environment:

```bash
uv run python src/main.py
```

Once executed, open your web browser and navigate to:
```text
http://127.0.0.1:7860
```

---

## 📂 Project Structure

```text
EpubMetadataEditor/
├── pyproject.toml         # Project definition and dependencies (uv)
├── uv.lock                # Dependency lockfile
├── README.md              # Project documentation
└── src/
    ├── main.py            # Main entry point (Gradio App)
    ├── services/          # Backend EPUB processing services
    │   ├── _book_service.py
    │   ├── _file_service.py
    │   └── ...
    └── ui/                # (Legacy GTK components)
```

---

## 🧰 Development & Code Quality

If you wish to run linting and formatting via pre-commit:

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run manual check
uv run pre-commit run --all-files
```

---

## 📄 License

This project is licensed under the Apache License 2.0.
