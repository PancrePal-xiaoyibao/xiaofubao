#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数字标题识别功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocess_enhanced import is_numeric_section, get_chunk_boundary_priority

def test_numeric_section_detection():
    """
    测试数字标题识别功能
    """
    print("=== 测试数字标题识别功能 ===")
    
    # 测试用例
    test_cases = [
        ("11维持治疗", True),
        ("12姑息治疗", True),
        ("1概述", True),
        ("2诊断", True),
        ("10乳房高位切线野", True),
        ("# 11维持治疗", True),
        ("## 12姑息治疗", True),
        ("（1）指南推荐", False),
        ("一、概述", False),
        ("这是普通文本", False),
        ("", False),
        ("123数字太多", False),  # 超过2位数字
        ("11", False),  # 只有数字没有中文
    ]
    
    print("测试 is_numeric_section 函数:")
    for text, expected in test_cases:
        result = is_numeric_section(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' -> {result} (期望: {expected})")
    
    print("\n测试 get_chunk_boundary_priority 函数:")
    for text, _ in test_cases:
        priority = get_chunk_boundary_priority(text)
        print(f"'{text}' -> 优先级: {priority}")

def test_with_real_document():
    """
    测试真实文档中的数字标题
    """
    print("\n=== 测试真实文档中的数字标题 ===")
    
    # 从增强版文档中查找数字标题
    enhanced_file = "/Users/qinxiaoqiang/Downloads/xiaofubao/Embedding增强项目/To_be_processed/乳腺癌诊疗指南2025_enhanced.md"
    
    if os.path.exists(enhanced_file):
        with open(enhanced_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        numeric_titles_found = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if is_numeric_section(stripped):
                numeric_titles_found.append((i, stripped))
        
        print(f"在增强版文档中找到 {len(numeric_titles_found)} 个数字标题:")
        for line_num, title in numeric_titles_found:
            priority = get_chunk_boundary_priority(title)
            print(f"  行 {line_num}: '{title}' (优先级: {priority})")
    else:
        print("增强版文档不存在")

if __name__ == "__main__":
    test_numeric_section_detection()
    test_with_real_document()