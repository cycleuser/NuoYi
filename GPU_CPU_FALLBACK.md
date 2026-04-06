# GPU自动降级+清空显存机制

## 工作流程

```
文件1: GPU处理 → 成功 ✓
文件2: GPU处理 → 成功 ✓  
文件3: GPU处理 → OOM → 清空GPU显存 → CPU处理 → 成功 ✓
文件4: GPU处理 → 成功 ✓ (显存已清空，重新开始)
文件5: GPU处理 → 成功 ✓
```

## 核心改进

### 1. GPU失败立即清空显存

```python
if "CUDA OOM" in error_msg:
    print("[Batch] CUDA OOM detected")
    print("[Batch] Clearing GPU memory...")
    
    # 清空转换器缓存
    clear_converter_cache()
    
    # 垃圾回收
    import gc
    gc.collect()
    
    # 清空CUDA缓存 + 强制同步
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    print("[Batch] GPU memory cleared")
    
    # 然后用CPU处理这个文件
    r = convert_file(..., device="cpu")
```

### 2. 下一个文件继续GPU

```python
# CPU fallback完成后，下一个文件自动用GPU
for i, f in enumerate(files):
    # 这里device还是原来的"cuda"
    r = convert_file(..., device=device)  # 继续GPU
```

## 日志输出示例

```
[Batch] 1/100: simple.pdf
[Batch] ✓ simple.pdf

[Batch] 2/100: complex.pdf  
[Batch] ✗ complex.pdf: CUDA OOM
[Batch] Attempting CPU fallback...
[Batch] GPU memory cleared
[Batch] ✓ complex.pdf (CPU fallback)

[Batch] 3/100: next.pdf
[Batch] ✓ next.pdf  ← 显存已清空，GPU重新开始

[Batch] 4/100: another_complex.pdf
[Batch] ✗ another_complex.pdf: CUDA OOM
[Batch] Attempting CPU fallback...
[Batch] GPU memory cleared
[Batch] ✓ another_complex.pdf (CPU fallback)
```

## 优势

### 1. 最大化GPU利用

- 简单文件（80%）用GPU快速处理
- 复杂文件（20%）自动CPU兜底
- 每次失败清空显存，下一个重新开始

### 2. 公式和图片完美保留

- GPU和CPU都用marker-pdf
- 公式识别完整
- 图片智能裁切保留
- OCR功能保留

### 3. 无需用户干预

- 自动检测OOM
- 自动清空显存
- 自动切换CPU
- 下个文件自动恢复GPU

## 性能分析

**假设100个PDF：**
- 80个简单PDF：GPU处理，每个2分钟
- 20个复杂PDF：GPU OOM → CPU，每个20分钟

**总时间：**
- GPU成功：80 × 2 = 160分钟
- CPU降级：20 × 20 = 400分钟
- **总计：560分钟**

**对比纯CPU：**
- 100 × 20 = 2000分钟
- **节省72%时间**

## 显存管理细节

### 为什么每次失败都要清空？

1. **防止累积**：复杂PDF可能占用大量显存，不清空会影响下一个
2. **重新开始**：清空后下一个文件有完整的显存可用
3. **避免连锁失败**：不清空可能导致连续OOM

### 为什么用synchronize()？

```python
torch.cuda.empty_cache()  # 异步标记清理
torch.cuda.synchronize()  # 强制等待完成
```

- `empty_cache()`只是标记要清理，不保证立即完成
- `synchronize()`强制等待GPU完成所有操作
- 组合使用确保显存真正释放

### 为什么清除converter缓存？

```python
clear_converter_cache()  # 删除缓存的转换器实例
```

- 转换器实例可能持有GPU内存引用
- 删除后重新创建，确保干净状态
- CPU模式用完后，下一个GPU模式重新创建

## 监控和调试

### 实时监控

```bash
# 终端1：运行转换
nuoyi ./papers --batch --device cuda

# 终端2：监控GPU
watch -n 1 nvidia-smi
```

### 关键指标

- **Memory-Usage**：已用显存
- **Memory-Usage跳动**：清空显存后应该下降
- **GPU-Util**：GPU利用率（GPU处理时高，CPU处理时低）

### 预期行为

```
文件1: 显存3.2GB → GPU处理 → 显存释放到1.5GB
文件2: 显存3.0GB → GPU处理 → 显存释放到1.5GB  
文件3: 显存尝试3.5GB → OOM → 清空到0.5GB → CPU处理
文件4: 显存2.8GB → GPU处理（从干净状态开始）
```

## 异常情况处理

### 情况1：CPU也失败

```
[Batch] ✗ file.pdf: CUDA OOM
[Batch] GPU memory cleared
[Batch] ✗ file.pdf: CPU fallback failed - corrupted PDF
```

- 记录失败文件
- 继续处理下一个
- 最后汇总失败列表

### 情况2：连续GPU OOM

```
[Batch] ✗ file1.pdf: CUDA OOM → CPU fallback ✓
[Batch] ✗ file2.pdf: CUDA OOM → CPU fallback ✓
[Batch] ✗ file3.pdf: CUDA OOM → CPU fallback ✓
```

- 连续3个OOM可能说明显存不足
- 考虑改用`--low-vram`模式
- 或者`--device cpu`纯CPU模式

## 最佳实践

### 1. 首次运行

```bash
nuoyi ./papers --batch --device cuda --existing-files update
```

- 自动GPU→CPU降级
- 自动清空显存
- 记录哪些文件CPU处理

### 2. 如果大量OOM

```bash
nuoyi ./papers --batch --device cuda --low-vram --existing-files update
```

- OCR模型放CPU
- 显存占用降到1.5GB
- 减少OOM概率

### 3. 分批处理

```bash
for i in {1..10}; do
    nuoyi ./batch_$i --batch --device cuda --existing-files update
    sleep 30  # 给GPU喘息时间
done
```

## 技术实现位置

- **自动降级逻辑**：`src/nuoyi/api.py` 的 `convert_directory` 函数
- **显存清理**：OOM时调用 `torch.cuda.empty_cache()` + `synchronize()`
- **转换器缓存清理**：调用 `clear_converter_cache()`
- **垃圾回收**：调用 `gc.collect()`

这个机制确保了GPU的最大化利用，同时保证了公式识别和图片裁切的质量。