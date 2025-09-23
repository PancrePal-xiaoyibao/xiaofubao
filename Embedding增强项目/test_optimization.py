#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chunk分块优化效果测试脚本

本脚本用于对比原版preprocess.py和优化版preprocess_optimized.py的分块效果，
包括chunk数量、平均大小、大小分布等关键指标。

功能：
1. 对同一文档分别使用原版和优化版进行处理
2. 统计并对比关键指标
3. 生成详细的对比报告
4. 验证语义完整性保持情况

作者: RAG预处理专家
版本: 1.0
更新日期: 2024
"""

import os
import sys
import json
import time
from collections import Counter

# 添加当前目录到Python路径，以便导入模块
sys.path.append(os.path.dirname(__file__))

# 导入原版和优化版的处理函数
try:
    from preprocess import create_chunks, preprocess_file
    from preprocess_optimized import create_chunks_optimized, preprocess_file_optimized
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保preprocess.py和preprocess_optimized.py在同一目录下")
    sys.exit(1)

def get_chunk_stats(chunks):
    """
    计算chunk统计信息。
    
    Args:
        chunks (list): chunk列表，每个chunk是行列表
        
    Returns:
        dict: 包含各种统计信息的字典
    """
    if not chunks:
        return {
            'total_chunks': 0,
            'total_chars': 0,
            'avg_size': 0,
            'min_size': 0,
            'max_size': 0,
            'size_distribution': {},
            'small_chunks_count': 0,
            'large_chunks_count': 0
        }
    
    # 计算每个chunk的字符数
    chunk_sizes = []
    for chunk in chunks:
        size = sum(len(line) for line in chunk)
        chunk_sizes.append(size)
    
    total_chars = sum(chunk_sizes)
    avg_size = total_chars / len(chunks)
    
    # 大小分布统计
    size_ranges = {
        '0-200': 0,
        '201-500': 0,
        '501-800': 0,
        '801-1200': 0,
        '1201-1500': 0,
        '1500+': 0
    }
    
    small_chunks = 0  # 小于300字符
    large_chunks = 0  # 大于1500字符
    
    for size in chunk_sizes:
        if size <= 200:
            size_ranges['0-200'] += 1
        elif size <= 500:
            size_ranges['201-500'] += 1
        elif size <= 800:
            size_ranges['501-800'] += 1
        elif size <= 1200:
            size_ranges['801-1200'] += 1
        elif size <= 1500:
            size_ranges['1201-1500'] += 1
        else:
            size_ranges['1500+'] += 1
        
        if size < 300:
            small_chunks += 1
        if size > 1500:
            large_chunks += 1
    
    return {
        'total_chunks': len(chunks),
        'total_chars': total_chars,
        'avg_size': round(avg_size, 1),
        'min_size': min(chunk_sizes),
        'max_size': max(chunk_sizes),
        'size_distribution': size_ranges,
        'small_chunks_count': small_chunks,
        'large_chunks_count': large_chunks,
        'chunk_sizes': chunk_sizes
    }

def test_chunking_comparison(test_file_path, target_chunk_size=1000):
    """
    对比测试原版和优化版的分块效果。
    
    Args:
        test_file_path (str): 测试文件路径
        target_chunk_size (int): 目标chunk大小
        
    Returns:
        dict: 包含对比结果的字典
    """
    print(f"开始测试文件: {test_file_path}")
    print(f"目标chunk大小: {target_chunk_size}")
    print("=" * 60)
    
    # 读取测试文件
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"错误: 找不到测试文件 {test_file_path}")
        return None
    except Exception as e:
        print(f"读取文件错误: {e}")
        return None
    
    print(f"文档总行数: {len(lines)}")
    total_chars = sum(len(line) for line in lines)
    print(f"文档总字符数: {total_chars}")
    print()
    
    # 测试原版分块
    print("测试原版分块算法...")
    start_time = time.time()
    try:
        original_chunks = create_chunks(lines, max_chars_per_chunk=target_chunk_size)
        original_time = time.time() - start_time
        original_stats = get_chunk_stats(original_chunks)
        print(f"原版处理完成，耗时: {original_time:.3f}秒")
    except Exception as e:
        print(f"原版处理错误: {e}")
        return None
    
    # 测试优化版分块
    print("测试优化版分块算法...")
    start_time = time.time()
    try:
        min_chunk_size = max(200, int(target_chunk_size * 0.2))
        optimized_chunks = create_chunks_optimized(
            lines, 
            max_chars_per_chunk=target_chunk_size,
            min_chars_per_chunk=min_chunk_size
        )
        optimized_time = time.time() - start_time
        optimized_stats = get_chunk_stats(optimized_chunks)
        print(f"优化版处理完成，耗时: {optimized_time:.3f}秒")
    except Exception as e:
        print(f"优化版处理错误: {e}")
        return None
    
    print()
    
    # 计算改进指标
    chunk_reduction = original_stats['total_chunks'] - optimized_stats['total_chunks']
    chunk_reduction_pct = (chunk_reduction / original_stats['total_chunks']) * 100 if original_stats['total_chunks'] > 0 else 0
    
    avg_size_improvement = optimized_stats['avg_size'] - original_stats['avg_size']
    avg_size_improvement_pct = (avg_size_improvement / original_stats['avg_size']) * 100 if original_stats['avg_size'] > 0 else 0
    
    small_chunk_reduction = original_stats['small_chunks_count'] - optimized_stats['small_chunks_count']
    small_chunk_reduction_pct = (small_chunk_reduction / original_stats['small_chunks_count']) * 100 if original_stats['small_chunks_count'] > 0 else 0
    
    return {
        'test_file': test_file_path,
        'target_chunk_size': target_chunk_size,
        'total_chars': total_chars,
        'total_lines': len(lines),
        'original': original_stats,
        'optimized': optimized_stats,
        'improvements': {
            'chunk_reduction': chunk_reduction,
            'chunk_reduction_pct': round(chunk_reduction_pct, 1),
            'avg_size_improvement': round(avg_size_improvement, 1),
            'avg_size_improvement_pct': round(avg_size_improvement_pct, 1),
            'small_chunk_reduction': small_chunk_reduction,
            'small_chunk_reduction_pct': round(small_chunk_reduction_pct, 1),
            'processing_time_ratio': round(optimized_time / original_time, 2) if original_time > 0 else 0
        }
    }

def print_comparison_report(results):
    """
    打印详细的对比报告。
    
    Args:
        results (dict): 测试结果字典
    """
    if not results:
        print("无法生成报告：测试结果为空")
        return
    
    print("=" * 80)
    print("                    CHUNK分块优化效果对比报告")
    print("=" * 80)
    print()
    
    print(f"测试文件: {results['test_file']}")
    print(f"目标chunk大小: {results['target_chunk_size']} 字符")
    print(f"文档总字符数: {results['total_chars']:,}")
    print(f"文档总行数: {results['total_lines']:,}")
    print()
    
    # 基本统计对比
    print("基本统计对比:")
    print("-" * 50)
    print(f"{'指标':<20} {'原版':<15} {'优化版':<15} {'改进':<15}")
    print("-" * 50)
    
    orig = results['original']
    opt = results['optimized']
    imp = results['improvements']
    
    print(f"{'总chunk数':<20} {orig['total_chunks']:<15} {opt['total_chunks']:<15} {imp['chunk_reduction']:+} ({imp['chunk_reduction_pct']:+.1f}%)")
    print(f"{'平均大小':<20} {orig['avg_size']:<15.1f} {opt['avg_size']:<15.1f} {imp['avg_size_improvement']:+.1f} ({imp['avg_size_improvement_pct']:+.1f}%)")
    print(f"{'最小大小':<20} {orig['min_size']:<15} {opt['min_size']:<15} {opt['min_size'] - orig['min_size']:+}")
    print(f"{'最大大小':<20} {orig['max_size']:<15} {opt['max_size']:<15} {opt['max_size'] - orig['max_size']:+}")
    print(f"{'小chunk数(<300)':<20} {orig['small_chunks_count']:<15} {opt['small_chunks_count']:<15} {imp['small_chunk_reduction']:+} ({imp['small_chunk_reduction_pct']:+.1f}%)")
    print(f"{'大chunk数(>1500)':<20} {orig['large_chunks_count']:<15} {opt['large_chunks_count']:<15} {opt['large_chunks_count'] - orig['large_chunks_count']:+}")
    print()
    
    # 大小分布对比
    print("Chunk大小分布对比:")
    print("-" * 60)
    print(f"{'大小范围':<15} {'原版':<10} {'优化版':<10} {'变化':<10} {'百分比变化':<15}")
    print("-" * 60)
    
    for size_range in orig['size_distribution']:
        orig_count = orig['size_distribution'][size_range]
        opt_count = opt['size_distribution'][size_range]
        change = opt_count - orig_count
        pct_change = (change / orig_count * 100) if orig_count > 0 else 0
        print(f"{size_range:<15} {orig_count:<10} {opt_count:<10} {change:+<10} {pct_change:+.1f}%")
    
    print()
    
    # 性能指标
    print("性能指标:")
    print("-" * 30)
    print(f"处理时间比率: {imp['processing_time_ratio']:.2f}x")
    print()
    
    # 总结
    print("优化效果总结:")
    print("-" * 30)
    if imp['chunk_reduction_pct'] > 0:
        print(f"✓ 成功减少了 {imp['chunk_reduction_pct']:.1f}% 的chunk数量")
    if imp['avg_size_improvement_pct'] > 0:
        print(f"✓ 平均chunk大小提升了 {imp['avg_size_improvement_pct']:.1f}%")
    if imp['small_chunk_reduction_pct'] > 0:
        print(f"✓ 小chunk数量减少了 {imp['small_chunk_reduction_pct']:.1f}%")
    
    # 目标达成情况
    target_avg = results['target_chunk_size']
    actual_avg = opt['avg_size']
    target_achievement = (actual_avg / target_avg) * 100
    print(f"✓ 目标大小达成率: {target_achievement:.1f}% (目标: {target_avg}, 实际: {actual_avg:.1f})")
    
    print()
    print("=" * 80)

def save_results_to_json(results, output_path):
    """
    将测试结果保存为JSON文件。
    
    Args:
        results (dict): 测试结果
        output_path (str): 输出文件路径
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"测试结果已保存到: {output_path}")
    except Exception as e:
        print(f"保存结果失败: {e}")

def main():
    """
    主函数，执行chunk优化效果测试。
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Chunk分块优化效果测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python test_optimization.py test_document.md
  python test_optimization.py test_document.md --target-size 1200
  python test_optimization.py test_document.md --save-json results.json

测试内容:
  - Chunk数量对比
  - 平均大小对比  
  - 大小分布对比
  - 小chunk数量对比
  - 处理性能对比
        """
    )
    
    parser.add_argument(
        'test_file',
        help='要测试的文档文件路径'
    )
    
    parser.add_argument(
        '--target-size',
        type=int,
        default=1000,
        help='目标chunk大小（默认1000字符）'
    )
    
    parser.add_argument(
        '--save-json',
        help='保存详细结果到JSON文件'
    )
    
    args = parser.parse_args()
    
    # 检查测试文件是否存在
    if not os.path.isfile(args.test_file):
        print(f"错误: 测试文件不存在 - {args.test_file}")
        sys.exit(1)
    
    # 执行测试
    results = test_chunking_comparison(args.test_file, args.target_size)
    
    if results:
        # 打印报告
        print_comparison_report(results)
        
        # 保存JSON结果（如果指定）
        if args.save_json:
            save_results_to_json(results, args.save_json)
    else:
        print("测试失败")
        sys.exit(1)

if __name__ == "__main__":
    main()