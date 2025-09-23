#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档质量扫描器 - 检查转换后的文档分块质量和结构
用于分析preprocess_enhanced.py处理后的文档，评估分块效果和质量

主要功能：
- 分析分块大小分布
- 检查分块边界质量
- 识别潜在的分块问题
- 生成详细的质量报告
- 验证章节结构完整性

作者: RAG预处理专家
版本: 1.0
更新日期: 2024
"""

import argparse
import re
import json
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import statistics

class DocumentQualityScanner:
    """文档质量扫描器"""
    
    def __init__(self):
        self.chunks = []
        self.chunk_boundaries = []
        self.statistics = {}
        self.issues = []
        
    def load_document(self, file_path: str) -> bool:
        """
        加载处理后的文档
        
        Args:
            file_path (str): 文档路径
            
        Returns:
            bool: 是否成功加载
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 按[CHUNK_BOUNDARY]分割文档
            chunks = content.split('[CHUNK_BOUNDARY]')
            self.chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
            
            print(f"成功加载文档: {file_path}")
            print(f"检测到 {len(self.chunks)} 个分块")
            return True
            
        except Exception as e:
            print(f"加载文档失败: {e}")
            return False
    
    def analyze_chunk_sizes(self) -> Dict:
        """
        分析分块大小分布
        
        Returns:
            Dict: 大小分析结果
        """
        sizes = [len(chunk) for chunk in self.chunks]
        
        if not sizes:
            return {}
        
        analysis = {
            'total_chunks': len(sizes),
            'total_characters': sum(sizes),
            'average_size': statistics.mean(sizes),
            'median_size': statistics.median(sizes),
            'min_size': min(sizes),
            'max_size': max(sizes),
            'std_deviation': statistics.stdev(sizes) if len(sizes) > 1 else 0
        }
        
        # 大小分布统计
        size_ranges = {
            'very_small': len([s for s in sizes if s < 200]),
            'small': len([s for s in sizes if 200 <= s < 500]),
            'medium': len([s for s in sizes if 500 <= s < 1000]),
            'large': len([s for s in sizes if 1000 <= s < 2000]),
            'very_large': len([s for s in sizes if s >= 2000])
        }
        
        analysis['size_distribution'] = size_ranges
        
        return analysis
    
    def analyze_chunk_boundaries(self) -> Dict:
        """
        分析分块边界质量
        
        Returns:
            Dict: 边界分析结果
        """
        boundary_types = {
            'markdown_heading': 0,
            'chinese_major_section': 0,
            'chinese_sub_section': 0,
            'numeric_section': 0,
            'table_title': 0,
            'empty_line': 0,
            'other': 0
        }
        
        boundary_quality_scores = []
        
        for i, chunk in enumerate(self.chunks):
            if not chunk:
                continue
                
            lines = chunk.split('\n')
            first_line = lines[0].strip() if lines else ""
            
            # 分析边界类型
            boundary_type = self._classify_boundary(first_line)
            boundary_types[boundary_type] += 1
            
            # 计算边界质量分数
            quality_score = self._calculate_boundary_quality(first_line, chunk)
            boundary_quality_scores.append(quality_score)
        
        return {
            'boundary_types': boundary_types,
            'average_quality_score': statistics.mean(boundary_quality_scores) if boundary_quality_scores else 0,
            'quality_scores': boundary_quality_scores
        }
    
    def _classify_boundary(self, line: str) -> str:
        """
        分类边界类型
        
        Args:
            line (str): 边界行
            
        Returns:
            str: 边界类型
        """
        if not line:
            return 'empty_line'
        
        # Markdown标题
        if line.startswith('#'):
            return 'markdown_heading'
        
        # 中文一级序号
        if re.match(r'^[一二三四五六七八九十]+、', line):
            return 'chinese_major_section'
        
        # 中文子序号
        if re.match(r'^\([一二三四五六七八九十]+\)', line):
            return 'chinese_sub_section'
        
        # 数字标题
        if re.match(r'^(<\d+>)?\d{1,2}[\u4e00-\u9fa5]', line):
            return 'numeric_section'
        
        # 表格标题（冒号结尾）
        if line.endswith('：') or line.endswith(':'):
            return 'table_title'
        
        return 'other'
    
    def _calculate_boundary_quality(self, boundary_line: str, chunk_content: str) -> float:
        """
        计算边界质量分数
        
        Args:
            boundary_line (str): 边界行
            chunk_content (str): 分块内容
            
        Returns:
            float: 质量分数 (0-1)
        """
        score = 0.0
        
        # 基础分数：有明确的标题结构
        if self._classify_boundary(boundary_line) in ['markdown_heading', 'chinese_major_section', 'numeric_section']:
            score += 0.4
        
        # 内容完整性：检查是否有完整的段落
        lines = chunk_content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        if len(non_empty_lines) >= 3:  # 至少3行非空内容
            score += 0.2
        
        # 语义连贯性：检查是否以句号结尾
        if chunk_content.strip().endswith(('。', '.', '！', '!', '？', '?')):
            score += 0.2
        
        # 结构完整性：检查是否包含表格或列表
        if '<table>' in chunk_content or re.search(r'^\d+\.', chunk_content, re.MULTILINE):
            score += 0.1
        
        # 长度合理性：避免过短或过长
        chunk_length = len(chunk_content)
        if 300 <= chunk_length <= 1500:
            score += 0.1
        
        return min(score, 1.0)
    
    def detect_issues(self) -> List[Dict]:
        """
        检测潜在问题
        
        Returns:
            List[Dict]: 问题列表
        """
        issues = []
        
        for i, chunk in enumerate(self.chunks):
            chunk_length = len(chunk)
            
            # 检测过小的分块
            if chunk_length < 100:
                issues.append({
                    'type': 'too_small',
                    'chunk_index': i,
                    'description': f'分块 {i+1} 过小 ({chunk_length} 字符)',
                    'severity': 'medium',
                    'chunk_preview': chunk[:100] + '...' if len(chunk) > 100 else chunk
                })
            
            # 检测过大的分块
            if chunk_length > 3000:
                issues.append({
                    'type': 'too_large',
                    'chunk_index': i,
                    'description': f'分块 {i+1} 过大 ({chunk_length} 字符)',
                    'severity': 'high',
                    'chunk_preview': chunk[:100] + '...'
                })
            
            # 检测空分块
            if not chunk.strip():
                issues.append({
                    'type': 'empty_chunk',
                    'chunk_index': i,
                    'description': f'分块 {i+1} 为空',
                    'severity': 'high',
                    'chunk_preview': ''
                })
            
            # 检测可能的分块边界问题
            lines = chunk.split('\n')
            first_line = lines[0].strip() if lines else ""
            
            if first_line and not self._is_good_boundary(first_line):
                issues.append({
                    'type': 'poor_boundary',
                    'chunk_index': i,
                    'description': f'分块 {i+1} 边界质量较差',
                    'severity': 'low',
                    'chunk_preview': first_line
                })
        
        return issues
    
    def _is_good_boundary(self, line: str) -> bool:
        """
        判断是否为良好的分块边界
        
        Args:
            line (str): 边界行
            
        Returns:
            bool: 是否为良好边界
        """
        boundary_type = self._classify_boundary(line)
        return boundary_type in ['markdown_heading', 'chinese_major_section', 'chinese_sub_section', 'numeric_section']
    
    def analyze_content_structure(self) -> Dict:
        """
        分析内容结构
        
        Returns:
            Dict: 结构分析结果
        """
        structure_stats = {
            'chunks_with_tables': 0,
            'chunks_with_lists': 0,
            'chunks_with_headings': 0,
            'chunks_with_references': 0,
            'average_lines_per_chunk': 0,
            'content_types': defaultdict(int)
        }
        
        total_lines = 0
        
        for chunk in self.chunks:
            lines = chunk.split('\n')
            total_lines += len(lines)
            
            # 检测表格
            if '<table>' in chunk:
                structure_stats['chunks_with_tables'] += 1
                structure_stats['content_types']['table'] += 1
            
            # 检测列表
            if re.search(r'^\d+\.', chunk, re.MULTILINE) or re.search(r'^[•\-\*]', chunk, re.MULTILINE):
                structure_stats['chunks_with_lists'] += 1
                structure_stats['content_types']['list'] += 1
            
            # 检测标题
            if re.search(r'^#+', chunk, re.MULTILINE):
                structure_stats['chunks_with_headings'] += 1
                structure_stats['content_types']['heading'] += 1
            
            # 检测引用或注释
            if '【注释】' in chunk or '注：' in chunk or re.search(r'\[\d+\]', chunk):
                structure_stats['chunks_with_references'] += 1
                structure_stats['content_types']['reference'] += 1
            
            # 检测纯文本
            if not any([
                '<table>' in chunk,
                re.search(r'^\d+\.', chunk, re.MULTILINE),
                re.search(r'^#+', chunk, re.MULTILINE),
                '【注释】' in chunk
            ]):
                structure_stats['content_types']['text'] += 1
        
        structure_stats['average_lines_per_chunk'] = total_lines / len(self.chunks) if self.chunks else 0
        
        return structure_stats
    
    def generate_report(self) -> Dict:
        """
        生成完整的质量报告
        
        Returns:
            Dict: 质量报告
        """
        print("正在分析文档质量...")
        
        # 执行各项分析
        size_analysis = self.analyze_chunk_sizes()
        boundary_analysis = self.analyze_chunk_boundaries()
        structure_analysis = self.analyze_content_structure()
        issues = self.detect_issues()
        
        # 计算总体质量分数
        overall_score = self._calculate_overall_score(size_analysis, boundary_analysis, issues)
        
        report = {
            'summary': {
                'total_chunks': len(self.chunks),
                'overall_quality_score': overall_score,
                'total_issues': len(issues),
                'high_severity_issues': len([i for i in issues if i['severity'] == 'high'])
            },
            'size_analysis': size_analysis,
            'boundary_analysis': boundary_analysis,
            'structure_analysis': structure_analysis,
            'issues': issues,
            'recommendations': self._generate_recommendations(issues, size_analysis)
        }
        
        return report
    
    def _calculate_overall_score(self, size_analysis: Dict, boundary_analysis: Dict, issues: List) -> float:
        """
        计算总体质量分数
        
        Args:
            size_analysis (Dict): 大小分析结果
            boundary_analysis (Dict): 边界分析结果
            issues (List): 问题列表
            
        Returns:
            float: 总体质量分数 (0-1)
        """
        score = 0.0
        
        # 大小分布分数 (30%)
        if size_analysis:
            avg_size = size_analysis.get('average_size', 0)
            if 400 <= avg_size <= 1200:  # 理想范围
                score += 0.3
            elif 200 <= avg_size <= 2000:  # 可接受范围
                score += 0.2
            else:
                score += 0.1
        
        # 边界质量分数 (40%)
        boundary_score = boundary_analysis.get('average_quality_score', 0)
        score += boundary_score * 0.4
        
        # 问题惩罚 (30%)
        issue_penalty = 0
        for issue in issues:
            if issue['severity'] == 'high':
                issue_penalty += 0.1
            elif issue['severity'] == 'medium':
                issue_penalty += 0.05
            else:
                issue_penalty += 0.02
        
        issue_score = max(0, 0.3 - issue_penalty)
        score += issue_score
        
        return min(score, 1.0)
    
    def _generate_recommendations(self, issues: List, size_analysis: Dict) -> List[str]:
        """
        生成改进建议
        
        Args:
            issues (List): 问题列表
            size_analysis (Dict): 大小分析结果
            
        Returns:
            List[str]: 建议列表
        """
        recommendations = []
        
        # 基于问题的建议
        issue_types = Counter([issue['type'] for issue in issues])
        
        if issue_types.get('too_small', 0) > 5:
            recommendations.append("建议调整分块策略，减少过小的分块数量，可以考虑合并相邻的小分块")
        
        if issue_types.get('too_large', 0) > 0:
            recommendations.append("建议对过大的分块进行进一步分割，保持分块大小的合理性")
        
        if issue_types.get('poor_boundary', 0) > 10:
            recommendations.append("建议优化分块边界检测逻辑，提高边界识别的准确性")
        
        # 基于大小分析的建议
        if size_analysis:
            avg_size = size_analysis.get('average_size', 0)
            if avg_size < 300:
                recommendations.append("平均分块大小偏小，建议增加分块的最小字符数限制")
            elif avg_size > 1500:
                recommendations.append("平均分块大小偏大，建议降低分块的最大字符数限制")
        
        if not recommendations:
            recommendations.append("文档分块质量良好，无需特别调整")
        
        return recommendations
    
    def print_report(self, report: Dict):
        """
        打印格式化的报告
        
        Args:
            report (Dict): 质量报告
        """
        print("\n" + "="*60)
        print("文档质量分析报告")
        print("="*60)
        
        # 总体概况
        summary = report['summary']
        print(f"\n📊 总体概况:")
        print(f"   总分块数: {summary['total_chunks']}")
        print(f"   质量分数: {summary['overall_quality_score']:.2f}/1.00")
        print(f"   发现问题: {summary['total_issues']} 个")
        print(f"   严重问题: {summary['high_severity_issues']} 个")
        
        # 大小分析
        size_analysis = report['size_analysis']
        if size_analysis:
            print(f"\n📏 分块大小分析:")
            print(f"   平均大小: {size_analysis['average_size']:.0f} 字符")
            print(f"   中位数: {size_analysis['median_size']:.0f} 字符")
            print(f"   最小/最大: {size_analysis['min_size']}/{size_analysis['max_size']} 字符")
            print(f"   标准差: {size_analysis['std_deviation']:.0f}")
            
            print(f"\n   大小分布:")
            dist = size_analysis['size_distribution']
            print(f"   很小(<200): {dist['very_small']} 个")
            print(f"   小(200-500): {dist['small']} 个")
            print(f"   中(500-1000): {dist['medium']} 个")
            print(f"   大(1000-2000): {dist['large']} 个")
            print(f"   很大(>=2000): {dist['very_large']} 个")
        
        # 边界分析
        boundary_analysis = report['boundary_analysis']
        if boundary_analysis:
            print(f"\n🎯 边界质量分析:")
            print(f"   平均质量分数: {boundary_analysis['average_quality_score']:.2f}/1.00")
            
            print(f"\n   边界类型分布:")
            types = boundary_analysis['boundary_types']
            for boundary_type, count in types.items():
                if count > 0:
                    print(f"   {boundary_type}: {count} 个")
        
        # 结构分析
        structure_analysis = report['structure_analysis']
        if structure_analysis:
            print(f"\n🏗️ 内容结构分析:")
            print(f"   包含表格的分块: {structure_analysis['chunks_with_tables']} 个")
            print(f"   包含列表的分块: {structure_analysis['chunks_with_lists']} 个")
            print(f"   包含标题的分块: {structure_analysis['chunks_with_headings']} 个")
            print(f"   包含引用的分块: {structure_analysis['chunks_with_references']} 个")
            print(f"   平均行数/分块: {structure_analysis['average_lines_per_chunk']:.1f}")
        
        # 问题列表
        issues = report['issues']
        if issues:
            print(f"\n⚠️ 发现的问题:")
            for i, issue in enumerate(issues[:10]):  # 只显示前10个问题
                severity_icon = "🔴" if issue['severity'] == 'high' else "🟡" if issue['severity'] == 'medium' else "🟢"
                print(f"   {severity_icon} {issue['description']}")
                if issue['chunk_preview']:
                    preview = issue['chunk_preview'][:50] + "..." if len(issue['chunk_preview']) > 50 else issue['chunk_preview']
                    print(f"      预览: {preview}")
            
            if len(issues) > 10:
                print(f"   ... 还有 {len(issues) - 10} 个问题")
        
        # 改进建议
        recommendations = report['recommendations']
        if recommendations:
            print(f"\n💡 改进建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        print("\n" + "="*60)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='文档质量扫描器')
    parser.add_argument('input_file', help='输入文件路径（处理后的文档）')
    parser.add_argument('--output', '-o', help='输出报告文件路径（JSON格式）')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 创建扫描器
    scanner = DocumentQualityScanner()
    
    # 加载文档
    if not scanner.load_document(args.input_file):
        return 1
    
    # 生成报告
    report = scanner.generate_report()
    
    # 打印报告
    scanner.print_report(report)
    
    # 保存报告
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存至: {args.output}")
    
    return 0

if __name__ == "__main__":
    exit(main())