#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 preprocess_enhanced.py 对 <1007> 格式数字标题的支持
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocess_enhanced import is_numeric_section, get_chunk_boundary_priority

def test_numeric_section_detection():
    """测试数字标题识别功能"""
    print("=== 测试数字标题识别功能 ===")
    
    test_cases = [
        # 原有格式
        ("11维持治疗", True),
        ("12姑息治疗", True),
        ("1概述", True),
        ("99其他治疗", True),
        ("# 11维持治疗", True),
        ("## 12姑息治疗", True),
        
        # 新增的 <1007> 格式
        ("<1007>11维持治疗", True),
        ("<1007>12姑息治疗", True),
        ("<1007>1概述", True),
        ("<1007>99其他治疗", True),
        ("# <1007>11维持治疗", True),
        ("## <1007>12姑息治疗", True),
        
        # 负面测试用例
        ("这是普通文本", False),
        ("一、概述", False),  # 中文序号，不是数字标题
        ("第一章", False),
        ("<>11维持治疗", False),  # 格式错误
        ("<100711维持治疗", False),  # 格式错误
        ("1007>11维持治疗", False),  # 格式错误
    ]
    
    passed = 0
    total = len(test_cases)
    
    for text, expected in test_cases:
        result = is_numeric_section(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' -> {result} (期望: {expected})")
        if result == expected:
            passed += 1
    
    print(f"\n数字标题识别测试: {passed}/{total} 通过")
    return passed == total

def test_boundary_priority():
    """测试分块边界优先级功能"""
    print("\n=== 测试分块边界优先级功能 ===")
    
    test_cases = [
        # 数字标题应该有最高优先级 (1)
        ("11维持治疗", 1),
        ("<1007>11维持治疗", 1),
        ("# <1007>12姑息治疗", 1),
        
        # Markdown标题
        ("# 一级标题", 2),
        ("## 二级标题", 3),
        ("### 三级标题", 4),
        
        # 普通文本
        ("这是普通文本", 0),
        ("", 0),  # 空行
        ("   ", 0),  # 只有空格
    ]
    
    passed = 0
    total = len(test_cases)
    
    for text, expected in test_cases:
        result = get_chunk_boundary_priority(text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{text}' -> 优先级 {result} (期望: {expected})")
        if result == expected:
            passed += 1
    
    print(f"\n边界优先级测试: {passed}/{total} 通过")
    return passed == total

def test_integration():
    """集成测试：模拟真实文档处理"""
    print("\n=== 集成测试：模拟真实文档处理 ===")
    
    sample_text = """
# 肺癌治疗指南

## 概述
肺癌是常见的恶性肿瘤。

<1007>11维持治疗
维持治疗是指...

<1007>12姑息治疗
姑息治疗主要用于...

13其他治疗方案
其他治疗包括...

## 总结
本指南提供了...
"""
    
    lines = sample_text.strip().split('\n')
    boundaries = []
    
    for i, line in enumerate(lines):
        priority = get_chunk_boundary_priority(line)
        if priority > 0:
            boundaries.append((i, line.strip(), priority))
    
    print("检测到的分块边界:")
    for line_num, text, priority in boundaries:
        print(f"  行 {line_num}: '{text}' (优先级: {priority})")
    
    # 验证关键边界
    expected_boundaries = [
        "# 肺癌治疗指南",
        "## 概述", 
        "<1007>11维持治疗",
        "<1007>12姑息治疗",
        "13其他治疗方案",
        "## 总结"
    ]
    
    detected_texts = [text for _, text, _ in boundaries]
    
    print(f"\n期望检测到 {len(expected_boundaries)} 个边界")
    print(f"实际检测到 {len(detected_texts)} 个边界")
    
    missing = set(expected_boundaries) - set(detected_texts)
    extra = set(detected_texts) - set(expected_boundaries)
    
    if missing:
        print(f"遗漏的边界: {missing}")
    if extra:
        print(f"多余的边界: {extra}")
    
    success = len(missing) == 0 and len(extra) == 0
    print(f"集成测试: {'通过' if success else '失败'}")
    
    return success

def main():
    """运行所有测试"""
    print("开始测试 preprocess_enhanced.py 的增强功能\n")
    
    results = []
    results.append(test_numeric_section_detection())
    results.append(test_boundary_priority())
    results.append(test_integration())
    
    print(f"\n=== 测试总结 ===")
    print(f"总测试数: {len(results)}")
    print(f"通过数: {sum(results)}")
    print(f"失败数: {len(results) - sum(results)}")
    
    if all(results):
        print("🎉 所有测试通过！preprocess_enhanced.py 已成功支持 <1007> 格式数字标题")
    else:
        print("❌ 部分测试失败，需要进一步检查")
    
    return all(results)

if __name__ == "__main__":
    main()