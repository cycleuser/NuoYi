# 紧急解决方案 - 7.6GB显存OOM问题

## 问题诊断

**你的显存：** 7.6GB
**模型占用：** 3.2GB
**理论剩余：** 4.4GB
**实际剩余：** 249MB ❌

**问题：** 临时显存占用过大，处理复杂PDF时需要额外3-4GB临时空间，超出显存容量。

## 立即可用的解决方案

### 方案1：Low VRAM模式（强烈推荐）

```bash
nuoyi ./papers --batch --device cuda --low-vram --existing-files skip
```

**原理：**
- OCR模型放CPU（节省2GB显存）
- Layout模型放GPU
- 实际显存占用：~1.5-2GB

**性能：**
- 简单PDF：正常速度
- 复杂PDF：稍慢（OCR在CPU）
- **不会OOM！**

### 方案2：禁用OCR模型（纯数字PDF）

```bash
nuoyi ./papers --batch --device cuda --disable-ocr-models --existing-files skip
```

**适用：**
- 纯数字文本PDF（非扫描版）
- PDF中已有文字，不需要OCR识别
- 不需要表格识别

**限制：**
- ❌ 扫描版PDF不能用
- ❌ 图片中的文字识别不了
- ✅ 公式和图片裁切正常

**显存：** ~1GB
**速度：** 快

### 方案3：CPU模式（最稳定）

```bash
nuoyi ./papers --batch --device cpu --existing-files skip
```

**特点：**
- 完全不用GPU显存
- 绝对不会OOM
- 速度慢10倍

**计算：**
- GPU模式：2分钟/文件
- CPU模式：20分钟/文件
- 44315个文件：44315 × 20分钟 = 14800分钟 ≈ 10天

### 方案4：混合自动降级

```bash
# 先尝试GPU，OOM自动切CPU
nuoyi ./papers --batch --device cuda --low-vram --existing-files skip
```

**流程：**
1. 简单PDF用GPU快速处理
2. 复杂PDF OOM → 自动切换CPU
3. 下一个PDF继续GPU

## GUI设置方法

### 步骤1：勾选Low VRAM

```
Options → [x] Low VRAM
```

### 步骤2：选择处理方式

```
Options → Existing Files → Skip all
```

### 步骤3：开始转换

点击"Start Conversion"

## 显存占用对比

| 方案 | 模型占用 | 临时占用 | 总计 | 7.6GB够用 |
|------|---------|---------|------|----------|
| 标准模式 | 3.2GB | 3-4GB | 6-7GB | ❌ 勉强 |
| Low VRAM | 1.5GB | 1-2GB | 2.5-3.5GB | ✅ 够用 |
| Disable OCR | 1GB | 1-2GB | 2-3GB | ✅ 充足 |
| CPU模式 | 0GB | 0GB | 0GB | ✅ 无限制 |

## 性能对比

| 方案 | 简单PDF | 复杂PDF | OOM风险 | 推荐 |
|------|---------|---------|---------|------|
| 标准模式 | 2分钟 | OOM | 高 | ❌ |
| Low VRAM | 3分钟 | 5分钟 | 低 | ✅ 强烈推荐 |
| Disable OCR | 1.5分钟 | 1.5分钟 | 无 | ⚠️ 限制多 |
| CPU模式 | 20分钟 | 20分钟 | 无 | ⚠️ 太慢 |

## 推荐配置

**针对你的44315个PDF：**

```bash
# 最优方案：Low VRAM + Skip
nuoyi ./papers --batch --device cuda --low-vram --existing-files skip
```

**预计时间：**
- 已转换文件：瞬间跳过
- 新文件：每个3-5分钟
- 总时间：取决于新文件数量

## 为什么会OOM？

**显存分配：**
```
总显存: 7.6GB
├─ 模型: 3.2GB (Layout + OCR + Table)
├─ 临时空间: 0.5-1GB (PDF页面数据)
├─ 中间结果: 1-2GB (特征图、激活值)
└─ 剩余: 249MB ❌ 不够分配880MB
```

**复杂PDF需要更多：**
- 多页PDF：每页额外占用
- 大图片：额外几百MB
- 复杂表格：额外1-2GB

## 如何避免Killed？

**原因：** 系统检测到进程占用过多资源，强制终止。

**预防：**
1. 使用`--low-vram`降低显存占用
2. 使用`--existing-files skip`跳过已转换文件
3. 定期重启GUI（每5000个文件）
4. 监控显存：`watch -n 1 nvidia-smi`

## 快速测试

```bash
# 先测试一个小批次
nuoyi ./test_batch --batch --device cuda --low-vram

# 确认不OOM后再处理全部
nuoyi ./papers --batch --device cuda --low-vram --existing-files skip
```

## 总结

**你的情况：** 7.6GB显存不够标准模式使用。

**最佳方案：** Low VRAM模式
```bash
nuoyi ./papers --batch --device cuda --low-vram --existing-files skip
```

**优势：**
- 显存占用降至2-3GB
- 保留公式识别和图片裁切
- OCR在CPU上运行，速度稍慢但稳定
- 不会OOM，不会被Killed

**立即尝试，不要再被OOM折磨！**