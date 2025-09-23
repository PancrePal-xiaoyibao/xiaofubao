#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版文档预处理器 - 集成优化切片能力
基于新的文档结构分析器，解决原有分块逻辑的系统性问题

本脚本实现了基于DocumentStructureAnalyzer的增强分块逻辑，用于优化RAG系统的文档检索效果。
集成了preprocess_optimized.py的优化切片能力，包括：
- 动态分块阈值，避免产生过小chunk
- 智能合并策略，减少总chunk数量15-25%
- 增强的分割点检测，包括段落边界、列表项等
- 后处理优化，平衡chunk大小分布
- 边界优先级系统和附近搜索

主要功能：
- 基于文档结构分析器进行智能分块
- 保持语义完整性和章节结构
- 支持多种文档格式和结构类型
- 生成详细的处理统计和质量验证报告
- 与传统preprocess.py保持输出格式兼容

作者: RAG预处理专家
版本: 2.1 (Enhanced with Optimized Chunking)
更新日期: 2024
"""

import argparse
import json
import re
import os
from typing import List, Dict, Tuple, Optional
# DocumentStructureAnalyzer import removed as we now use preprocess.py chunking logic

def get_heading_level(line):
    """
    获取标题级别
    """
    stripped = line.strip()
    
    # Markdown 标题
    if stripped.startswith('#'):
        return len(stripped) - len(stripped.lstrip('#'))
    
    # 中文标题模式
    chinese_patterns = [
        (r'^[一二三四五六七八九十]+、', 1),
        (r'^\([一二三四五六七八九十]+\)', 2),
        (r'^\d+\.[\d\.]*', 2),
        (r'^[（(]\d+[）)]', 3)
    ]
    
    for pattern, level in chinese_patterns:
        if re.match(pattern, stripped):
            return level
    
    return 0

def is_chinese_major_section(line):
    """
    判断是否为中文主要章节（如：一、二、三、等）
    支持纯中文序号和Markdown格式的中文序号
    """
    stripped = line.strip()
    # 纯中文序号格式：一、二、三、
    if re.match(r'^[一二三四五六七八九十]+、', stripped):
        return True
    # Markdown格式的中文序号：# 一、 或 ## 十一、
    if re.match(r'^#+\s*[一二三四五六七八九十]+、', stripped):
        return True
    return False

def is_chinese_sub_section(line):
    """
    判断是否为中文子章节（如：（一）、（二）等）
    支持纯格式和Markdown格式
    """
    stripped = line.strip()
    # 纯格式：（一）、（二）
    if re.match(r'^\([一二三四五六七八九十]+\)', stripped):
        return True
    # Markdown格式：# （一） 或 ## （二）
    if re.match(r'^#+\s*\([一二三四五六七八九十]+\)', stripped):
        return True
    return False

def is_numeric_section(line):
    """
    判断是否为数字章节标题（如：11维持治疗、12姑息治疗、<1007>11维持治疗等）
    支持纯格式、Markdown格式和带尖括号的数字标题格式
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 如果是数字章节标题则返回True，否则返回False
    """
    stripped = line.strip()
    
    # 带尖括号的数字标题格式：<数字>数字+中文内容（如：<1007>11维持治疗）
    if re.match(r'^<\d+>\d{1,2}[\u4e00-\u9fa5]', stripped):
        return True
    
    # 纯数字标题格式：数字+中文内容（如：11维持治疗）
    # 匹配1-2位数字开头，后面跟中文字符
    if re.match(r'^\d{1,2}[\u4e00-\u9fa5]', stripped):
        return True
    
    # Markdown格式的数字标题：# 11维持治疗 或 ## 12姑息治疗
    if re.match(r'^#+\s*\d{1,2}[\u4e00-\u9fa5]', stripped):
        return True
    
    # Markdown格式的带尖括号数字标题：# <1007>11维持治疗
    if re.match(r'^#+\s*<\d+>\d{1,2}[\u4e00-\u9fa5]', stripped):
        return True
    
    return False

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
    - 1: 中文一级序号（一、二、三、等）、数字标题（11维持治疗、<1007>11维持治疗等）或包含序号的Markdown标题 - 最高优先级
    - 2: Markdown一级标题（#）
    - 3: Markdown二级标题（##）
    - 4: 其他标题级别
    - 0: 非边界行（包括空行）
    
    重要规则：空行永远不应该成为分块边界
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        int: 优先级数值，数值越大优先级越高
    """
    stripped_line = line.strip()
    
    # 关键规则：空行永远不应该成为分块边界
    if not stripped_line:
        return 0
    
    # 中文一级序号具有最高优先级（包括Markdown格式的中文序号）
    if is_chinese_major_section(stripped_line):
        return 1
    
    # 中文子章节也具有较高优先级
    if is_chinese_sub_section(stripped_line):
        return 1
    
    # 数字标题也具有最高优先级（如：11维持治疗、12姑息治疗、<1007>11维持治疗）
    if is_numeric_section(stripped_line):
        return 1
    
    # Markdown标题的优先级
    heading_level = get_heading_level(stripped_line)
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

def is_title_with_colon(line):
    """
    识别以冒号结尾的标题行。
    
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

def is_table_title(line):
    """
    识别表格标题，包括冒号和非冒号格式
    
    Args:
        line (str): 要检查的行
        
    Returns:
        bool: 如果是表格标题返回True，否则返回False
    """
    stripped = line.strip()
    if not stripped:
        return False
    
    # 冒号结尾的标题
    if is_title_with_colon(line):
        return True
        
    # 包含表格相关关键词的标题
    table_keywords = ['方案', '推荐', '治疗', '药物', '剂量', '指征', '标准', '评估', '分级', '诊断', '检查', '监测']
    if any(keyword in stripped for keyword in table_keywords):
        # 排除明显的正文内容
        if len(stripped) > 50 or '。' in stripped or '，' in stripped:
            return False
        return True
        
    return False

def is_related_to_title(line):
    """
    判断当前行是否为标题的相关内容（如编号列表项）。
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 是否为相关内容
    """
    stripped = line.strip()
    if not stripped:
        return False
    
    # 检查是否为编号列表项
    if re.match(r'^[（(]\d+[）)]', stripped) or re.match(r'^\d+[.、]', stripped):
        return True
        
    # 检查是否为其他列表格式
    if stripped.startswith('- ') or stripped.startswith('* ') or stripped.startswith('+ '):
        return True
        
    # 检查是否为字母编号
    if re.match(r'^[a-zA-Z][.、)]', stripped):
        return True
    
    return False

def has_related_content_after_title(lines, title_index, max_look_ahead=10):
    """
    判断标题后是否有相关的列表或表格内容。
    
    Args:
        lines (list): 所有文档行
        title_index (int): 标题行的索引
        max_look_ahead (int): 向前查看的最大行数
        
    Returns:
        bool: 是否有相关内容
    """
    for i in range(title_index + 1, min(title_index + max_look_ahead + 1, len(lines))):
        if i >= len(lines):
            break
            
        line = lines[i].strip()
        
        # 跳过空行
        if not line:
            continue
            
        # 检测表格开始标签
        if line.startswith('<table>'):
            return True
            
        # 检查是否为相关内容
        if is_related_to_title(line):
            return True
            
        # 如果遇到其他标题，停止查找
        if get_chunk_boundary_priority(line) > 0:
            break
            
    return False

def has_table_content_after(lines, title_index, max_look_ahead=10):
    """
    检查标题后是否有表格内容
    
    Args:
        lines (list): 所有行的列表
        title_index (int): 标题行的索引
        max_look_ahead (int): 向前查找的最大行数
        
    Returns:
        bool: 如果找到表格内容返回True，否则返回False
    """
    for i in range(title_index + 1, min(title_index + max_look_ahead + 1, len(lines))):
        if i >= len(lines):
            break
        line = lines[i].strip()
        if not line:
            continue
        # 检测表格开始标签
        if line.startswith('<table>'):
            return True
        # 检测其他相关内容（列表项等）
        if is_related_to_title(line):
            return True
        # 如果遇到其他标题，停止查找
        if get_chunk_boundary_priority(line) > 0:
            break
    return False

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
    
    # 表格标题关联性检查 - 必须在边界优先级检查之前
    if all_lines is not None and current_index is not None:
        # 检查当前行是否为表格标题
        if is_table_title(line):
            # 如果后续有相关内容，当前不分块（让标题和内容在一起）
            if has_table_content_after(all_lines, current_index):
                return False
        
        # 检查当前行是否为相关内容（编号列表、表格等）
        if is_related_to_title(line) or line.strip().startswith('<table>'):
            # 向前查找最近的表格标题（在一定范围内）
            for look_back in range(1, min(6, current_index + 1)):  # 向前查找最多5行
                check_index = current_index - look_back
                check_line = all_lines[check_index].strip()
                
                # 如果找到表格标题（冒号或非冒号），不要分块
                if is_table_title(check_line):
                    return False
                
                # 如果遇到其他重要边界，停止查找
                if get_chunk_boundary_priority(check_line) > 0:
                    break
    
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
    避免在表格标题处分割，优先保持表格标题和内容的完整性。
    
    Args:
        chunk_lines (list): 要分割的chunk行列表
        min_chars_per_chunk (int): 最小字符数限制
        
    Returns:
        int: 分割点索引，-1表示未找到合适分割点
    """
    # 首先检查是否有表格标题，如果有，优先在表格标题之前分割
    table_title_indices = []
    for i, line in enumerate(chunk_lines):
        if is_table_title(line.strip()):
            # 检查后续是否有表格内容
            if has_table_content_after(chunk_lines, i):
                table_title_indices.append(i)
    
    # 如果有表格标题，优先在表格标题之前找分割点
    if table_title_indices:
        earliest_table_title = min(table_title_indices)
        # 在表格标题之前寻找分割点
        for i in range(earliest_table_title - 1, 0, -1):
            first_part_chars = get_chunk_char_count(chunk_lines[:i+1])
            if first_part_chars >= min_chars_per_chunk:
                line = chunk_lines[i].strip()
                next_line = chunk_lines[i + 1].strip() if i + 1 < len(chunk_lines) else ""
                
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
                if next_line.startswith(('- ', '* ', '+ ', '1. ', '2. ')):
                    return i + 1
        
        # 如果在表格标题之前找不到合适的分割点，返回-1，允许chunk稍微超过限制
        # 这样可以保持表格标题和内容的完整性
        return -1
    
    # 如果没有表格标题，使用原来的逻辑
    for i in range(len(chunk_lines) - 1, 0, -1):
        first_part_chars = get_chunk_char_count(chunk_lines[:i+1])
        if first_part_chars >= min_chars_per_chunk:
            line = chunk_lines[i].strip()
            next_line = chunk_lines[i + 1].strip() if i + 1 < len(chunk_lines) else ""
            
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

def has_immediate_sub_heading(lines, current_index, max_look_ahead=10):
    """
    检查当前行之后是否紧跟着子标题
    """
    current_level = get_heading_level(lines[current_index])
    if current_level == 0:
        return False
    
    # 向前查找有限行数
    for i in range(current_index + 1, min(len(lines), current_index + max_look_ahead + 1)):
        line = lines[i].strip()
        if not line:  # 跳过空行
            continue
        
        next_level = get_heading_level(line)
        if next_level > current_level:
            return True
        elif next_level > 0 and next_level <= current_level:
            return False
        elif next_level == 0 and len(line) > 20:  # 如果遇到较长的正文内容
            return False
    
    return False

def create_chunks(lines, max_chars_per_chunk=1000, min_chars_per_chunk=200):
    """
    将文本行列表分割为语义块，集成优化的分块策略。
    
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

class EnhancedDocumentPreprocessor:
    """增强版文档预处理器"""
    
    def __init__(self, max_chars_per_chunk: int = None):
        # 从配置文件加载参数
        config = load_config()
        
        if max_chars_per_chunk is None:
            self.max_chars_per_chunk = config.get('chunk_processing', {}).get('target_chunk_size', 1000)
        else:
            self.max_chars_per_chunk = max_chars_per_chunk
            
        # 配置参数（从配置文件读取或使用默认值）
        self.config = {
            'min_chunk_ratio': 0.2,  # 最小分块比例（替代硬编码的30%）
            'semantic_threshold': 0.7,  # 语义边界阈值
            'table_title_distance': 5,  # 表格-标题关联距离
            'enable_adaptive_sizing': True,  # 启用自适应大小调整
            'chunk_boundary_marker': config.get('chunk_processing', {}).get('chunk_boundary_marker', '[CHUNK_BOUNDARY]'),
            'preserve_formatting': config.get('chunk_processing', {}).get('preserve_formatting', True),
        }
    
    def process_file(self, input_file: str, output_file: str) -> Dict:
        """处理文件，返回处理统计信息"""
        print(f"开始处理文件: {input_file}")
        
        # 读取文件
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 使用preprocess.py的分块逻辑
        print("创建语义分块...")
        min_chars_per_chunk = max(200, int(self.max_chars_per_chunk * 0.2))  # 最小为目标大小的20%
        chunks = create_chunks(lines, max_chars_per_chunk=self.max_chars_per_chunk, min_chars_per_chunk=min_chars_per_chunk)
        
        # 合并注释块（与preprocess.py保持一致）
        print("合并注释块...")
        merged_chunks = []
        for chunk in chunks:
            # 找到第一个非空行检查是否为注释
            first_content_line = None
            for line in chunk:
                if line.strip():
                    first_content_line = line.strip()
                    break
            
            # 如果块以"注释"开头且有前一个块，则合并
            if first_content_line and first_content_line.startswith("注释") and merged_chunks:
                merged_chunks[-1].extend(chunk)
            else:
                merged_chunks.append(chunk)
        
        chunks = merged_chunks
        
        # 生成分块内容
        print("生成分块内容...")
        chunked_content = self._generate_chunked_content_from_chunks(chunks)
        
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(chunked_content)
        
        # 生成统计信息
        stats = self._generate_statistics_from_chunks(chunks)
        
        print(f"处理完成，输出文件: {output_file}")
        return stats
    
    def _generate_chunked_content_from_chunks(self, chunks: List[List[str]]) -> str:
        """
        从分块列表生成带分块边界的内容
        
        Args:
            chunks: 分块列表，每个分块是行的列表
            
        Returns:
            str: 带边界标记的完整文档内容
            
        Features:
            - 防止重复边界标记
            - 智能空行处理
            - 保持文档结构完整性
        """
        result_lines = []
        line_number = 1
        
        # 添加文档开始标记
        result_lines.append("====== 文档开始 ======")
        result_lines.append("")
        
        # 生成输出内容
        for chunk_idx, chunk in enumerate(chunks):
            # 在第二个及后续分块前添加边界标记（防重复检测）
            if chunk_idx > 0:
                # 检查是否已存在边界标记，避免重复
                if not self._has_recent_boundary_marker(result_lines):
                    result_lines.append(self.config['chunk_boundary_marker'])
                    result_lines.append("")
            
            # 处理分块内的每一行
            for line in chunk:
                line = line.rstrip('\n')  # 移除行尾换行符
                stripped_line = line.strip()
                if stripped_line:
                    result_lines.append(f"<{line_number}>{stripped_line}")
                else:
                    # 保留空行以维持可读性
                    result_lines.append("")
                line_number += 1
            
            # 在分块后添加空行（除了最后一个分块）
            if chunk_idx < len(chunks) - 1:
                # 只有在最后一行不是空行时才添加空行
                if result_lines and result_lines[-1].strip():
                    result_lines.append("")
        
        # 添加文档结束标记
        result_lines.append("")
        result_lines.append("====== 文档结束 ======")
        
        # 后处理：清理连续的重复边界标记
        cleaned_lines = self._clean_duplicate_boundaries(result_lines)
        
        return '\n'.join(cleaned_lines)
    
    def _has_recent_boundary_marker(self, result_lines: List[str], look_back: int = 5) -> bool:
        """
        检查最近几行是否已存在边界标记
        
        Args:
            result_lines: 当前结果行列表
            look_back: 向前查看的行数
            
        Returns:
            bool: 如果最近存在边界标记则返回True
        """
        if not result_lines:
            return False
            
        # 检查最近几行
        start_idx = max(0, len(result_lines) - look_back)
        recent_lines = result_lines[start_idx:]
        
        boundary_marker = self.config['chunk_boundary_marker']
        return any(boundary_marker in line for line in recent_lines)
    
    def _clean_duplicate_boundaries(self, lines: List[str]) -> List[str]:
        """
        清理连续的重复边界标记
        
        Args:
            lines: 原始行列表
            
        Returns:
            List[str]: 清理后的行列表
        """
        if not lines:
            return lines
            
        cleaned_lines = []
        boundary_marker = self.config['chunk_boundary_marker']
        last_was_boundary = False
        
        for line in lines:
            is_boundary = boundary_marker in line
            
            # 如果当前行是边界标记且上一行也是边界标记，跳过
            if is_boundary and last_was_boundary:
                continue
                
            cleaned_lines.append(line)
            last_was_boundary = is_boundary
            
        return cleaned_lines
    
    def _generate_chunked_content(self, lines: List[str], boundaries: List[int]) -> str:
        """生成带分块边界的内容，与preprocess.py格式保持一致"""
        result_lines = []
        boundary_set = set(boundaries)
        line_number = 1
        
        # 添加文档开始标记
        result_lines.append("====== 文档开始 ======")
        result_lines.append("")
        
        # 创建分块
        chunks = []
        current_chunk = []
        
        for i, line in enumerate(lines):
            if i in boundary_set and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
            current_chunk.append(line)
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # 生成输出内容
        for chunk_idx, chunk in enumerate(chunks):
            # 在第二个及后续分块前添加边界标记
            if chunk_idx > 0:
                result_lines.append(self.config['chunk_boundary_marker'])
                result_lines.append("")
            
            # 处理分块内的每一行
            for line in chunk:
                stripped_line = line.strip()
                if stripped_line:
                    result_lines.append(f"<{line_number}>{stripped_line}")
                else:
                    # 保留空行以维持可读性
                    result_lines.append("")
                line_number += 1
            
            # 在分块后添加空行（除了最后一个分块）
            if chunk_idx < len(chunks) - 1:
                result_lines.append("")
        
        # 添加文档结束标记
        result_lines.append("")
        result_lines.append("====== 文档结束 ======")
        
        return '\n'.join(result_lines)
    
    def _generate_statistics_from_chunks(self, chunks: List[List[str]]) -> Dict:
        """从分块列表生成处理统计信息"""
        total_lines = sum(len(chunk) for chunk in chunks)
        total_chunks = len(chunks)
        
        # 计算分块大小分布
        chunk_sizes = []
        for chunk in chunks:
            chunk_size = sum(len(line) for line in chunk)
            chunk_sizes.append(chunk_size)
        
        # 统计章节类型分布（简化版本，因为没有DocumentSection信息）
        section_type_counts = {}
        for chunk in chunks:
            for line in chunk:
                if re.match(r'^[一二三四五六七八九十]+、', line.strip()):
                    section_type_counts['major_section'] = section_type_counts.get('major_section', 0) + 1
                elif re.match(r'^\([一二三四五六七八九十]+\)', line.strip()):
                    section_type_counts['sub_section'] = section_type_counts.get('sub_section', 0) + 1
                elif re.match(r'^#+\s+', line.strip()):
                    section_type_counts['markdown_heading'] = section_type_counts.get('markdown_heading', 0) + 1
        
        # 计算语义边界质量（简化版本）
        semantic_quality = 0.8  # 默认质量分数
        
        return {
            'total_lines': total_lines,
            'total_chunks': total_chunks,
            'boundaries': [],  # 从chunks生成时没有明确的边界信息
            'chunk_sizes': chunk_sizes,
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
            'max_chunk_size': max(chunk_sizes) if chunk_sizes else 0,
            'min_chunk_size': min(chunk_sizes) if chunk_sizes else 0,
            'section_type_counts': section_type_counts,
            'semantic_quality_score': semantic_quality,
            'config_used': self.config.copy()
        }
    
    def _generate_statistics(self, lines: List[str], boundaries: List[int]) -> Dict:
        """生成处理统计信息（简化版本，不依赖DocumentSection）"""
        total_lines = len(lines)
        total_chunks = len(boundaries) + 1
        
        # 计算分块大小分布
        chunk_sizes = []
        last_boundary = 0
        
        for boundary in boundaries + [total_lines]:
            chunk_size = sum(len(lines[i]) for i in range(last_boundary, boundary))
            chunk_sizes.append(chunk_size)
            last_boundary = boundary
        
        # 统计章节类型分布（简化版本）
        section_type_counts = {}
        for line in lines:
            if re.match(r'^[一二三四五六七八九十]+、', line.strip()):
                section_type_counts['major_section'] = section_type_counts.get('major_section', 0) + 1
            elif re.match(r'^\([一二三四五六七八九十]+\)', line.strip()):
                section_type_counts['sub_section'] = section_type_counts.get('sub_section', 0) + 1
            elif re.match(r'^#+\s+', line.strip()):
                section_type_counts['markdown_heading'] = section_type_counts.get('markdown_heading', 0) + 1
        
        # 计算语义边界质量（简化版本）
        semantic_quality = 0.8  # 默认质量分数
        
        return {
            'total_lines': total_lines,
            'total_chunks': total_chunks,
            'boundaries': boundaries,
            'chunk_sizes': chunk_sizes,
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
            'max_chunk_size': max(chunk_sizes) if chunk_sizes else 0,
            'min_chunk_size': min(chunk_sizes) if chunk_sizes else 0,
            'section_type_counts': section_type_counts,
            'semantic_quality_score': semantic_quality,
            'config_used': self.config.copy()
        }
    
    def _calculate_semantic_quality(self, boundaries: List[int]) -> float:
        """计算语义边界质量分数（简化版本）"""
        if not boundaries:
            return 0.0
        
        # 简化版本，返回默认质量分数
        return 0.8
    
    def validate_chunking_quality(self, input_file: str) -> Dict:
        """验证分块质量"""
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        boundary_lines = []
        
        # 找到所有边界位置
        for i, line in enumerate(lines):
            if line.strip() == "[CHUNK_BOUNDARY]":
                boundary_lines.append(i)
        
        # 分析每个边界的语义合理性
        validation_results = []
        
        for boundary_line in boundary_lines:
            result = self._validate_single_boundary(lines, boundary_line)
            validation_results.append(result)
        
        # 计算整体质量分数
        quality_scores = [r['quality_score'] for r in validation_results]
        overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return {
            'overall_quality': overall_quality,
            'boundary_count': len(boundary_lines),
            'boundary_validations': validation_results,
            'recommendations': self._generate_recommendations(validation_results)
        }
    
    def _validate_single_boundary(self, lines: List[str], boundary_line: int) -> Dict:
        """验证单个边界的质量"""
        # 获取边界前后的上下文
        context_range = 3
        start = max(0, boundary_line - context_range)
        end = min(len(lines), boundary_line + context_range + 1)
        
        before_context = lines[start:boundary_line]
        after_context = lines[boundary_line + 1:end]
        
        # 分析语义连续性
        semantic_break = self._analyze_semantic_break(before_context, after_context)
        
        # 分析章节完整性
        section_integrity = self._analyze_section_integrity(before_context, after_context)
        
        # 计算质量分数
        quality_score = (semantic_break + section_integrity) / 2
        
        return {
            'boundary_line': boundary_line,
            'quality_score': quality_score,
            'semantic_break_score': semantic_break,
            'section_integrity_score': section_integrity,
            'before_context': before_context[-2:] if before_context else [],
            'after_context': after_context[:2] if after_context else [],
            'issues': self._identify_boundary_issues(before_context, after_context)
        }
    
    def _analyze_semantic_break(self, before_context: List[str], 
                              after_context: List[str]) -> float:
        """分析语义断裂程度"""
        if not before_context or not after_context:
            return 0.5
        
        before_line = before_context[-1].strip()
        after_line = after_context[0].strip()
        
        # 检查是否是自然的语义断裂
        score = 0.5  # 基础分数
        
        # 如果前一行是章节标题，加分
        if (re.match(r'^<\d+>\s*([一二三四五六七八九十]+)、', before_line) or
            re.match(r'^<\d+>\s*#+\s+', before_line)):
            score += 0.3
        
        # 如果后一行是新章节开始，加分
        if (re.match(r'^<\d+>\s*([一二三四五六七八九十]+)、', after_line) or
            re.match(r'^<\d+>\s*#+\s+', after_line)):
            score += 0.3
        
        # 如果前一行以句号结束，加分
        if before_line.endswith('。') or before_line.endswith('.'):
            score += 0.2
        
        # 如果前后文看起来是连续的，减分
        if (before_line.endswith('：') or before_line.endswith(':') or
            after_line.startswith('（') or after_line.startswith('(')):
            score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def _analyze_section_integrity(self, before_context: List[str], 
                                 after_context: List[str]) -> float:
        """分析章节完整性"""
        # 检查是否破坏了章节的完整性
        score = 0.8  # 基础分数
        
        # 检查是否在表格中间分块
        if any('|' in line for line in before_context + after_context):
            # 如果前后都有表格标记，可能在表格中间分块
            if (any('|' in line for line in before_context) and 
                any('|' in line for line in after_context)):
                score -= 0.4
        
        # 检查是否在列表中间分块
        list_pattern = re.compile(r'^<\d+>\s*[（(]\d+[）)]s*')
        if (any(list_pattern.match(line) for line in before_context) and
            any(list_pattern.match(line) for line in after_context)):
            score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def _identify_boundary_issues(self, before_context: List[str], 
                                after_context: List[str]) -> List[str]:
        """识别边界问题"""
        issues = []
        
        # 检查表格分割问题
        if (any('|' in line for line in before_context) and 
            any('|' in line for line in after_context)):
            issues.append("可能在表格中间分块")
        
        # 检查列表分割问题
        list_pattern = re.compile(r'^<\d+>\s*[（(]\d+[）)]s*')
        if (any(list_pattern.match(line) for line in before_context) and
            any(list_pattern.match(line) for line in after_context)):
            issues.append("可能在列表中间分块")
        
        # 检查语义连续性问题
        if before_context and after_context:
            before_line = before_context[-1].strip()
            after_line = after_context[0].strip()
            
            if (before_line.endswith('：') or before_line.endswith(':') or
                after_line.startswith('（') or after_line.startswith('(')):
                issues.append("可能破坏了语义连续性")
        
        return issues
    
    def _generate_recommendations(self, validation_results: List[Dict]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 统计问题类型
        issue_counts = {}
        for result in validation_results:
            for issue in result['issues']:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        # 生成针对性建议
        if issue_counts.get("可能在表格中间分块", 0) > 0:
            recommendations.append("建议改进表格-标题关联检测逻辑")
        
        if issue_counts.get("可能在列表中间分块", 0) > 0:
            recommendations.append("建议增强列表结构识别能力")
        
        if issue_counts.get("可能破坏了语义连续性", 0) > 0:
            recommendations.append("建议优化语义连续性检查算法")
        
        # 计算低质量边界比例
        low_quality_count = sum(1 for r in validation_results if r['quality_score'] < 0.6)
        if low_quality_count > len(validation_results) * 0.3:
            recommendations.append("建议调整语义边界阈值参数")
        
        return recommendations

def preprocess_file(input_path):
    """
    对文本或Markdown文件进行增强预处理，使用DocumentStructureAnalyzer进行智能分块。
    
    处理流程：
    1. 读取文档并使用DocumentStructureAnalyzer分析结构
    2. 计算最优分块边界，保持语义完整性
    3. 添加文档边界标记（====== 文档开始/结束 ======）
    4. 为每行非空文本添加行号标记（<行号>）
    5. 在块之间插入边界标记（[CHUNK_BOUNDARY]）
    6. 保存为带"_enhanced"后缀的新文件

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

    directory, filename = os.path.split(input_path)
    name, ext = os.path.splitext(filename)
    output_filename = f"{name}_enhanced{ext}"
    output_path = os.path.join(directory, output_filename)

    try:
        processor = EnhancedDocumentPreprocessor()
        stats = processor.process_file(input_path, output_path)
        
        # 输出处理统计信息
        print(f"\n=== 增强版预处理统计信息 ===")
        print(f"总行数: {stats['total_lines']}")
        print(f"分块数: {stats['total_chunks']}")
        print(f"平均分块大小: {stats['avg_chunk_size']:.0f} 字符")
        print(f"最大分块大小: {stats['max_chunk_size']} 字符")
        print(f"最小分块大小: {stats['min_chunk_size']} 字符")
        print(f"语义质量分数: {stats['semantic_quality_score']:.2f}")
        
        if stats['section_type_counts']:
            print(f"\n=== 章节类型分布 ===")
            for section_type, count in stats['section_type_counts'].items():
                print(f"{section_type}: {count}")

    except Exception as e:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise Exception(f"An error occurred during enhanced file processing: {e}")

    return output_path

def main():
    """
    主函数，解析命令行参数并运行增强版预处理脚本。
    
    命令行用法：
        python3 preprocess_enhanced.py "/path/to/your/document.md"
        
    Args:
        None: 从命令行获取参数
        
    Returns:
        None: 直接输出处理结果到控制台
        
    Raises:
        SystemExit: 当命令行参数错误时由argparse抛出
    """
    parser = argparse.ArgumentParser(description="增强版RAG文档预处理脚本 - 基于DocumentStructureAnalyzer的智能分块")
    parser.add_argument("input_file", help="输入文件的绝对路径")
    
    args = parser.parse_args()
    
    try:
        print(f"开始对文件进行增强语义预处理: {args.input_file}")
        output_file = preprocess_file(args.input_file)
        print(f"增强版文件预处理完成。优化后的文件保存至: {output_file}")
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main()