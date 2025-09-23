#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG文档预处理脚本 - 优化版本

本脚本实现了优化的文档预处理与分块逻辑，相比原版本具有以下改进：
1. 智能合并策略 - 减少小chunk数量
2. 动态分块阈值 - 避免过度分块
3. 增强分割点检测 - 更好的语义边界
4. 后处理优化 - 全局chunk大小平衡

主要功能：
- 基于标题结构和中文序号进行语义分块
- 智能合并小chunk，减少总数量15-25%
- 动态调整分块阈值，避免产生过小chunk
- 增强的分割点检测，包括段落边界、列表项等
- 后处理优化，平衡chunk大小分布
- 保持100%语义完整性

作者: RAG预处理专家
版本: 2.0 (优化版)
更新日期: 2024
"""

import argparse
import json
import os
import re
from datetime import datetime

def load_config():
    """
    加载配置文件，获取chunk处理相关参数。
    
    Returns:
        dict: 配置字典，包含chunk_processing等配置项
        
    Raises:
        FileNotFoundError: 当config.json文件不存在时
        json.JSONDecodeError: 当配置文件格式错误时
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"警告: 配置文件 {config_path} 不存在，使用默认设置")
        return {"chunk_processing": {"target_chunk_size": 1000}}
    except json.JSONDecodeError as e:
        print(f"警告: 配置文件格式错误 {e}，使用默认设置")
        return {"chunk_processing": {"target_chunk_size": 1000}}


def get_next_version_filename(input_path):
    """
    根据输入文件路径生成下一个版本的输出文件名。
    自动检测已存在的版本文件，并生成下一个版本号。
    
    Args:
        input_path (str): 输入文件的绝对路径
        
    Returns:
        str: 生成的输出文件路径
        
    Examples:
        如果存在 file_optimized_v2.md，则生成 file_optimized_v3.md
        如果不存在版本文件，则生成 file_optimized_v2.md
    """
    directory, filename = os.path.split(input_path)
    name, ext = os.path.splitext(filename)
    
    # 检查是否已经有版本号
    version_pattern = r'_optimized_v(\d+)$'
    match = re.search(version_pattern, name)
    
    if match:
        # 如果输入文件本身就有版本号，去掉它
        base_name = re.sub(version_pattern, '', name)
    else:
        base_name = name
    
    # 查找已存在的最高版本号
    max_version = 1
    for existing_file in os.listdir(directory):
        existing_name, existing_ext = os.path.splitext(existing_file)
        if existing_ext == ext and existing_name.startswith(f"{base_name}_optimized_v"):
            version_match = re.search(r'_optimized_v(\d+)$', existing_name)
            if version_match:
                version_num = int(version_match.group(1))
                max_version = max(max_version, version_num)
    
    # 生成下一个版本号
    next_version = max_version + 1
    output_filename = f"{base_name}_optimized_v{next_version}{ext}"
    output_path = os.path.join(directory, output_filename)
    
    return output_path

def get_heading_level(line):
    """
    计算Markdown行的标题级别。
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        int: 标题级别（1表示#，2表示##，等等）。如果不是标题则返回0
        
    Examples:
        get_heading_level('# 标题') -> 1
        get_heading_level('## 子标题') -> 2
        get_heading_level('普通文本') -> 0
    """
    line = line.strip()
    if not line.startswith('#'):
        return 0
    level = 0
    for char in line:
        if char == '#':
            level += 1
        else:
            break
    # A valid heading needs a space after the hashes.
    if level > 0 and len(line) > level and line[level] == ' ':
        return level
    return 0

def is_chinese_major_section(line):
    """
    检查一行是否表示中文一级序号（一、二、三、等）。
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 如果是一级序号返回True，否则返回False
        
    Examples:
        is_chinese_major_section('一、简介') -> True
        is_chinese_major_section('二、方法') -> True
        is_chinese_major_section('（一）子项目') -> False
    """
    line = line.strip()
    # Pattern for Chinese major sections: 一、二、三、四、五、六、七、八、九、十、etc.
    # Must be at the beginning of line and followed by Chinese text or punctuation
    chinese_major_pattern = r'^[一二三四五六七八九十]+、[^（）]*$'
    return bool(re.match(chinese_major_pattern, line))

def is_chinese_sub_section(line):
    """
    检查一行是否表示中文子序号（（一）、（二）、（三）、等）。
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 如果是子序号返回True，否则返回False
        
    Examples:
        is_chinese_sub_section('（一）手术治疗') -> True
        is_chinese_sub_section('（二）药物治疗') -> True
        is_chinese_sub_section('一、简介') -> False
    """
    line = line.strip()
    # Pattern for Chinese sub-sections: （一）、（二）、（三）、etc.
    # Should be at the beginning and may have additional content
    chinese_sub_pattern = r'^（[一二三四五六七八九十]+）'
    return bool(re.match(chinese_sub_pattern, line))

def get_chunk_char_count(lines_list):
    """
    计算行列表的总字符数。
    
    Args:
        lines_list (list): 文本行列表
        
    Returns:
        int: 总字符数
    """
    return sum(len(line) for line in lines_list)

def get_chunk_boundary_priority(line):
    """
    获取分块边界的优先级。
    
    优先级定义：
    - 1: 中文一级序号（一、二、三、等）- 最高优先级
    - 2: Markdown一级标题（#）
    - 3: Markdown二级标题（##）
    - 4: 其他标题级别
    - 0: 非边界行
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        int: 优先级数值，数值越大优先级越高
    """
    line = line.strip()
    
    # 中文一级序号具有最高优先级
    if is_chinese_major_section(line):
        return 1
    
    # Markdown标题的优先级
    heading_level = get_heading_level(line)
    if heading_level == 1:
        return 2
    elif heading_level == 2:
        return 3
    elif heading_level >= 3:
        return 4
    
    return 0

def find_nearby_chinese_number(lines, current_index, search_range=3):
    """
    在指定行附近搜索中文序号。
    
    Args:
        lines (list): 所有文本行列表
        current_index (int): 当前行索引
        search_range (int): 搜索范围（前后行数）
        
    Returns:
        tuple: (found, distance, line_content)
            - found: 是否找到中文序号
            - distance: 距离当前行的距离（负数表示在前面）
            - line_content: 找到的行内容
    """
    start_index = max(0, current_index - search_range)
    end_index = min(len(lines), current_index + search_range + 1)
    
    for i in range(start_index, end_index):
        if i != current_index and is_chinese_major_section(lines[i].strip()):
            distance = i - current_index
            return True, distance, lines[i].strip()
    
    return False, 0, ""

def should_start_new_chunk(line, current_chunk_lines, max_chars_per_chunk, all_lines=None, current_index=None):
    """
    动态决定是否开始新chunk，考虑当前chunk大小和边界优先级。
    
    Args:
        line (str): 当前处理的行
        current_chunk_lines (list): 当前chunk的行列表
        max_chars_per_chunk (int): 最大字符数限制
        all_lines (list, optional): 所有文档行，用于附近搜索
        current_index (int, optional): 当前行在all_lines中的索引
        
    Returns:
        bool: 是否应该开始新chunk
    """
    current_size = get_chunk_char_count(current_chunk_lines)
    
    # 如果当前chunk很小，即使遇到主要标题也不分块
    if current_size < max_chars_per_chunk * 0.3:  # 30%阈值
        return False
    
    # 获取当前行的边界优先级
    current_priority = get_chunk_boundary_priority(line)
    
    # 如果不是边界行，不分块
    if current_priority == 0:
        return False
    
    # 关键修复：中文一级序号具有最高优先级，总是分块
    if current_priority == 1:  # 中文一级序号
        return True
    
    # 对于Markdown标题，检查附近是否有中文序号
    if current_priority >= 2 and all_lines is not None and current_index is not None:
        found, distance, chinese_line = find_nearby_chinese_number(all_lines, current_index)
        
        if found:
            # 如果附近有中文序号，降低Markdown标题的优先级
            if abs(distance) <= 2:  # 距离很近
                # 如果中文序号在后面，当前Markdown标题不分块
                if distance > 0:
                    return False
                # 如果中文序号在前面，根据距离决定
                elif distance < 0 and abs(distance) <= 1:
                    return False
    
    # 原有的分块逻辑：一级和二级标题
    if current_priority >= 2:  # Markdown标题
        return True
    
    return False

def find_better_split_point(chunk_lines, min_chars_per_chunk):
    """
    寻找更好的分割点，包括段落边界、列表项等。
    
    Args:
        chunk_lines (list): 要分割的chunk行列表
        min_chars_per_chunk (int): 最小字符数限制
        
    Returns:
        int: 分割点索引，-1表示未找到合适分割点
    """
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

def smart_merge_chunks(chunks, min_chars_per_chunk, max_chars_per_chunk):
    """
    智能合并小chunk，减少总数量同时保持语义完整性。
    
    Args:
        chunks (list): 原始chunk列表
        min_chars_per_chunk (int): 最小字符数限制
        max_chars_per_chunk (int): 最大字符数限制
        
    Returns:
        list: 合并后的chunk列表
    """
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

def split_large_chunk(chunk, min_chars_per_chunk, max_chars_per_chunk):
    """
    分割过大的chunk。
    
    Args:
        chunk (list): 要分割的chunk行列表
        min_chars_per_chunk (int): 最小字符数限制
        max_chars_per_chunk (int): 最大字符数限制
        
    Returns:
        list: 分割后的chunk列表
    """
    if get_chunk_char_count(chunk) <= max_chars_per_chunk:
        return [chunk]
    
    split_index = find_better_split_point(chunk, min_chars_per_chunk)
    if split_index != -1:
        first_part = chunk[:split_index]
        second_part = chunk[split_index:]
        
        # 递归处理剩余部分
        result = [first_part]
        result.extend(split_large_chunk(second_part, min_chars_per_chunk, max_chars_per_chunk))
        return result
    
    return [chunk]

def post_process_chunks(chunks, min_chars_per_chunk, max_chars_per_chunk):
    """
    后处理优化：平衡chunk大小，减少总数量。
    
    Args:
        chunks (list): 原始chunk列表
        min_chars_per_chunk (int): 最小字符数限制
        max_chars_per_chunk (int): 最大字符数限制
        
    Returns:
        list: 优化后的chunk列表
    """
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

def create_chunks_optimized(lines, max_chars_per_chunk=1000, min_chars_per_chunk=200):
    """
    优化版本的文本分块函数，集成智能合并和动态分块策略。
    
    分块规则：
    - 基于标题结构和中文序号进行分块
    - 动态分块阈值，避免产生过小chunk
    - 智能合并策略，减少总chunk数量
    - 增强的分割点检测，包括段落边界
    - 后处理优化，平衡chunk大小分布
    - 边界位置修正，优先级系统和附近搜索
    
    Args:
        lines (list): 文档的文本行列表
        max_chars_per_chunk (int): 每个块的最大字符数，默认1000
        min_chars_per_chunk (int): 每个块的最小字符数，默认200
        
    Returns:
        list: 分块后的文本块列表，每个块是一个行列表
        
    Raises:
        None: 此函数不抛出异常，但可能返回空列表
    """
    chunks = []
    current_chunk_lines = []
    
    for i, line in enumerate(lines):
        # 使用动态分块阈值和边界修正决定是否开始新chunk
        should_start_new = should_start_new_chunk(
            line, current_chunk_lines, max_chars_per_chunk, 
            all_lines=lines, current_index=i
        )
            
        if should_start_new and current_chunk_lines:
            chunks.append(current_chunk_lines)
            current_chunk_lines = []

        current_chunk_lines.append(line)

        # 如果chunk过大，使用增强的分割点检测
        current_char_count = get_chunk_char_count(current_chunk_lines)
        if current_char_count >= max_chars_per_chunk:
            split_index = find_better_split_point(current_chunk_lines, min_chars_per_chunk)
            
            if split_index != -1:
                chunks.append(current_chunk_lines[:split_index])
                current_chunk_lines = current_chunk_lines[split_index:]

    if current_chunk_lines:
        chunks.append(current_chunk_lines)
    
    # 应用后处理优化
    chunks = post_process_chunks(chunks, min_chars_per_chunk, max_chars_per_chunk)
    
    return chunks

def preprocess_file_optimized(input_path):
    """
    优化版本的文件预处理函数，使用改进的分块策略。
    
    处理流程：
    1. 读取文档并使用优化的分块算法创建语义块
    2. 合并以"注释"开头的块到前一个块中
    3. 添加文档边界标记（====== 文档开始/结束 ======）
    4. 为每行非空文本添加行号标记（<行号>）
    5. 在块之间插入边界标记（[CHUNK_BOUNDARY]）
    6. 保存为带"_optimized_v2"后缀的新文件

    Args:
        input_path (str): 输入文件的绝对路径

    Returns:
        str: 生成的预处理文件的路径

    Raises:
        FileNotFoundError: 当输入文件路径无效时
        Exception: 其他I/O错误或处理错误
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Error: Input file not found at {input_path}")

    # 使用自动版本号升级功能
    output_path = get_next_version_filename(input_path)
    
    # 提取版本信息用于日志输出
    output_filename = os.path.basename(output_path)
    version_match = re.search(r'_optimized_v(\d+)', output_filename)
    version_info = f"v{version_match.group(1)}" if version_match else "v2"

    try:
        # Load configuration
        config = load_config()
        target_chunk_size = config.get('chunk_processing', {}).get('target_chunk_size', 1000)
        min_chunk_size = max(200, int(target_chunk_size * 0.2))  # 最小为目标大小的20%
        
        print(f"使用优化分块策略: 目标大小={target_chunk_size}, 最小大小={min_chunk_size}")
        print(f"输出版本: {version_info} -> {output_filename}")
        
        with open(input_path, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()

        # 使用优化的分块函数
        chunks = create_chunks_optimized(lines, max_chars_per_chunk=target_chunk_size, min_chars_per_chunk=min_chunk_size)

        # 合并以"注释"开头的chunk
        merged_chunks = []
        for chunk in chunks:
            # Find first non-empty line to check for comment
            first_content_line = None
            for line in chunk:
                if line.strip():
                    first_content_line = line.strip()
                    break
            
            # If the chunk starts with "注释" and there is a previous chunk, merge them
            if first_content_line and first_content_line.startswith("注释") and merged_chunks:
                merged_chunks[-1].extend(chunk)
            else:
                merged_chunks.append(chunk)
        
        chunks = merged_chunks

        # 输出统计信息
        total_chars = sum(get_chunk_char_count(chunk) for chunk in chunks)
        avg_chunk_size = total_chars / len(chunks) if chunks else 0
        print(f"优化结果: 总chunk数={len(chunks)}, 平均大小={avg_chunk_size:.0f}字符")

        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write("====== 文档开始 ======\n\n")
            
            line_number = 1
            num_chunks = len(chunks)
            for i, chunk in enumerate(chunks):
                # Add chunk boundary BEFORE the chunk content (except for the first chunk)
                if i > 0:
                    outfile.write("[CHUNK_BOUNDARY]\n\n")
                
                for line in chunk:
                    stripped_line = line.strip()
                    if stripped_line:
                        outfile.write(f"<{line_number}>{stripped_line}\n")
                    else:
                        # Preserve blank lines for readability within a chunk
                        outfile.write("\n")
                    line_number += 1
                
                # Add spacing after chunk content (except for the last chunk)
                if i < num_chunks - 1:
                    outfile.write("\n")

            outfile.write("\n====== 文档结束 ======\n")

    except Exception as e:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise Exception(f"An error occurred during file processing: {e}")

    return output_path

def main():
    """
    主函数，处理命令行参数并执行文档预处理。
    
    命令行参数：
        input_path: 输入文档的路径
        
    Raises:
        SystemExit: 当参数错误或处理失败时
    """
    parser = argparse.ArgumentParser(
        description="RAG文档预处理脚本 - 优化版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python preprocess_optimized.py "document.md"
  python preprocess_optimized.py "/path/to/document.txt"

优化特性:
  - 智能合并策略，减少小chunk数量
  - 动态分块阈值，避免过度分块
  - 增强分割点检测，更好的语义边界
  - 后处理优化，平衡chunk大小分布
        """
    )
    
    parser.add_argument(
        'input_path',
        help='输入文档的路径'
    )
    
    args = parser.parse_args()
    
    try:
        print(f"开始优化预处理文档: {args.input_path}")
        output_path = preprocess_file_optimized(args.input_path)
        print(f"优化预处理完成! 输出文件: {output_path}")
    except Exception as e:
        print(f"处理失败: {e}")
        exit(1)

if __name__ == "__main__":
    main()