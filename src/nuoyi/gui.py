"""
NuoYi - PySide6 GUI for batch PDF/DOCX to Markdown conversion.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QThread, Signal

# --- PySide6 (GUI) ---
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .converter import (
    DocxConverter,
    MarkerPDFConverter,
)
from .utils import DEFAULT_LANGS, SUPPORTED_LANGUAGES, save_images_and_update_markdown


class MarkerWorker(QThread):
    """Background worker for batch file processing."""

    progress_signal = Signal(int, int)   # row, progress percentage
    status_signal = Signal(int, str)     # row, status message
    log_signal = Signal(str)             # log message
    finished_signal = Signal()

    def __init__(self, files: List[Tuple[int, str]], output_dir: str,
                 force_ocr: bool = False, page_range: str = None,
                 langs: str = DEFAULT_LANGS, device: str = "auto", parent=None):
        super().__init__(parent)
        self.files = files
        self.output_dir = output_dir
        self.force_ocr = force_ocr
        self.page_range = page_range
        self.langs = langs
        self.device = device
        self.is_running = True

    def run(self):
        self.log_signal.emit(
            f"Starting processing of {len(self.files)} files..."
        )

        pdf_converter = None
        docx_converter = None

        try:
            if any(fp.lower().endswith(".pdf") for _, fp in self.files):
                self.log_signal.emit(f"Loading marker-pdf models (device={self.device})...")
                self.status_signal.emit(self.files[0][0], "Loading models...")
                pdf_converter = MarkerPDFConverter(
                    force_ocr=self.force_ocr,
                    page_range=self.page_range,
                    langs=self.langs,
                    device=self.device,
                )
                self.log_signal.emit(f"Models loaded on {pdf_converter.device.upper()}.")
        except Exception as e:
            self.log_signal.emit(
                f"Failed to load marker-pdf: {e}. PDF files will be skipped."
            )

        if any(fp.lower().endswith(".docx") for _, fp in self.files):
            docx_converter = DocxConverter()

        for index, filepath in self.files:
            if not self.is_running:
                break

            filename = os.path.basename(filepath)
            suffix = Path(filepath).suffix.lower()
            self.status_signal.emit(index, "Converting...")
            self.progress_signal.emit(index, 10)
            self.log_signal.emit(f"Processing: {filename}")

            try:
                images = {}
                if suffix == ".pdf" and pdf_converter:
                    content, images = pdf_converter.convert_file(filepath)
                elif suffix == ".docx" and docx_converter:
                    content = docx_converter.convert_file(filepath)
                else:
                    self.status_signal.emit(index, "Skipped")
                    self.log_signal.emit(
                        f"[{filename}] Unsupported format or converter unavailable."
                    )
                    continue

                base_name = Path(filepath).stem
                out_path = os.path.join(self.output_dir, f"{base_name}.md")

                if images:
                    images_subdir = f"{base_name}_images"
                    content = save_images_and_update_markdown(
                        content, images, Path(self.output_dir), images_subdir
                    )
                    self.log_signal.emit(f"[{filename}] Saved {len(images)} images")

                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)

                self.status_signal.emit(index, "Completed")
                self.progress_signal.emit(index, 100)
                self.log_signal.emit(
                    f"[{filename}] Done -> {os.path.basename(out_path)}"
                )

            except Exception as e:
                self.status_signal.emit(index, "Error")
                self.log_signal.emit(f"[{filename}] Error: {e}")

        self.finished_signal.emit()

    def stop(self):
        self.is_running = False


class MainWindow(QMainWindow):
    """PySide6 GUI for batch PDF/DOCX to Markdown conversion."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NuoYi - PDF/DOCX to Markdown Converter")
        self.resize(900, 700)

        self.setup_ui()

        self.files_to_process: List[Tuple[int, str]] = []
        self.worker: Optional[MarkerWorker] = None

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # --- Input directory ---
        in_layout = QHBoxLayout()
        in_label = QLabel("Input Directory:")
        self.in_dir_input = QLineEdit()
        self.in_dir_input.setReadOnly(True)
        self.in_dir_input.setPlaceholderText(
            "Select a directory containing PDF/DOCX files"
        )
        self.browse_in_btn = QPushButton("Browse")
        self.browse_in_btn.clicked.connect(self.browse_input_directory)
        in_layout.addWidget(in_label)
        in_layout.addWidget(self.in_dir_input)
        in_layout.addWidget(self.browse_in_btn)
        layout.addLayout(in_layout)

        # --- Output directory ---
        out_layout = QHBoxLayout()
        out_label = QLabel("Output Directory:")
        self.out_dir_input = QLineEdit()
        self.out_dir_input.setReadOnly(True)
        self.out_dir_input.setPlaceholderText(
            "Same as input (default)"
        )
        self.browse_out_btn = QPushButton("Browse")
        self.browse_out_btn.clicked.connect(self.browse_output_directory)
        out_layout.addWidget(out_label)
        out_layout.addWidget(self.out_dir_input)
        out_layout.addWidget(self.browse_out_btn)
        layout.addLayout(out_layout)

        # --- Options row 1 ---
        opts_layout = QHBoxLayout()

        self.force_ocr_cb = QCheckBox("Force OCR")
        self.force_ocr_cb.setToolTip(
            "Force OCR even for digital PDFs with embedded text"
        )
        opts_layout.addWidget(self.force_ocr_cb)

        opts_layout.addWidget(QLabel("Page Range:"))
        self.page_range_input = QLineEdit()
        self.page_range_input.setPlaceholderText("e.g. 0-5,10")
        self.page_range_input.setMaximumWidth(150)
        opts_layout.addWidget(self.page_range_input)

        opts_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu", "cuda"])
        self.device_combo.setToolTip(
            "auto: Use GPU if enough VRAM, else CPU\n"
            "cpu: Force CPU (slower but no VRAM limit)\n"
            "cuda: Force GPU (may OOM on large PDFs)"
        )
        self.device_combo.setMaximumWidth(100)
        opts_layout.addWidget(self.device_combo)

        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        # --- Languages ---
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Languages:"))

        default_codes = DEFAULT_LANGS.split(",")
        self.lang_checkboxes = {}
        for code, name in SUPPORTED_LANGUAGES.items():
            cb = QCheckBox(f"{code} ({name.split('/')[0].strip()})")
            cb.setChecked(code in default_codes)
            self.lang_checkboxes[code] = cb
            lang_layout.addWidget(cb)

        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # --- File table ---
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            ["Filename", "Status", "Progress"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Fixed
        )
        self.table.setColumnWidth(2, 100)
        layout.addWidget(self.table)

        # --- Start button ---
        self.start_btn = QPushButton("Start Conversion")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-weight: bold; padding: 10px;"
        )
        layout.addWidget(self.start_btn)

        # --- Log area ---
        log_label = QLabel("Logs:")
        layout.addWidget(log_label)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def browse_input_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Input Directory"
        )
        if directory:
            self.in_dir_input.setText(directory)
            self.scan_directory(directory)

    def browse_output_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        if directory:
            self.out_dir_input.setText(directory)

    def scan_directory(self, directory: str):
        self.table.setRowCount(0)
        self.files_to_process = []

        try:
            exts = ('.pdf', '.docx')
            files = sorted(
                f for f in os.listdir(directory)
                if f.lower().endswith(exts)
            )
            if not files:
                QMessageBox.information(
                    self, "No Files Found",
                    "No PDF or DOCX files found in the selected directory."
                )
                self.start_btn.setEnabled(False)
                return

            self.table.setRowCount(len(files))
            for i, filename in enumerate(files):
                filepath = os.path.join(directory, filename)
                self.files_to_process.append((i, filepath))

                self.table.setItem(i, 0, QTableWidgetItem(filename))
                self.table.setItem(i, 1, QTableWidgetItem("Pending"))
                self.table.setItem(i, 2, QTableWidgetItem("0%"))

            self.start_btn.setEnabled(True)
            self.log(f"Found {len(files)} files in {directory}")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to scan directory: {e}"
            )

    def start_processing(self):
        output_dir = self.out_dir_input.text().strip()
        if not output_dir:
            output_dir = self.in_dir_input.text().strip()
        if not output_dir:
            QMessageBox.warning(
                self, "No Directory", "Please select an input directory."
            )
            return

        force_ocr = self.force_ocr_cb.isChecked()
        page_range = self.page_range_input.text().strip() or None
        selected = [code for code, cb in self.lang_checkboxes.items() if cb.isChecked()]
        langs = ",".join(selected) if selected else DEFAULT_LANGS
        device = self.device_combo.currentText()

        self.start_btn.setEnabled(False)
        self.browse_in_btn.setEnabled(False)
        self.browse_out_btn.setEnabled(False)

        self.worker = MarkerWorker(
            files=self.files_to_process,
            output_dir=output_dir,
            force_ocr=force_ocr,
            page_range=page_range,
            langs=langs,
            device=device,
        )
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.status_signal.connect(self.update_status)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.processing_finished)
        self.worker.start()

    def update_progress(self, row: int, progress: int):
        item = self.table.item(row, 2)
        if item:
            item.setText(f"{progress}%")

    def update_status(self, row: int, status: str):
        item = self.table.item(row, 1)
        if item:
            item.setText(status)
            if status == "Completed":
                item.setBackground(Qt.green)
            elif status in ("Failed", "Error"):
                item.setBackground(Qt.red)
            elif "Converting" in status or "Loading" in status:
                item.setBackground(Qt.yellow)

    def log(self, message: str):
        self.log_area.append(
            f"[{time.strftime('%H:%M:%S')}] {message}"
        )

    def processing_finished(self):
        self.start_btn.setEnabled(True)
        self.browse_in_btn.setEnabled(True)
        self.browse_out_btn.setEnabled(True)
        self.log("All tasks completed.")
        QMessageBox.information(self, "Done", "Processing completed.")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Processing is running. Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def run_gui():
    """Launch the NuoYi GUI application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
