# 文件存在检测逻辑优化

## 改进前的问题

**旧逻辑：先转换，再判断是否跳过**
```python
# 错误的方式
for file in files:
    # 1. 先转换文件（耗时操作）
    result = convert_file(file)
    
    # 2. 转换完才发现文件已存在
    if output_exists and should_skip:
        skip  # 白白转换了！
```

**问题：**
- 浪费时间：已存在的文件还要转换一遍
- 浪费资源：GPU/CPU资源被浪费
- 效率低：大批量处理时重复工作多

## 改进后的逻辑

**新逻辑：先判断，再决定是否转换**
```python
# 正确的方式
for file in files:
    output_path = get_output_path(file)
    
    # 1. 先检查输出文件是否存在
    if output_path.exists():
        if existing_files == "skip":
            # 直接跳过，不转换
            print("Skipping (already exists)")
            continue
        elif existing_files == "update":
            # 检查修改时间
            if source_not_newer:
                print("Skipping (source not newer)")
                continue
    
    # 2. 只有确实需要转换时才执行
    result = convert_file(file)
```

## 性能对比

### 场景1：已有1000个文件，新增100个

**旧逻辑：**
- 检查1000个已存在文件
- 转换1000个已存在文件（浪费！）
- 转换100个新文件
- **总耗时：1100 × 2分钟 = 2200分钟**

**新逻辑：**
- 检查1000个已存在文件
- 跳过1000个已存在文件（瞬间）
- 转换100个新文件
- **总耗时：100 × 2分钟 = 200分钟**

**节省91%时间**

### 场景2：断点续传

**旧逻辑：**
- 转换到第500个文件程序崩溃
- 重启后从头开始
- 前500个文件重新转换
- **浪费：500 × 2分钟 = 1000分钟**

**新逻辑：**
- 转换到第500个文件程序崩溃
- 重启后检测到前500个文件已存在
- 直接从第501个继续
- **节省：1000分钟**

## 实现细节

### 1. 检测输出文件路径

```python
out_path = get_output_path(f, input_dir, output_dir, recursive)
```

### 2. 检查文件是否存在

```python
if out_path.exists():
    # 处理已存在文件
```

### 3. 根据策略决定是否跳过

```python
if existing_files == "skip":
    skipped_count += 1
    print(f"Skipping (already exists)")
    results.append({...})
    continue  # 直接跳到下一个文件
```

### 4. 更新模式：检查修改时间

```python
elif existing_files == "update":
    src_mtime = f.stat().st_mtime
    out_mtime = out_path.stat().st_mtime
    if src_mtime <= out_mtime:
        # 源文件不比输出新，跳过
        print("Skipping (source not newer)")
        continue
```

### 5. 交互模式：询问用户

```python
elif existing_files == "ask_each":
    print("Output file already exists")
    choice = input("Your choice (o/s/u/O/S/U): ")
    if choice == "s":
        print("Skipping")
        continue
```

## 代码位置

**主要修改：** `src/nuoyi/api.py` 的 `convert_directory` 函数

```python
def convert_directory(..., existing_files: str = "ask"):
    for i, f in enumerate(files, 1):
        out_path = get_output_path(f, input_dir, output_dir, recursive)
        
        # 先检查文件是否存在
        if out_path.exists():
            if existing_files == "skip":
                # 直接跳过，不转换
                skipped_count += 1
                results.append({...})
                continue
        
        # 只有需要转换时才执行
        result = convert_file(f, ...)
```

## 测试验证

所有测试通过：
```
tests/test_existing_files.py::test_skip_existing_files PASSED
tests/test_existing_files.py::test_overwrite_existing_files PASSED
tests/test_existing_files.py::test_update_only_newer_files PASSED
```

## 使用场景

### 1. 批量转换（推荐）

```bash
nuoyi ./papers --batch --existing-files skip
```

**适用：**
- 已有部分转换结果
- 不想重复转换
- 最快速度完成

### 2. 增量更新

```bash
nuoyi ./papers --batch --existing-files update
```

**适用：**
- 部分源文件有更新
- 只转换修改过的文件
- 保持输出最新

### 3. 完全重做

```bash
nuoyi ./papers --batch --existing-files overwrite
```

**适用：**
- 需要重新转换所有文件
- 转换参数改变
- 修复之前的问题

### 4. 交互式选择

```bash
nuoyi ./papers --batch --existing-files ask
```

**适用：**
- 需要逐个确认
- 不确定哪些文件需要更新
- 手动控制

## 性能提升总结

| 场景 | 旧逻辑 | 新逻辑 | 节省 |
|------|--------|--------|------|
| 1000文件已存在 | 2000分钟 | <1分钟 | 99.9% |
| 500文件断点续传 | 1000分钟 | 0分钟 | 100% |
| 10%文件已存在 | 2000分钟 | 1800分钟 | 10% |
| 50%文件已存在 | 2000分钟 | 1000分钟 | 50% |

**核心优势：避免不必要的转换操作，大幅提升批量处理效率。**