#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预处理脚本版本对比分析工具
对比V1、V2、V3三个版本的处理效果

功能：
1. 加载三个版本的统计数据
2. 对比关键指标
3. 分析改进效果
4. 生成详细报告

作者: RAG预处理专家
版本: 1.0
"""

import json
import argparse
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class VersionStats:
    """版本统计信息"""
    version: str
    total_chunks: int
    avg_chunk_size: float
    avg_quality_score: float
    boundary_quality_score: float
    size_distribution: Dict[str, int]
    forced_splits: int = 0
    boundary_candidates: int = 0

class VersionComparator:
    """版本对比分析器"""
    
    def __init__(self):
        """初始化对比器"""
        self.versions = {}
    
    def load_v1_data(self, quality_file: str) -> VersionStats:
        """
        加载V1版本数据（从quality_report.json）
        
        Args:
            quality_file (str): V1质量报告文件路径
            
        Returns:
            VersionStats: V1版本统计信息
        """
        try:
            with open(quality_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 从V1数据中提取信息
            chunks_info = data.get('chunks_analysis', {})
            total_chunks = chunks_info.get('total_chunks', 0)
            
            # 计算平均分块大小
            chunk_sizes = chunks_info.get('chunk_sizes', [])
            avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
            
            # 质量分数
            quality_scores = chunks_info.get('quality_scores', [])
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            # 边界质量（高质量分块比例）
            high_quality = sum(1 for score in quality_scores if score > 0.7)
            boundary_quality = high_quality / len(quality_scores) if quality_scores else 0
            
            # 大小分布
            size_dist = {
                'small': sum(1 for size in chunk_sizes if size < 400),
                'medium': sum(1 for size in chunk_sizes if 400 <= size <= 800),
                'large': sum(1 for size in chunk_sizes if 800 < size <= 1500),
                'extra_large': sum(1 for size in chunk_sizes if size > 1500)
            }
            
            return VersionStats(
                version="V1",
                total_chunks=total_chunks,
                avg_chunk_size=avg_size,
                avg_quality_score=avg_quality,
                boundary_quality_score=boundary_quality,
                size_distribution=size_dist
            )
            
        except Exception as e:
            print(f"❌ 加载V1数据失败: {e}")
            raise
    
    def load_v2_v3_data(self, stats_file: str, version: str) -> VersionStats:
        """
        加载V2/V3版本数据（从processing_stats.json）
        
        Args:
            stats_file (str): 统计文件路径
            version (str): 版本号（V2或V3）
            
        Returns:
            VersionStats: 版本统计信息
        """
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取统计信息
            stats = data.get('statistics', {})
            processing_info = data.get('processing_info', {})
            
            return VersionStats(
                version=version,
                total_chunks=stats.get('total_chunks', 0),
                avg_chunk_size=stats.get('average_chunk_size', 0),
                avg_quality_score=stats.get('average_quality_score', 0),
                boundary_quality_score=stats.get('boundary_quality_score', 0),
                size_distribution=stats.get('size_distribution', {}),
                forced_splits=processing_info.get('forced_splits', 0),
                boundary_candidates=processing_info.get('boundary_candidates_found', 0)
            )
            
        except Exception as e:
            print(f"❌ 加载{version}数据失败: {e}")
            raise
    
    def calculate_improvements(self, baseline: VersionStats, current: VersionStats) -> Dict[str, float]:
        """
        计算改进百分比
        
        Args:
            baseline (VersionStats): 基线版本
            current (VersionStats): 当前版本
            
        Returns:
            Dict[str, float]: 改进百分比字典
        """
        improvements = {}
        
        # 分块数量变化
        if baseline.total_chunks > 0:
            improvements['chunks_change'] = ((current.total_chunks - baseline.total_chunks) / baseline.total_chunks) * 100
        
        # 平均分块大小变化
        if baseline.avg_chunk_size > 0:
            improvements['size_change'] = ((current.avg_chunk_size - baseline.avg_chunk_size) / baseline.avg_chunk_size) * 100
        
        # 质量分数改进
        if baseline.avg_quality_score > 0:
            improvements['quality_improvement'] = ((current.avg_quality_score - baseline.avg_quality_score) / baseline.avg_quality_score) * 100
        
        # 边界质量改进
        if baseline.boundary_quality_score > 0:
            improvements['boundary_improvement'] = ((current.boundary_quality_score - baseline.boundary_quality_score) / baseline.boundary_quality_score) * 100
        
        return improvements
    
    def analyze_size_distribution(self, versions: List[VersionStats]) -> Dict[str, Any]:
        """
        分析大小分布变化
        
        Args:
            versions (List[VersionStats]): 版本列表
            
        Returns:
            Dict[str, Any]: 分布分析结果
        """
        analysis = {}
        
        for version in versions:
            total = version.total_chunks
            if total > 0:
                dist_percentages = {
                    'small_pct': (version.size_distribution.get('small', 0) / total) * 100,
                    'medium_pct': (version.size_distribution.get('medium', 0) / total) * 100,
                    'large_pct': (version.size_distribution.get('large', 0) / total) * 100,
                    'extra_large_pct': (version.size_distribution.get('extra_large', 0) / total) * 100
                }
                analysis[version.version] = dist_percentages
        
        return analysis
    
    def generate_report(self, v1_stats: VersionStats, v2_stats: VersionStats, v3_stats: VersionStats) -> str:
        """
        生成详细对比报告
        
        Args:
            v1_stats (VersionStats): V1统计信息
            v2_stats (VersionStats): V2统计信息
            v3_stats (VersionStats): V3统计信息
            
        Returns:
            str: 对比报告
        """
        report = []
        report.append("=" * 80)
        report.append("📊 预处理脚本版本对比分析报告")
        report.append("=" * 80)
        report.append("")
        
        # 基本信息对比
        report.append("📋 基本信息对比:")
        report.append("-" * 50)
        report.append(f"{'指标':<20} {'V1':<15} {'V2':<15} {'V3':<15}")
        report.append("-" * 50)
        report.append(f"{'分块总数':<20} {v1_stats.total_chunks:<15} {v2_stats.total_chunks:<15} {v3_stats.total_chunks:<15}")
        report.append(f"{'平均分块大小':<20} {v1_stats.avg_chunk_size:<15.0f} {v2_stats.avg_chunk_size:<15.0f} {v3_stats.avg_chunk_size:<15.0f}")
        report.append(f"{'平均质量分数':<20} {v1_stats.avg_quality_score:<15.2f} {v2_stats.avg_quality_score:<15.2f} {v3_stats.avg_quality_score:<15.2f}")
        report.append(f"{'边界质量分数':<20} {v1_stats.boundary_quality_score:<15.2f} {v2_stats.boundary_quality_score:<15.2f} {v3_stats.boundary_quality_score:<15.2f}")
        report.append("")
        
        # V2相对V1的改进
        v2_improvements = self.calculate_improvements(v1_stats, v2_stats)
        report.append("📈 V2相对V1的改进:")
        report.append("-" * 30)
        for metric, improvement in v2_improvements.items():
            report.append(f"{metric}: {improvement:+.1f}%")
        report.append("")
        
        # V3相对V1的改进
        v3_improvements = self.calculate_improvements(v1_stats, v3_stats)
        report.append("📈 V3相对V1的改进:")
        report.append("-" * 30)
        for metric, improvement in v3_improvements.items():
            report.append(f"{metric}: {improvement:+.1f}%")
        report.append("")
        
        # V3相对V2的改进
        v3_v2_improvements = self.calculate_improvements(v2_stats, v3_stats)
        report.append("📈 V3相对V2的改进:")
        report.append("-" * 30)
        for metric, improvement in v3_v2_improvements.items():
            report.append(f"{metric}: {improvement:+.1f}%")
        report.append("")
        
        # 大小分布分析
        size_analysis = self.analyze_size_distribution([v1_stats, v2_stats, v3_stats])
        report.append("📊 分块大小分布分析:")
        report.append("-" * 50)
        report.append(f"{'大小类别':<15} {'V1 (%)':<15} {'V2 (%)':<15} {'V3 (%)':<15}")
        report.append("-" * 50)
        
        categories = ['small_pct', 'medium_pct', 'large_pct', 'extra_large_pct']
        category_names = ['小分块(<400)', '中分块(400-800)', '大分块(800-1500)', '超大分块(>1500)']
        
        for cat, name in zip(categories, category_names):
            v1_pct = size_analysis.get('V1', {}).get(cat, 0)
            v2_pct = size_analysis.get('V2', {}).get(cat, 0)
            v3_pct = size_analysis.get('V3', {}).get(cat, 0)
            report.append(f"{name:<15} {v1_pct:<15.1f} {v2_pct:<15.1f} {v3_pct:<15.1f}")
        report.append("")
        
        # 技术特性对比
        report.append("🔧 技术特性对比:")
        report.append("-" * 30)
        report.append(f"V1: 基础版本，简单边界检测")
        report.append(f"V2: 优化边界检测，强制分割: {v2_stats.forced_splits}次")
        report.append(f"V3: 最终优化，强制分割: {v3_stats.forced_splits}次")
        report.append("")
        
        # 关键发现
        report.append("🔍 关键发现:")
        report.append("-" * 20)
        
        # 分块数量分析
        if v3_stats.total_chunks > v1_stats.total_chunks * 2:
            report.append(f"✅ V3显著增加了分块数量，从{v1_stats.total_chunks}增加到{v3_stats.total_chunks}")
        
        # 分块大小分析
        if v3_stats.avg_chunk_size < v1_stats.avg_chunk_size:
            report.append(f"✅ V3成功减小了平均分块大小，从{v1_stats.avg_chunk_size:.0f}减少到{v3_stats.avg_chunk_size:.0f}")
        
        # 超大分块控制
        v1_extra_large = v1_stats.size_distribution.get('extra_large', 0)
        v3_extra_large = v3_stats.size_distribution.get('extra_large', 0)
        if v3_extra_large < v1_extra_large:
            report.append(f"✅ V3有效控制了超大分块，从{v1_extra_large}个减少到{v3_extra_large}个")
        
        # 质量分数分析
        if v3_stats.avg_quality_score < v1_stats.avg_quality_score:
            report.append(f"⚠️  V3的质量分数较低，可能是由于强制分割导致的")
        
        report.append("")
        
        # 推荐建议
        report.append("💡 推荐建议:")
        report.append("-" * 20)
        
        if v3_stats.avg_chunk_size < 500:
            report.append("✅ V3成功达到了目标分块大小（400-600字符）")
        else:
            report.append("⚠️  建议进一步优化分块大小控制")
        
        if v3_extra_large == 0:
            report.append("✅ V3成功消除了超大分块问题")
        else:
            report.append(f"⚠️  仍有{v3_extra_large}个超大分块需要处理")
        
        if v3_stats.boundary_quality_score < 0.5:
            report.append("⚠️  建议优化边界检测算法以提高质量分数")
        
        report.append("")
        report.append("=" * 80)
        report.append("📝 报告生成完成")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, report: str, output_path: str):
        """
        保存对比报告
        
        Args:
            report (str): 报告内容
            output_path (str): 输出路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"📄 对比报告已保存至: {output_path}")
            
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")
            raise

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='预处理脚本版本对比分析工具')
    parser.add_argument('--v1-quality', required=True, help='V1质量报告文件路径')
    parser.add_argument('--v2-stats', required=True, help='V2统计文件路径')
    parser.add_argument('--v3-stats', required=True, help='V3统计文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出报告路径')
    
    args = parser.parse_args()
    
    try:
        # 创建对比器
        comparator = VersionComparator()
        
        print("📊 开始版本对比分析...")
        
        # 加载数据
        print("📥 加载V1数据...")
        v1_stats = comparator.load_v1_data(args.v1_quality)
        
        print("📥 加载V2数据...")
        v2_stats = comparator.load_v2_v3_data(args.v2_stats, "V2")
        
        print("📥 加载V3数据...")
        v3_stats = comparator.load_v2_v3_data(args.v3_stats, "V3")
        
        # 生成报告
        print("📝 生成对比报告...")
        report = comparator.generate_report(v1_stats, v2_stats, v3_stats)
        
        # 保存报告
        comparator.save_report(report, args.output)
        
        # 打印摘要
        print("\n" + "="*50)
        print("📊 对比摘要:")
        print(f"V1: {v1_stats.total_chunks}个分块, 平均{v1_stats.avg_chunk_size:.0f}字符")
        print(f"V2: {v2_stats.total_chunks}个分块, 平均{v2_stats.avg_chunk_size:.0f}字符")
        print(f"V3: {v3_stats.total_chunks}个分块, 平均{v3_stats.avg_chunk_size:.0f}字符")
        print("="*50)
        
        print("✅ 版本对比分析完成!")
        return 0
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return 1

if __name__ == "__main__":
    exit(main())