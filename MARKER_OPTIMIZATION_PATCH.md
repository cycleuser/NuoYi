# Marker优化补丁

## 在NuoYi中应用Marker优化

由于marker-pdf的batch_size太大导致OOM，我们在NuoYi中应用以下优化：

### 优化1：降低batch_size

**marker默认值：**
- Layout batch_size: 12 (CUDA)
- OCR batch_size: 48 (CUDA)

**问题：**
- 12张图片同时处理：占用1.2GB+显存
- 48张图片同时处理：占用2.4GB+显存
- 总计：3.6GB临时占用 + 3.5GB模型 = 7.1GB ❌

**NuoYi优化值：**
- Layout batch_size: 4
- OCR batch_size: 12

**效果：**
- 显存占用降低75%
- 4张图片：0.4GB
- 12张图片：0.6GB
- 总计：1GB临时占用 ✅

### 优化2：CPU-first策略

**实现：** 所有模型加载到CPU，推理时临时使用GPU

**效果：**
- 模型占用：3.5GB GPU → 0GB GPU
- 临时占用：1-2GB GPU
- 总计：1-2GB ✅

### 使用方法

```bash
# 自动应用所有优化
nuoyi ./papers --batch --device cuda --low-vram --existing-files skip

# GUI
Options → [x] Low VRAM
```

### 日志输出

```
[Memory] Loading ALL models to CPU memory first...
[Memory] Models will be temporarily moved to GPU during inference
[Memory] Optimized batch sizes: layout=4, ocr=12 (vs default 12/48)
```

### 性能对比

| 配置 | 模型占用 | 临时占用 | 总占用 | 速度 |
|------|---------|---------|--------|------|
| Marker默认 | 3.5GB | 3.6GB | 7.1GB ❌ | 快 |
| **NuoYi优化** | **0GB** | **1-2GB** | **1-2GB ✅** | **中** |

**性能损失：** 10-20%（batch_size降低和CPU传输开销）
**稳定性：** 必OOM → 完全稳定