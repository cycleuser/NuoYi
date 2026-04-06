# 快速解决您的OOM问题

## 🚨 立即可用的解决方案

您有44315个数字PDF文件需要处理，当前遇到显存不足问题。

### ✅ 推荐方案：使用 PyMuPDF 引擎

**最适合您的情况**：
- ✅ 数字PDF（有嵌入文本）
- ✅ 零GPU占用
- ✅ 处理速度极快
- ✅ 不会OOM

**立即执行**：
```bash
cd ~/Documents/参考文献/arXiv_45000/pdfs/arxiv

# 批量处理所有PDF
nuoyi . --batch --recursive --engine pymupdf -o ./markdown_output
```

### 📊 性能对比

| 指标 | marker引擎 | pymupdf引擎 |
|------|-----------|-------------|
| 显存占用 | 3-4GB | **0GB** |
| 处理速度 | 慢 | **极快** |
| 适合文档 | 混合/扫描版 | **数字版** |
| OOM风险 | **高** | **无** |

### 🔧 如果必须使用marker引擎

#### 方案A：使用集成显卡显示（推荐）

```bash
# 运行GPU切换脚本
bash switch_gpu.sh

# 选择选项1：使用集成显卡显示
# 注销后生效
# 这样NVIDIA显卡完全用于计算，释放0.5-1GB显存

# 然后使用low-vram模式
nuoyi . --batch --recursive --engine marker --low-vram
```

#### 方案B：限制GPU显存使用

```bash
# 设置环境变量
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,max_split_size_mb:32"

# 使用low-vram模式
nuoyi . --batch --recursive --engine marker --low-vram
```

## 🎯 智能转换脚本

我为您创建了一个智能脚本，自动检测PDF类型并选择最佳引擎：

```bash
# 使用智能转换脚本
python auto_convert.py ~/Documents/参考文献/arXiv_45000/pdfs/arxiv

# 脚本会自动：
# 1. 检测PDF是数字版还是扫描版
# 2. 数字版 -> 使用pymupdf（快速、无GPU）
# 3. 扫描版 -> 使用marker（带OCR、low-vram）
```

## 📝 总结

**对于您的44315个数字PDF**：

1. **首选命令**（零GPU，最快）：
   ```bash
   nuoyi . --batch --recursive --engine pymupdf
   ```

2. **次选方案**（如果需要OCR）：
   ```bash
   # 先切换到集成显卡显示
   bash switch_gpu.sh  # 选择选项1
   
   # 注销后重新登录
   # 然后使用marker引擎
   nuoyi . --batch --recursive --engine marker --low-vram
   ```

3. **智能方案**（自动选择）：
   ```bash
   python auto_convert.py ~/Documents/参考文献/arXiv_45000/pdfs/arxiv
   ```

## ⚠️ 重要提示

- `--disable-ocr-models` 参数在marker-pdf中**无法完全禁用OCR**，因为marker会根据内容自动判断
- 对于数字PDF，直接使用 `--engine pymupdf` 更高效
- 如果使用集成显卡显示，可以释放独显的全部显存用于计算

---

**立即开始转换**：
```bash
cd ~/Documents/参考文献/arXiv_45000/pdfs/arxiv
nuoyi . --batch --recursive --engine pymupdf -o ./markdown_output
```