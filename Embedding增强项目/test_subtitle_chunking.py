#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子标题分块功能综合测试

本测试文件验证子标题识别和分块优先级逻辑的正确性，
包括对乳腺癌诊疗指南等医学文档的实际测试。

测试内容：
1. 基础功能测试（标题识别、优先级评估）
2. 分块策略测试（边界保护、质量验证）
3. 实际文档测试（乳腺癌诊疗指南）
4. 性能和质量评估

作者：AI Assistant
创建时间：2025年1月24日
"""

import os
import sys
import time
from typing import List, Dict, Any
from subtitle_chunking_enhanced import (
    is_numeric_section, is_subtitle, is_first_subtitle,
    get_chunk_boundary_priority, optimize_subtitle_chunking,
    analyze_subtitle_distribution, validate_chunking_quality,
    protect_title_subtitle_cohesion
)


def load_test_document(file_path: str) -> List[str]:
    """
    加载测试文档
    
    Args:
        file_path (str): 文档路径
        
    Returns:
        List[str]: 文档行列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except FileNotFoundError:
        print(f"警告：测试文档 {file_path} 未找到")
        return []
    except Exception as e:
        print(f"加载文档时出错：{e}")
        return []


def create_test_chunks(lines: List[str], boundaries: List[int]) -> List[List[str]]:
    """
    根据边界创建分块
    
    Args:
        lines (List[str]): 原始文档行
        boundaries (List[int]): 分块边界
        
    Returns:
        List[List[str]]: 分块结果
    """
    if not boundaries:
        return [lines] if lines else []
    
    chunks = []
    start = 0
    
    for boundary in sorted(boundaries):
        if boundary > start:
            chunks.append(lines[start:boundary])
        start = boundary
    
    # 添加最后一个chunk
    if start < len(lines):
        chunks.append(lines[start:])
    
    return chunks


def test_basic_functions():
    """测试基础功能"""
    print("=== 基础功能测试 ===")
    
    test_cases = [
        ("<1007>11维持治疗", "数字标题"),
        ("# 11维持治疗", "Markdown数字标题"),
        ("(1)化疗目的", "数字子标题"),
        ("（一）内分泌治疗", "中文子标题"),
        ("### 子标题", "Markdown子标题"),
        ("普通文本", "普通文本"),
        ("一、总体原则", "中文一级序号"),
        ("## 主要章节", "H2标题")
    ]
    
    for text, description in test_cases:
        print(f"\n测试: {description}")
        print(f"文本: {text}")
        print(f"  数字标题: {is_numeric_section(text)}")
        print(f"  子标题: {is_subtitle(text)}")
        print(f"  第一个子标题: {is_first_subtitle(text)}")
        print(f"  优先级: {get_chunk_boundary_priority(text)}")


def test_chunking_strategy():
    """测试分块策略"""
    print("\n=== 分块策略测试 ===")
    
    # 创建模拟文档
    test_lines = [
        "<1007>11维持治疗",
        "维持治疗是指...",
        "(1)化疗目的",
        "化疗的主要目的是...",
        "详细说明内容...",
        "(2)适应证",
        "适应证包括...",
        "更多详细内容...",
        "(3)治疗方案",
        "推荐的治疗方案...",
        "<1008>12随访管理",
        "随访管理的重要性...",
        "(1)随访时间",
        "建议的随访时间..."
    ]
    
    print(f"测试文档行数: {len(test_lines)}")
    
    # 测试分块优化
    boundaries = optimize_subtitle_chunking(test_lines, max_chunk_size=200)
    print(f"分块边界: {boundaries}")
    
    # 创建分块
    chunks = create_test_chunks(test_lines, boundaries)
    print(f"分块数量: {len(chunks)}")
    
    # 显示分块结果
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        for line in chunk:
            print(f"  {line.strip()}")
    
    # 验证质量
    quality = validate_chunking_quality(chunks, test_lines)
    print(f"\n质量评估: {quality}")


def test_real_document():
    """测试真实文档"""
    print("\n=== 真实文档测试 ===")
    
    # 尝试加载乳腺癌诊疗指南
    doc_path = "乳腺癌诊疗指南2025_enhanced.md"
    lines = load_test_document(doc_path)
    
    if not lines:
        print("未找到真实文档，跳过此测试")
        return
    
    print(f"文档总行数: {len(lines)}")
    
    # 分析子标题分布
    analysis = analyze_subtitle_distribution(lines)
    print("\n子标题分布分析:")
    for key, value in analysis.items():
        if isinstance(value, list) and len(value) > 3:
            print(f"{key}: {len(value)} 个（显示前3个）")
            for item in value[:3]:
                print(f"  {item}")
        else:
            print(f"{key}: {value}")
    
    # 测试分块优化
    start_time = time.time()
    boundaries = optimize_subtitle_chunking(lines, max_chunk_size=1000)
    end_time = time.time()
    
    print(f"\n分块处理时间: {end_time - start_time:.3f}秒")
    print(f"分块边界数量: {len(boundaries)}")
    
    if boundaries:
        print("前10个分块边界:")
        for i, boundary in enumerate(boundaries[:10]):
            if boundary < len(lines):
                print(f"  {boundary}: {lines[boundary].strip()}")
    
    # 创建分块并验证质量
    chunks = create_test_chunks(lines, boundaries)
    quality = validate_chunking_quality(chunks, lines)
    
    print(f"\n质量评估结果:")
    print(f"  总分块数: {quality['total_chunks']}")
    print(f"  分离的第一子标题: {quality['separated_first_subtitles']}")
    print(f"  质量分数: {quality['quality_score']:.3f}")
    
    if quality['issues']:
        print("  发现的问题:")
        for issue in quality['issues'][:5]:  # 只显示前5个问题
            print(f"    {issue}")


def test_edge_cases():
    """测试边界情况"""
    print("\n=== 边界情况测试 ===")
    
    edge_cases = [
        # 空文档
        ([], "空文档"),
        
        # 只有主标题
        (["<1007>11维持治疗"], "只有主标题"),
        
        # 主标题后直接是第一个子标题
        (["<1007>11维持治疗", "(1)化疗目的"], "主标题+第一子标题"),
        
        # 连续的子标题
        (["(1)第一项", "(2)第二项", "(3)第三项"], "连续子标题"),
        
        # 混合格式
        (["# 主标题", "（一）中文子标题", "(1)数字子标题", "### Markdown子标题"], "混合格式")
    ]
    
    for lines, description in edge_cases:
        print(f"\n测试: {description}")
        print(f"输入行数: {len(lines)}")
        
        if lines:
            boundaries = optimize_subtitle_chunking(lines, max_chunk_size=100)
            chunks = create_test_chunks(lines, boundaries)
            quality = validate_chunking_quality(chunks, lines)
            
            print(f"  分块数: {len(chunks)}")
            print(f"  质量分数: {quality['quality_score']:.3f}")
        else:
            print("  跳过空文档测试")


def run_performance_test():
    """性能测试"""
    print("\n=== 性能测试 ===")
    
    # 创建大型测试文档
    large_doc = []
    for i in range(100):
        large_doc.extend([
            f"<{1000+i}>{i+1}章节标题",
            "章节介绍内容...",
            "(1)第一个子项",
            "子项内容详细说明...",
            "更多内容...",
            "(2)第二个子项",
            "第二个子项的详细说明...",
            "额外的说明内容...",
            "(3)第三个子项",
            "第三个子项的内容..."
        ])
    
    print(f"大型文档行数: {len(large_doc)}")
    
    # 性能测试
    start_time = time.time()
    boundaries = optimize_subtitle_chunking(large_doc, max_chunk_size=500)
    end_time = time.time()
    
    print(f"处理时间: {end_time - start_time:.3f}秒")
    print(f"处理速度: {len(large_doc) / (end_time - start_time):.0f} 行/秒")
    print(f"分块数量: {len(boundaries)}")
    
    # 质量验证
    chunks = create_test_chunks(large_doc, boundaries)
    quality = validate_chunking_quality(chunks, large_doc)
    print(f"质量分数: {quality['quality_score']:.3f}")


def main():
    """主测试函数"""
    print("子标题分块功能综合测试", flush=True)
    print("=" * 50, flush=True)
    
    try:
        # 运行所有测试
        test_basic_functions()
        test_chunking_strategy()
        test_real_document()
        test_edge_cases()
        run_performance_test()
        
        print("\n" + "=" * 50, flush=True)
        print("所有测试完成！", flush=True)
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}", flush=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()