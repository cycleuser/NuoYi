# 递归目录转换功能 - 完整使用说明

## 功能概述

NuoYi 现在支持递归转换目录中的所有 PDF/DOCX 文件，并**完整保持输入目录的层级结构**，在每个输出子目录名后添加 `_md` 后缀。

## 核心特性

### 1. 目录结构保持

输入目录结构会被完整复制到输出目录，所有子目录名后添加 `_md` 后缀。

**示例：**
```
输入目录 (input/)               输出目录 (output/)
├── overview.pdf         ->     ├── overview.md
├── projects/                   ├── projects_md/
│   ├── ProjectA/               │   ├── ProjectA_md/
│   │   ├── spec.pdf            │   │   ├── spec.md
│   │   └── docs/               │   │   └── docs_md/
│   │       └── manual.pdf      │   │       └── manual.md
│   └── ProjectB/               │   └── ProjectB_md/
│       └── reports/            │       └── reports_md/
│           └── quarterly.docx  │           └── quarterly.md
```

### 2. 三个界面支持

- **CLI**: 命令行界面
- **Python API**: 程序化调用
- **GUI**: 图形用户界面

## 使用方法

### CLI 命令行

```bash
# 基本用法（递归模式）
nuoyi ./input --batch --recursive
nuoyi ./input --batch -r

# 指定输出目录
nuoyi ./input --batch -r -o ./output

# 完整示例
nuoyi ./documents --batch -r -o ./markdown_output
```

**输出示例：**
```
Found 15 files to process.

[1/15] overview.pdf... OK
[2/15] projects/ProjectA/spec.pdf... OK
[3/15] projects/ProjectA/docs/manual.pdf... OK
...
Batch complete: 15 succeeded, 0 failed.
Output directory structure preserved with '_md' suffix on subdirectories.
```

### Python API

```python
from nuoyi import convert_directory

# 递归转换，保持目录结构
result = convert_directory(
    "./input",
    output_dir="./output",
    recursive=True,
)

# 检查结果
if result.success:
    print(f"✓ Converted {result.data['success']} files")
    for file_info in result.data['files']:
        print(f"  {file_info['file']} -> {file_info['output']}")
else:
    print(f"✗ Failed: {result.error}")
```

**返回示例：**
```python
{
    'success': True,
    'data': {
        'files': [
            {
                'file': 'projects/ProjectA/spec.pdf',
                'success': True,
                'output': '/path/to/output/projects_md/ProjectA_md/spec.md'
            },
            ...
        ],
        'success': 15,
        'failed': 0
    },
    'metadata': {
        'input_dir': '/path/to/input',
        'output_dir': '/path/to/output',
        'total': 15,
        'recursive': True
    }
}
```

### GUI 图形界面

1. 启动 GUI：`nuoyi --gui`
2. 点击 "Browse" 选择**输入目录**
3. 勾选 **"Recursive (include subdirectories)"**
4. （可选）点击 "Browse" 选择**输出目录**
5. 点击 "Start Conversion"

**文件列表显示：**
```
Filename                                    Status      Progress
overview.pdf                                Pending     0%
projects/ProjectA/spec.pdf                  Pending     0%
projects/ProjectA/docs/manual.pdf           Pending     0%
projects/ProjectB/reports/quarterly.docx    Pending     0%
```

## 目录结构规则

### 输入目录
```
documents/
├── root.pdf
├── folder1/
│   ├── file1.pdf
│   └── nested/
│       └── file2.pdf
└── folder2/
    └── file3.docx
```

### 输出目录（recursive=True）
```
output/
├── root.md                          # 根目录文件无 _md 后缀
├── folder1_md/                      # 子目录添加 _md
│   ├── file1.md
│   └── nested_md/                   # 嵌套目录也添加 _md
│       └── file2.md
└── folder2_md/
    └── file3.md
```

### 输出目录（recursive=False）
```
output/
├── root.md                          # 所有文件在同一层
├── file1.md
├── file2.md
└── file3.md
```

## 技术实现

### 核心函数

```python
from nuoyi.utils import get_output_path, create_output_directories

# 计算输出路径
output_path = get_output_path(
    input_file=Path("projects/ProjectA/spec.pdf"),
    input_dir=Path("./input"),
    output_dir=Path("./output"),
    recursive=True,
    suffix="_md"
)
# 结果：./output/projects_md/ProjectA_md/spec.md

# 创建输出目录结构
files = find_documents(input_dir, recursive=True)
create_output_directories(files, input_dir, output_dir, recursive=True)
```

### 路径计算逻辑

```python
def get_output_path(input_file, input_dir, output_dir, recursive=True, suffix="_md"):
    if not recursive:
        # 扁平模式：所有文件直接放到输出目录
        return output_dir / f"{input_file.stem}.md"
    
    # 递归模式：保持目录结构
    rel_path = input_file.relative_to(input_dir)
    
    # 为每个目录组件添加 _md 后缀
    output_parts = []
    for part in rel_path.parts[:-1]:  # 所有目录部分
        output_parts.append(f"{part}{suffix}")
    
    # 添加文件名
    output_parts.append(f"{input_file.stem}.md")
    
    return output_dir / Path(*output_parts)
```

## 实际使用场景

### 场景 1：技术文档库

```bash
# 输入
docs/
├── API/
│   ├── v1/
│   │   ├── intro.pdf
│   │   └── endpoints.pdf
│   └── v2/
│       └── changelog.pdf
└── guides/
    └── quickstart.pdf

# 命令
nuoyi ./docs --batch -r -o ./markdown

# 输出
markdown/
├── API_md/
│   ├── v1_md/
│   │   ├── intro.md
│   │   └── endpoints.md
│   └── v2_md/
│       └── changelog.md
└── guides_md/
    └── quickstart.md
```

### 场景 2：学术论文集合

```bash
# 输入
papers/
├── 2023/
│   ├── conference/
│   │   └── paper1.pdf
│   └── journal/
│       └── paper2.pdf
└── 2024/
    └── workshop/
        └── paper3.pdf

# Python API
from nuoyi import convert_directory

result = convert_directory("./papers", recursive=True)
```

### 场景 3：多语言文档

```bash
# 输入
documentation/
├── en/
│   ├── user_guide.pdf
│   └── api_ref.pdf
├── zh/
│   ├── user_guide.pdf
│   └── api_ref.pdf
└── ja/
    └── user_guide.pdf

# GUI: 勾选 Recursive 复选框
```

## 验证测试

运行测试脚本验证功能：

```bash
# 测试路径计算逻辑
python test_path_logic.py

# 测试结果
======================================================================
Directory Structure Preservation Test
======================================================================

✓ Created 6 files

--- Output Paths (recursive=True) ---
  overview.pdf                                  -> overview.md
  projects/ProjectA/spec.pdf                    -> projects_md/ProjectA_md/spec.md
  projects/ProjectA/notes.docx                  -> projects_md/ProjectA_md/notes.md
  projects/ProjectA/docs/manual.pdf             -> projects_md/ProjectA_md/docs_md/manual.md
  projects/ProjectB/design.pdf                  -> projects_md/ProjectB_md/design.md
  projects/ProjectB/reports/quarterly.docx      -> projects_md/ProjectB_md/reports_md/quarterly.md

--- Verification ---
  ✓ overview.md
  ✓ projects_md/ProjectA_md/spec.md
  ✓ projects_md/ProjectA_md/docs_md/manual.md
  ✓ projects_md/ProjectB_md/reports_md/quarterly.md

--- Non-recursive Mode ---
  overview.pdf              -> overview.md (flat: ✓)
  spec.pdf                  -> spec.md (flat: ✓)
  ...

✓ SUCCESS: All paths correct with _md suffix!
======================================================================
Result: PASS
======================================================================
```

## 注意事项

### 1. 文件命名冲突

如果不同子目录中有同名文件，它们会被放到不同的 `_md` 目录中，不会冲突：

```
input/A/file.pdf  ->  output/A_md/file.md
input/B/file.pdf  ->  output/B_md/file.md
```

### 2. 图片资源

PDF 中提取的图片会保存在对应输出文件的同级目录：

```
input/docs/manual.pdf  ->  output/docs_md/manual.md
                           output/docs_md/manual_images/
                               ├── image1.png
                               └── image2.png
```

### 3. 性能考虑

- 深层嵌套目录可能较慢
- 大量文件时建议分批处理
- 首次运行需要下载模型（2-3GB）

### 4. 向后兼容

- 默认 `recursive=False`，保持原有行为
- 现有脚本无需修改
- GUI 复选框默认未选中

## 常见问题

**Q: 如何只转换特定子目录？**  
A: 直接指定该子目录为输入目录，或使用文件过滤功能。

**Q: 可以自定义 `_md` 后缀吗？**  
A: 当前版本固定为 `_md`，未来版本可能支持自定义。

**Q: 输出目录已存在怎么办？**  
A: 会自动创建 `_md` 子目录，不会覆盖现有文件。

**Q: 如何查看转换进度？**  
A: CLI 会显示每个文件的处理状态，GUI 有进度条显示。

## 更新日志

### v0.3.0 (当前版本)

- ✅ 新增递归目录扫描功能
- ✅ 保持输入目录结构
- ✅ 自动添加 `_md` 后缀
- ✅ CLI、API、GUI 全面支持
- ✅ 完整测试覆盖

---

**开发团队**: NuoYi Team  
**许可**: GPL-3.0-or-later
