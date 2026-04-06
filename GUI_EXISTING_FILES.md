# GUI现有文件处理功能添加完成

## 已添加的功能

在GUI界面"Options"区域添加了"Existing Files"下拉选择框：

### 选项说明

1. **Ask (interactive)** - 默认选项，交互式询问
   - 发现已存在文件时会弹出提示
   - 用户可选择：覆盖、跳过、更新、询问每个文件

2. **Overwrite all** - 全部覆盖
   - 替换所有已存在的输出文件

3. **Skip all** - 全部跳过
   - 保留所有已存在的文件，不重新转换

4. **Update if newer** - 仅更新较新的文件
   - 只有当源文件比输出文件新时才转换

## GUI界面位置

```
Options
├── [x] Force OCR    [x] Recursive    [ ] Low VRAM    [ ] No OCR Models    Page Range: [____]
├── Engine: [Auto ▼]    Device: [Auto ▼]    [Refresh]
└── Languages: [x]zh [x]en [ ]ja ...    Existing Files: [Ask (interactive) ▼]
```

## 代码修改位置

### 1. GUI界面添加（gui.py）

```python
# 在_create_options_group方法中添加
row3.addWidget(QLabel("Existing Files:"))
self.existing_files_combo = QComboBox()
self.existing_files_combo.addItem("Ask (interactive)", "ask")
self.existing_files_combo.addItem("Overwrite all", "overwrite")
self.existing_files_combo.addItem("Skip all", "skip")
self.existing_files_combo.addItem("Update if newer", "update")
```

### 2. ConverterWorker传递参数（gui.py）

```python
# 在__init__中添加
self.existing_files = existing_files

# 在start_processing中获取并传递
existing_files = self.existing_files_combo.currentData() or "ask"
self.worker = ConverterWorker(..., existing_files=existing_files)
```

## 使用流程

1. **打开GUI**
   ```bash
   nuoyi --gui
   ```

2. **选择输入目录**
   - 点击"Browse"选择包含PDF/DOCX的目录

3. **配置Existing Files选项**
   - 在Options区域找到"Existing Files"下拉框
   - 选择处理方式：Ask/Overwrite/Skip/Update

4. **开始转换**
   - 点击"Start Conversion"
   - 根据选择的处理方式自动处理已存在文件

## 与CLI一致

GUI和CLI使用相同的处理逻辑：

```bash
# CLI
nuoyi ./papers --batch --existing-files overwrite

# GUI
Options → Existing Files → Overwrite all
```

两者都会调用`convert_directory`函数的相同参数。

## 测试验证

所有测试通过：
```
tests/test_existing_files.py::test_skip_existing_files PASSED
tests/test_existing_files.py::test_overwrite_existing_files PASSED
tests/test_existing_files.py::test_update_only_newer_files PASSED
```

GUI导入正常：
```
from nuoyi.gui import MainWindow, ConverterWorker  # OK
```