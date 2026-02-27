# NuoYi

A simple tool to transform PDF and DOCX to Markdown.

[中文文档](README_CN.md)

NuoYi uses [marker-pdf](https://github.com/VikParuchuri/marker) for high-quality PDF conversion with OCR and layout detection. All processing is done **fully offline** after the initial model download.

## Features

- **PDF to Markdown**: High-quality conversion using marker-pdf with surya OCR
- **DOCX to Markdown**: Native support for Microsoft Word documents
- **Automatic GPU/CPU Selection**: Detects available VRAM and falls back to CPU if needed
- **Batch Processing**: Convert entire directories of documents
- **GUI Interface**: PySide6-based graphical interface for easy batch conversion
- **Image Extraction**: Automatically extracts and saves images from PDFs
- **Multi-language Support**: 10 languages supported including Chinese, English, Japanese, French, Russian, German, Spanish, Portuguese, Italian, Korean

## Installation

### From PyPI

```bash
pip install nuoyi
```

### With GUI support

```bash
pip install nuoyi[gui]
```

### From source

```bash
git clone https://github.com/cycleuser/NuoYi.git
cd NuoYi
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Convert a single PDF file
nuoyi paper.pdf

# Specify output file
nuoyi paper.pdf -o output/result.md

# Convert a DOCX file
nuoyi document.docx -o document.md

# Batch convert all files in a directory
nuoyi ./papers --batch

# Batch convert with custom output directory
nuoyi ./papers --batch -o ./output

# Force CPU mode (for low VRAM GPUs)
nuoyi paper.pdf --device cpu

# Force OCR even for digital PDFs
nuoyi paper.pdf --force-ocr

# Specify page range
nuoyi paper.pdf --page-range "0-5,10,15-20"

# Specify languages
nuoyi paper.pdf --langs "zh,en,ja"
```

### GUI Mode

```bash
nuoyi --gui
```

The GUI provides:
- Directory selection for input/output
- File list with status tracking
- Device selection (auto/CPU/CUDA)
- Force OCR option
- Page range and language configuration
- Real-time progress and logging

**Startup interface:**

![Startup](images/1-启动界面.png)

**Select input directory:**

![Select directory](images/2-选择路径.png)

**Configure device and options:**

![Configure](images/3-选择模型.png)

**Conversion result (viewed in VS Code):**

![Result](images/4-结果.png)

### Python API

```python
from nuoyi import MarkerPDFConverter, DocxConverter

# Convert PDF
pdf_converter = MarkerPDFConverter(
    force_ocr=False,
    langs="zh,en",
    device="auto"  # or "cpu", "cuda", "mps"
)
markdown_text, images = pdf_converter.convert_file("input.pdf")

# Convert DOCX
docx_converter = DocxConverter()
markdown_text = docx_converter.convert_file("input.docx")
```

## Supported Languages

| Code | Language |
|------|----------|
| `zh` | Chinese / 中文 |
| `en` | English |
| `ja` | Japanese / 日本語 |
| `fr` | French / Français |
| `ru` | Russian / Русский |
| `de` | German / Deutsch |
| `es` | Spanish / Español |
| `pt` | Portuguese / Português |
| `it` | Italian / Italiano |
| `ko` | Korean / 한국어 |

Use `nuoyi --list-langs` to see the full list. Default: `zh,en`.

## Command Line Options

| Option | Description |
|--------|-------------|
| `input` | Input PDF/DOCX file or directory (with --batch) |
| `-o, --output` | Output file path (single file) or directory (batch mode) |
| `--force-ocr` | Force OCR even for digital PDFs with embedded text |
| `--page-range` | Page range to convert, e.g. '0-5,10,15-20' |
| `--langs` | Comma-separated languages (default: zh,en). See `--list-langs` |
| `--list-langs` | List all supported languages and exit |
| `--batch` | Process all PDF/DOCX files in the input directory |
| `--device` | Device for model inference: auto (default), cpu, cuda, or mps |
| `--gui` | Launch PySide6 GUI mode |
| `-V, --version` | Show version and exit |

## Memory Management

NuoYi automatically manages GPU memory:

- **Auto mode** (default): Detects available VRAM and uses GPU if sufficient (>6GB free)
- **CPU mode**: Forces CPU processing (slower but no VRAM limit)
- **CUDA mode**: Forces GPU processing (may OOM on large PDFs)
- **MPS mode**: For Apple Silicon Macs

If CUDA out of memory occurs during conversion, NuoYi automatically falls back to CPU.

## Dependencies

### Required
- `marker-pdf>=1.0.0` - PDF conversion engine
- `PyMuPDF>=1.23.0` - PDF page counting
- `python-docx>=0.8.11` - DOCX conversion
- `Pillow>=9.0.0` - Image processing

### Optional
- `PySide6>=6.5.0` - GUI support (install with `pip install nuoyi[gui]`)

## Model Download

### Download Location

Models are downloaded automatically on first run and stored in:

```
~/.cache/huggingface/hub/
```

The models are from [Hugging Face](https://huggingface.co/) and include:
- `vikp/surya_det` - Layout detection model
- `vikp/surya_rec` - Text recognition model
- `vikp/surya_order` - Reading order model
- Other marker-pdf related models

Total size: approximately **2-3 GB**.

### For Users in China

Hugging Face may be blocked or slow in mainland China due to GFW. You can use a mirror:

```bash
# Set Hugging Face mirror (add to ~/.bashrc or run before nuoyi)
export HF_ENDPOINT=https://hf-mirror.com

# Then run nuoyi normally
nuoyi paper.pdf
```

Alternatively, you can download models manually and place them in the cache directory.

### Custom Model Path

The current version does not support custom model paths to keep the tool simple and avoid configuration complexity. Models are always stored in the default Hugging Face cache location.

## Notes

- After initial model download, everything works fully offline
- Use `--device cpu` if you encounter CUDA out of memory errors
- Legacy `.doc` format is not supported; convert to `.docx` first

## License

GPL-3.0 License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [marker-pdf](https://github.com/VikParuchuri/marker) - The excellent PDF conversion engine
- [surya](https://github.com/VikParuchuri/surya) - OCR and layout detection models
