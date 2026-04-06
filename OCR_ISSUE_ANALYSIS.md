# OCR仍在执行的原因分析

## 问题

用户设置了`--disable-ocr-models`，但marker还是在执行OCR：
```
Recognizing Text:   0%|                                                    | 0/97 [
```

## 根本原因

**marker判定页面需要OCR的逻辑：**

1. **LineBuilder** (`marker/builders/line.py:200-208`)：
```python
# 检查页面文本质量
if has_good_text:
    document_page.text_extraction_method = "pdftext"
else:
    document_page.text_extraction_method = "surya"  # 需要OCR
```

2. **OcrBuilder** (`marker/builders/ocr.py:83`)：
```python
# 只处理标记为'surya'的页面
pages_to_ocr = [page for page in document.pages 
                if page.text_extraction_method == 'surya']
```

**问题所在：**
- `disable_ocr_models`只是不加载OCR模型
- 但没有告诉marker跳过OCR判断
- PDF文本质量差时，marker还是会标记为需要OCR
- OCR builder会尝试执行OCR（即使模型在CPU或不完整）

## 解决方案

### 方案1：告诉marker不要OCR（推荐）

**在NuoYi的converter.py中，传递force_ocr=False并添加配置：**

```python
# 创建PdfProvider时传递参数
provider_config = {
    "force_ocr": False,  # 不强制OCR
    # 其他OCR检测参数，放宽判断标准
    "ocr_space_threshold": 1.0,  # 放宽空格阈值
    "ocr_newline_threshold": 1.0,  # 放宽换行阈值
    "ocr_alphanum_threshold": 0.0,  # 放宽字母数字阈值
}
```

### 方案2：完全跳过OcrBuilder（激进）

**修改artifact_dict，不提供recognition_model：**

```python
if self.disable_ocr_models:
    # 完全不提供OCR模型
    model_dict = {
        "layout_model": ...,
        # 不提供 "recognition_model"
    }
```

**问题：** marker可能会报错。

### 方案3：使用pdftext模式（最简单）

**直接告诉marker使用pdftext，不要surya：**

通过设置provider的配置，让所有页面都标记为pdftext。

## 快速测试

**检查PDF是否真的需要OCR：**

```bash
# 用pypdfium2检查PDF是否有文本
python3 << 'EOF'
import pypdfium2 as pdfium
pdf_path = "your.pdf"
doc = pdfium.PdfDocument(pdf_path)
page = doc.get_page(0)
text_objects = list(page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_TEXT]))
print(f"Page has {len(text_objects)} text objects")
if len(text_objects) > 0:
    print("PDF has embedded text - should NOT need OCR")
else:
    print("PDF is image-based - needs OCR")
EOF
```

## 正确的使用方式

**纯数字PDF（不需要OCR）：**
```bash
nuoyi ./papers --batch --device cuda --low-vram
# 不要用 --disable-ocr-models
# 让marker自己判断是否需要OCR
```

**如果marker误判，可以：**
1. 调整OCR检测参数（修改provider配置）
2. 使用force_ocr=False明确告诉marker不要OCR

## 临时解决方案

**如果确定PDF是纯数字的，可以：**

1. 不使用`--disable-ocr-models`
2. 只使用`--low-vram`
3. 让marker自己判断

或者：

1. 修改NuoYi，传递更宽松的OCR检测参数
2. 或者完全禁用OCR builder（需要修改marker代码）

## 总结

**`disable_ocr_models`的问题：**
- ✅ 确实不加载OCR模型
- ❌ 但marker还是会判断页面是否需要OCR
- ❌ OCR builder还是会执行（使用CPU模型）

**正确的做法：**
- 不要用`disable_ocr_models`
- 只用`--low-vram`
- 或者传递配置告诉marker不要OCR（需要代码修改）