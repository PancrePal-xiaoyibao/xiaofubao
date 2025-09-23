#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复边界标记检测脚本
功能：检测文档中所有重复的[CHUNK_BOUNDARY]标记位置
作者：AI Assistant
"""

import re
import sys
from typing import List, Tuple, Dict

def detect_duplicate_boundaries(file_path: str) -> Dict[str, any]:
    """
    检测文档中重复的[CHUNK_BOUNDARY]标记
    
    参数:
        file_path (str): 文档文件路径
        
    返回:
        Dict[str, any]: 包含检测结果的字典
        
    异常:
        FileNotFoundError: 文件不存在
        UnicodeDecodeError: 文件编码问题
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 不存在")
        return {}
    except UnicodeDecodeError:
        print(f"错误：文件 {file_path} 编码问题")
        return {}
    
    # 查找所有[CHUNK_BOUNDARY]标记的位置
    boundary_positions = []
    for i, line in enumerate(lines, 1):
        if '[CHUNK_BOUNDARY]' in line:
            boundary_positions.append(i)
    
    # 检测重复的边界标记（连续的空行中有多个边界标记）
    duplicate_groups = []
    current_group = []
    
    for i in range(len(boundary_positions)):
        line_num = boundary_positions[i]
        
        # 检查当前边界标记周围的情况
        start_check = max(0, line_num - 3)
        end_check = min(len(lines), line_num + 3)
        
        # 在当前边界标记附近查找其他边界标记
        nearby_boundaries = []
        for j in range(start_check, end_check):
            if j != line_num - 1 and '[CHUNK_BOUNDARY]' in lines[j]:
                nearby_boundaries.append(j + 1)
        
        if nearby_boundaries:
            # 找到重复的边界标记
            group = [line_num] + nearby_boundaries
            group = sorted(list(set(group)))  # 去重并排序
            
            # 检查是否已经在某个组中
            found_in_existing = False
            for existing_group in duplicate_groups:
                if any(pos in existing_group for pos in group):
                    # 合并到现有组
                    existing_group.extend(group)
                    existing_group = sorted(list(set(existing_group)))
                    found_in_existing = True
                    break
            
            if not found_in_existing:
                duplicate_groups.append(group)
    
    # 去重duplicate_groups
    final_groups = []
    for group in duplicate_groups:
        is_subset = False
        for existing in final_groups:
            if set(group).issubset(set(existing)):
                is_subset = True
                break
        if not is_subset:
            # 检查是否需要合并
            merged = False
            for i, existing in enumerate(final_groups):
                if set(group) & set(existing):  # 有交集
                    final_groups[i] = sorted(list(set(existing + group)))
                    merged = True
                    break
            if not merged:
                final_groups.append(group)
    
    return {
        'total_boundaries': len(boundary_positions),
        'boundary_positions': boundary_positions,
        'duplicate_groups': final_groups,
        'duplicate_count': len(final_groups)
    }

def analyze_duplicate_context(file_path: str, duplicate_groups: List[List[int]]) -> None:
    """
    分析重复边界标记的上下文
    
    参数:
        file_path (str): 文档文件路径
        duplicate_groups (List[List[int]]): 重复边界标记组
        
    异常:
        FileNotFoundError: 文件不存在
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 不存在")
        return
    
    print("\n=== 重复边界标记上下文分析 ===")
    for i, group in enumerate(duplicate_groups, 1):
        print(f"\n重复组 {i}: 行号 {group}")
        
        # 显示每个重复位置的上下文
        for line_num in group:
            print(f"\n--- 行 {line_num} 上下文 ---")
            start = max(0, line_num - 4)
            end = min(len(lines), line_num + 3)
            
            for j in range(start, end):
                marker = ">>> " if j == line_num - 1 else "    "
                print(f"{marker}{j+1:4d}: {lines[j].rstrip()}")

def main():
    """
    主函数：执行重复边界标记检测
    """
    if len(sys.argv) != 2:
        print("用法: python detect_duplicate_boundaries.py <文件路径>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print(f"检测文件: {file_path}")
    print("=" * 50)
    
    # 检测重复边界标记
    result = detect_duplicate_boundaries(file_path)
    
    if not result:
        return
    
    print(f"总边界标记数: {result['total_boundaries']}")
    print(f"重复组数: {result['duplicate_count']}")
    
    if result['duplicate_count'] > 0:
        print(f"\n发现 {result['duplicate_count']} 组重复的边界标记:")
        for i, group in enumerate(result['duplicate_groups'], 1):
            print(f"  组 {i}: 行号 {group}")
        
        # 分析上下文
        analyze_duplicate_context(file_path, result['duplicate_groups'])
        
        print(f"\n建议:")
        print("1. 检查预处理逻辑是否存在重复插入边界标记的问题")
        print("2. 清理重复的边界标记")
        print("3. 添加验证逻辑防止未来出现重复")
    else:
        print("\n✅ 未发现重复的边界标记")

if __name__ == "__main__":
    main()