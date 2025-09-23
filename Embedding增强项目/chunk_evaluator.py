#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chunk质量评估模块
用于评估文档分块的质量，包括分块数量、语义完整性、格式正确性等指标
"""

import re
import os
import json
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class ChunkEvaluationResult:
    """
    Chunk评估结果数据类
    
    Attributes:
        total_chunks: 总分块数量
        total_chars: 总字符数
        avg_chunk_size: 平均分块大小
        chunk_size_distribution: 分块大小分布
        semantic_integrity_score: 语义完整性评分
        format_correctness_score: 格式正确性评分
        overall_score: 总体评分
        recommendations: 优化建议
    """
    total_chunks: int
    total_chars: int
    avg_chunk_size: int
    chunk_size_distribution: Dict[str, int]
    semantic_integrity_score: float
    format_correctness_score: float
    overall_score: float
    recommendations: List[str]


class ChunkEvaluator:
    """
    Chunk质量评估器
    
    用于评估文档分块的质量，提供详细的评估报告和优化建议
    """
    
    @staticmethod
    def load_config():
        """
        加载配置文件，获取chunk处理相关参数。
        
        Returns:
            dict: 配置字典，包含chunk_processing等配置项
        """
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"chunk_processing": {"target_chunk_size": 1000}}
    
    def __init__(self, target_chunk_size: int = None, chunk_boundary_marker: str = "[CHUNK_BOUNDARY]"):
        """
        初始化评估器
        
        Args:
            target_chunk_size: 目标分块大小（字符数），如果为None则从配置文件读取
            chunk_boundary_marker: 分块边界标记
        """
        if target_chunk_size is None:
            config = self.load_config()
            target_chunk_size = config.get('chunk_processing', {}).get('target_chunk_size', 1000)
        
        self.target_chunk_size = target_chunk_size
        self.chunk_boundary_marker = chunk_boundary_marker
        
        # 医学文档语义完整性检查模式
        self.semantic_patterns = {
            'chapter_titles': r'<\d+># .+',  # 章节标题
            'drug_names': r'[A-Za-z\u4e00-\u9fff]+(?:酸|素|胺|醇|酮|肽|霉素|西林|沙星)',  # 药物名称
            'medical_terms': r'(?:治疗|诊断|症状|并发症|副作用|禁忌|适应症)',  # 医学术语
            'dosage_info': r'\d+(?:mg|g|ml|μg|IU)(?:/(?:日|次|kg))?',  # 剂量信息
            'numbered_lists': r'^\d+[\.、]',  # 编号列表
            'bullet_points': r'^[•·\-\*]',  # 项目符号
        }
    
    def evaluate_file(self, file_path: str) -> ChunkEvaluationResult:
        """
        评估单个文件的chunk质量
        
        Args:
            file_path: 文件路径
            
        Returns:
            ChunkEvaluationResult: 评估结果
            
        Raises:
            FileNotFoundError: 文件不存在
            UnicodeDecodeError: 文件编码错误
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(f"文件编码错误: {e}")
        
        return self._evaluate_content(content, file_path)
    
    def _evaluate_content(self, content: str, file_path: str = "") -> ChunkEvaluationResult:
        """
        评估文档内容的chunk质量
        
        Args:
            content: 文档内容
            file_path: 文件路径（用于报告）
            
        Returns:
            ChunkEvaluationResult: 评估结果
        """
        # 分割chunks
        chunks = self._split_chunks(content)
        
        # 基础统计
        total_chunks = len(chunks)
        total_chars = len(content.replace(self.chunk_boundary_marker, ''))
        avg_chunk_size = total_chars // total_chunks if total_chunks > 0 else 0
        
        # 分块大小分布
        chunk_size_distribution = self._analyze_chunk_size_distribution(chunks)
        
        # 语义完整性评分
        semantic_score = self._evaluate_semantic_integrity(chunks)
        
        # 格式正确性评分
        format_score = self._evaluate_format_correctness(content, chunks)
        
        # 总体评分
        overall_score = (semantic_score + format_score) / 2
        
        # 生成建议
        recommendations = self._generate_recommendations(
            total_chunks, avg_chunk_size, chunk_size_distribution, 
            semantic_score, format_score
        )
        
        return ChunkEvaluationResult(
            total_chunks=total_chunks,
            total_chars=total_chars,
            avg_chunk_size=avg_chunk_size,
            chunk_size_distribution=chunk_size_distribution,
            semantic_integrity_score=semantic_score,
            format_correctness_score=format_score,
            overall_score=overall_score,
            recommendations=recommendations
        )
    
    def _split_chunks(self, content: str) -> List[str]:
        """
        根据边界标记分割chunks
        
        Args:
            content: 文档内容
            
        Returns:
            List[str]: 分割后的chunks列表
        """
        chunks = content.split(self.chunk_boundary_marker)
        # 移除空chunks
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    
    def _analyze_chunk_size_distribution(self, chunks: List[str]) -> Dict[str, int]:
        """
        分析chunk大小分布
        
        Args:
            chunks: chunks列表
            
        Returns:
            Dict[str, int]: 大小分布统计
        """
        distribution = {
            'very_small': 0,    # < 500字符
            'small': 0,         # 500-800字符
            'optimal': 0,       # 800-1200字符
            'large': 0,         # 1200-1500字符
            'very_large': 0     # > 1500字符
        }
        
        for chunk in chunks:
            size = len(chunk)
            if size < 500:
                distribution['very_small'] += 1
            elif size < 800:
                distribution['small'] += 1
            elif size < 1200:
                distribution['optimal'] += 1
            elif size < 1500:
                distribution['large'] += 1
            else:
                distribution['very_large'] += 1
        
        return distribution
    
    def _evaluate_semantic_integrity(self, chunks: List[str]) -> float:
        """
        评估语义完整性
        
        Args:
            chunks: chunks列表
            
        Returns:
            float: 语义完整性评分 (0-100)
        """
        total_score = 0
        total_checks = 0
        
        for chunk in chunks:
            chunk_score = 0
            chunk_checks = 0
            
            # 检查是否有完整的句子结构
            sentences = re.split(r'[。！？]', chunk)
            complete_sentences = [s for s in sentences if len(s.strip()) > 10]
            if complete_sentences:
                chunk_score += 20
            chunk_checks += 1
            
            # 检查是否有医学术语的完整性
            for pattern_name, pattern in self.semantic_patterns.items():
                matches = re.findall(pattern, chunk, re.MULTILINE)
                if matches:
                    # 检查术语是否被截断
                    for match in matches:
                        if not self._is_term_truncated(match, chunk):
                            chunk_score += 10
                        chunk_checks += 1
            
            # 检查段落完整性
            if self._has_complete_paragraphs(chunk):
                chunk_score += 15
            chunk_checks += 1
            
            # 检查列表完整性
            if self._has_complete_lists(chunk):
                chunk_score += 15
            chunk_checks += 1
            
            if chunk_checks > 0:
                total_score += min(100, chunk_score / chunk_checks * 100)
                total_checks += 1
        
        return total_score / total_checks if total_checks > 0 else 0
    
    def _evaluate_format_correctness(self, content: str, chunks: List[str]) -> float:
        """
        评估格式正确性
        
        Args:
            content: 原始内容
            chunks: chunks列表
            
        Returns:
            float: 格式正确性评分 (0-100)
        """
        score = 0
        
        # 检查边界标记的正确性
        boundary_count = content.count(self.chunk_boundary_marker)
        expected_boundaries = len(chunks) - 1
        if boundary_count == expected_boundaries:
            score += 30
        elif abs(boundary_count - expected_boundaries) <= 2:
            score += 20
        else:
            score += 10
        
        # 检查chunk开始和结束的格式
        well_formatted_chunks = 0
        for chunk in chunks:
            if self._is_chunk_well_formatted(chunk):
                well_formatted_chunks += 1
        
        format_ratio = well_formatted_chunks / len(chunks) if chunks else 0
        score += format_ratio * 40
        
        # 检查特殊标记的保留
        if self._are_special_markers_preserved(content):
            score += 30
        else:
            score += 15
        
        return min(100, score)
    
    def _is_term_truncated(self, term: str, chunk: str) -> bool:
        """
        检查术语是否被截断
        
        Args:
            term: 术语
            chunk: chunk内容
            
        Returns:
            bool: 是否被截断
        """
        # 简单的截断检查：术语前后是否有合理的上下文
        term_index = chunk.find(term)
        if term_index == -1:
            return True
        
        # 检查前后字符
        before_char = chunk[term_index - 1] if term_index > 0 else ' '
        after_char = chunk[term_index + len(term)] if term_index + len(term) < len(chunk) else ' '
        
        # 如果前后都是字母或汉字，可能被截断
        if (before_char.isalnum() or '\u4e00' <= before_char <= '\u9fff') and \
           (after_char.isalnum() or '\u4e00' <= after_char <= '\u9fff'):
            return True
        
        return False
    
    def _has_complete_paragraphs(self, chunk: str) -> bool:
        """
        检查是否有完整的段落
        
        Args:
            chunk: chunk内容
            
        Returns:
            bool: 是否有完整段落
        """
        # 检查是否以段落开始和结束
        lines = chunk.strip().split('\n')
        if not lines:
            return False
        
        # 至少有一个完整的段落（以句号结尾）
        for line in lines:
            if line.strip().endswith(('。', '！', '？', '.')):
                return True
        
        return False
    
    def _has_complete_lists(self, chunk: str) -> bool:
        """
        检查是否有完整的列表
        
        Args:
            chunk: chunk内容
            
        Returns:
            bool: 是否有完整列表
        """
        lines = chunk.strip().split('\n')
        list_items = []
        
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+[\.、]', line) or re.match(r'^[•·\-\*]', line):
                list_items.append(line)
        
        # 如果有列表项，检查是否连续
        if len(list_items) >= 2:
            return True
        
        return len(list_items) == 0  # 没有列表也算完整
    
    def _is_chunk_well_formatted(self, chunk: str) -> bool:
        """
        检查chunk格式是否良好
        
        Args:
            chunk: chunk内容
            
        Returns:
            bool: 格式是否良好
        """
        chunk = chunk.strip()
        if not chunk:
            return False
        
        # 检查是否以合理的内容开始（不是标点符号）
        if chunk[0] in '，。！？；：':
            return False
        
        # 检查是否有基本的结构
        if len(chunk) < 50:  # 太短
            return False
        
        return True
    
    def _are_special_markers_preserved(self, content: str) -> bool:
        """
        检查特殊标记是否被保留
        
        Args:
            content: 文档内容
            
        Returns:
            bool: 特殊标记是否被保留
        """
        # 检查文档开始和结束标记
        has_start_marker = '====== 文档开始 ======' in content
        has_end_marker = '====== 文档结束 ======' in content
        
        # 检查编号标记
        has_numbered_content = bool(re.search(r'<\d+>', content))
        
        return has_start_marker and has_end_marker and has_numbered_content
    
    def _generate_recommendations(self, total_chunks: int, avg_chunk_size: int, 
                                distribution: Dict[str, int], semantic_score: float, 
                                format_score: float) -> List[str]:
        """
        生成优化建议
        
        Args:
            total_chunks: 总chunk数
            avg_chunk_size: 平均chunk大小
            distribution: 大小分布
            semantic_score: 语义评分
            format_score: 格式评分
            
        Returns:
            List[str]: 建议列表
        """
        recommendations = []
        
        # 基于平均大小的建议
        if avg_chunk_size < 800:
            recommendations.append("平均chunk大小偏小，建议增加chunk大小以提高上下文完整性")
        elif avg_chunk_size > 1200:
            recommendations.append("平均chunk大小偏大，建议减小chunk大小以提高检索精度")
        
        # 基于分布的建议
        if distribution['very_small'] > total_chunks * 0.3:
            recommendations.append("过多的小chunk，建议合并相邻的小chunk")
        
        if distribution['very_large'] > total_chunks * 0.2:
            recommendations.append("存在过大的chunk，建议进一步分割")
        
        # 基于语义评分的建议
        if semantic_score < 70:
            recommendations.append("语义完整性较低，建议在语义边界处分割chunk")
            recommendations.append("检查医学术语是否被截断，调整分割策略")
        
        # 基于格式评分的建议
        if format_score < 80:
            recommendations.append("格式正确性有待提升，检查边界标记和特殊格式")
        
        # 总体建议
        overall_score = (semantic_score + format_score) / 2
        if overall_score >= 90:
            recommendations.append("chunk质量优秀，可以直接用于RAG系统")
        elif overall_score >= 75:
            recommendations.append("chunk质量良好，建议微调后使用")
        else:
            recommendations.append("chunk质量需要改进，建议重新处理")
        
        return recommendations if recommendations else ["chunk质量评估完成，未发现明显问题"]
    
    def print_evaluation_report(self, result: ChunkEvaluationResult, file_path: str = ""):
        """
        打印评估报告
        
        Args:
            result: 评估结果
            file_path: 文件路径
        """
        print("=" * 60)
        print("CHUNK质量评估报告")
        print("=" * 60)
        
        if file_path:
            print(f"文件: {file_path}")
            print("-" * 60)
        
        print(f"总chunk数量: {result.total_chunks}")
        print(f"总字符数: {result.total_chars:,}")
        print(f"平均chunk大小: {result.avg_chunk_size} 字符")
        print()
        
        print("Chunk大小分布:")
        for size_range, count in result.chunk_size_distribution.items():
            percentage = (count / result.total_chunks * 100) if result.total_chunks > 0 else 0
            print(f"  {size_range}: {count} ({percentage:.1f}%)")
        print()
        
        print(f"语义完整性评分: {result.semantic_integrity_score:.1f}/100")
        print(f"格式正确性评分: {result.format_correctness_score:.1f}/100")
        print(f"总体评分: {result.overall_score:.1f}/100")
        print()
        
        print("优化建议:")
        for i, recommendation in enumerate(result.recommendations, 1):
            print(f"  {i}. {recommendation}")
        
        print("=" * 60)


def main():
    """
    主函数，支持命令行参数指定文件路径
    """
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python chunk_evaluator.py <文件路径>")
        print("示例: python chunk_evaluator.py To_be_processed/乳腺癌诊疗指南2025_optimized.md")
        sys.exit(1)
    
    file_path = sys.argv[1]
    evaluator = ChunkEvaluator()
    
    try:
        result = evaluator.evaluate_file(file_path)
        evaluator.print_evaluation_report(result, file_path)
    except Exception as e:
        print(f"评估失败: {e}")


if __name__ == "__main__":
    main()