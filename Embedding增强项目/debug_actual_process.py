#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocess_enhanced import (
    should_start_new_chunk, 
    is_table_title, 
    has_table_content_after,
    get_chunk_char_count,
    find_better_split_point,
    create_chunks
)

def debug_actual_chunking_process():
    """模拟实际的分块处理过程"""
    
    # 读取原始文档，找到表格标题附近的内容
    input_file = "/Users/qinxiaoqiang/Downloads/xiaofubao/Embedding增强项目/To_be_processed/乳腺癌诊疗指南2025.md"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 去除换行符
    lines = [line.rstrip('\n') for line in lines]
    
    # 找到表格标题的位置
    table_title_line = "复发或转移性乳腺癌常用的单药化疗方案"
    table_title_index = -1
    
    for i, line in enumerate(lines):
        if table_title_line in line:
            table_title_index = i
            break
    
    if table_title_index == -1:
        print("未找到表格标题")
        return
    
    print(f"=== 实际分块过程调试 ===")
    print(f"表格标题位置: 第{table_title_index + 1}行")
    print(f"表格标题: {lines[table_title_index]}")
    print()
    
    # 模拟分块过程
    max_chars_per_chunk = 1000
    min_chars_per_chunk = 200
    
    # 获取表格标题前的内容作为当前chunk
    start_index = max(0, table_title_index - 20)  # 取前20行作为上下文
    current_chunk_lines = lines[start_index:table_title_index]
    
    print(f"当前chunk内容 (第{start_index + 1}-{table_title_index}行):")
    for i, line in enumerate(current_chunk_lines[-5:]):  # 只显示最后5行
        print(f"  {start_index + len(current_chunk_lines) - 5 + i + 1}: {line}")
    print()
    
    current_size = get_chunk_char_count(current_chunk_lines)
    print(f"当前chunk大小: {current_size} 字符")
    print(f"最大chunk限制: {max_chars_per_chunk} 字符")
    print()
    
    # 测试should_start_new_chunk
    should_split = should_start_new_chunk(
        lines[table_title_index], 
        current_chunk_lines, 
        max_chars_per_chunk,
        lines,
        table_title_index
    )
    
    print(f"should_start_new_chunk结果: {should_split}")
    
    # 如果不应该分块，但实际分块了，可能是因为chunk过大导致的强制分割
    if not should_split:
        # 模拟添加表格标题后的情况
        test_chunk = current_chunk_lines + [lines[table_title_index]]
        test_size = get_chunk_char_count(test_chunk)
        print(f"添加表格标题后chunk大小: {test_size} 字符")
        
        if test_size >= max_chars_per_chunk:
            print("⚠️  chunk过大，会触发强制分割")
            
            # 测试find_better_split_point
            split_point = find_better_split_point(test_chunk, min_chars_per_chunk)
            print(f"find_better_split_point结果: {split_point}")
            
            if split_point != -1:
                split_line = test_chunk[split_point - 1] if split_point > 0 else ""
                print(f"分割点前一行: {split_line}")
                next_line = test_chunk[split_point] if split_point < len(test_chunk) else ""
                print(f"分割点后一行: {next_line}")
                
                # 检查是否在表格标题处分割
                if split_point == len(test_chunk) - 1:
                    print("❌ 分割点正好在表格标题处！")
                elif is_table_title(next_line):
                    print("❌ 分割点后是表格标题！")
    
    print()
    print("=== 完整分块测试 ===")
    
    # 测试完整的分块过程
    test_lines = lines[start_index:table_title_index + 10]  # 包含表格标题和后续内容
    chunks = create_chunks(test_lines, max_chars_per_chunk, min_chars_per_chunk)
    
    print(f"生成了 {len(chunks)} 个chunk")
    
    # 找到包含表格标题的chunk
    for i, chunk in enumerate(chunks):
        chunk_text = '\n'.join(chunk)
        if table_title_line in chunk_text:
            print(f"\nChunk {i + 1} (包含表格标题):")
            print(f"  大小: {get_chunk_char_count(chunk)} 字符")
            print(f"  行数: {len(chunk)}")
            
            # 显示chunk的开始和结束
            print(f"  开始: {chunk[0][:50]}...")
            print(f"  结束: {chunk[-1][:50]}...")
            
            # 检查是否包含表格内容
            has_table = any('<table>' in line for line in chunk)
            print(f"  包含表格内容: {has_table}")
            
            if not has_table:
                print("  ❌ 表格标题与内容被分离！")
            else:
                print("  ✅ 表格标题与内容在同一chunk")

if __name__ == "__main__":
    debug_actual_chunking_process()