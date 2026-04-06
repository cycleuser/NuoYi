# Existing Files Handling Feature

## Overview

Added a feature to handle existing output files during batch conversion. Users can now choose how to proceed when output files already exist.

## Usage

### CLI Options

```bash
# Interactive mode - asks for each file (default)
nuoyi ./papers --batch --existing-files ask

# Overwrite all existing files
nuoyi ./papers --batch --existing-files overwrite

# Skip all existing files
nuoyi ./papers --batch --existing-files skip

# Only convert files newer than existing output
nuoyi ./papers --batch --existing-files update
```

### Interactive Choices

When using `--existing-files ask`, the user gets a menu:

```
[Batch] Found X existing output files.
Choose how to handle them:
  [1] Overwrite all - Replace all existing files
  [2] Skip all - Keep all existing files
  [3] Update all - Only convert if source is newer
  [4] Ask for each file individually
```

If choosing option 4 (ask for each), for each file:

```
[Batch] 1/10: filename.pdf
  Output file already exists: output/filename.md
  [o] Overwrite this file
  [s] Skip this file
  [u] Update if source is newer
  [O] Overwrite all remaining
  [S] Skip all remaining
  [U] Update all remaining
```

### API Usage

```python
from nuoyi.api import convert_directory

# Skip existing files
result = convert_directory(
    input_dir="./papers",
    output_dir="./output",
    existing_files="skip"
)

# Overwrite existing files
result = convert_directory(
    input_dir="./papers",
    output_dir="./output",
    existing_files="overwrite"
)

# Only update newer files
result = convert_directory(
    input_dir="./papers",
    output_dir="./output",
    existing_files="update"
)
```

## Modes

1. **ask** (default): Interactive prompt before processing
2. **overwrite**: Replace all existing output files
3. **skip**: Keep all existing output files unchanged
4. **update**: Only convert if source file is newer than output file (based on modification time)

## Implementation Details

- Added `--existing-files` parameter to CLI (choices: ask/overwrite/skip/update)
- Modified `convert_directory` in `api.py` to detect existing files
- Added interactive prompt system with batch action options
- Added modification time comparison for update mode
- Added `skipped` count to conversion results

## Testing

Test coverage includes:
- Skip existing files mode
- Overwrite existing files mode  
- Update only newer files mode

All tests pass successfully.