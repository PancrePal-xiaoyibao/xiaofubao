#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
边界问题分析器 - 深入分析边界质量差的根本原因
用于识别边界检测算法的薄弱环节并提出针对性优化方案

功能：
- 分析边界质量差的分块模式
- 识别问题分块的共同特征
- 统计不同类型边界的质量分布
- 生成优化建议和改进方案

作者: RAG预处理专家
版本: 1.0
"""

import json
import re
import argparse
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Set

class BoundaryIssueAnalyzer:
    """边界问题分析器类"""
    
    def __init__(self, quality_report_path: str, original_doc_path: str):
        """
        初始化分析器
        
        Args:
            quality_report_path (str): 质量报告JSON文件路径
            original_doc_path (str): 原始处理后文档路径
        """
        self.quality_report_path = quality_report_path
        self.original_doc_path = original_doc_path
        self.quality_data = {}
        self.document_lines = []
        self.chunk_boundaries = []
        
    def load_data(self) -> bool:
        """
        加载质量报告和原始文档数据
        
        Returns:
            bool: 加载是否成功
        """
        try:
            # 加载质量报告
            with open(self.quality_report_path, 'r', encoding='utf-8') as f:
                self.quality_data = json.load(f)
            
            # 加载原始文档
            with open(self.original_doc_path, 'r', encoding='utf-8') as f:
                self.document_lines = f.readlines()
            
            print(f"✅ 成功加载质量报告和文档数据")
            print(f"   - 质量报告问题数: {len(self.quality_data.get('issues', []))}")
            print(f"   - 文档总行数: {len(self.document_lines)}")
            
            return True
            
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False
    
    def extract_chunk_boundaries(self) -> List[Tuple[int, str, str]]:
        """
        从文档中提取分块边界信息
        
        Returns:
            List[Tuple[int, str, str]]: (行号, 边界类型, 内容) 的列表
        """
        boundaries = []
        
        for i, line in enumerate(self.document_lines):
            line = line.strip()
            
            # 检测各种边界类型
            if line.startswith('====== 分块'):
                boundaries.append((i, 'chunk_separator', line))
            elif re.match(r'^<\d+>', line):
                boundaries.append((i, 'numeric_title', line))
            elif line.startswith('#'):
                boundaries.append((i, 'markdown_heading', line))
            elif line.startswith('|') and line.endswith('|'):
                boundaries.append((i, 'table_row', line))
            elif re.match(r'^\[\d+\]', line):
                boundaries.append((i, 'reference', line))
            elif line == '':
                boundaries.append((i, 'empty_line', line))
        
        self.chunk_boundaries = boundaries
        return boundaries
    
    def analyze_poor_boundary_patterns(self) -> Dict[str, any]:
        """
        分析边界质量差的模式
        
        Returns:
            Dict[str, any]: 分析结果
        """
        poor_boundary_issues = [
            issue for issue in self.quality_data.get('issues', [])
            if issue.get('type') == 'poor_boundary'
        ]
        
        print(f"\n🔍 分析 {len(poor_boundary_issues)} 个边界质量差问题")
        
        # 分析问题分块的内容模式
        content_patterns = defaultdict(int)
        length_distribution = []
        starting_patterns = defaultdict(int)
        
        for issue in poor_boundary_issues:
            preview = issue.get('chunk_preview', '')
            chunk_index = issue.get('chunk_index', 0)
            
            # 统计内容长度
            length_distribution.append(len(preview))
            
            # 分析起始模式
            if preview.startswith('<'):
                if re.match(r'^<\d+>', preview):
                    starting_patterns['numeric_marker'] += 1
                else:
                    starting_patterns['other_bracket'] += 1
            elif preview.startswith('#'):
                starting_patterns['markdown_heading'] += 1
            elif preview.startswith('===='):
                starting_patterns['separator'] += 1
            elif preview.startswith('['):
                starting_patterns['reference'] += 1
            elif preview.startswith('|'):
                starting_patterns['table'] += 1
            else:
                starting_patterns['text_content'] += 1
            
            # 分析内容类型
            if '=====' in preview:
                content_patterns['document_separator'] += 1
            elif re.search(r'<\d+>', preview):
                content_patterns['has_numeric_marker'] += 1
            elif '版权' in preview or '侵权' in preview:
                content_patterns['copyright_info'] += 1
            elif '专家' in preview or '委员会' in preview:
                content_patterns['expert_info'] += 1
            elif '目录' in preview:
                content_patterns['table_of_contents'] += 1
            elif re.search(r'\[\d+\]', preview):
                content_patterns['reference_content'] += 1
            elif '·' in preview:
                content_patterns['bullet_point'] += 1
            else:
                content_patterns['general_text'] += 1
        
        return {
            'total_poor_boundaries': len(poor_boundary_issues),
            'content_patterns': dict(content_patterns),
            'starting_patterns': dict(starting_patterns),
            'length_stats': {
                'min': min(length_distribution) if length_distribution else 0,
                'max': max(length_distribution) if length_distribution else 0,
                'avg': sum(length_distribution) / len(length_distribution) if length_distribution else 0
            }
        }
    
    def analyze_boundary_quality_distribution(self) -> Dict[str, any]:
        """
        分析边界质量分数分布
        
        Returns:
            Dict[str, any]: 边界质量分析结果
        """
        boundary_analysis = self.quality_data.get('boundary_analysis', {})
        quality_scores = boundary_analysis.get('quality_scores', [])
        
        if not quality_scores:
            return {'error': '无边界质量分数数据'}
        
        # 统计质量分数分布
        score_distribution = Counter()
        for score in quality_scores:
            score_range = f"{score:.1f}"
            score_distribution[score_range] += 1
        
        # 计算统计指标
        good_boundaries = sum(1 for score in quality_scores if score >= 0.7)
        poor_boundaries = sum(1 for score in quality_scores if score <= 0.3)
        
        return {
            'total_boundaries': len(quality_scores),
            'good_boundaries': good_boundaries,
            'poor_boundaries': poor_boundaries,
            'average_quality': sum(quality_scores) / len(quality_scores),
            'score_distribution': dict(score_distribution.most_common()),
            'quality_percentage': {
                'good': (good_boundaries / len(quality_scores)) * 100,
                'poor': (poor_boundaries / len(quality_scores)) * 100
            }
        }
    
    def identify_problematic_sections(self) -> List[Dict[str, any]]:
        """
        识别问题集中的文档区域
        
        Returns:
            List[Dict[str, any]]: 问题区域列表
        """
        poor_boundary_issues = [
            issue for issue in self.quality_data.get('issues', [])
            if issue.get('type') == 'poor_boundary'
        ]
        
        # 按分块索引分组
        chunk_issue_counts = Counter()
        for issue in poor_boundary_issues:
            chunk_index = issue.get('chunk_index', 0)
            chunk_issue_counts[chunk_index] += 1
        
        # 识别问题集中区域（连续的问题分块）
        problematic_sections = []
        current_section = None
        
        for chunk_index in sorted(chunk_issue_counts.keys()):
            if current_section is None:
                current_section = {
                    'start_chunk': chunk_index,
                    'end_chunk': chunk_index,
                    'issue_count': chunk_issue_counts[chunk_index],
                    'chunk_previews': []
                }
            elif chunk_index == current_section['end_chunk'] + 1:
                # 连续区域
                current_section['end_chunk'] = chunk_index
                current_section['issue_count'] += chunk_issue_counts[chunk_index]
            else:
                # 新区域开始
                if current_section['issue_count'] >= 3:  # 只记录问题较多的区域
                    problematic_sections.append(current_section)
                
                current_section = {
                    'start_chunk': chunk_index,
                    'end_chunk': chunk_index,
                    'issue_count': chunk_issue_counts[chunk_index],
                    'chunk_previews': []
                }
        
        # 添加最后一个区域
        if current_section and current_section['issue_count'] >= 3:
            problematic_sections.append(current_section)
        
        # 为每个区域添加预览信息
        for section in problematic_sections:
            for issue in poor_boundary_issues:
                chunk_index = issue.get('chunk_index', 0)
                if section['start_chunk'] <= chunk_index <= section['end_chunk']:
                    section['chunk_previews'].append({
                        'chunk_index': chunk_index,
                        'preview': issue.get('chunk_preview', '')[:50]
                    })
        
        return problematic_sections
    
    def generate_optimization_recommendations(self, analysis_results: Dict[str, any]) -> List[str]:
        """
        基于分析结果生成优化建议
        
        Args:
            analysis_results (Dict[str, any]): 分析结果
            
        Returns:
            List[str]: 优化建议列表
        """
        recommendations = []
        
        pattern_analysis = analysis_results.get('pattern_analysis', {})
        quality_analysis = analysis_results.get('quality_analysis', {})
        
        # 基于内容模式的建议
        content_patterns = pattern_analysis.get('content_patterns', {})
        if content_patterns.get('has_numeric_marker', 0) > 20:
            recommendations.append(
                "🔧 优化数字标记边界检测：大量分块包含<数字>标记但边界质量差，"
                "建议改进数字标记的边界优先级算法"
            )
        
        if content_patterns.get('reference_content', 0) > 30:
            recommendations.append(
                "📚 改进引用文献处理：引用内容分块边界质量普遍较差，"
                "建议专门优化引用文献的分块逻辑"
            )
        
        if content_patterns.get('document_separator', 0) > 5:
            recommendations.append(
                "📄 优化文档分隔符处理：文档分隔符应该有更高的边界优先级，"
                "避免被误判为低质量边界"
            )
        
        # 基于质量分布的建议
        poor_percentage = quality_analysis.get('quality_percentage', {}).get('poor', 0)
        if poor_percentage > 30:
            recommendations.append(
                f"⚠️ 整体边界质量需要提升：{poor_percentage:.1f}%的边界质量较差，"
                "建议重新设计边界评分算法"
            )
        
        # 基于起始模式的建议
        starting_patterns = pattern_analysis.get('starting_patterns', {})
        if starting_patterns.get('text_content', 0) > starting_patterns.get('numeric_marker', 0):
            recommendations.append(
                "🎯 加强语义边界检测：大量问题分块以普通文本开始，"
                "建议增加基于语义的边界检测逻辑"
            )
        
        return recommendations
    
    def run_analysis(self) -> Dict[str, any]:
        """
        运行完整的边界问题分析
        
        Returns:
            Dict[str, any]: 完整分析结果
        """
        if not self.load_data():
            return {'error': '数据加载失败'}
        
        print("\n🔍 开始边界问题深度分析...")
        
        # 提取边界信息
        boundaries = self.extract_chunk_boundaries()
        
        # 分析边界质量差的模式
        pattern_analysis = self.analyze_poor_boundary_patterns()
        
        # 分析边界质量分布
        quality_analysis = self.analyze_boundary_quality_distribution()
        
        # 识别问题区域
        problematic_sections = self.identify_problematic_sections()
        
        # 生成分析结果
        analysis_results = {
            'pattern_analysis': pattern_analysis,
            'quality_analysis': quality_analysis,
            'problematic_sections': problematic_sections,
            'boundary_count': len(boundaries)
        }
        
        # 生成优化建议
        recommendations = self.generate_optimization_recommendations(analysis_results)
        analysis_results['recommendations'] = recommendations
        
        return analysis_results
    
    def print_analysis_report(self, results: Dict[str, any]):
        """
        打印分析报告
        
        Args:
            results (Dict[str, any]): 分析结果
        """
        print("\n" + "="*60)
        print("📊 边界问题深度分析报告")
        print("="*60)
        
        # 模式分析
        pattern_analysis = results.get('pattern_analysis', {})
        print(f"\n🔍 问题模式分析:")
        print(f"   总问题数: {pattern_analysis.get('total_poor_boundaries', 0)}")
        
        print(f"\n📋 内容类型分布:")
        for content_type, count in pattern_analysis.get('content_patterns', {}).items():
            print(f"   • {content_type}: {count} 个")
        
        print(f"\n🎯 起始模式分布:")
        for pattern, count in pattern_analysis.get('starting_patterns', {}).items():
            print(f"   • {pattern}: {count} 个")
        
        # 质量分析
        quality_analysis = results.get('quality_analysis', {})
        if 'error' not in quality_analysis:
            print(f"\n📈 边界质量分布:")
            print(f"   总边界数: {quality_analysis.get('total_boundaries', 0)}")
            print(f"   优质边界: {quality_analysis.get('good_boundaries', 0)} 个 "
                  f"({quality_analysis.get('quality_percentage', {}).get('good', 0):.1f}%)")
            print(f"   低质边界: {quality_analysis.get('poor_boundaries', 0)} 个 "
                  f"({quality_analysis.get('quality_percentage', {}).get('poor', 0):.1f}%)")
            print(f"   平均质量: {quality_analysis.get('average_quality', 0):.3f}")
        
        # 问题区域
        problematic_sections = results.get('problematic_sections', [])
        if problematic_sections:
            print(f"\n🎯 问题集中区域 ({len(problematic_sections)} 个):")
            for i, section in enumerate(problematic_sections, 1):
                print(f"   {i}. 分块 {section['start_chunk']+1}-{section['end_chunk']+1}: "
                      f"{section['issue_count']} 个问题")
        
        # 优化建议
        recommendations = results.get('recommendations', [])
        if recommendations:
            print(f"\n💡 优化建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        print("\n" + "="*60)

def main():
    """
    主函数 - 处理命令行参数并执行边界问题分析
    
    Returns:
        int: 程序退出码，0表示成功，1表示失败
    """
    parser = argparse.ArgumentParser(description='边界问题深度分析器')
    parser.add_argument('--report', '-r', default='quality_report.json',
                       help='质量报告JSON文件路径')
    parser.add_argument('--document', '-d', 
                       default='To_be_processed/乳腺癌诊疗指南2025_enhanced.md',
                       help='处理后的文档路径')
    parser.add_argument('--output', '-o', help='输出分析结果到JSON文件')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = BoundaryIssueAnalyzer(args.report, args.document)
    
    # 运行分析
    results = analyzer.run_analysis()
    
    if 'error' in results:
        print(f"❌ 分析失败: {results['error']}")
        return 1
    
    # 打印报告
    analyzer.print_analysis_report(results)
    
    # 保存结果（如果指定）
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 分析结果已保存至: {args.output}")
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())