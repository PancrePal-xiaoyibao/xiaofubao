#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子标题识别和分块优先级逻辑实现

本模块实现了数字标题和子标题的识别、分块优先级评估和优化策略，
专门用于处理医学文档中的(1)(2)格式子标题分块问题。

主要功能：
1. 数字标题识别（如"11维持治疗"）
2. 子标题识别（如"(1)"、"（一）"等格式）
3. 分块边界优先级评估
4. 主标题与子标题关联性保护
5. 优化的分块策略实现

作者：AI Assistant
创建时间：2025年1月24日
"""

import re
from typing import List, Tuple, Dict, Optional, Union


def is_numeric_section(line: str) -> bool:
    """
    识别数字章节标题，支持纯格式和Markdown格式
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 是否为数字章节标题
        
    Examples:
        >>> is_numeric_section("<1007>11维持治疗")
        True
        >>> is_numeric_section("# 11维持治疗")
        True
        >>> is_numeric_section("普通文本")
        False
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


def is_subtitle(line: str) -> bool:
    """
    判断是否为子标题，支持多种格式
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 是否为子标题
        
    Examples:
        >>> is_subtitle("(1)化疗目的")
        True
        >>> is_subtitle("（一）内分泌治疗")
        True
        >>> is_subtitle("### 子标题")
        True
        >>> is_subtitle("普通文本")
        False
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


def is_chinese_major_section(line: str) -> bool:
    """
    判断是否为中文一级序号（如"一、"、"二、"）
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 是否为中文一级序号
    """
    stripped = line.strip()
    if not stripped:
        return False
    
    # 中文一级序号格式
    return bool(re.match(r'^[一二三四五六七八九十]+[、．]', stripped))


def get_heading_level(line: str) -> int:
    """
    获取Markdown标题级别
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        int: 标题级别（1-6），如果不是标题返回0
    """
    stripped = line.strip()
    if not stripped.startswith('#'):
        return 0
    
    level = 0
    for char in stripped:
        if char == '#':
            level += 1
        else:
            break
    
    return min(level, 6) if level <= 6 else 0


def get_chunk_boundary_priority(line: str) -> int:
    """
    获取分块边界的优先级，数字标题具有最高优先级
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        int: 优先级（数字越大优先级越高，0表示无优先级）
    """
    # 数字标题具有最高优先级
    if is_numeric_section(line):
        return 10
    
    # 中文一级序号
    if is_chinese_major_section(line):
        return 10
    
    # Markdown H1、H2标题
    heading_level = get_heading_level(line)
    if heading_level == 1:
        return 9
    elif heading_level == 2:
        return 8
    
    # 子标题具有中等优先级
    if is_subtitle(line):
        return 5
    
    # Markdown H3及以下标题
    if heading_level >= 3:
        return 3
    
    return 0


def is_first_subtitle(line: str) -> bool:
    """
    判断是否为第一个子标题（如"(1)"、"（1）"等）
    
    Args:
        line (str): 要检查的文本行
        
    Returns:
        bool: 是否为第一个子标题
    """
    stripped = line.strip()
    if not stripped:
        return False
    
    # 检查是否为第一个数字子标题
    return bool(re.match(r'^(\([1１]\)|（[1１]）|[1１]\.|[1１]、)', stripped))


def should_split_at_subtitle(current_chunk_size: int, subtitle_line: str, 
                           max_chunk_size: int, is_first_sub: bool = False) -> bool:
    """
    决定是否在子标题处分块
    
    Args:
        current_chunk_size (int): 当前chunk的字符数
        subtitle_line (str): 子标题行内容
        max_chunk_size (int): 最大chunk大小
        is_first_sub (bool): 是否为第一个子标题
        
    Returns:
        bool: 是否应该分块
    """
    # 第一个子标题(1)不分块，与主标题保持在一起
    if is_first_sub or is_first_subtitle(subtitle_line):
        return False
    
    # 如果当前chunk大小超过80%阈值，在子标题处分块
    if current_chunk_size > max_chunk_size * 0.8:
        return True
    
    return False


def detect_title_subtitle_relationship(lines: List[str], title_index: int) -> Tuple[bool, int]:
    """
    检测主标题与子标题的关系
    
    Args:
        lines (List[str]): 所有文档行
        title_index (int): 主标题行的索引
        
    Returns:
        Tuple[bool, int]: (是否有子标题, 第一个子标题的索引)
    """
    # 检查后续5行内是否有子标题
    for i in range(title_index + 1, min(title_index + 6, len(lines))):
        if i >= len(lines):
            break
            
        line = lines[i].strip()
        if not line:
            continue
            
        # 检测子标题格式
        if is_subtitle(line):
            return True, i
            
        # 如果遇到其他主标题，停止查找
        if get_chunk_boundary_priority(line) >= 8:  # H2级别以上
            break
            
    return False, -1


def protect_title_subtitle_cohesion(lines: List[str], chunk_boundaries: List[int]) -> List[int]:
    """
    保护主标题与第一个子标题的关联性
    
    Args:
        lines (List[str]): 所有文档行
        chunk_boundaries (List[int]): 当前的分块边界列表
        
    Returns:
        List[int]: 优化后的分块边界列表
    """
    protected_boundaries = []
    
    for boundary in chunk_boundaries:
        # 检查边界是否在第一个子标题之前
        if boundary < len(lines) and is_subtitle(lines[boundary]):
            # 检查是否为第一个子标题
            if is_first_subtitle(lines[boundary]):
                # 向前查找主标题
                found_main_title = False
                for i in range(boundary - 1, max(boundary - 6, 0), -1):
                    if get_chunk_boundary_priority(lines[i]) >= 8:  # 主标题级别
                        found_main_title = True
                        break
                
                # 如果找到主标题，不在第一个子标题前分块
                if found_main_title:
                    continue
                
        protected_boundaries.append(boundary)
    
    return protected_boundaries


def optimize_subtitle_chunking(lines: List[str], max_chunk_size: int) -> List[int]:
    """
    优化子标题分块策略
    
    Args:
        lines (List[str]): 所有文档行
        max_chunk_size (int): 最大chunk大小
        
    Returns:
        List[int]: 优化后的分块边界列表
    """
    boundaries = []
    current_chunk_size = 0
    in_title_subtitle_group = False
    first_subtitle_protected = False
    
    for i, line in enumerate(lines):
        line_size = len(line)
        current_chunk_size += line_size
        
        # 检测主标题
        priority = get_chunk_boundary_priority(line)
        if priority >= 8:  # 主标题级别
            if current_chunk_size > line_size:  # 不在开头时才添加边界
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
        if line.strip() and not is_subtitle(line) and priority < 3:
            in_title_subtitle_group = False
    
    return boundaries


def analyze_subtitle_distribution(lines: List[str]) -> Dict[str, Union[int, List[str]]]:
    """
    分析文档中子标题的分布情况
    
    Args:
        lines (List[str]): 所有文档行
        
    Returns:
        Dict[str, Union[int, List[str]]]: 分析结果统计
    """
    result = {
        'total_lines': len(lines),
        'numeric_titles': 0,
        'subtitles': 0,
        'first_subtitles': 0,
        'subtitle_examples': [],
        'numeric_title_examples': []
    }
    
    for i, line in enumerate(lines):
        if is_numeric_section(line):
            result['numeric_titles'] += 1
            if len(result['numeric_title_examples']) < 5:
                result['numeric_title_examples'].append(f"Line {i+1}: {line.strip()}")
        
        if is_subtitle(line):
            result['subtitles'] += 1
            if len(result['subtitle_examples']) < 10:
                result['subtitle_examples'].append(f"Line {i+1}: {line.strip()}")
            
            if is_first_subtitle(line):
                result['first_subtitles'] += 1
    
    return result


def validate_chunking_quality(chunks: List[List[str]], original_lines: List[str]) -> Dict[str, Union[int, float, List[str]]]:
    """
    验证分块质量，特别关注子标题处理
    
    Args:
        chunks (List[List[str]]): 分块结果
        original_lines (List[str]): 原始文档行
        
    Returns:
        Dict[str, Union[int, float, List[str]]]: 质量评估结果
    """
    result = {
        'total_chunks': len(chunks),
        'separated_first_subtitles': 0,
        'quality_score': 0.0,
        'issues': []
    }
    
    # 检查第一个子标题是否被错误分离
    for i, chunk in enumerate(chunks):
        if not chunk:
            continue
            
        first_line = chunk[0].strip()
        if is_first_subtitle(first_line):
            # 检查前一个chunk是否包含相关主标题
            if i > 0:
                prev_chunk = chunks[i-1]
                has_main_title = any(get_chunk_boundary_priority(line) >= 8 for line in prev_chunk)
                if has_main_title:
                    result['separated_first_subtitles'] += 1
                    result['issues'].append(f"Chunk {i}: 第一个子标题被分离: {first_line}")
    
    # 计算质量分数
    if result['total_chunks'] > 0:
        separation_rate = result['separated_first_subtitles'] / result['total_chunks']
        result['quality_score'] = max(0.0, 1.0 - separation_rate)
    
    return result


if __name__ == "__main__":
    # 测试代码
    test_lines = [
        "<1007>11维持治疗",
        "(1)化疗目的",
        "(2)适应证",
        "普通文本内容",
        "（一）内分泌治疗",
        "### 子标题示例",
        "更多内容"
    ]
    
    print("=== 子标题识别测试 ===")
    for i, line in enumerate(test_lines):
        print(f"Line {i+1}: {line}")
        print(f"  - 数字标题: {is_numeric_section(line)}")
        print(f"  - 子标题: {is_subtitle(line)}")
        print(f"  - 第一个子标题: {is_first_subtitle(line)}")
        print(f"  - 优先级: {get_chunk_boundary_priority(line)}")
        print()
    
    print("=== 分布分析测试 ===")
    analysis = analyze_subtitle_distribution(test_lines)
    for key, value in analysis.items():
        print(f"{key}: {value}")