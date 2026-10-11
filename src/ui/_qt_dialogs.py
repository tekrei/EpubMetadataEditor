import urllib.error
import urllib.request

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class Dialogs:
    @staticmethod
    def get_folder(parent=None):
        folder = QFileDialog.getExistingDirectory(parent, "Choose EPUB folder")
        return folder or None

    @staticmethod
    def get_image_file(parent=None):
        filename, _ = QFileDialog.getOpenFileName(
            parent,
            "Select Cover Image",
            "",
            "Images (*.jpg *.jpeg *.png)",
        )
        return filename or None

    @staticmethod
    def show_error_message(parent, message):
        QMessageBox.critical(parent, "Error", message)

    @staticmethod
    def ask_confirmation(parent, title, message):
        return (
            QMessageBox.question(
                parent,
                title,
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

    @staticmethod
    def show_settings(parent, current_template, current_provider):
        dialog = QDialog(parent)
        dialog.setWindowTitle("Settings")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        template = QLineEdit(current_template)
        provider = QComboBox()
        provider.addItem("Google Books", "google")
        provider.addItem("Open Library", "openlibrary")
        provider.setCurrentIndex(max(0, provider.findData(current_provider)))
        form.addRow("Naming template", template)
        form.addRow("Metadata provider", provider)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        value = template.text()
        try:
            value.format(
                year="2024",
                title="Title",
                author="Author",
                publisher="Publisher",
                date="Date",
            )
        except (KeyError, ValueError) as error:
            Dialogs.show_error_message(parent, f"Invalid naming template: {error}")
            return Dialogs.show_settings(parent, value, provider.currentData())
        return value, provider.currentData()

    @staticmethod
    def show_rename_preview(parent, renames):
        dialog = QDialog(parent)
        dialog.setWindowTitle("Confirm Batch Rename")
        dialog.resize(700, 450)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Review the following {len(renames)} changes:"))

        table = QTableWidget(len(renames), 2)
        table.setHorizontalHeaderLabels(["Current Name", "New Name"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        for row, (old_name, new_name) in enumerate(renames):
            table.setItem(row, 0, QTableWidgetItem(old_name))
            table.setItem(row, 1, QTableWidgetItem(new_name))
        layout.addWidget(table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        return dialog.exec() == QDialog.DialogCode.Accepted

    @staticmethod
    def show_metadata_diff(parent, current_meta, fetched_meta, current_cover_data):
        remote_cover_data = None
        cover_url = fetched_meta.get("cover_url")
        if cover_url:
            try:
                with urllib.request.urlopen(cover_url, timeout=5) as response:
                    remote_cover_data = response.read()
            except (urllib.error.URLError, TimeoutError, OSError):
                pass

        dialog = QDialog(parent)
        dialog.setWindowTitle("Compare Metadata")
        dialog.resize(760, 460)
        layout = QVBoxLayout(dialog)

        buttons_row = QHBoxLayout()
        select_all = QPushButton("Select All")
        deselect_all = QPushButton("Deselect All")
        buttons_row.addWidget(select_all)
        buttons_row.addWidget(deselect_all)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        content = QWidget()
        grid = QGridLayout(content)
        grid.addWidget(QLabel("Apply?"), 0, 0)
        grid.addWidget(QLabel("Field"), 0, 1)
        grid.addWidget(QLabel("Current"), 0, 2)
        grid.addWidget(QLabel("Fetched"), 0, 3)

        checks = {}
        fields = [
            ("title", "Title"),
            ("author", "Author"),
            ("publisher", "Publisher"),
            ("date", "Date"),
            ("isbn", "ISBN"),
        ]
        for row, (key, label) in enumerate(fields, 1):
            fetched = fetched_meta.get(key, "") or "-"
            current = current_meta.get(key, "") or "-"
            check = QCheckBox()
            check.setChecked(fetched != "-" and fetched != current)
            checks[key] = check
            grid.addWidget(check, row, 0, Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(QLabel(f"{label}:"), row, 1)
            grid.addWidget(QLabel(current), row, 2)
            fetched_label = QLabel(fetched)
            if check.isChecked():
                fetched_label.setStyleSheet("font-weight: 600; color: #1769aa")
            fetched_label.setWordWrap(True)
            grid.addWidget(fetched_label, row, 3)

        cover_row = len(fields) + 1
        cover_check = QCheckBox()
        has_cover_diff = bool(
            remote_cover_data
            and (not current_cover_data or remote_cover_data != current_cover_data)
        )
        cover_check.setChecked(has_cover_diff)
        checks["_apply_cover"] = cover_check
        grid.addWidget(cover_check, cover_row, 0, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(QLabel("Cover Preview:"), cover_row, 1)
        grid.addWidget(_cover_preview(current_cover_data), cover_row, 2)
        grid.addWidget(_cover_preview(remote_cover_data), cover_row, 3)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        select_all.clicked.connect(
            lambda: [check.setChecked(True) for check in checks.values()]
        )
        deselect_all.clicked.connect(
            lambda: [check.setChecked(False) for check in checks.values()]
        )
        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        dialog_buttons.accepted.connect(dialog.accept)
        dialog_buttons.rejected.connect(dialog.reject)
        layout.addWidget(dialog_buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return {
            key: fetched_meta[key]
            for key, check in checks.items()
            if check.isChecked() and key in fetched_meta
        } | ({"_apply_cover": True} if checks["_apply_cover"].isChecked() else {})

    @staticmethod
    def get_text_input(parent, title, label_text, default_text=""):
        text, accepted = QInputDialog.getText(
            parent, title, label_text, QLineEdit.EchoMode.Normal, default_text
        )
        return text if accepted else None

    @staticmethod
    def show_about(parent):
        QMessageBox.about(
            parent,
            "About EpubMetadata Editor",
            "<b>EpubMetadata Editor</b><br>Apache License Version 2.0<br>"
            '<a href="https://github.com/tekrei/EpubMetadataEditor">'
            "Project website</a>",
        )


def _cover_preview(data):
    label = QLabel()
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setMinimumSize(120, 140)
    if data:
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            label.setPixmap(
                pixmap.scaled(
                    120,
                    140,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            return label
    label.setText("No cover")
    return label
