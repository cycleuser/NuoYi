# 立即可用的完整命令

## 你的情况

GPU: RTX 4060, 7.6GB VRAM
文件数: 44315个PDF
已有转换: 大部分已完成

## 必须使用的完整命令

```bash
nuoyi /home/fred/Documents/参考文献/arXiv_45000/pdfs/arxiv \
  --batch \
  --device cuda \
  --low-vram \
  --batch-size-1 \
  --existing-files skip \
  --output /home/fred/Documents/参考文献/arXiv_45000/markdown
```

**所有参数必须加上！少一个都会OOM！**

## 参数说明

```bash
--batch              # 批量处理模式（必须）
--device cuda        # 使用GPU（必须）
--low-vram           # CPU-first策略，模型在CPU（必须！）
--batch-size-1       # batch_size=1，最小显存占用（必须！）
--existing-files skip  # 跳过已存在文件（节省时间）
--output ...         # 输出目录
```

## 预期日志

```
[Memory] Creating offloaded models (layout GPU, OCR CPU)
[Memory] Batch sizes: layout=1, ocr=1 (minimal VRAM mode)
[Memory] Layout model: cuda (torch.float16)
[Memory] OCR models: cpu (offloaded)
[Memory] Models loaded: 1.3GB used, 1.3GB reserved  # 不是3.2GB！
```

## 如果还是OOM

```bash
# 使用pymupdf（无OCR，极快，无GPU）
nuoyi /home/fred/Documents/参考文献/arXiv_45000/pdfs/arxiv \
  --batch \
  --engine pymupdf \
  --existing-files skip \
  --output /home/fred/Documents/参考文献/arXiv_45000/markdown
```

**速度极快（每个文件几秒），但无公式识别！**