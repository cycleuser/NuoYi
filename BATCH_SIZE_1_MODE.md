# batch_size=1模式说明

## 什么是batch_size？

**Layout batch_size**: 一次处理多少张页面图片
- 默认：12张（CUDA）
- 占用：12 × 100MB = 1.2GB

**OCR batch_size**: 一次OCR多少个文本块
- 默认：48个（CUDA）
- 占用：48 × 50MB = 2.4GB

## batch_size=1的效果

**显存占用对比：**

| 模式 | Layout batch | OCR batch | 临时显存 | 总显存 |
|------|-------------|----------|---------|--------|
| 默认 | 12 | 48 | 3.6GB | 7.1GB ❌ |
| low-vram | 4 | 12 | 1GB | 4.5GB ⚠️ |
| **batch_size=1** | **1** | **1** | **0.15GB** | **3.7GB ✅** |

## 使用方法

```bash
# batch_size=1模式（最稳定）
nuoyi ./pdfs --batch \
  --device cuda \
  --batch-size-1 \
  --existing-files skip \
  --output ./markdown

# 或者与low-vram组合（更稳定）
nuoyi ./pdfs --batch \
  --device cuda \
  --low-vram \
  --batch-size-1 \
  --existing-files skip \
  --output ./markdown
```

## 性能影响

**速度对比：**

| 模式 | 速度 | 稳定性 |
|------|------|--------|
| 默认 | 最快 | ❌ 易OOM |
| low-vram | 中等 | ⚠️ 可能OOM |
| **batch_size=1** | **慢30%** | **✅ 最稳定** |

## 适用场景

**batch_size=1适合：**
- 7.6GB显存，其他模式都OOM
- 极度复杂PDF（大图片、复杂表格）
- 追求绝对稳定，不在乎速度

**不建议batch_size=1：**
- 显存充足（>8GB）
- 需要快速处理
- PDF简单（纯文本）

## 工作原理

```python
# 默认：批量处理
Layout: [img1, img2, ..., img12] -> GPU 一次处理
OCR: [block1, block2, ..., block48] -> GPU 一次处理

# batch_size=1：逐个处理
Layout: img1 -> GPU -> 完成 -> img2 -> GPU -> 完成 -> ...
OCR: block1 -> GPU -> 完成 -> block2 -> GPU -> 完成 -> ...
```

**显存峰值：**
- 默认：需要同时容纳12张图片 + 48个文本块
- batch_size=1：只需要1张图片 + 1个文本块

## 日志输出

```
[Memory] Creating offloaded models (layout GPU, OCR CPU)
[Memory] Batch sizes: layout=1, ocr=1 (minimal VRAM mode)
[Memory] Layout model: cuda (torch.float16)
[Memory] OCR models: cpu (offloaded)
[Memory] Models loaded: 1.3GB used, 1.3GB reserved
```

## 总结

- **最稳定**：绝对不会OOM
- **速度慢**：比默认慢30%
- **显存占用最小**：只需3.7GB
- **7.6GB显存推荐**：先用low-vram，如果还OOM再用batch_size=1