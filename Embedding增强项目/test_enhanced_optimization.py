#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的preprocess_enhanced.py效果
对比原版preprocess.py和优化后的preprocess_enhanced.py的分块效果
"""

import subprocess
import re
import os
import time
from typing import Dict, List, Tuple

def extract_chunks_from_file(file_path: str) -> List[str]:
    """从处理后的文件中提取chunks"""
    chunks = []
    current_chunk = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line == "[CHUNK_BOUNDARY]":
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
            elif line and not line.startswith("======"):
                # 移除行号标记
                clean_line = re.sub(r'^<\d+>\s*', '', line)
                if clean_line:
                    current_chunk.append(clean_line)
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

def analyze_chunks(chunks: List[str]) -> Dict:
    """分析chunks的统计信息"""
    if not chunks:
        return {}
    
    chunk_sizes = [len(chunk) for chunk in chunks]
    
    # 计算大小分布
    size_distribution = {
        "< 200": sum(1 for size in chunk_sizes if size < 200),
        "200-500": sum(1 for size in chunk_sizes if 200 <= size < 500),
        "500-800": sum(1 for size in chunk_sizes if 500 <= size < 800),
        "800-1200": sum(1 for size in chunk_sizes if 800 <= size < 1200),
        "> 1200": sum(1 for size in chunk_sizes if size >= 1200)
    }
    
    return {
        "total_chunks": len(chunks),
        "avg_size": sum(chunk_sizes) / len(chunks),
        "min_size": min(chunk_sizes),
        "max_size": max(chunk_sizes),
        "size_distribution": size_distribution,
        "small_chunks_ratio": size_distribution["< 200"] / len(chunks),
        "optimal_chunks_ratio": (size_distribution["500-800"] + size_distribution["800-1200"]) / len(chunks)
    }

def run_preprocess_script(script_name: str, input_file: str) -> Tuple[bool, str, float]:
    """运行预处理脚本并返回结果"""
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ['python', script_name, input_file], 
            capture_output=True, 
            text=True,
            timeout=60
        )
        
        processing_time = time.time() - start_time
        
        if result.returncode == 0:
            return True, result.stdout, processing_time
        else:
            return False, result.stderr, processing_time
            
    except subprocess.TimeoutExpired:
        return False, "处理超时", time.time() - start_time
    except Exception as e:
        return False, str(e), time.time() - start_time

def test_enhanced_optimization(test_file: str):
    """测试优化后的preprocess_enhanced.py效果"""
    
    print("=" * 60)
    print("测试优化后的preprocess_enhanced.py效果")
    print("=" * 60)
    print(f"测试文件: {test_file}")
    print()
    
    # 确保测试文件存在
    if not os.path.exists(test_file):
        print(f"错误: 测试文件不存在 - {test_file}")
        return
    
    results = {}
    
    # 测试原版preprocess.py
    print("1. 测试原版preprocess.py...")
    success, output, time_taken = run_preprocess_script("preprocess.py", test_file)
    
    if success:
        print(f"   ✓ 处理成功 (耗时: {time_taken:.2f}秒)")
        
        # 分析输出文件
        base_name = os.path.splitext(test_file)[0]
        output_file = f"{base_name}_optimized.md"
        
        if os.path.exists(output_file):
            chunks = extract_chunks_from_file(output_file)
            results['original'] = analyze_chunks(chunks)
            results['original']['processing_time'] = time_taken
            
            print(f"   分块数: {results['original']['total_chunks']}")
            print(f"   平均大小: {results['original']['avg_size']:.0f} 字符")
            print(f"   小chunk比例: {results['original']['small_chunks_ratio']:.1%}")
        else:
            print(f"   警告: 输出文件不存在 - {output_file}")
    else:
        print(f"   ✗ 处理失败: {output}")
    
    print()
    
    # 测试优化后的preprocess_enhanced.py
    print("2. 测试优化后的preprocess_enhanced.py...")
    success, output, time_taken = run_preprocess_script("preprocess_enhanced.py", test_file)
    
    if success:
        print(f"   ✓ 处理成功 (耗时: {time_taken:.2f}秒)")
        
        # 从输出中提取统计信息
        lines = output.split('\n')
        enhanced_stats = {}
        
        for line in lines:
            if '分块数:' in line:
                enhanced_stats['total_chunks'] = int(re.search(r'(\d+)', line).group(1))
            elif '平均分块大小:' in line:
                enhanced_stats['avg_size'] = float(re.search(r'([\d.]+)', line).group(1))
            elif '语义质量分数:' in line:
                enhanced_stats['semantic_quality'] = float(re.search(r'([\d.]+)', line).group(1))
        
        # 分析输出文件
        base_name = os.path.splitext(test_file)[0]
        output_file = f"{base_name}_enhanced.md"
        
        if os.path.exists(output_file):
            chunks = extract_chunks_from_file(output_file)
            results['enhanced'] = analyze_chunks(chunks)
            results['enhanced']['processing_time'] = time_taken
            results['enhanced']['semantic_quality'] = enhanced_stats.get('semantic_quality', 0)
            
            print(f"   分块数: {results['enhanced']['total_chunks']}")
            print(f"   平均大小: {results['enhanced']['avg_size']:.0f} 字符")
            print(f"   小chunk比例: {results['enhanced']['small_chunks_ratio']:.1%}")
            print(f"   语义质量分数: {results['enhanced']['semantic_quality']:.2f}")
        else:
            print(f"   警告: 输出文件不存在 - {output_file}")
    else:
        print(f"   ✗ 处理失败: {output}")
    
    print()
    
    # 对比分析
    if 'original' in results and 'enhanced' in results:
        print("3. 对比分析结果:")
        print("-" * 40)
        
        orig = results['original']
        enh = results['enhanced']
        
        # 基本统计对比
        chunk_reduction = (orig['total_chunks'] - enh['total_chunks']) / orig['total_chunks']
        size_improvement = (enh['avg_size'] - orig['avg_size']) / orig['avg_size']
        small_chunk_reduction = (orig['small_chunks_ratio'] - enh['small_chunks_ratio']) / orig['small_chunks_ratio'] if orig['small_chunks_ratio'] > 0 else 0
        
        print(f"分块数量变化: {orig['total_chunks']} → {enh['total_chunks']} ({chunk_reduction:+.1%})")
        print(f"平均大小变化: {orig['avg_size']:.0f} → {enh['avg_size']:.0f} ({size_improvement:+.1%})")
        print(f"小chunk比例: {orig['small_chunks_ratio']:.1%} → {enh['small_chunks_ratio']:.1%} ({small_chunk_reduction:+.1%})")
        print(f"最优chunk比例: {orig['optimal_chunks_ratio']:.1%} → {enh['optimal_chunks_ratio']:.1%}")
        
        if 'semantic_quality' in enh:
            print(f"语义质量分数: {enh['semantic_quality']:.2f}")
        
        print()
        print("大小分布对比:")
        print("原版:")
        for size_range, count in orig['size_distribution'].items():
            percentage = count / orig['total_chunks'] * 100
            print(f"  {size_range}: {count} ({percentage:.1f}%)")
        
        print("优化版:")
        for size_range, count in enh['size_distribution'].items():
            percentage = count / enh['total_chunks'] * 100
            print(f"  {size_range}: {count} ({percentage:.1f}%)")
        
        print()
        print("优化效果总结:")
        if chunk_reduction > 0:
            print(f"✓ 成功减少了 {chunk_reduction:.1%} 的chunk数量")
        if size_improvement > 0:
            print(f"✓ 平均chunk大小提升了 {size_improvement:.1%}")
        if small_chunk_reduction > 0:
            print(f"✓ 小chunk比例降低了 {small_chunk_reduction:.1%}")
        if enh['optimal_chunks_ratio'] > orig['optimal_chunks_ratio']:
            print(f"✓ 最优大小chunk比例提升了 {(enh['optimal_chunks_ratio'] - orig['optimal_chunks_ratio']):.1%}")
        
        if 'semantic_quality' in enh and enh['semantic_quality'] >= 0.75:
            print(f"✓ 语义质量分数达到 {enh['semantic_quality']:.2f} (良好)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python test_enhanced_optimization.py <测试文件路径>")
        sys.exit(1)
    
    test_file = sys.argv[1]
    test_enhanced_optimization(test_file)