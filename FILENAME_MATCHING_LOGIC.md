# 文件名相同判断逻辑说明

## 实现原理

**文件名相同指的是主文件名相同，不包括扩展名**

### 示例

| 输入文件 | 主文件名(stem) | 输出文件 | 判断结果 |
|---------|---------------|---------|---------|
| `paper.pdf` | `paper` | `paper.md` | 相同 |
| `paper.docx` | `paper` | `paper.md` | 相同 |
| `document.pdf` | `document` | `document.md` | 相同 |
| `thesis.pdf` | `thesis` | `thesis.md` | 相同 |
| `thesis.docx` | `thesis` | `thesis.md` | 相同 |

**关键：** `paper.pdf` 和 `paper.docx` 会输出到同一个 `paper.md`，因为它们的主文件名相同。

## 代码实现

### 1. 提取主文件名

```python
from pathlib import Path

input_file = Path('/home/fred/Documents/papers/-Qing_2002_Hawking_Radiation_of_arXiv-gr-qc-0204005.pdf')
stem = input_file.stem  # 不带扩展名的文件名
# 结果: '-Qing_2002_Hawking_Radiation_of_arXiv-gr-qc-0204005'
```

### 2. 生成输出路径

```python
def get_output_path(input_file: Path, input_dir: Path, output_dir: Path) -> Path:
    return output_dir / f"{input_file.stem}.md"
```

**示例：**
```python
input_file = Path('/home/fred/Documents/参考文献/arXiv_45000/pdfs/arxiv/-Qing_2002_Hawking_Radiation_of_arXiv-gr-qc-0204005.pdf')
output_dir = Path('/home/fred/Documents/参考文献/arXiv_45000/markdown')

out_path = get_output_path(input_file, input_dir, output_dir)
# 结果: '/home/fred/Documents/参考文献/arXiv_45000/markdown/-Qing_2002_Hawking_Radiation_of_arXiv-gr-qc-0204005.md'
```

### 3. 检查文件是否存在

```python
if out_path.exists():
    # 输出文件已存在，根据策略决定是否跳过
    if existing_files == "skip":
        print("Skipping (already exists)")
        continue
```

## 实际场景

### 场景1：PDF和DOCX同时存在

```
输入目录:
├── paper.pdf
└── paper.docx

输出目录（已有）:
└── paper.md
```

**处理逻辑：**
1. 检查 `paper.pdf` → 输出 `paper.md` → 发现已存在
2. 根据策略决定跳过/覆盖/更新
3. 检查 `paper.docx` → 输出 `paper.md` → 发现已存在
4. 再次根据策略决定

### 场景2：递归目录结构

```
输入目录:
├── chapter1/
│   ├── intro.pdf
│   └── background.pdf
└── chapter2/
    └── method.pdf

输出目录:
├── chapter1_md/
│   ├── intro.md
│   └── background.md
└── chapter2_md/
    └── method.md
```

**递归模式：**
```python
get_output_path(input_file, input_dir, output_dir, recursive=True)
# chapter1/intro.pdf -> chapter1_md/intro.md
# chapter2/method.pdf -> chapter2_md/method.md
```

## 文件名处理细节

### stem vs name vs suffix

```python
file = Path('/path/to/paper.pdf')

file.name   # 'paper.pdf'      - 完整文件名
file.stem   # 'paper'          - 主文件名（无扩展名）
file.suffix # '.pdf'           - 扩展名（包含点）
```

### 多个点的文件名

```python
file = Path('/path/to/paper.v2.final.pdf')

file.stem   # 'paper.v2.final' - 主文件名
file.suffix # '.pdf'           - 最后一个扩展名
```

### 无扩展名的文件

```python
file = Path('/path/to/README')

file.stem   # 'README'
file.suffix # ''
```

## 测试验证

### 测试1：相同主文件名

```python
from nuoyi.utils import get_output_path
from pathlib import Path

input_dir = Path('/input')
output_dir = Path('/output')

pdf = input_dir / 'thesis.pdf'
docx = input_dir / 'thesis.docx'

pdf_out = get_output_path(pdf, input_dir, output_dir)
docx_out = get_output_path(docx, input_dir, output_dir)

assert pdf_out == docx_out  # 相同！
assert pdf_out.name == 'thesis.md'
```

### 测试2：不同主文件名

```python
pdf1 = input_dir / 'paper1.pdf'
pdf2 = input_dir / 'paper2.pdf'

out1 = get_output_path(pdf1, input_dir, output_dir)
out2 = get_output_path(pdf2, input_dir, output_dir)

assert out1 != out2  # 不同
assert out1.name == 'paper1.md'
assert out2.name == 'paper2.md'
```

### 测试3：复杂文件名

```python
pdf = input_dir / '-Qing_2002_Hawking_Radiation_of_arXiv-gr-qc-0204005.pdf'
out = get_output_path(pdf, input_dir, output_dir)

assert out.name == '-Qing_2002_Hawking_Radiation_of_arXiv-gr-qc-0204005.md'
```

## 使用建议

### 1. 批量转换PDF和DOCX混合目录

```bash
nuoyi ./documents --batch --existing-files skip
```

**效果：**
- `paper.pdf` → `paper.md`（如果已存在则跳过）
- `paper.docx` → `paper.md`（会覆盖或跳过，取决于哪个先处理）

**建议：** 如果PDF和DOCX内容相同，建议只用一个格式，或分别处理到不同目录。

### 2. 分别处理PDF和DOCX

```bash
# 只处理PDF
nuoyi ./pdfs --batch --output ./markdown_pdf

# 只处理DOCX
nuoyi ./docxs --batch --output ./markdown_docx
```

### 3. 使用递归模式保留目录结构

```bash
nuoyi ./papers --batch --recursive --existing-files update
```

## 核心代码位置

- **get_output_path函数**：`src/nuoyi/utils.py:1384`
- **文件存在检测**：`src/nuoyi/api.py:325`
- **跳过/覆盖/更新逻辑**：`src/nuoyi/api.py:326-402`

## 总结

✅ **已正确实现：**
- 文件名相同 = 主文件名相同（不包括扩展名）
- `paper.pdf` 和 `paper.docx` 都输出到 `paper.md`
- 使用 `Path.stem` 获取主文件名
- 检测逻辑在转换前执行，避免浪费

✅ **符合预期：**
- `-Qing_2002_Hawking_Radiation_of_arXiv-gr-qc-0204005.pdf` → `-Qing_2002_Hawking_Radiation_of_arXiv-gr-qc-0204005.md`
- 支持 `--existing-files skip/update/overwrite/ask` 参数
- GUI和CLI都支持此功能