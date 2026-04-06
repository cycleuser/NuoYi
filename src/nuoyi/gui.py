"""
NuoYi - PySide6 GUI for batch PDF/DOCX to Markdown conversion.

Supported acceleration backends:
- CUDA: NVIDIA GPUs
- ROCm: AMD GPUs (Linux)
- DirectML: AMD/Intel/NVIDIA GPUs (Windows)
- MPS: Apple Silicon Metal (macOS)
- MLX: Apple MLX framework (macOS)
- Vulkan: Cross-platform GPU
- OpenVINO: Intel CPU/GPU
- CPU: Universal fallback
"""

import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
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

from .converter import DocxConverter, get_converter, list_available_engines
from .utils import (
    DEFAULT_LANGS,
    SUPPORTED_LANGUAGES,
    find_documents,
    list_available_devices,
    save_images_and_update_markdown,
)

DEVICE_DESCRIPTIONS = {
    "auto": "Auto (recommended)",
    "cuda": "CUDA (NVIDIA GPU)",
    "rocm": "ROCm (AMD GPU - Linux)",
    "directml": "DirectML (AMD/Intel - Windows)",
    "mps": "MPS (Apple Metal)",
    "mlx": "MLX (Apple Silicon)",
    "vulkan": "Vulkan (cross-platform)",
    "openvino": "OpenVINO (Intel)",
    "cpu": "CPU (fallback)",
}

ENGINE_DESCRIPTIONS = {
    "auto": "Auto (recommended)",
    "marker": "Marker - Best quality, GPU",
    "mineru": "MinerU - Chinese docs, GPU optional",
    "docling": "Docling - Balanced, GPU optional",
    "pymupdf": "PyMuPDF - Fastest, no GPU",
    "pdfplumber": "PDFPlumber - Lightweight, no GPU",
    "llamaparse": "LlamaParse - Cloud, API key",
    "mathpix": "Mathpix - Math specialist, API key",
}


class ConverterWorker(QThread):
    """Background worker for batch file processing."""

    progress_signal = Signal(int, int)
    status_signal = Signal(int, str)
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(
        self,
        files,
        input_dir: str,
        output_dir: str,
        force_ocr: bool = False,
        page_range: str | None = None,
        langs: str = "zh,en",
        device: str = "auto",
        low_vram: bool = False,
        engine: str = "auto",
        recursive: bool = False,
        existing_files: str = "ask",
        parent=None,
    ):
        super().__init__(parent)
        self.files = files
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.force_ocr = force_ocr
        self.page_range = page_range
        self.langs = langs
        self.device = device
        self.low_vram = low_vram
        self.engine = engine
        self.recursive = recursive
        self.existing_files = existing_files
        self.is_running = True

    def run(self):

        os.environ["GRPC_VERBOSITY"] = "ERROR"
        os.environ["GLOG_minloglevel"] = "2"
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        os.environ["IN_STREAMLIT"] = "true"

        self.log_signal.emit(f"Starting processing of {len(self.files)} files...")
        self.log_signal.emit(f"Engine: {self.engine}, Device: {self.device}")

        from .utils import get_output_path

        pdf_converter = None
        docx_converter = None

        # 统计
        success_count = 0
        failed_count = 0
        skipped_count = 0

        try:
            if any(fp.lower().endswith(".pdf") for _, fp in self.files):
                self.log_signal.emit(f"Initializing {self.engine} converter...")
                self.status_signal.emit(self.files[0][0], "Loading...")
                pdf_converter = get_converter(
                    engine=self.engine,
                    force_ocr=self.force_ocr,
                    page_range=self.page_range,
                    langs=self.langs,
                    device=self.device,
                    low_vram=self.low_vram,
                )
                self.log_signal.emit("Converter ready.")
        except Exception as e:
            self.log_signal.emit(f"Failed to initialize PDF converter: {e}")
            self.log_signal.emit("PDF files will be skipped.")

        if any(fp.lower().endswith(".docx") for _, fp in self.files):
            docx_converter = DocxConverter()

        for index, filepath in self.files:
            if not self.is_running:
                break

            filename = os.path.basename(filepath)
            suffix = Path(filepath).suffix.lower()

            # 计算输出路径
            out_path = get_output_path(
                Path(filepath), self.input_dir, self.output_dir, self.recursive
            )

            # 检查文件是否存在，根据策略决定是否跳过
            should_convert = True
            if out_path.exists():
                if self.existing_files == "skip":
                    should_convert = False
                    self.status_signal.emit(index, "Skipped")
                    self.log_signal.emit(f"[{filename}] Skipped (already exists)")
                    skipped_count += 1
                    continue
                elif self.existing_files == "update":
                    src_mtime = Path(filepath).stat().st_mtime
                    out_mtime = out_path.stat().st_mtime
                    if src_mtime <= out_mtime:
                        should_convert = False
                        self.status_signal.emit(index, "Skipped")
                        self.log_signal.emit(f"[{filename}] Skipped (source not newer)")
                        skipped_count += 1
                        continue
                    else:
                        self.log_signal.emit(f"[{filename}] Updating (source is newer)")
                elif self.existing_files == "overwrite":
                    self.log_signal.emit(f"[{filename}] Overwriting existing file")

            if not should_convert:
                continue
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
                self.log_signal.emit(f"[{filename}] Done -> {out_path.name}")
                success_count += 1

            except Exception as e:
                self.status_signal.emit(index, "Error")
                self.log_signal.emit(f"[{filename}] Error: {e}")
                failed_count += 1

        self.log_signal.emit(
            f"Done: {success_count} converted, {skipped_count} skipped, {failed_count} failed"
        )
        self.finished_signal.emit()

    def stop(self):
        self.is_running = False


class MainWindow(QMainWindow):
    """PySide6 GUI for batch PDF/DOCX to Markdown conversion."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NuoYi - PDF/DOCX to Markdown Converter")
        self.resize(1000, 800)

        self.files_to_process: list[tuple[int, str]] = []
        self.worker: ConverterWorker | None = None
        self.available_devices: list[str] = []
        self.available_engines: dict[str, dict] = {}

        self.setup_ui()
        self.detect_hardware()

    def detect_hardware(self):
        """Detect available acceleration devices and engines."""
        self.log("Detecting hardware...")

        self.available_devices = list_available_devices()
        self.available_engines = list_available_engines()

        self.update_device_combo()
        self.update_engine_combo()

        device_list = ", ".join(self.available_devices)
        self.log(f"Devices: {device_list}")

        engine_list = [k for k, v in self.available_engines.items() if v["available"]]
        self.log(f"Engines: {', '.join(engine_list)}")

    def update_device_combo(self):
        self.device_combo.clear()
        self.device_combo.addItem(DEVICE_DESCRIPTIONS["auto"], "auto")

        for device in self.available_devices:
            if device != "cpu":
                desc = DEVICE_DESCRIPTIONS.get(device, device)
                self.device_combo.addItem(desc, device)

        self.device_combo.addItem(DEVICE_DESCRIPTIONS["cpu"], "cpu")

        if "mps" in self.available_devices:
            self.device_combo.setCurrentIndex(self.device_combo.findData("mps"))
        elif "mlx" in self.available_devices:
            self.device_combo.setCurrentIndex(self.device_combo.findData("mlx"))
        elif "cuda" in self.available_devices:
            self.device_combo.setCurrentIndex(self.device_combo.findData("cuda"))

    def update_engine_combo(self):
        self.engine_combo.clear()
        self.engine_combo.addItem(ENGINE_DESCRIPTIONS["auto"], "auto")

        for engine, info in self.available_engines.items():
            if info["available"]:
                desc = ENGINE_DESCRIPTIONS.get(engine, engine)
                status = "" if info["available"] else " (unavailable)"
                self.engine_combo.addItem(desc + status, engine)

        self.engine_combo.setToolTip(self._get_engine_tooltip())

        if self.available_engines.get("marker", {}).get("available"):
            self.engine_combo.setCurrentIndex(self.engine_combo.findData("auto"))
        elif self.available_engines.get("pymupdf", {}).get("available"):
            self.engine_combo.setCurrentIndex(self.engine_combo.findData("pymupdf"))

    def _get_engine_tooltip(self) -> str:
        lines = ["PDF Engines:"]
        for name, info in self.available_engines.items():
            status = "[OK]" if info["available"] else "[--]"
            lines.append(f"  {status} {name}: {info.get('notes', '')}")
        return "\n".join(lines)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        layout.addWidget(self._create_io_group())
        layout.addWidget(self._create_options_group())
        layout.addWidget(self._create_file_table())
        layout.addWidget(self._create_log_area())

    def _create_io_group(self) -> QGroupBox:
        group = QGroupBox("Input / Output")
        layout = QVBoxLayout(group)

        in_layout = QHBoxLayout()
        in_layout.addWidget(QLabel("Input:"))
        self.in_dir_input = QLineEdit()
        self.in_dir_input.setReadOnly(True)
        self.in_dir_input.setPlaceholderText("Select directory or files")
        self.browse_in_btn = QPushButton("Browse")
        self.browse_in_btn.clicked.connect(self.browse_input_directory)
        in_layout.addWidget(self.in_dir_input)
        in_layout.addWidget(self.browse_in_btn)
        layout.addLayout(in_layout)

        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("Output:"))
        self.out_dir_input = QLineEdit()
        self.out_dir_input.setReadOnly(True)
        self.out_dir_input.setPlaceholderText("Same as input (default)")
        self.browse_out_btn = QPushButton("Browse")
        self.browse_out_btn.clicked.connect(self.browse_output_directory)
        out_layout.addWidget(self.out_dir_input)
        out_layout.addWidget(self.browse_out_btn)
        layout.addLayout(out_layout)

        return group

    def _create_options_group(self) -> QGroupBox:
        group = QGroupBox("Options")
        layout = QVBoxLayout(group)

        row1 = QHBoxLayout()
        self.force_ocr_cb = QCheckBox("Force OCR")
        self.force_ocr_cb.setToolTip("Force OCR for digital PDFs")
        row1.addWidget(self.force_ocr_cb)

        self.recursive_cb = QCheckBox("Recursive")
        self.recursive_cb.setToolTip("Scan subdirectories")
        row1.addWidget(self.recursive_cb)

        self.low_vram_cb = QCheckBox("Low VRAM")
        self.low_vram_cb.setToolTip("Enable for GPUs <8GB")
        row1.addWidget(self.low_vram_cb)

        row1.addWidget(QLabel("Page Range:"))
        self.page_range_input = QLineEdit()
        self.page_range_input.setPlaceholderText("e.g. 0-5,10")
        self.page_range_input.setMaximumWidth(100)
        row1.addWidget(self.page_range_input)

        row1.addStretch()
        layout.addLayout(row1)

        row2 = QHBoxLayout()

        row2.addWidget(QLabel("Engine:"))
        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumWidth(200)
        row2.addWidget(self.engine_combo)

        row2.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(180)
        row2.addWidget(self.device_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Re-detect hardware")
        self.refresh_btn.clicked.connect(self.detect_hardware)
        row2.addWidget(self.refresh_btn)

        row2.addStretch()
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Languages:"))
        default_codes = DEFAULT_LANGS.split(",")
        self.lang_checkboxes = {}
        for code, name in SUPPORTED_LANGUAGES.items():
            cb = QCheckBox(code)
            cb.setChecked(code in default_codes)
            cb.setToolTip(name)
            self.lang_checkboxes[code] = cb
            row3.addWidget(cb)

        row3.addSpacing(20)
        row3.addWidget(QLabel("Existing Files:"))
        self.existing_files_combo = QComboBox()
        self.existing_files_combo.addItem("Ask (interactive)", "ask")
        self.existing_files_combo.addItem("Overwrite all", "overwrite")
        self.existing_files_combo.addItem("Skip all", "skip")
        self.existing_files_combo.addItem("Update if newer", "update")
        self.existing_files_combo.setCurrentIndex(0)
        self.existing_files_combo.setToolTip(
            "How to handle existing output files:\n"
            "• Ask: Interactive prompt\n"
            "• Overwrite: Replace all existing files\n"
            "• Skip: Keep all existing files\n"
            "• Update: Only convert if source is newer"
        )
        row3.addWidget(self.existing_files_combo)

        row3.addStretch()
        layout.addLayout(row3)

        return group

    def _create_file_table(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Filename", "Status", "Progress"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 100)
        layout.addWidget(self.table)

        self.start_btn = QPushButton("Start Conversion")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;"
        )
        layout.addWidget(self.start_btn)

        return widget

    def _create_log_area(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Logs:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(120)
        layout.addWidget(self.log_area)

        return widget

    def browse_input_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if directory:
            self.in_dir_input.setText(directory)
            self.scan_directory(directory)

    def browse_output_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.out_dir_input.setText(directory)

    def scan_directory(self, directory: str):
        self.table.setRowCount(0)
        self.files_to_process = []

        try:
            recursive = self.recursive_cb.isChecked()
            files = find_documents(Path(directory), recursive=recursive)

            if not files:
                QMessageBox.information(self, "No Files", "No PDF or DOCX files found.")
                self.start_btn.setEnabled(False)
                return

            self.table.setRowCount(len(files))
            for i, filepath in enumerate(files):
                self.files_to_process.append((i, str(filepath)))

                filename = filepath.name
                if recursive:
                    try:
                        filename = str(filepath.relative_to(Path(directory)))
                    except ValueError:
                        pass

                self.table.setItem(i, 0, QTableWidgetItem(filename))
                self.table.setItem(i, 1, QTableWidgetItem("Pending"))
                self.table.setItem(i, 2, QTableWidgetItem("0%"))

            self.start_btn.setEnabled(True)
            self.log(f"Found {len(files)} files")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to scan: {e}")

    def start_processing(self):
        output_dir = self.out_dir_input.text().strip()
        if not output_dir:
            output_dir = self.in_dir_input.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "No Directory", "Select input directory.")
            return

        force_ocr = self.force_ocr_cb.isChecked()
        recursive = self.recursive_cb.isChecked()
        low_vram = self.low_vram_cb.isChecked()
        existing_files = self.existing_files_combo.currentData() or "ask"
        page_range = self.page_range_input.text().strip() or None
        selected = [code for code, cb in self.lang_checkboxes.items() if cb.isChecked()]
        langs = ",".join(selected) if selected else DEFAULT_LANGS
        device = self.device_combo.currentData() or "auto"
        engine = self.engine_combo.currentData() or "auto"

        self.start_btn.setEnabled(False)
        self.browse_in_btn.setEnabled(False)
        self.browse_out_btn.setEnabled(False)
        self.engine_combo.setEnabled(False)
        self.device_combo.setEnabled(False)
        self.refresh_btn.setEnabled(False)

        self.worker = ConverterWorker(
            files=self.files_to_process,
            input_dir=self.in_dir_input.text().strip(),
            output_dir=output_dir,
            force_ocr=force_ocr,
            page_range=page_range,
            langs=langs,
            device=device,
            low_vram=low_vram,
            engine=engine,
            recursive=recursive,
            existing_files=existing_files,
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
                item.setBackground(Qt.GlobalColor.green)
            elif status in ("Failed", "Error"):
                item.setBackground(Qt.GlobalColor.red)
            elif "Converting" in status or "Loading" in status:
                item.setBackground(Qt.GlobalColor.yellow)

    def log(self, message: str):
        self.log_area.append(f"[{time.strftime('%H:%M:%S')}] {message}")

    def processing_finished(self):
        self.start_btn.setEnabled(True)
        self.browse_in_btn.setEnabled(True)
        self.browse_out_btn.setEnabled(True)
        self.engine_combo.setEnabled(True)
        self.device_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.log("All tasks completed.")
        QMessageBox.information(self, "Done", "Processing completed.")

    def closeEvent(self, event):  # noqa: N802
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Processing is running. Exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
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
