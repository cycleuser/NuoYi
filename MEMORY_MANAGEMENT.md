# Memory Management Improvements

## Summary of Changes

This update adds comprehensive memory management and OCR model control features to NuoYi, solving the "CUDA out of memory" errors when processing large batches of PDFs.

## New Features

### 1. Disable OCR Models Flag (`--disable-ocr-models`)

**Purpose**: Save ~1.5GB VRAM by not loading OCR-related models for digital PDFs.

**Usage**:
```bash
nuoyi paper.pdf --disable-ocr-models
```

**When to use**:
- Digital PDFs with embedded text (not scanned documents)
- PDFs without complex tables requiring OCR
- PDFs without mathematical formulas requiring OCR

**Warning**: OCR features will not work when this flag is enabled.

### 2. Enhanced Low VRAM Mode (`--low-vram`)

**Improvements**:
- More aggressive memory optimization
- Better VRAM threshold detection (4GB and 6GB thresholds)
- Automatic cleanup every N files during batch processing

### 3. Lazy Model Loading

Models are only loaded when the first file is processed, not at initialization. This allows:
- Checking available memory before loading
- Providing helpful error messages if memory is insufficient
- Automatic cleanup between files in batch mode

### 4. Automatic OOM Recovery

When CUDA OOM occurs during conversion:
1. Automatic aggressive memory cleanup
2. Retry with cleaned cache
3. Helpful suggestions if still fails

### 5. Memory Monitoring

New utility functions:
- `get_current_memory_usage()` - Get detailed GPU memory statistics
- `check_memory_available(required_mb)` - Check if enough memory available
- `aggressive_memory_cleanup()` - Force cleanup of GPU memory

## Implementation Details

### Files Modified

1. **src/nuoyi/utils.py**
   - Added `aggressive_memory_cleanup()`
   - Added `check_memory_available()`
   - Added `get_current_memory_usage()`
   - Added `VERY_LOW_VRAM_THRESHOLD_GB` constant
   - Added `_setup_directml_env()` function

2. **src/nuoyi/converter.py**
   - `MarkerPDFConverter`:
     - Added `disable_ocr_models` parameter
     - Lazy model loading
     - `_create_minimal_model_dict()` for OCR-disabled mode
     - OOM retry mechanism with cleanup
     - `cleanup()` method for explicit resource release

3. **src/nuoyi/cli.py**
   - Added `--disable-ocr-models` CLI flag
   - Updated `convert_single_file()` and `convert_directory()`
   - Better memory management in batch processing
   - Conflict warning between `--disable-ocr-models` and `--force-ocr`

4. **src/nuoyi/api.py**
   - Updated `convert_file()` with `disable_ocr_models` parameter
   - Updated `convert_directory()` with `disable_ocr_models` parameter

5. **src/nuoyi/gui.py**
   - Added "No OCR Models" checkbox
   - Updated `ConverterWorker` to support `disable_ocr_models`

### Memory Usage Comparison

| Mode | VRAM Required | Features |
|------|---------------|----------|
| Full models | ~3GB | All features (OCR, tables, formulas) |
| Minimal models (--disable-ocr-models) | ~1.5GB | Layout detection only, no OCR |
| CPU mode | 0GB | All features, slower |

## Testing

All tests pass (49 passed, 3 deselected):
- `tests/test_memory_management.py` - 13 new tests for memory features
- All existing tests continue to pass

## Documentation Updates

- **README.md** - Added low VRAM options section, updated CLI options table
- **README_CN.md** - Chinese documentation updated with same content
- CLI help text includes new `--disable-ocr-models` option

## Usage Examples

### For Digital PDFs (Low VRAM GPUs)
```bash
nuoyi paper.pdf --disable-ocr-models --low-vram
```

### For Batch Processing
```bash
nuoyi ./papers --batch --disable-ocr-models
```

### For Scanned PDFs (Full OCR)
```bash
nuoyi scanned.pdf --low-vram
```

### Using Python API
```python
# Minimal models for digital PDFs
converter = MarkerPDFConverter(
    disable_ocr_models=True,
    low_vram=True,
    device="auto"
)
markdown, images = converter.convert_file("digital.pdf")

# Don't forget to cleanup when done
converter.cleanup()
```

## Future Improvements

Potential future enhancements:
1. Auto-detect PDF type (digital vs scanned) and auto-disable OCR models
2. Model swapping: unload OCR models after OCR-heavy pages
3. Streaming batch processing to reduce memory footprint
4. Integration with system memory monitors for adaptive processing