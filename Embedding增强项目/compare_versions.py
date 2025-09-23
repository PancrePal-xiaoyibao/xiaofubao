#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本对比分析脚本
比较preprocess_enhanced.py (v1) 和 preprocess_enhanced_v2.py (v2) 的处理效果

功能：
1. 加载两个版本的处理结果
2. 对比关键指标
3. 分析改进效果
4. 生成对比报告

作者: RAG预处理专家
版本: 1.0
"""

import json
import argparse
from typing import Dict, List, Any

class VersionComparator:
    """版本对比分析器"""
    
    def __init__(self):
        """初始化对比器"""
        self.v1_quality = None
        self.v2_data = None
    
    def load_v1_results(self, quality_file: str):
        """
        加载V1版本结果
        
        Args:
            quality_file (str): V1质量报告文件路径
        """
        try:
            # 加载质量报告
            with open(quality_file, 'r', encoding='utf-8') as f:
                self.v1_quality = json.load(f)
            
            print(f"✅ V1结果加载成功")
            
        except Exception as e:
            print(f"❌ V1结果加载失败: {e}")
            raise
    
    def load_v2_results(self, stats_file: str):
        """
        加载V2版本结果
        
        Args:
            stats_file (str): V2统计文件路径
        """
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                self.v2_data = json.load(f)
            
            print(f"✅ V2结果加载成功")
            
        except Exception as e:
            print(f"❌ V2结果加载失败: {e}")
            raise
    
    def extract_v1_metrics(self) -> Dict[str, Any]:
        """
        提取V1版本关键指标
        
        Returns:
            Dict[str, Any]: V1指标字典
        """
        if not self.v1_quality:
            return {}
        
        summary = self.v1_quality.get('summary', {})
        size_analysis = self.v1_quality.get('size_analysis', {})
        boundary_analysis = self.v1_quality.get('boundary_analysis', {})
        
        return {
            'total_chunks': summary.get('total_chunks', 0),
            'overall_quality_score': summary.get('overall_quality_score', 0),
            'total_issues': summary.get('total_issues', 0),
            'high_severity_issues': summary.get('high_severity_issues', 0),
            'average_chunk_size': size_analysis.get('average_size', 0),
            'median_chunk_size': size_analysis.get('median_size', 0),
            'boundary_quality_score': boundary_analysis.get('average_quality_score', 0),
            'large_chunks_count': size_analysis.get('distribution', {}).get('large', 0),
            'extra_large_chunks_count': size_analysis.get('distribution', {}).get('extra_large', 0)
        }
    
    def extract_v2_metrics(self) -> Dict[str, Any]:
        """
        提取V2版本关键指标
        
        Returns:
            Dict[str, Any]: V2指标字典
        """
        if not self.v2_data:
            return {}
        
        stats = self.v2_data.get('statistics', {})
        
        return {
            'total_chunks': stats.get('total_chunks', 0),
            'overall_quality_score': stats.get('average_quality_score', 0),
            'boundary_quality_score': stats.get('boundary_quality_score', 0),
            'average_chunk_size': stats.get('average_chunk_size', 0),
            'large_chunks_count': stats.get('size_distribution', {}).get('large', 0),
            'extra_large_chunks_count': stats.get('size_distribution', {}).get('extra_large', 0),
            'medium_chunks_count': stats.get('size_distribution', {}).get('medium', 0),
            'small_chunks_count': stats.get('size_distribution', {}).get('small', 0)
        }
    
    def calculate_improvements(self, v1_metrics: Dict[str, Any], v2_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算改进效果
        
        Args:
            v1_metrics (Dict[str, Any]): V1指标
            v2_metrics (Dict[str, Any]): V2指标
            
        Returns:
            Dict[str, Any]: 改进效果字典
        """
        improvements = {}
        
        # 计算各项指标的变化
        for key in v1_metrics:
            if key in v2_metrics:
                v1_val = v1_metrics[key]
                v2_val = v2_metrics[key]
                
                if v1_val != 0:
                    change_percent = ((v2_val - v1_val) / v1_val) * 100
                    improvements[key] = {
                        'v1': v1_val,
                        'v2': v2_val,
                        'change': v2_val - v1_val,
                        'change_percent': round(change_percent, 2)
                    }
                else:
                    improvements[key] = {
                        'v1': v1_val,
                        'v2': v2_val,
                        'change': v2_val - v1_val,
                        'change_percent': 'N/A'
                    }
        
        return improvements
    
    def generate_report(self, output_file: str = None) -> str:
        """
        生成对比报告
        
        Args:
            output_file (str): 输出文件路径（可选）
            
        Returns:
            str: 报告内容
        """
        if not self.v1_quality or not self.v2_data:
            return "❌ 缺少必要的数据，无法生成报告"
        
        # 提取指标
        v1_metrics = self.extract_v1_metrics()
        v2_metrics = self.extract_v2_metrics()
        
        # 计算改进
        improvements = self.calculate_improvements(v1_metrics, v2_metrics)
        
        # 生成报告
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("📊 预处理版本对比报告")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # 基本信息对比
        report_lines.append("📋 基本信息对比:")
        report_lines.append(f"  V1 总分块数: {v1_metrics.get('total_chunks', 'N/A')}")
        report_lines.append(f"  V2 总分块数: {v2_metrics.get('total_chunks', 'N/A')}")
        if 'total_chunks' in improvements:
            change = improvements['total_chunks']['change']
            change_pct = improvements['total_chunks']['change_percent']
            report_lines.append(f"  变化: {change:+d} ({change_pct:+.1f}%)")
        report_lines.append("")
        
        # 质量分数对比
        report_lines.append("🎯 质量分数对比:")
        
        # 整体质量
        if 'overall_quality_score' in improvements:
            imp = improvements['overall_quality_score']
            report_lines.append(f"  整体质量分数: {imp['v1']:.2f} → {imp['v2']:.2f} ({imp['change_percent']:+.1f}%)")
        
        # 边界质量
        if 'boundary_quality_score' in improvements:
            imp = improvements['boundary_quality_score']
            report_lines.append(f"  边界质量分数: {imp['v1']:.2f} → {imp['v2']:.2f} ({imp['change_percent']:+.1f}%)")
        
        report_lines.append("")
        
        # 分块大小对比
        report_lines.append("📏 分块大小对比:")
        if 'average_chunk_size' in improvements:
            imp = improvements['average_chunk_size']
            report_lines.append(f"  平均分块大小: {imp['v1']} → {imp['v2']} 字符 ({imp['change_percent']:+.1f}%)")
        
        # 超大分块对比
        if 'extra_large_chunks_count' in improvements:
            imp = improvements['extra_large_chunks_count']
            report_lines.append(f"  超大分块数量: {imp['v1']} → {imp['v2']} ({imp['change']:+d})")
        
        report_lines.append("")
        
        # 问题分析
        report_lines.append("⚠️ 发现的问题:")
        
        if v2_metrics.get('total_chunks', 0) < 50:
            report_lines.append("  1. ❌ V2分块数量过少，可能导致分块过大")
        
        if v2_metrics.get('extra_large_chunks_count', 0) > 0:
            report_lines.append(f"  2. ❌ V2仍有{v2_metrics.get('extra_large_chunks_count', 0)}个超大分块")
        
        if v2_metrics.get('boundary_quality_score', 0) < 0.75:
            report_lines.append("  3. ⚠️ V2边界质量仍需提升")
        
        # 改进建议
        report_lines.append("")
        report_lines.append("💡 改进建议:")
        report_lines.append("  1. 降低目标分块大小（建议400-600字符）")
        report_lines.append("  2. 强制分割超过1500字符的分块")
        report_lines.append("  3. 优化数字标题检测的置信度阈值")
        report_lines.append("  4. 增加更多语义边界检测规则")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        
        report_content = "\n".join(report_lines)
        
        # 保存报告
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                print(f"📄 对比报告已保存至: {output_file}")
            except Exception as e:
                print(f"❌ 报告保存失败: {e}")
        
        return report_content

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='版本对比分析脚本')
    parser.add_argument('--v1-quality', required=True, help='V1质量报告文件路径')
    parser.add_argument('--v2-stats', required=True, help='V2统计文件路径')
    parser.add_argument('--output', '-o', help='输出报告文件路径')
    
    args = parser.parse_args()
    
    try:
        # 创建对比器
        comparator = VersionComparator()
        
        # 加载数据
        comparator.load_v1_results(args.v1_quality)
        comparator.load_v2_results(args.v2_stats)
        
        # 生成报告
        report = comparator.generate_report(args.output)
        
        # 打印报告
        print(report)
        
        return 0
        
    except Exception as e:
        print(f"❌ 对比分析失败: {e}")
        return 1

if __name__ == "__main__":
    exit(main())