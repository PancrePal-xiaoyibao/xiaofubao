#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试边界位置修复效果的验证脚本

检查修复后的分块文件中边界位置是否正确，特别关注：
1. [CHUNK_BOUNDARY] 是否正确放置在中文序号前
2. Markdown标题附近有中文序号时的处理
3. 边界位置的优先级是否正确

作者: RAG预处理专家
版本: 1.0
"""

import re
import os

def is_chinese_major_section(line):
    """检查是否为中文一级序号"""
    line = line.strip()
    chinese_major_pattern = r'^[一二三四五六七八九十]+、[^（）]*$'
    return bool(re.match(chinese_major_pattern, line))

def get_heading_level(line):
    """获取Markdown标题级别"""
    line = line.strip()
    if not line.startswith('#'):
        return 0
    level = 0
    for char in line:
        if char == '#':
            level += 1
        else:
            break
    if level > 0 and len(line) > level and line[level] == ' ':
        return level
    return 0

def analyze_boundary_positions(file_path):
    """分析分块边界位置"""
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    boundary_issues = []
    correct_boundaries = []
    acceptable_boundaries = []
    
    for i, line in enumerate(lines):
        if '[CHUNK_BOUNDARY]' in line:
            # 检查边界前后的内容，跳过空行找到实际内容
            prev_line = lines[i-1].strip() if i > 0 else ""
            
            # 找到边界后的第一个非空行
            next_line = ""
            next_line_index = i + 1
            while next_line_index < len(lines) and not lines[next_line_index].strip():
                next_line_index += 1
            if next_line_index < len(lines):
                next_line = lines[next_line_index].strip()
            
            # 检查下一行是否为中文序号 - 最优边界
            if next_line and is_chinese_major_section(next_line):
                correct_boundaries.append({
                    'line_num': i+1,
                    'next_content': next_line,
                    'type': '中文序号前（最优）'
                })
            # 检查下一行是否为Markdown标题
            elif next_line and get_heading_level(next_line) > 0:
                # 检查附近是否有中文序号
                has_nearby_chinese = False
                chinese_distance = None
                for j in range(max(0, i-5), min(len(lines), i+8)):
                    if j != i and is_chinese_major_section(lines[j].strip()):
                        has_nearby_chinese = True
                        chinese_distance = j - i
                        break
                
                if has_nearby_chinese:
                    # 如果附近有中文序号，这个边界可能不是最优的，但可以接受
                    acceptable_boundaries.append({
                        'line_num': i+1,
                        'next_content': next_line,
                        'type': f'Markdown标题前（附近{chinese_distance}行有中文序号）'
                    })
                else:
                    # 没有附近中文序号的Markdown标题，这是合理的边界
                    correct_boundaries.append({
                        'line_num': i+1,
                        'next_content': next_line,
                        'type': 'Markdown标题前（无附近中文序号）'
                    })
            else:
                # 检查是否是合理的分块点（比如段落开始、重要内容等）
                if next_line and (len(next_line) > 5 or next_line.startswith('#')):  # 包含短标题
                    acceptable_boundaries.append({
                        'line_num': i+1,
                        'next_content': next_line,
                        'type': '其他合理分块点'
                    })
                else:
                    boundary_issues.append({
                        'line_num': i+1,
                        'next_content': next_line,
                        'issue': '边界后内容不合适'
                    })
    
    total_boundaries = len(correct_boundaries) + len(acceptable_boundaries) + len(boundary_issues)
    
    print(f"=== 边界位置分析结果 ===")
    print(f"文件: {file_path}")
    print(f"总边界数: {total_boundaries}")
    print(f"最优边界: {len(correct_boundaries)}")
    print(f"可接受边界: {len(acceptable_boundaries)}")
    print(f"问题边界: {len(boundary_issues)}")
    
    if correct_boundaries:
        print(f"\n最优边界位置 (前{min(5, len(correct_boundaries))}个):")
        for boundary in correct_boundaries[:5]:
            print(f"  行{boundary['line_num']}: {boundary['type']} - {boundary['next_content'][:50]}...")
    
    if acceptable_boundaries:
        print(f"\n可接受边界位置 (前{min(5, len(acceptable_boundaries))}个):")
        for boundary in acceptable_boundaries[:5]:
            print(f"  行{boundary['line_num']}: {boundary['type']} - {boundary['next_content'][:50]}...")
    
    if boundary_issues:
        print(f"\n问题边界位置 (前{min(10, len(boundary_issues))}个):")
        for issue in boundary_issues[:10]:
            print(f"  行{issue['line_num']}: {issue['issue']} - {issue['next_content'][:50]}...")
    
    # 计算成功率
    success_rate = (len(correct_boundaries) + len(acceptable_boundaries)) / total_boundaries * 100 if total_boundaries > 0 else 0
    print(f"\n边界质量评估:")
    print(f"  最优边界率: {len(correct_boundaries)/total_boundaries*100:.1f}%")
    print(f"  总体成功率: {success_rate:.1f}%")
    
    return len(boundary_issues) < total_boundaries * 0.1  # 允许10%的问题边界

def main():
    """主函数"""
    # 测试修复后的文件
    test_files = [
        "To_be_processed/乳腺癌诊疗指南2025_optimized_v2.md"
    ]
    
    all_passed = True
    
    for file_path in test_files:
        print(f"\n{'='*60}")
        result = analyze_boundary_positions(file_path)
        all_passed = all_passed and result
        
        if result:
            print(f"✅ {file_path} - 边界位置正确")
        else:
            print(f"❌ {file_path} - 发现边界位置问题")
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 所有测试通过！边界位置修复成功！")
    else:
        print("⚠️  仍有边界位置问题需要进一步修复")

if __name__ == "__main__":
    main()