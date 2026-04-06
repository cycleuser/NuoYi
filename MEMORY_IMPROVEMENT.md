# Marker-PDF 内存优化方案

## 核心优势保持

**marker-pdf能做到：**
- 公式识别：自动识别LaTeX公式并转换为可渲染的Markdown
- 图片智能裁切：自动提取图片，裁剪空白区域，优化尺寸
- OCR：扫描版PDF也能处理
- 表格识别：复杂表格也能正确转换

**这些都是必须的功能，不能用pymupdf替代。**

## OOM问题根本原因

1. **GPU内存累积**：多个文件处理后内存没清理干净
2. **复杂PDF差异**：不同PDF需要的临时内存差异很大
3. **模型缓存**：转换器缓存导致内存持续占用

## 已实施的改进方案

### 1. 自动CPU降级机制

当CUDA OOM时，自动切换到CPU继续处理：

```python
# 在api.py中实现
if "CUDA OOM" in error_msg:
    print("[Batch] Attempting fallback to CPU...")
    r = convert_file(..., device="cpu", use_cache=False)
```

**优点：**
- 保证公式识别和图片裁切不丢失
- GPU失败时CPU兜底
- 用户不需要手动干预

### 2. 更激进的内存清理

```python
# 每5个文件清理GPU缓存
if i % 5 == 0:
    torch.cuda.empty_cache()
    torch.cuda.synchronize()  # 强制同步，确保清理完成

# 每10个文件清理转换器缓存
if i % 10 == 0:
    gc.collect()
    clear_converter_cache()
```

### 3. 批处理完成后深度清理

```python
clear_converter_cache()
gc.collect()
torch.cuda.empty_cache()
torch.cuda.synchronize()
```

## 推荐使用策略

### 方案A：自动降级模式（推荐）

```bash
nuoyi ./papers --batch --device cuda --existing-files update
```

- 先用GPU处理，速度快
- OOM自动切换CPU
- 公式和图片完美保留
- 用户无需手动切换

### 方案B：智能混合模式（需添加）

**未来可添加：根据文件大小预判**
```python
# 检测PDF页数和大小
page_count = get_pdf_page_count(f)
file_size = f.stat().st_size

# 大文件预判用CPU
if page_count > 50 or file_size > 20MB:
    device = "cpu"
else:
    device = "cuda"
```

### 方案C：低显存优化模式

```bash
nuoyi ./papers --batch --device cuda --low-vram
```

- 使用FP16量化
- 减小batch size
- 模型分段加载
- 公式识别和图片裁切保留

### 方案D：纯数字PDF优化

```bash
nuoyi ./papers --batch --disable-ocr-models
```

- 禁用OCR模型（省1.5GB VRAM）
- 只适合纯数字文本PDF
- 公式识别和图片裁切保留
- 扫描版PDF不能用

## 性能对比

| 方案 | 公式识别 | 图片裁切 | OCR | 速度 | 显存占用 |
|------|---------|---------|-----|------|---------|
| GPU自动降级 | ✓ 完美 | ✓ 完美 | ✓ | 快 | 3-4GB |
| CPU模式 | ✓ 完美 | ✓ 完美 | ✓ | 慢10倍 | 0GB |
| 低VRAM模式 | ✓ 完美 | ✓ 完美 | ✓ | 中 | 2GB |
| disable-ocr | ✓ 完美 | ✓ 完美 | ✗ | 快 | 1.5GB |
| pymupdf | ✗ 无 | ✗ 简单 | ✗ | 极快 | 0GB |

## 实际建议

**44315个PDF批量转换推荐策略：**

```bash
# 第一次尝试：GPU自动降级
nuoyi ./papers --batch --device cuda --existing-files update

# 如果仍有大量OOM，启用低VRAM模式
nuoyi ./papers --batch --device cuda --low-vram --existing-files update

# 如果纯数字PDF为主，禁用OCR模型
nuoyi ./papers --batch --device cuda --disable-ocr-models --existing-files update

# 如果GPU实在不够用，全部用CPU（慢但稳定）
nuoyi ./papers --batch --device cpu --existing-files update
```

## 内存管理最佳实践

1. **每处理100个文件重启一次**：防止内存泄漏累积
2. **关闭其他GPU程序**：释放更多显存
3. **监控GPU内存**：`nvidia-smi -l 1` 实时监控
4. **分批处理**：分成多个小批次，每批5000个文件
5. **保存进度**：`--existing-files update` 避免重复处理

## 技术细节

**marker-pdf公式识别原理：**
- 使用surya模型识别公式区域
- 提取LaTeX代码
- 转换为可渲染的Markdown公式

**图片智能裁切原理：**
- 检测图片边界框
- 裁剪空白边缘
- 优化分辨率和尺寸
- 保存为PNG/JPEG

**这些都是marker-pdf的核心优势，不能放弃。**