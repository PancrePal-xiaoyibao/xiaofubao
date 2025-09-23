#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分块边界修复方案验证脚本
验证修复方案的有效性，确保类似问题不再发生
"""

import re
from typing import List, Tuple, Optional

def get_chunk_boundary_priority(line: str) -> int:
    """获取分块边界优先级"""
    line = line.strip()
    
    # 中文一级序号（最高优先级）
    if re.match(r'^[一二三四五六七八九十]+、', line):
        return 10
    
    # 中文二级序号
    if re.match(r'^\([一二三四五六七八九十]+\)', line):
        return 8
    
    # 阿拉伯数字序号
    if re.match(r'^\d+\.', line):
        return 7
    
    # Markdown标题
    if line.startswith('#'):
        level = len(line) - len(line.lstrip('#'))
        return max(1, 6 - level)  # h1=5, h2=4, h3=3, h4=2, h5=1, h6=1
    
    return 0

def find_nearby_chinese_number(lines: List[str], start_idx: int, search_range: int = 10) -> Optional[Tuple[int, str]]:
    """在指定范围内查找中文序号"""
    for i in range(max(0, start_idx - search_range), 
                   min(len(lines), start_idx + search_range + 1)):
        line = lines[i].strip()
        if re.match(r'^[一二三四五六七八九十]+、', line):
            return i, line
    return None

def should_start_new_chunk_fixed(lines: List[str], idx: int) -> bool:
    """修复后的分块判断逻辑"""
    if idx == 0:
        return True
    
    current_line = lines[idx].strip()
    current_priority = get_chunk_boundary_priority(current_line)
    
    if current_priority == 0:
        return False
    
    # 中文一级序号始终开始新chunk（最高优先级）
    if current_priority == 10:
        return True
    
    # 对于Markdown标题，检查附近是否有中文一级序号
    if current_line.startswith('#'):
        nearby_chinese = find_nearby_chinese_number(lines, idx)
        if nearby_chinese:
            nearby_idx, nearby_line = nearby_chinese
            # 如果附近有中文序号，且中文序号在当前位置之后，则当前位置不应该分块
            if nearby_idx > idx:
                return False
    
    # 其他情况按优先级判断
    return current_priority >= 5

def detect_boundary_errors_fixed(lines: List[str]) -> List[dict]:
    """使用修复后的逻辑检测边界错误"""
    errors = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 检查Markdown标题
        if line.startswith('#'):
            # 查找附近的中文序号
            nearby_chinese = find_nearby_chinese_number(lines, i)
            if nearby_chinese:
                nearby_idx, nearby_line = nearby_chinese
                if nearby_idx > i:  # 中文序号在Markdown标题之后
                    errors.append({
                        'type': 'boundary_before_markdown_heading',
                        'current_position': i + 1,
                        'current_line': line,
                        'suggested_position': nearby_idx + 1,
                        'suggested_line': nearby_line,
                        'description': f'边界应放在中文序号"{nearby_line}"之前，而不是Markdown标题"{line}"之前'
                    })
    
    return errors

def apply_boundary_fix(lines: List[str]) -> List[List[str]]:
    """应用边界修复，返回正确的分块"""
    chunks = []
    current_chunk = []
    
    for i, line in enumerate(lines):
        if should_start_new_chunk_fixed(lines, i) and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
        current_chunk.append(line)
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def main():
    print("=== 分块边界修复方案验证 ===\n")
    
    # 测试案例：模拟乳腺癌诊疗指南的问题区域
    test_content = [
        "前面的内容...",
        "",
        "# 4.特殊时期的患者管理",
        "",
        "在特殊时期，患者管理需要特别注意...",
        "",
        "十二、循环肿瘤标志物检测和临床应用",
        "",
        "循环肿瘤标志物检测是..."
    ]
    
    print("1. 测试优先级系统")
    test_lines = [
        "十二、循环肿瘤标志物检测和临床应用",
        "# 4.特殊时期的患者管理",
        "1. 基本原则",
        "（一）检测方法"
    ]
    
    for line in test_lines:
        priority = get_chunk_boundary_priority(line)
        print(f"  '{line}' -> 优先级: {priority}")
    
    print("\n2. 测试附近搜索功能")
    for i, line in enumerate(test_content):
        if line.strip().startswith('#'):
            nearby = find_nearby_chinese_number(test_content, i)
            if nearby:
                nearby_idx, nearby_line = nearby
                print(f"  第{i+1}行 '{line}' -> 附近找到中文序号: 第{nearby_idx+1}行 - '{nearby_line}'")
    
    print("\n3. 检测边界错误（修复前）")
    errors = detect_boundary_errors_fixed(test_content)
    if errors:
        for error in errors:
            print(f"  - 错误类型: {error['type']}")
            print(f"  - 当前边界位置: 第{error['current_position']}行 - '{error['current_line']}'")
            print(f"  - 建议边界位置: 第{error['suggested_position']}行 - '{error['suggested_line']}'")
            print(f"  - 描述: {error['description']}")
    else:
        print("  未检测到边界错误")
    
    print("\n4. 应用修复方案")
    fixed_chunks = apply_boundary_fix(test_content)
    print("修复后的分块结构:")
    for i, chunk in enumerate(fixed_chunks):
        print(f"  Chunk {i}: {chunk}")
    
    print("\n5. 验证修复效果")
    # 检查分块边界是否正确
    boundary_positions = []
    for i, chunk in enumerate(fixed_chunks):
        if i > 0:  # 跳过第一个chunk
            start_line = chunk[0] if chunk else ""
            boundary_positions.append((i, start_line))
    
    print("分块边界位置:")
    for chunk_idx, line in boundary_positions:
        priority = get_chunk_boundary_priority(line)
        print(f"  Chunk {chunk_idx}: '{line}' (优先级: {priority})")
    
    # 验证修复是否成功：检查边界是否在中文序号前
    success = True
    for chunk_idx, line in boundary_positions:
        if line.strip() == "十二、循环肿瘤标志物检测和临床应用":
            print(f"\n✅ 边界正确放置在中文序号前: '{line}'")
        elif line.strip().startswith('#') and not re.match(r'^[一二三四五六七八九十]+、', line.strip()):
            # 检查这个Markdown标题后面是否有中文序号
            chunk = fixed_chunks[chunk_idx]
            has_chinese_after = False
            for chunk_line in chunk:
                if re.match(r'^[一二三四五六七八九十]+、', chunk_line.strip()):
                    has_chinese_after = True
                    break
            
            if has_chinese_after:
                print(f"\n❌ 边界错误：在Markdown标题前分块，但该chunk包含中文序号")
                success = False
            else:
                print(f"\n✅ 边界合理：Markdown标题前分块，且该chunk不包含中文序号")
    
    if success:
        print("\n✅ 修复成功，边界位置正确")
        return True
    else:
        print("\n❌ 修复失败，边界位置仍有问题")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n=== 验证结果 ===")
    if success:
        print("✅ 修复方案有效")
        exit(0)
    else:
        print("❌ 修复方案需要改进")
        exit(1)