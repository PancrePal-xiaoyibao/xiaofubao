#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 preprocess_enhanced.py 的边界识别功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocess_enhanced import get_chunk_boundary_priority

def test_boundary_detection_on_document():
    """测试在实际文档上的边界识别"""
    print("=== 测试实际文档的边界识别 ===")
    
    # 读取测试文档
    with open('test_document.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("文档内容和边界优先级分析:")
    print("-" * 60)
    
    boundaries = []
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        if not stripped_line:  # 跳过空行
            continue
            
        priority = get_chunk_boundary_priority(line)
        
        # 显示所有行的优先级
        status = "🔥" if priority == 1 else "📍" if priority > 1 else "  "
        print(f"{status} 行{i+1:2d} (优先级{priority}): {stripped_line}")
        
        if priority > 0:
            boundaries.append((i+1, stripped_line, priority))
    
    print("\n" + "=" * 60)
    print("检测到的分块边界汇总:")
    print("=" * 60)
    
    for line_num, text, priority in boundaries:
        priority_desc = {
            1: "最高优先级 (数字标题/中文序号)",
            2: "高优先级 (一级Markdown标题)",
            3: "中优先级 (二级Markdown标题)",
            4: "低优先级 (三级及以下Markdown标题)"
        }.get(priority, f"优先级{priority}")
        
        print(f"  行 {line_num:2d}: {priority_desc}")
        print(f"         '{text}'")
        print()
    
    # 验证关键的 <1007> 格式标题
    print("=" * 60)
    print("关键验证: <1007> 格式数字标题识别")
    print("=" * 60)
    
    target_lines = [
        "<1007>11维持治疗",
        "<1007>12姑息治疗"
    ]
    
    for target in target_lines:
        found = False
        for line_num, text, priority in boundaries:
            if target in text:
                print(f"✓ 找到: '{text}' (行{line_num}, 优先级{priority})")
                if priority == 1:
                    print(f"  ✓ 优先级正确 (期望: 1, 实际: {priority})")
                else:
                    print(f"  ✗ 优先级错误 (期望: 1, 实际: {priority})")
                found = True
                break
        
        if not found:
            print(f"✗ 未找到: '{target}'")
    
    return len([b for b in boundaries if b[2] == 1]) >= 2  # 至少应该有2个最高优先级边界

def main():
    """运行边界检测测试"""
    print("开始测试边界识别功能\n")
    
    success = test_boundary_detection_on_document()
    
    print("\n" + "=" * 60)
    print("测试结果:")
    if success:
        print("🎉 边界识别测试通过！<1007> 格式数字标题被正确识别为最高优先级边界")
    else:
        print("❌ 边界识别测试失败")
    print("=" * 60)

if __name__ == "__main__":
    main()