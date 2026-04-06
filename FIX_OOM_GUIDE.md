# 解决显存不足问题 - 完整指南

## 问题分析

您的系统配置：
- NVIDIA 独立显卡：7.6GB VRAM
- AMD 610M 集成显卡
- 需要处理：44315个数字PDF文件
- 当前问题：独立显卡显存不足导致OOM

## 最佳解决方案

### 方案1：使用 PyMuPDF 引擎（推荐）✅

**最适合您的场景**：44315个数字PDF，无需OCR

```bash
# 批量处理数字PDF（快速、无GPU、无OCR）
nuoyi ./pdfs --batch --engine pymupdf

# 递归处理
nuoyi ./pdfs --batch --recursive --engine pymupdf
```

**优势**：
- ✅ 不使用GPU，零显存占用
- ✅ 处理速度极快
- ✅ 适合数字PDF（带嵌入文本）
- ✅ 可处理44315个文件而不OOM

**何时不用**：
- ❌ 扫描版PDF（需要OCR）
- ❌ 复杂表格PDF

### 方案2：强制使用集成显卡显示

让桌面使用AMD 610M，完全释放NVIDIA显卡用于计算：

#### Ubuntu系统设置：

```bash
# 方法1：使用 prime-select（NVIDIA驱动）
sudo prime-select intel  # 使用集成显卡显示
# 注销后生效

# 方法2：环境变量强制（临时）
__NV_PRIME_RENDER_OFFLOAD=1 \
__GLX_VENDOR_LIBRARY_NAME=nvidia \
nuoyi file.pdf --device cuda

# 查看当前显卡使用情况
nvidia-smi
```

#### BIOS设置：

1. 重启进入BIOS
2. 找到显卡设置（Graphics Settings）
3. 设置为"Integrated Graphics"（集成显卡）
4. 保存并重启

### 方案3：智能引擎选择（推荐脚本）

```bash
#!/bin/bash
# auto_convert.sh - 自动选择最佳引擎

PDF_DIR="$1"

# 检测是否为扫描版PDF
is_scanned() {
    local pdf="$1"
    # 如果PDF文字少于50字符，认为是扫描版
    text=$(pdftotext "$pdf" - 2>/dev/null | wc -c)
    [ "$text" -lt 50 ]
}

# 处理单个文件
process_file() {
    local pdf="$1"
    
    if is_scanned "$pdf"; then
        echo "扫描版PDF，使用marker引擎: $pdf"
        nuoyi "$pdf" --engine marker --low-vram
    else
        echo "数字版PDF，使用pymupdf引擎: $pdf"
        nuoyi "$pdf" --engine pymupdf
    fi
}

# 批量处理
find "$PDF_DIR" -name "*.pdf" -type f | while read pdf; do
    process_file "$pdf"
done
```

## 性能对比

| 引擎 | VRAM占用 | 速度 | 适用场景 |
|------|----------|------|----------|
| **pymupdf** | 0GB | ⭐⭐⭐⭐⭐ | 数字PDF |
| **pdfplumber** | 0GB | ⭐⭐⭐⭐ | 数字PDF+表格 |
| **marker** (low-vram) | ~3GB | ⭐⭐⭐ | 混合PDF |
| **marker** (full) | ~4GB | ⭐⭐⭐ | 扫描PDF |

## 针对您的情况

### 推荐命令：

```bash
# 方案A：全部使用pymupdf（最快）
nuoyi ./pdfs --batch --recursive --engine pymupdf

# 方案B：混合处理（智能选择）
# 先用pymupdf处理所有文件
nuoyi ./pdfs --batch --recursive --engine pymupdf -o ./output

# 然后检查失败或质量差的文件
# 用marker重新处理这些文件
nuoyi ./failed_pdfs.txt --batch --engine marker --low-vram
```

### 如果必须使用marker引擎：

```bash
# 设置环境变量，限制GPU使用
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,max_split_size_mb:32"

# 使用low-vram模式
nuoyi ./pdfs --batch --engine marker --low-vram --device cuda
```

## 检查系统显卡配置

```bash
# 查看GPU使用情况
nvidia-smi

# 查看哪个GPU在显示
glxinfo | grep "OpenGL renderer"

# 如果显示NVIDIA，说明独显用于显示
# 切换到集成显卡显示可以释放约0.5-1GB显存
```

## 常见问题

### Q: 如何判断PDF是数字版还是扫描版？
```bash
# 方法1：使用pdftotext检查文字量
pdftotext file.pdf - | wc -c
# 输出<100通常是扫描版

# 方法2：查看PDF元数据
pdfinfo file.pdf | grep "Page size"
# 如果是图片分辨率（如2480x3508），可能是扫描版
```

### Q: 为什么disable-ocr-models不起作用？
A: marker-pdf的架构会根据PDF内容自动决定是否需要OCR，无法完全禁用。对于数字PDF，直接使用pymupdf引擎更高效。

### Q: 如何批量转换44315个文件？
```bash
# 使用GNU parallel并行处理
find ./pdfs -name "*.pdf" | \
  parallel -j 4 nuoyi {} --engine pymupdf

# 或者分批处理
nuoyi ./pdfs --batch --engine pymupdf --recursive 2>&1 | tee conversion.log
```

## 总结建议

**对于您的44315个数字PDF文件**：

1. ✅ **首选**：`nuoyi ./pdfs --batch --recursive --engine pymupdf`
   - 零GPU占用
   - 最快速度
   - 无OOM风险

2. 🔄 **备选**：设置集成显卡显示 + marker引擎
   - 释放独显全部显存
   - 可处理扫描版PDF

3. 📊 **智能方案**：编写脚本检测PDF类型，自动选择引擎

---

**立即执行**：
```bash
cd ~/Documents/参考文献/arXiv_45000/pdfs/arxiv
nuoyi . --batch --recursive --engine pymupdf -o ./markdown_output
```