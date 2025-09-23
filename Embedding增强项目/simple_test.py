#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的子标题分块测试
"""

from subtitle_chunking_enhanced import (
    is_numeric_section, is_subtitle, is_first_subtitle,
    get_chunk_boundary_priority, optimize_subtitle_chunking,
    analyze_subtitle_distribution
)

def main():
    print("=== 简化测试开始 ===")
    
    # 测试基础功能
    test_cases = [
        "<1007>11维持治疗",
        "(1)化疗目的", 
        "(2)适应证",
        "（一）内分泌治疗",
        "### 子标题",
        "普通文本"
    ]
    
    print("\n基础功能测试:")
    for text in test_cases:
        print(f"'{text}' -> 数字标题:{is_numeric_section(text)}, 子标题:{is_subtitle(text)}, 第一子标题:{is_first_subtitle(text)}, 优先级:{get_chunk_boundary_priority(text)}")
    
    # 测试分块
    print("\n分块测试:")
    test_lines = [
        "<1007>11维持治疗",
        "维持治疗介绍",
        "(1)化疗目的",
        "化疗目的说明",
        "(2)适应证", 
        "适应证说明",
        "<1008>12随访管理",
        "(1)随访时间"
    ]
    
    boundaries = optimize_subtitle_chunking(test_lines, 100)
    print(f"分块边界: {boundaries}")
    
    # 分析分布
    analysis = analyze_subtitle_distribution(test_lines)
    print(f"\n分布分析: {analysis}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()