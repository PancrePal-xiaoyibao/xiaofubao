# Chunk分块逻辑优化方案

## 当前分析总结

### 现有分块逻辑
1. **分块触发条件**：
   - Markdown H1、H2标题
   - 中文一级序号（一、二、三、等）
   - 中文子序号（（一）、（二）、等）不触发分块

2. **大块分割策略**：
   - 超过max_chars_per_chunk时从后往前寻找分割点
   - 优先选择H3+标题（非中文子序号）或空行
   - 确保分割后第一部分≥min_chars_per_chunk

3. **后处理**：
   - 仅合并以"注释"开头的chunk

## 主要问题

1. **过度分块**：H1、H2标题强制分块，产生过小chunk
2. **合并策略单一**：只处理"注释"chunk，缺少智能合并
3. **分割点有限**：只考虑标题和空行，忽略段落、列表等语义边界
4. **缺少全局优化**：线性处理，无后处理平衡

## 优化方案

### 1. 智能合并策略
```python
def smart_merge_chunks(chunks, min_chars_per_chunk, max_chars_per_chunk):
    """智能合并小chunk，减少总数量同时保持语义完整性"""
    merged_chunks = []
    i = 0
    
    while i < len(chunks):
        current_chunk = chunks[i]
        current_size = get_chunk_char_count(current_chunk)
        
        # 如果当前chunk太小，尝试与下一个合并
        if current_size < min_chars_per_chunk and i + 1 < len(chunks):
            next_chunk = chunks[i + 1]
            combined_size = current_size + get_chunk_char_count(next_chunk)
            
            # 如果合并后不超过最大限制，则合并
            if combined_size <= max_chars_per_chunk:
                merged_chunk = current_chunk + next_chunk
                merged_chunks.append(merged_chunk)
                i += 2  # 跳过下一个chunk
                continue
        
        merged_chunks.append(current_chunk)
        i += 1
    
    return merged_chunks
```

### 2. 数字标题和子标题优化策略

#### 2.1 数字标题识别与分块优化
```python
def is_numeric_section(line):
    """
    识别数字章节标题，支持纯格式和Markdown格式
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 是否为数字章节标题
    """
    stripped = line.strip()
    if not stripped:
        return False
    
    # 移除行号标记（如<1007>）
    cleaned = re.sub(r'^<\d+>', '', stripped)
    
    # 检查纯数字格式（如"11维持治疗"）
    if re.match(r'^[0-9]+[^0-9]', cleaned):
        return True
    
    # 检查Markdown格式（如"# 11维持治疗"）
    if re.match(r'^#+\s*[0-9]+[^0-9]', cleaned):
        return True
    
    return False

def get_chunk_boundary_priority(line):
    """
    获取分块边界的优先级，数字标题具有最高优先级
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        int: 优先级（1=最高，0=无优先级）
    """
    # 数字标题具有最高优先级
    if is_numeric_section(line):
        return 1
    
    # 中文一级序号
    if is_chinese_major_section(line):
        return 1
    
    # Markdown H1、H2标题
    heading_level = get_heading_level(line)
    if heading_level in [1, 2]:
        return 1
    
    # 子标题具有中等优先级
    if is_subtitle(line):
        return 2
    
    return 0
```

#### 2.2 子标题识别与分块策略
```python
def is_subtitle(line):
    """
    判断是否为子标题，支持多种格式
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 是否为子标题
    """
    stripped = line.strip()
    if not stripped:
        return False
    
    # Markdown子标题（H3及以下）
    if stripped.startswith('##') and not stripped.startswith('###'):
        return False  # H2不算子标题
    if stripped.startswith('###'):
        return True
    
    # 中文二级序号（如"（一）"、"（二）"）
    if re.match(r'^（[一二三四五六七八九十]+）', stripped):
        return True
    
    # 数字序号（如"(1)"、"(2)"、"1."、"1、"）
    if re.match(r'^(\([1-9][0-9]*\)|（[1-9][0-9]*）|[1-9][0-9]*\.|[1-9][0-9]*、)', stripped):
        return True
    
    # 字母序号（如"a)"、"A."）
    if re.match(r'^[a-zA-Z][.)、]', stripped):
        return True
    
    return False

def should_split_at_subtitle(current_chunk_size, subtitle_line, max_chunk_size, is_first_subtitle=False):
    """
    决定是否在子标题处分块
    
    Args:
        current_chunk_size (int): 当前chunk的字符数
        subtitle_line (str): 子标题行内容
        max_chunk_size (int): 最大chunk大小
        is_first_subtitle (bool): 是否为第一个子标题
        
    Returns:
        bool: 是否应该分块
    """
    # 第一个子标题(1)不分块，与主标题保持在一起
    if is_first_subtitle or re.match(r'^(\([1１]\)|（[1１]）|[1１]\.|[1１]、)', subtitle_line.strip()):
        return False
    
    # 如果当前chunk大小超过80%阈值，在子标题处分块
    if current_chunk_size > max_chunk_size * 0.8:
        return True
    
    return False

def detect_title_subtitle_relationship(lines, title_index):
    """
    检测主标题与子标题的关系
    
    Args:
        lines (list): 所有文档行
        title_index (int): 主标题行的索引
        
    Returns:
        tuple: (是否有子标题, 第一个子标题的索引)
    """
    # 检查后续5行内是否有子标题
    for i in range(title_index + 1, min(title_index + 6, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
            
        # 检测子标题格式
        if is_subtitle(line):
            return True, i
            
        # 如果遇到其他主标题，停止查找
        if get_chunk_boundary_priority(line) >= 1:
            break
            
    return False, -1
```

#### 2.3 主标题与子标题的分块保护策略
```python
def protect_title_subtitle_cohesion(lines, chunk_boundaries):
    """
    保护主标题与第一个子标题的关联性
    
    Args:
        lines (list): 所有文档行
        chunk_boundaries (list): 当前的分块边界列表
        
    Returns:
        list: 优化后的分块边界列表
    """
    protected_boundaries = []
    
    for boundary in chunk_boundaries:
        # 检查边界是否在第一个子标题之前
        if boundary < len(lines) and is_subtitle(lines[boundary]):
            # 检查是否为第一个子标题
            if re.match(r'^(\([1１]\)|（[1１]）|[1１]\.|[1１]、)', lines[boundary].strip()):
                # 向前查找主标题
                for i in range(boundary - 1, max(boundary - 6, 0), -1):
                    if get_chunk_boundary_priority(lines[i]) >= 1:
                        # 找到主标题，不在第一个子标题前分块
                        continue
                
        protected_boundaries.append(boundary)
    
    return protected_boundaries

def optimize_subtitle_chunking(lines, max_chunk_size):
    """
    优化子标题分块策略
    
    Args:
        lines (list): 所有文档行
        max_chunk_size (int): 最大chunk大小
        
    Returns:
        list: 优化后的分块边界列表
    """
    boundaries = []
    current_chunk_size = 0
    in_title_subtitle_group = False
    first_subtitle_protected = False
    
    for i, line in enumerate(lines):
        line_size = len(line)
        current_chunk_size += line_size
        
        # 检测主标题
        if get_chunk_boundary_priority(line) >= 1:
            if current_chunk_size > 0:  # 不在开头时才添加边界
                boundaries.append(i)
                current_chunk_size = line_size
            in_title_subtitle_group = True
            first_subtitle_protected = False
            continue
        
        # 检测子标题
        if is_subtitle(line):
            # 第一个子标题不分块
            if in_title_subtitle_group and not first_subtitle_protected:
                first_subtitle_protected = True
                continue
            
            # 后续子标题根据大小决定是否分块
            if should_split_at_subtitle(current_chunk_size, line, max_chunk_size):
                boundaries.append(i)
                current_chunk_size = line_size
                continue
        
        # 重置标题组状态
        if line.strip() and not is_subtitle(line):
            in_title_subtitle_group = False
    
    return boundaries
```

### 4. 动态分块阈值
```python
def should_start_new_chunk(line, current_chunk_lines, max_chars_per_chunk):
    """动态决定是否开始新chunk，考虑当前chunk大小"""
    heading_level = get_heading_level(line)
    is_major_section = is_chinese_major_section(line)
    current_size = get_chunk_char_count(current_chunk_lines)
    
    # 如果当前chunk很小，即使遇到主要标题也不分块
    if current_size < max_chars_per_chunk * 0.3:  # 30%阈值
        return False
    
    # 原有的分块逻辑
    if heading_level in [1, 2] or is_major_section:
        return True
    
    return False
```

### 5. 增强分割点检测
```python
def find_better_split_point(chunk_lines, min_chars_per_chunk):
    """寻找更好的分割点，包括段落边界、列表项等"""
    for i in range(len(chunk_lines) - 1, 0, -1):
        first_part_chars = get_chunk_char_count(chunk_lines[:i+1])
        if first_part_chars >= min_chars_per_chunk:
            line = chunk_lines[i].strip()
            
            # 优先级1: H3+标题（非中文子序号）
            if get_heading_level(chunk_lines[i]) >= 3 and not is_chinese_sub_section(chunk_lines[i]):
                return i + 1
            
            # 优先级2: 空行
            if not line:
                return i + 1
            
            # 优先级3: 段落结束（句号、感叹号、问号结尾）
            if line.endswith(('。', '！', '？', '.', '!', '?')):
                return i + 1
            
            # 优先级4: 列表项开始
            next_line = chunk_lines[i + 1].strip() if i + 1 < len(chunk_lines) else ""
            if next_line.startswith(('- ', '* ', '+ ', '1. ', '2. ')):
                return i + 1
    
    return -1
```

### 6. 表格标题与内容保持一致的分块规则

#### 4.1 问题描述
当前的分块逻辑存在一个严重问题：以冒号结尾的标题（如"乳腺癌内分泌药物用法及用量："）与其后续的表格内容被分离到不同的chunk中。这破坏了内容的语义完整性，影响了文档的可读性和检索效果。

#### 4.2 核心原则
- **标题+冒号与后续内容的关联性**：以冒号（：）结尾的标题行应该与其后续的相关内容保持在同一个chunk中
- **内容关联性判断标准**：
  - 直接关联：标题后紧跟的编号列表（如（1）、（2）等）
  - 间接关联：标题后的空行+编号列表
  - 表格内容：标题后的结构化数据

#### 4.3 实现规则
```python
def is_title_with_colon(line):
    """
    识别以冒号结尾的标题行
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 是否为以冒号结尾的标题
    """
    stripped = line.strip()
    if not stripped:
        return False
    
    # 检查是否以中文冒号或英文冒号结尾
    if stripped.endswith('：') or stripped.endswith(':'):
        # 排除纯数字+冒号的情况（可能是时间）
        if not re.match(r'^\d+[：:]$', stripped):
            return True
    
    return False

def has_related_content_after_title(lines, title_index, max_look_ahead=5):
    """
    判断标题后是否有相关的列表或表格内容
    
    Args:
        lines (list): 所有文档行
        title_index (int): 标题行的索引
        max_look_ahead (int): 向前查看的最大行数
        
    Returns:
        bool: 是否有相关内容
    """
    for i in range(title_index + 1, min(title_index + max_look_ahead + 1, len(lines))):
        line = lines[i].strip()
        
        # 跳过空行
        if not line:
            continue
            
        # 检查是否为编号列表项
        if re.match(r'^[（(]\d+[）)]', line) or re.match(r'^\d+[.、]', line):
            return True
            
        # 检查是否为其他列表格式
        if line.startswith('- ') or line.startswith('* ') or line.startswith('+ '):
            return True
            
        # 如果遇到其他标题，停止查找
        if get_chunk_boundary_priority(line) > 0:
            break
            
    return False

def should_start_new_chunk_with_title_cohesion(line, current_chunk_lines, max_chars_per_chunk, all_lines=None, current_index=None):
    """
    考虑标题与内容关联性的分块决策函数
    
    Args:
        line (str): 当前处理的行
        current_chunk_lines (list): 当前chunk的行列表
        max_chars_per_chunk (int): 最大字符数限制
        all_lines (list): 所有文档行
        current_index (int): 当前行在all_lines中的索引
        
    Returns:
        bool: 是否应该开始新chunk
    """
    # 检查当前行是否为相关内容，向前查找标题+冒号
    if all_lines and current_index is not None and is_related_to_title(line):
        # 向前查找最多5行，寻找标题+冒号
        for i in range(max(0, current_index - 5), current_index):
            if is_title_with_colon(all_lines[i]):
                return False  # 不分块，保持与标题在一起
            # 如果遇到其他重要边界，停止查找
            if get_chunk_boundary_priority(all_lines[i]) >= 1:
                break
    
    # 检查当前行是否为以冒号结尾的标题
    if is_title_with_colon(line) and all_lines and current_index is not None:
        # 如果后续有相关内容，当前不分块（让标题和内容在一起）
        if has_related_content_after_title(all_lines, current_index):
            return False
    
    # 原有的分块逻辑
    return original_should_start_new_chunk(line, current_chunk_lines, max_chars_per_chunk, all_lines, current_index)
```

#### 4.4 测试用例
- **基本标题+列表测试**：乳腺癌内分泌药物用法及用量：+ 编号列表
- **标题+空行+列表测试**：治疗方案：+ 空行 + 编号列表
- **多级标题测试**：主要治疗方案：+ 子标题 + 列表

#### 4.5 预期效果
1. **语义完整性**：标题与其说明内容保持在同一chunk中
2. **检索准确性**：提高相关内容的检索效果
3. **可读性提升**：保持文档结构的逻辑性
4. **分块质量**：减少不合理的分块边界

### 7. 后处理优化
```python
def post_process_chunks(chunks, min_chars_per_chunk, max_chars_per_chunk):
    """后处理优化：平衡chunk大小，减少总数量"""
    # 第一步：智能合并小chunk
    chunks = smart_merge_chunks(chunks, min_chars_per_chunk, max_chars_per_chunk)
    
    # 第二步：处理过大的chunk
    optimized_chunks = []
    for chunk in chunks:
        if get_chunk_char_count(chunk) > max_chars_per_chunk * 1.2:  # 20%容忍度
            # 重新分割过大的chunk
            split_chunks = split_large_chunk(chunk, min_chars_per_chunk, max_chars_per_chunk)
            optimized_chunks.extend(split_chunks)
        else:
            optimized_chunks.append(chunk)
    
    return optimized_chunks
```

## 预期效果

1. **减少chunk数量**：通过智能合并，预计减少15-25%的chunk数量
2. **提高平均大小**：更接近target_chunk_size配置值
3. **保持语义完整性**：改进的分割点检测确保语义边界
4. **更好的大小分布**：减少过小和过大的chunk

## 实施步骤

1. **第一阶段**：实现智能合并策略
2. **第二阶段**：添加动态分块阈值
3. **第三阶段**：增强分割点检测
4. **第四阶段**：集成后处理优化
5. **测试验证**：使用现有文档验证效果

## 8. 边界检测和修复策略

### 8.1 边界位置错误检测

基于发现的问题（如乳腺癌诊疗指南第2215-2221行），需要实现边界位置错误的自动检测和修复：

```python
def detect_boundary_position_errors(chunks, original_lines):
    """
    检测边界位置错误
    
    返回:
    - list: 错误边界位置列表
    """
    errors = []
    
    for i, chunk in enumerate(chunks):
        chunk_start_line = get_chunk_start_line(chunk, original_lines)
        
        # 检查边界是否放在了低优先级位置
        if chunk_start_line > 0:
            boundary_line = original_lines[chunk_start_line - 1]
            current_line = original_lines[chunk_start_line]
            
            # 检查是否在Markdown标题前错误放置边界
            if (is_markdown_heading(current_line) and 
                not is_chinese_major_section(current_line)):
                
                # 查找附近是否有更高优先级的分块点
                nearby_chinese_section = find_nearby_chinese_section(
                    chunk_start_line, original_lines, search_range=10
                )
                
                if nearby_chinese_section:
                    errors.append({
                        'chunk_index': i,
                        'error_line': chunk_start_line,
                        'error_type': 'boundary_before_markdown_heading',
                        'suggested_line': nearby_chinese_section['line_index'],
                        'description': f'边界应放在中文序号"{nearby_chinese_section["content"]}"之前'
                    })
    
    return errors

def find_nearby_chinese_section(line_index, original_lines, search_range=10):
    """
    在指定范围内查找中文一级序号
    """
    start = max(0, line_index - search_range)
    end = min(len(original_lines), line_index + search_range)
    
    for i in range(start, end):
        line = original_lines[i].strip()
        if is_chinese_major_section(line):
            return {
                'line_index': i,
                'content': line,
                'priority': get_chunk_boundary_priority(line)
            }
    
    return None
```

### 8.2 主标题和子标题关系检测与修复

针对主标题与紧邻子标题被边界标记错误分开的问题，实现专门的检测和修复机制：

```python
def detect_title_subtitle_separation_errors(file_path):
    """
    检测主标题和子标题被边界标记错误分开的问题
    
    Args:
        file_path: 处理后的文档路径
        
    Returns:
        dict: 包含检测结果的详细报告
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    main_titles = []
    separation_errors = []
    
    # 查找所有主标题
    for i, line in enumerate(lines):
        line = line.strip()
        if (line.startswith('#') and not line.startswith('##')) or \
           re.match(r'^[一二三四五六七八九十]+、', line):
            main_titles.append((i, line))
    
    # 检查每个主标题与紧邻子标题的关系
    for title_idx, title_content in main_titles:
        # 检查后续5行
        for j in range(title_idx + 1, min(title_idx + 6, len(lines))):
            next_line = lines[j].strip()
            
            # 如果遇到边界标记
            if '[CHUNK_BOUNDARY]' in next_line:
                # 检查边界标记后是否紧跟子标题
                if j + 1 < len(lines):
                    after_boundary = lines[j + 1].strip()
                    if is_subtitle(after_boundary):
                        separation_errors.append({
                            'main_title_line': title_idx + 1,
                            'main_title': title_content,
                            'boundary_line': j + 1,
                            'subtitle_line': j + 2,
                            'subtitle': after_boundary,
                            'error_type': 'main_title_subtitle_separated'
                        })
                break
                
            # 如果遇到子标题但没有边界标记，这是正确的
            if is_subtitle(next_line):
                break
    
    return {
        'total_main_titles': len(main_titles),
        'separation_errors': separation_errors,
        'errors_count': len(separation_errors),
        'success_rate': (len(main_titles) - len(separation_errors)) / len(main_titles) * 100 if main_titles else 100
    }

def is_subtitle(line):
    """
    判断是否为子标题
    
    Args:
        line: 文本行
        
    Returns:
        bool: 是否为子标题
    """
    line = line.strip()
    return (line.startswith('##') or  # Markdown子标题
            re.match(r'^（[一二三四五六七八九十]+）', line) or  # 中文二级序号
            re.match(r'^\d+\.', line) or  # 数字序号
            re.match(r'^[a-zA-Z]\)', line))  # 字母序号

def has_immediate_sub_heading(lines, current_index):
    """
    检测主标题后是否紧跟子标题
    
    Args:
        lines: 文档行列表
        current_index: 当前主标题的行索引
        
    Returns:
        bool: 如果紧跟子标题返回True，否则返回False
    """
    # 检查后续5行内容
    for i in range(current_index + 1, min(current_index + 6, len(lines))):
        line = lines[i].strip()
        if not line:  # 跳过空行
            continue
            
        # 检测各种子标题模式
        if is_subtitle(line):
            return True
            
        # 如果遇到其他内容，停止检测
        if line and not line.startswith('#'):
            break
            
    return False

def fix_title_subtitle_separation(chunks, original_lines):
    """
    修复主标题和子标题被错误分开的问题
    
    Args:
        chunks: 当前分块列表
        original_lines: 原始文档行列表
        
    Returns:
        list: 修复后的分块列表
    """
    fixed_chunks = []
    i = 0
    
    while i < len(chunks):
        current_chunk = chunks[i]
        
        # 检查当前chunk的最后一行是否为主标题
        last_line = current_chunk[-1].strip() if current_chunk else ""
        
        if (last_line.startswith('#') and not last_line.startswith('##')) or \
           re.match(r'^[一二三四五六七八九十]+、', last_line):
            
            # 检查下一个chunk的第一行是否为子标题
            if i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                first_line = next_chunk[0].strip() if next_chunk else ""
                
                if is_subtitle(first_line):
                    # 合并这两个chunk
                    merged_chunk = current_chunk + next_chunk
                    fixed_chunks.append(merged_chunk)
                    i += 2  # 跳过下一个chunk
                    continue
        
        fixed_chunks.append(current_chunk)
        i += 1
    
    return fixed_chunks
```

### 8.4 自动化检测和修复流程

```python
def automated_boundary_detection_and_fix(file_path):
    """
    自动化边界检测和修复流程
    
    Args:
        file_path: 处理后的文档路径
        
    Returns:
        dict: 检测和修复结果报告
    """
    # 第一步：检测主标题和子标题分离错误
    title_subtitle_report = detect_title_subtitle_separation_errors(file_path)
    
    # 第二步：检测边界位置错误
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    boundary_errors = detect_boundary_position_errors(None, lines)
    
    # 第三步：生成综合报告
    report = {
        'file_path': file_path,
        'total_lines': len(lines),
        'total_boundaries': len([line for line in lines if '[CHUNK_BOUNDARY]' in line]),
        'title_subtitle_errors': title_subtitle_report,
        'boundary_position_errors': boundary_errors,
        'overall_quality_score': calculate_boundary_quality_score(title_subtitle_report, boundary_errors),
        'recommendations': generate_fix_recommendations(title_subtitle_report, boundary_errors)
    }
    
    return report

def calculate_boundary_quality_score(title_subtitle_report, boundary_errors):
    """
    计算边界质量分数
    
    Args:
        title_subtitle_report: 主标题子标题检测报告
        boundary_errors: 边界位置错误列表
        
    Returns:
        float: 质量分数 (0-100)
    """
    total_issues = title_subtitle_report['errors_count'] + len(boundary_errors)
    total_boundaries = title_subtitle_report['total_main_titles']
    
    if total_boundaries == 0:
        return 100.0
    
    error_rate = total_issues / total_boundaries
    quality_score = max(0, 100 - (error_rate * 100))
    
    return round(quality_score, 2)

def generate_fix_recommendations(title_subtitle_report, boundary_errors):
    """
    生成修复建议
    
    Args:
        title_subtitle_report: 主标题子标题检测报告
        boundary_errors: 边界位置错误列表
        
    Returns:
        list: 修复建议列表
    """
    recommendations = []
    
    if title_subtitle_report['errors_count'] > 0:
        recommendations.append({
            'type': 'title_subtitle_separation',
            'priority': 'high',
            'description': f'发现{title_subtitle_report["errors_count"]}个主标题与子标题被错误分开的问题',
            'action': '使用has_immediate_sub_heading()函数优化分块逻辑'
        })
    
    if len(boundary_errors) > 0:
        recommendations.append({
            'type': 'boundary_position',
            'priority': 'medium',
            'description': f'发现{len(boundary_errors)}个边界位置错误',
            'action': '调整边界优先级算法，优先选择中文序号作为分块点'
        })
    
    return recommendations
```

### 8.5 自动边界修复

```python
def auto_fix_boundary_errors(chunks, original_lines, errors):
    """
    自动修复边界位置错误
    
    参数:
    - chunks: 原始chunk列表
    - original_lines: 原始文档行列表
    - errors: 检测到的错误列表
    
    返回:
    - list: 修复后的chunk列表
    """
    if not errors:
        return chunks
    
    # 按行号倒序排序，避免修复时索引变化
    errors.sort(key=lambda x: x['error_line'], reverse=True)
    
    fixed_chunks = chunks.copy()
    
    for error in errors:
        chunk_index = error['chunk_index']
        suggested_line = error['suggested_line']
        
        # 重新分割受影响的chunk
        if chunk_index < len(fixed_chunks):
            current_chunk = fixed_chunks[chunk_index]
            
            # 找到新的分割点
            new_chunks = resplit_chunk_at_line(
                current_chunk, suggested_line, original_lines
            )
            
            # 替换原chunk
            fixed_chunks[chunk_index:chunk_index+1] = new_chunks
    
    return fixed_chunks

def resplit_chunk_at_line(chunk, split_line_index, original_lines):
    """
    在指定行重新分割chunk
    """
    chunk_start = get_chunk_start_line(chunk, original_lines)
    chunk_end = get_chunk_end_line(chunk, original_lines)
    
    if chunk_start <= split_line_index <= chunk_end:
        # 分割为两个chunk
        first_chunk = original_lines[chunk_start:split_line_index]
        second_chunk = original_lines[split_line_index:chunk_end + 1]
        
        return [first_chunk, second_chunk]
    
    return [chunk]
```

### 8.6 边界优先级重新评估

```python
def reassess_boundary_priorities(original_lines):
    """
    重新评估所有潜在边界的优先级
    
    返回:
    - dict: 行号到优先级的映射
    """
    priorities = {}
    
    for i, line in enumerate(original_lines):
        line_stripped = line.strip()
        
        # 中文一级序号：最高优先级
        if is_chinese_major_section(line_stripped):
            priorities[i] = 10
        
        # Markdown H1标题：高优先级（但需检查上下文）
        elif get_heading_level(line_stripped) == 1:
            # 检查附近是否有中文序号
            nearby_chinese = find_nearby_chinese_section(i, original_lines, 5)
            if nearby_chinese:
                priorities[i] = 5  # 降低优先级
            else:
                priorities[i] = 9
        
        # Markdown H2标题：中等优先级
        elif get_heading_level(line_stripped) == 2:
            priorities[i] = 7
        
        # 其他标题：较低优先级
        elif get_heading_level(line_stripped) >= 3:
            priorities[i] = 3
    
    return priorities
```

### 8.7 边界验证和质量检查

```python
def validate_chunk_boundaries_quality(chunks, original_lines):
    """
    验证chunk边界质量
    
    返回:
    - dict: 质量评估结果
    """
    quality_report = {
        'total_chunks': len(chunks),
        'boundary_errors': [],
        'quality_score': 0,
        'recommendations': []
    }
    
    # 检测边界位置错误
    boundary_errors = detect_boundary_position_errors(chunks, original_lines)
    quality_report['boundary_errors'] = boundary_errors
    
    # 计算质量分数
    error_penalty = len(boundary_errors) * 10
    base_score = 100
    quality_score = max(0, base_score - error_penalty)
    quality_report['quality_score'] = quality_score
    
    # 生成改进建议
    if boundary_errors:
        quality_report['recommendations'].append(
            f"发现{len(boundary_errors)}个边界位置错误，建议运行自动修复"
        )
    
    if quality_score < 80:
        quality_report['recommendations'].append(
            "边界质量较低，建议重新评估分块策略"
        )
    
    return quality_report
```

## 9. 每次转换后的检测和输出机制

### 9.1 自动检测流程

每次文档转换完成后，系统将自动执行以下检测流程：

```python
def post_conversion_detection_and_output(optimized_file_path, original_file_path):
    """
    转换后的自动检测和输出机制
    
    Args:
        optimized_file_path: 优化后的文件路径
        original_file_path: 原始文件路径
    """
    print(f"\n{'='*60}")
    print(f"文档转换完成 - 开始质量检测")
    print(f"{'='*60}")
    
    # 1. 基础统计信息
    with open(optimized_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    boundary_count = sum(1 for line in lines if line.strip() == '---CHUNK_BOUNDARY---')
    total_lines = len(lines)
    
    print(f"📊 基础统计:")
    print(f"   - 文档总行数: {total_lines}")
    print(f"   - 边界标记数: {boundary_count}")
    print(f"   - 预计chunk数: {boundary_count + 1}")
    
    # 2. 主标题和子标题关系检测
    print(f"\n🔍 主标题和子标题关系检测:")
    title_subtitle_issues = verify_title_subtitle_relationships(lines)
    
    if title_subtitle_issues:
        print(f"   ❌ 发现 {len(title_subtitle_issues)} 个问题:")
        for issue in title_subtitle_issues[:5]:  # 显示前5个问题
            print(f"      - 行 {issue['line_num']}: {issue['title'][:50]}...")
        if len(title_subtitle_issues) > 5:
            print(f"      - ... 还有 {len(title_subtitle_issues) - 5} 个问题")
    else:
        print(f"   ✅ 未发现主标题和子标题分离问题")
    
    # 3. 边界位置质量检测
    print(f"\n🎯 边界位置质量检测:")
    chunks = []
    current_chunk = []
    
    for line in lines:
        if line.strip() == '---CHUNK_BOUNDARY---':
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
        else:
            current_chunk.append(line)
    
    if current_chunk:
        chunks.append(current_chunk)
    
    boundary_errors = detect_boundary_position_errors(chunks, lines)
    
    if boundary_errors:
        print(f"   ❌ 发现 {len(boundary_errors)} 个边界位置错误:")
        for error in boundary_errors[:3]:  # 显示前3个错误
            print(f"      - {error}")
        if len(boundary_errors) > 3:
            print(f"      - ... 还有 {len(boundary_errors) - 3} 个错误")
    else:
        print(f"   ✅ 所有边界位置正确")
    
    # 4. 整体质量评分
    total_issues = len(title_subtitle_issues) + len(boundary_errors)
    max_possible_issues = boundary_count + 50  # 假设最大可能问题数
    quality_score = max(0, 100 - (total_issues / max_possible_issues * 100))
    
    print(f"\n📈 整体质量评分:")
    print(f"   - 质量分数: {quality_score:.1f}/100")
    
    if quality_score >= 95:
        print(f"   - 质量等级: 🌟 优秀")
    elif quality_score >= 85:
        print(f"   - 质量等级: ✅ 良好")
    elif quality_score >= 70:
        print(f"   - 质量等级: ⚠️  一般")
    else:
        print(f"   - 质量等级: ❌ 需要改进")
    
    # 5. 改进建议
    print(f"\n💡 改进建议:")
    if total_issues == 0:
        print(f"   ✅ 文档质量优秀，无需改进")
    else:
        if title_subtitle_issues:
            print(f"   - 建议运行主标题子标题关系修复")
        if boundary_errors:
            print(f"   - 建议运行边界位置自动修复")
        print(f"   - 可考虑调整分块参数以提升质量")
    
    # 6. 输出详细报告文件
    report_file = optimized_file_path.replace('.md', '_quality_report.txt')
    generate_detailed_quality_report(
        report_file, 
        optimized_file_path, 
        total_lines, 
        boundary_count, 
        title_subtitle_issues, 
        boundary_errors, 
        quality_score
    )
    
    print(f"\n📄 详细报告已保存至: {report_file}")
    print(f"{'='*60}\n")
    
    return {
        'quality_score': quality_score,
        'total_issues': total_issues,
        'title_subtitle_issues': len(title_subtitle_issues),
        'boundary_errors': len(boundary_errors)
    }

def generate_detailed_quality_report(report_file, optimized_file, total_lines, 
                                   boundary_count, title_subtitle_issues, 
                                   boundary_errors, quality_score):
    """
    生成详细的质量检测报告
    """
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"文档质量检测报告\n")
        f.write(f"{'='*50}\n\n")
        
        f.write(f"文件信息:\n")
        f.write(f"  - 文件路径: {optimized_file}\n")
        f.write(f"  - 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"  - 文档总行数: {total_lines}\n")
        f.write(f"  - 边界标记数: {boundary_count}\n\n")
        
        f.write(f"质量评分: {quality_score:.1f}/100\n\n")
        
        f.write(f"主标题和子标题关系检测:\n")
        if title_subtitle_issues:
            f.write(f"  发现 {len(title_subtitle_issues)} 个问题:\n")
            for i, issue in enumerate(title_subtitle_issues, 1):
                f.write(f"    {i}. 行 {issue['line_num']}: {issue['title']}\n")
        else:
            f.write(f"  ✅ 未发现问题\n")
        f.write(f"\n")
        
        f.write(f"边界位置质量检测:\n")
        if boundary_errors:
            f.write(f"  发现 {len(boundary_errors)} 个错误:\n")
            for i, error in enumerate(boundary_errors, 1):
                f.write(f"    {i}. {error}\n")
        else:
            f.write(f"  ✅ 未发现错误\n")
        f.write(f"\n")
        
        f.write(f"改进建议:\n")
        if title_subtitle_issues or boundary_errors:
            if title_subtitle_issues:
                f.write(f"  - 运行主标题子标题关系修复\n")
            if boundary_errors:
                f.write(f"  - 运行边界位置自动修复\n")
            f.write(f"  - 考虑调整分块参数\n")
        else:
            f.write(f"  - 文档质量优秀，无需改进\n")
```

### 9.2 集成到主处理流程

在 `preprocess.py` 的主函数中集成检测机制：

```python
def main():
    # ... 现有处理逻辑 ...
    
    # 处理完成后自动执行检测
    if optimized_file_path:
        detection_result = post_conversion_detection_and_output(
            optimized_file_path, 
            input_file
        )
        
        # 根据检测结果决定是否需要进一步处理
        if detection_result['total_issues'] > 0:
            print(f"检测到 {detection_result['total_issues']} 个问题，建议查看详细报告")
        else:
            print(f"文档质量检测通过，可以进行后续处理")
```

### 9.3 输出格式示例

```
============================================================
文档转换完成 - 开始质量检测
============================================================
📊 基础统计:
   - 文档总行数: 3456
   - 边界标记数: 252
   - 预计chunk数: 253

🔍 主标题和子标题关系检测:
   ✅ 未发现主标题和子标题分离问题

🎯 边界位置质量检测:
   ✅ 所有边界位置正确

📈 整体质量评分:
   - 质量分数: 98.5/100
   - 质量等级: 🌟 优秀

💡 改进建议:
   ✅ 文档质量优秀，无需改进

📄 详细报告已保存至: To_be_processed/乳腺癌诊疗指南2025_optimized_quality_report.txt
============================================================
```

## 风险评估

- **低风险**：智能合并策略（向后兼容）
- **中风险**：动态分块阈值（可能改变现有行为）
- **低风险**：增强分割点检测（改进现有逻辑）
- **低风险**：后处理优化（额外处理步骤）
- **低风险**：边界检测和修复（提升质量，可选启用）
- **低风险**：自动检测输出机制（纯检测功能，不影响原有逻辑）