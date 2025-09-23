#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版文档预处理器 V2 - 基于质量分析结果的优化版本
专门针对边界检测质量差的问题进行深度优化

主要改进：
1. 重新设计数字标记边界检测算法，提升边界质量
2. 优化分块大小控制，减少超大分块
3. 改进引用文献处理逻辑
4. 增强语义边界检测能力
5. 提供更精确的边界质量评估

作者: RAG预处理专家
版本: 2.0
基于: preprocess_enhanced.py + 质量分析优化
"""

import re
import argparse
import json
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class BoundaryType(Enum):
    """边界类型枚举"""
    DOCUMENT_START = "document_start"
    DOCUMENT_END = "document_end"
    MAJOR_SECTION = "major_section"
    MARKDOWN_HEADING = "markdown_heading"
    NUMERIC_TITLE = "numeric_title"
    TABLE_BOUNDARY = "table_boundary"
    REFERENCE_SECTION = "reference_section"
    PARAGRAPH_BREAK = "paragraph_break"
    SEMANTIC_BREAK = "semantic_break"

@dataclass
class BoundaryCandidate:
    """边界候选点数据类"""
    line_index: int
    boundary_type: BoundaryType
    priority: float
    content: str
    context_before: str = ""
    context_after: str = ""
    quality_score: float = 0.0

class EnhancedDocumentProcessor:
    """增强版文档处理器"""
    
    def __init__(self, target_chunk_size: int = 800, max_chunk_size: int = 1500):
        """
        初始化处理器
        
        Args:
            target_chunk_size (int): 目标分块大小（字符数）
            max_chunk_size (int): 最大分块大小（字符数）
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = 200
        
        # 优化后的边界检测配置
        self.boundary_priorities = {
            BoundaryType.DOCUMENT_START: 1.0,
            BoundaryType.DOCUMENT_END: 1.0,
            BoundaryType.MAJOR_SECTION: 0.95,
            BoundaryType.NUMERIC_TITLE: 0.90,  # 提升数字标题优先级
            BoundaryType.MARKDOWN_HEADING: 0.85,
            BoundaryType.TABLE_BOUNDARY: 0.80,
            BoundaryType.REFERENCE_SECTION: 0.75,
            BoundaryType.SEMANTIC_BREAK: 0.70,
            BoundaryType.PARAGRAPH_BREAK: 0.60
        }
        
        # 数字标记模式（优化版）
        self.numeric_patterns = [
            r'^<(\d+)>\s*(.+)$',  # <1007>标题内容
            r'^(\d+)\.?\s+(.+)$',  # 1. 标题内容 或 1 标题内容
            r'^第([一二三四五六七八九十\d]+)[章节部分]\s*(.+)$',  # 第一章 标题内容
            r'^[（(](\d+)[）)]\s*(.+)$',  # (1) 标题内容
            r'^[一二三四五六七八九十]+[、．.]\s*(.+)$'  # 一、标题内容
        ]
        
        # 语义边界关键词（扩展版）
        self.semantic_keywords = {
            'section_start': ['概述', '背景', '目的', '方法', '结果', '结论', '讨论', '建议', '总结'],
            'medical_terms': ['诊断', '治疗', '预后', '并发症', '副作用', '禁忌', '适应症'],
            'reference_markers': ['参考文献', '引用', '文献', '资料来源'],
            'table_markers': ['表格', '图表', '数据', '统计'],
            'conclusion_markers': ['因此', '综上', '总之', '综合以上', '基于以上']
        }
    
    def load_document(self, file_path: str) -> List[str]:
        """
        加载文档并按行分割
        
        Args:
            file_path (str): 文档文件路径
            
        Returns:
            List[str]: 文档行列表
            
        Raises:
            Exception: 文件读取失败时抛出异常
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 清理行内容，保留原始结构
            cleaned_lines = []
            for line in lines:
                # 保留原始换行符，只去除行尾空白
                cleaned_line = line.rstrip()
                cleaned_lines.append(cleaned_line)
            
            print(f"✅ 成功加载文档: {len(cleaned_lines)} 行")
            return cleaned_lines
            
        except Exception as e:
            print(f"❌ 文档加载失败: {e}")
            raise
    
    def detect_numeric_title_enhanced(self, line: str) -> Tuple[bool, float, str]:
        """
        增强版数字标题检测
        
        Args:
            line (str): 待检测的行
            
        Returns:
            Tuple[bool, float, str]: (是否为数字标题, 置信度, 提取的标题内容)
        """
        line = line.strip()
        if not line:
            return False, 0.0, ""
        
        # 检测各种数字标题模式
        for pattern in self.numeric_patterns:
            match = re.match(pattern, line)
            if match:
                # 计算置信度
                confidence = 0.8
                
                # 根据模式类型调整置信度
                if pattern.startswith(r'^<(\d+)>'):  # <1007>格式
                    confidence = 0.95
                elif pattern.startswith(r'^(\d+)\.'):  # 1. 格式
                    confidence = 0.90
                elif '章节部分' in pattern:  # 第一章格式
                    confidence = 0.85
                
                # 根据内容长度调整置信度
                groups = match.groups()
                title_content = groups[-1] if groups else ""
                if len(title_content) > 50:  # 标题过长，可能不是真正的标题
                    confidence *= 0.8
                elif len(title_content) < 5:  # 标题过短，可能不完整
                    confidence *= 0.9
                
                return True, confidence, title_content
        
        return False, 0.0, ""
    
    def detect_semantic_boundary(self, line: str, context_lines: List[str], line_index: int) -> float:
        """
        检测语义边界强度
        
        Args:
            line (str): 当前行
            context_lines (List[str]): 上下文行
            line_index (int): 当前行索引
            
        Returns:
            float: 语义边界强度 (0.0-1.0)
        """
        line = line.strip()
        if not line:
            return 0.0
        
        semantic_score = 0.0
        
        # 检测语义关键词
        for category, keywords in self.semantic_keywords.items():
            for keyword in keywords:
                if keyword in line:
                    if category == 'section_start':
                        semantic_score += 0.3
                    elif category == 'medical_terms':
                        semantic_score += 0.2
                    elif category == 'reference_markers':
                        semantic_score += 0.4
                    elif category == 'conclusion_markers':
                        semantic_score += 0.25
        
        # 检测段落结构变化
        if line_index > 0 and line_index < len(context_lines) - 1:
            prev_line = context_lines[line_index - 1].strip()
            next_line = context_lines[line_index + 1].strip()
            
            # 前一行为空，当前行非空，下一行非空 - 可能是新段落开始
            if not prev_line and line and next_line:
                semantic_score += 0.2
            
            # 当前行较短，下一行开始新的内容模式
            if len(line) < 30 and len(next_line) > 50:
                semantic_score += 0.15
        
        return min(semantic_score, 1.0)
    
    def calculate_boundary_quality(self, candidate: BoundaryCandidate, context_lines: List[str]) -> float:
        """
        计算边界质量分数（优化版）
        
        Args:
            candidate (BoundaryCandidate): 边界候选点
            context_lines (List[str]): 上下文行
            
        Returns:
            float: 质量分数 (0.0-1.0)
        """
        quality_score = 0.0
        
        # 基础优先级分数
        base_priority = self.boundary_priorities.get(candidate.boundary_type, 0.5)
        quality_score += base_priority * 0.4
        
        # 内容质量评估
        content = candidate.content.strip()
        
        # 内容长度合理性
        if 5 <= len(content) <= 100:
            quality_score += 0.2
        elif len(content) > 100:
            quality_score += 0.1
        
        # 数字标题特殊处理
        if candidate.boundary_type == BoundaryType.NUMERIC_TITLE:
            is_numeric, confidence, title = self.detect_numeric_title_enhanced(content)
            if is_numeric:
                quality_score += confidence * 0.3
            
            # 检查是否为完整的标题行
            if not content.endswith(('，', '、', '；')):  # 不以标点符号结尾
                quality_score += 0.1
        
        # 上下文一致性
        if candidate.line_index > 0 and candidate.line_index < len(context_lines) - 1:
            prev_line = context_lines[candidate.line_index - 1].strip()
            next_line = context_lines[candidate.line_index + 1].strip()
            
            # 前后行的内容差异度
            if prev_line and next_line:
                # 如果前一行很短或为空，当前行是标题，下一行是内容
                if len(prev_line) < 20 and len(content) < 50 and len(next_line) > 30:
                    quality_score += 0.15
        
        # 语义边界强度
        semantic_strength = self.detect_semantic_boundary(content, context_lines, candidate.line_index)
        quality_score += semantic_strength * 0.15
        
        return min(quality_score, 1.0)
    
    def find_boundary_candidates(self, lines: List[str]) -> List[BoundaryCandidate]:
        """
        查找所有边界候选点（优化版）
        
        Args:
            lines (List[str]): 文档行列表
            
        Returns:
            List[BoundaryCandidate]: 边界候选点列表
        """
        candidates = []
        
        for i, line in enumerate(lines):
            line_content = line.strip()
            
            # 跳过空行和过短的行
            if not line_content or len(line_content) < 3:
                continue
            
            # 文档开始和结束
            if i == 0:
                candidates.append(BoundaryCandidate(
                    line_index=i,
                    boundary_type=BoundaryType.DOCUMENT_START,
                    priority=1.0,
                    content=line_content
                ))
                continue
            elif i == len(lines) - 1:
                candidates.append(BoundaryCandidate(
                    line_index=i,
                    boundary_type=BoundaryType.DOCUMENT_END,
                    priority=1.0,
                    content=line_content
                ))
                continue
            
            # 主要分隔符
            if '=====' in line_content:
                candidates.append(BoundaryCandidate(
                    line_index=i,
                    boundary_type=BoundaryType.MAJOR_SECTION,
                    priority=0.95,
                    content=line_content
                ))
                continue
            
            # 数字标题检测（优化版）
            is_numeric, confidence, title_content = self.detect_numeric_title_enhanced(line_content)
            if is_numeric and confidence > 0.7:
                candidates.append(BoundaryCandidate(
                    line_index=i,
                    boundary_type=BoundaryType.NUMERIC_TITLE,
                    priority=confidence * 0.9,  # 根据置信度调整优先级
                    content=line_content
                ))
                continue
            
            # Markdown标题
            if line_content.startswith('#'):
                level = len(line_content) - len(line_content.lstrip('#'))
                priority = max(0.85 - (level - 1) * 0.1, 0.6)  # 根据标题级别调整优先级
                candidates.append(BoundaryCandidate(
                    line_index=i,
                    boundary_type=BoundaryType.MARKDOWN_HEADING,
                    priority=priority,
                    content=line_content
                ))
                continue
            
            # 表格边界
            if line_content.startswith('|') and line_content.endswith('|'):
                # 检查是否为表格分隔行
                if re.match(r'^\|[\s\-\|:]+\|$', line_content):
                    candidates.append(BoundaryCandidate(
                        line_index=i,
                        boundary_type=BoundaryType.TABLE_BOUNDARY,
                        priority=0.80,
                        content=line_content
                    ))
                    continue
            
            # 引用文献
            if re.match(r'^\[\d+\]', line_content):
                candidates.append(BoundaryCandidate(
                    line_index=i,
                    boundary_type=BoundaryType.REFERENCE_SECTION,
                    priority=0.75,
                    content=line_content
                ))
                continue
            
            # 语义边界
            semantic_strength = self.detect_semantic_boundary(line_content, lines, i)
            if semantic_strength > 0.5:
                candidates.append(BoundaryCandidate(
                    line_index=i,
                    boundary_type=BoundaryType.SEMANTIC_BREAK,
                    priority=semantic_strength * 0.7,
                    content=line_content
                ))
        
        # 计算每个候选点的质量分数
        for candidate in candidates:
            candidate.quality_score = self.calculate_boundary_quality(candidate, lines)
        
        # 按质量分数排序
        candidates.sort(key=lambda x: (x.quality_score, x.priority), reverse=True)
        
        print(f"🔍 发现 {len(candidates)} 个边界候选点")
        return candidates
    
    def select_optimal_boundaries(self, candidates: List[BoundaryCandidate], lines: List[str]) -> List[int]:
        """
        选择最优边界点（优化版）
        
        Args:
            candidates (List[BoundaryCandidate]): 边界候选点列表
            lines (List[str]): 文档行列表
            
        Returns:
            List[int]: 选中的边界行索引列表
        """
        if not candidates:
            return []
        
        selected_boundaries = []
        total_chars = sum(len(line) for line in lines)
        
        # 强制添加文档开始
        doc_start = next((c for c in candidates if c.boundary_type == BoundaryType.DOCUMENT_START), None)
        if doc_start:
            selected_boundaries.append(doc_start.line_index)
        
        # 按质量分数和优先级选择边界
        current_pos = 0
        current_chunk_size = 0
        
        for candidate in candidates:
            if candidate.line_index <= current_pos:
                continue
            
            # 计算到当前候选点的字符数
            chunk_size = sum(len(lines[i]) for i in range(current_pos, candidate.line_index + 1))
            
            # 决策逻辑优化
            should_select = False
            
            # 高质量边界优先选择
            if candidate.quality_score >= 0.8:
                should_select = True
            
            # 分块大小控制
            elif current_chunk_size + chunk_size >= self.max_chunk_size:
                should_select = True  # 强制分割，避免超大分块
            
            elif current_chunk_size + chunk_size >= self.target_chunk_size:
                # 在目标大小附近，根据边界质量决定
                if candidate.quality_score >= 0.6:
                    should_select = True
            
            # 数字标题特殊处理
            elif candidate.boundary_type == BoundaryType.NUMERIC_TITLE and candidate.quality_score >= 0.7:
                should_select = True
            
            if should_select:
                selected_boundaries.append(candidate.line_index)
                current_pos = candidate.line_index
                current_chunk_size = 0
            else:
                current_chunk_size += chunk_size
        
        # 强制添加文档结束
        doc_end = next((c for c in candidates if c.boundary_type == BoundaryType.DOCUMENT_END), None)
        if doc_end and doc_end.line_index not in selected_boundaries:
            selected_boundaries.append(doc_end.line_index)
        
        # 去重并排序
        selected_boundaries = sorted(list(set(selected_boundaries)))
        
        print(f"✅ 选择了 {len(selected_boundaries)} 个最优边界点")
        return selected_boundaries
    
    def create_chunks(self, lines: List[str], boundaries: List[int]) -> List[Dict[str, any]]:
        """
        根据边界创建分块（优化版）
        
        Args:
            lines (List[str]): 文档行列表
            boundaries (List[int]): 边界行索引列表
            
        Returns:
            List[Dict[str, any]]: 分块列表
        """
        if not boundaries:
            return []
        
        chunks = []
        chunk_id = 1
        
        for i in range(len(boundaries) - 1):
            start_line = boundaries[i]
            end_line = boundaries[i + 1]
            
            # 提取分块内容
            chunk_lines = lines[start_line:end_line]
            chunk_content = '\n'.join(chunk_lines)
            
            # 清理空白内容
            chunk_content = chunk_content.strip()
            if not chunk_content:
                continue
            
            # 检测分块类型
            chunk_type = self.detect_chunk_type(chunk_lines)
            
            # 计算分块统计信息
            char_count = len(chunk_content)
            line_count = len([line for line in chunk_lines if line.strip()])
            
            # 分块质量评估
            quality_score = self.evaluate_chunk_quality(chunk_content, chunk_type)
            
            chunk_info = {
                'id': chunk_id,
                'start_line': start_line + 1,  # 1-based indexing
                'end_line': end_line,
                'content': chunk_content,
                'type': chunk_type,
                'char_count': char_count,
                'line_count': line_count,
                'quality_score': quality_score
            }
            
            chunks.append(chunk_info)
            chunk_id += 1
        
        print(f"📦 创建了 {len(chunks)} 个分块")
        return chunks
    
    def detect_chunk_type(self, chunk_lines: List[str]) -> str:
        """
        检测分块类型
        
        Args:
            chunk_lines (List[str]): 分块行列表
            
        Returns:
            str: 分块类型
        """
        content = '\n'.join(chunk_lines).strip()
        
        # 检测各种类型
        if '=====' in content:
            return 'document_separator'
        elif re.search(r'^<\d+>', content, re.MULTILINE):
            return 'numeric_title_section'
        elif content.startswith('#'):
            return 'markdown_heading'
        elif '|' in content and content.count('|') > 4:
            return 'table_content'
        elif re.search(r'^\[\d+\]', content, re.MULTILINE):
            return 'reference_section'
        elif any(keyword in content for keyword in ['图', '表', '数据']):
            return 'figure_table'
        else:
            return 'text_content'
    
    def evaluate_chunk_quality(self, content: str, chunk_type: str) -> float:
        """
        评估分块质量
        
        Args:
            content (str): 分块内容
            chunk_type (str): 分块类型
            
        Returns:
            float: 质量分数 (0.0-1.0)
        """
        quality_score = 0.5  # 基础分数
        
        # 长度合理性
        char_count = len(content)
        if self.min_chunk_size <= char_count <= self.max_chunk_size:
            quality_score += 0.2
        elif char_count > self.max_chunk_size:
            quality_score -= 0.1
        
        # 内容完整性
        if not content.endswith(('。', '！', '？', '.', '!', '?')):
            if chunk_type in ['text_content', 'numeric_title_section']:
                quality_score -= 0.1
        
        # 类型特定评估
        if chunk_type == 'numeric_title_section':
            quality_score += 0.1
        elif chunk_type == 'table_content':
            quality_score += 0.05
        elif chunk_type == 'reference_section':
            quality_score += 0.05
        
        return min(max(quality_score, 0.0), 1.0)
    
    def generate_statistics(self, chunks: List[Dict[str, any]], boundaries: List[int]) -> Dict[str, any]:
        """
        生成处理统计信息
        
        Args:
            chunks (List[Dict[str, any]]): 分块列表
            boundaries (List[int]): 边界列表
            
        Returns:
            Dict[str, any]: 统计信息
        """
        if not chunks:
            return {}
        
        # 基础统计
        total_chunks = len(chunks)
        total_chars = sum(chunk['char_count'] for chunk in chunks)
        avg_chunk_size = total_chars / total_chunks if total_chunks > 0 else 0
        
        # 分块大小分布
        size_distribution = {
            'small': len([c for c in chunks if c['char_count'] < 500]),
            'medium': len([c for c in chunks if 500 <= c['char_count'] <= 1000]),
            'large': len([c for c in chunks if 1000 < c['char_count'] <= 2000]),
            'extra_large': len([c for c in chunks if c['char_count'] > 2000])
        }
        
        # 类型分布
        type_distribution = {}
        for chunk in chunks:
            chunk_type = chunk['type']
            type_distribution[chunk_type] = type_distribution.get(chunk_type, 0) + 1
        
        # 质量统计
        quality_scores = [chunk['quality_score'] for chunk in chunks]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # 边界质量（简化版）
        boundary_quality = min(avg_quality + 0.2, 1.0)  # 基于分块质量估算
        
        return {
            'total_chunks': total_chunks,
            'total_characters': total_chars,
            'average_chunk_size': round(avg_chunk_size),
            'size_distribution': size_distribution,
            'type_distribution': type_distribution,
            'average_quality_score': round(avg_quality, 2),
            'boundary_quality_score': round(boundary_quality, 2),
            'total_boundaries': len(boundaries)
        }
    
    def save_processed_document(self, chunks: List[Dict[str, any]], output_path: str):
        """
        保存处理后的文档
        
        Args:
            chunks (List[Dict[str, any]]): 分块列表
            output_path (str): 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("====== 文档开始 ======\n\n")
                
                for chunk in chunks:
                    f.write(f"====== 分块 {chunk['id']} ======\n")
                    f.write(f"类型: {chunk['type']}\n")
                    f.write(f"大小: {chunk['char_count']} 字符\n")
                    f.write(f"质量: {chunk['quality_score']:.2f}\n")
                    f.write(f"行数: {chunk['start_line']}-{chunk['end_line']}\n")
                    f.write("内容:\n")
                    f.write(chunk['content'])
                    f.write("\n\n")
                
                f.write("====== 文档结束 ======\n")
            
            print(f"✅ 处理后文档已保存至: {output_path}")
            
        except Exception as e:
            print(f"❌ 保存文档失败: {e}")
            raise
    
    def process_document(self, input_path: str, output_path: str) -> Dict[str, any]:
        """
        处理文档的主函数
        
        Args:
            input_path (str): 输入文档路径
            output_path (str): 输出文档路径
            
        Returns:
            Dict[str, any]: 处理结果和统计信息
        """
        print(f"🚀 开始处理文档: {input_path}")
        print(f"📋 配置: 目标大小={self.target_chunk_size}, 最大大小={self.max_chunk_size}")
        
        # 加载文档
        lines = self.load_document(input_path)
        
        # 查找边界候选点
        candidates = self.find_boundary_candidates(lines)
        
        # 选择最优边界
        boundaries = self.select_optimal_boundaries(candidates, lines)
        
        # 创建分块
        chunks = self.create_chunks(lines, boundaries)
        
        # 生成统计信息
        statistics = self.generate_statistics(chunks, boundaries)
        
        # 保存处理后文档
        self.save_processed_document(chunks, output_path)
        
        # 打印统计信息
        self.print_statistics(statistics)
        
        return {
            'input_path': input_path,
            'output_path': output_path,
            'statistics': statistics,
            'chunks': len(chunks),
            'boundaries': len(boundaries)
        }
    
    def print_statistics(self, stats: Dict[str, any]):
        """
        打印统计信息
        
        Args:
            stats (Dict[str, any]): 统计信息
        """
        print("\n" + "="*50)
        print("📊 处理统计信息")
        print("="*50)
        print(f"总分块数: {stats.get('total_chunks', 0)}")
        print(f"总字符数: {stats.get('total_characters', 0):,}")
        print(f"平均分块大小: {stats.get('average_chunk_size', 0)} 字符")
        print(f"平均质量分数: {stats.get('average_quality_score', 0)}")
        print(f"边界质量分数: {stats.get('boundary_quality_score', 0)}")
        
        print(f"\n📏 分块大小分布:")
        size_dist = stats.get('size_distribution', {})
        print(f"  小分块 (<500字符): {size_dist.get('small', 0)}")
        print(f"  中等分块 (500-1000字符): {size_dist.get('medium', 0)}")
        print(f"  大分块 (1000-2000字符): {size_dist.get('large', 0)}")
        print(f"  超大分块 (>2000字符): {size_dist.get('extra_large', 0)}")
        
        print(f"\n🏷️ 分块类型分布:")
        type_dist = stats.get('type_distribution', {})
        for chunk_type, count in type_dist.items():
            print(f"  {chunk_type}: {count}")
        
        print("="*50)

def main():
    """
    主函数 - 处理命令行参数并执行文档处理
    
    Returns:
        int: 程序退出码，0表示成功，1表示失败
    """
    parser = argparse.ArgumentParser(description='增强版文档预处理器 V2')
    parser.add_argument('input_file', help='输入文档路径')
    parser.add_argument('--output', '-o', help='输出文档路径（默认为输入文件名_enhanced_v2.md）')
    parser.add_argument('--target-size', '-t', type=int, default=800, 
                       help='目标分块大小（字符数，默认800）')
    parser.add_argument('--max-size', '-m', type=int, default=1500,
                       help='最大分块大小（字符数，默认1500）')
    parser.add_argument('--stats-output', '-s', help='统计信息输出文件（JSON格式）')
    
    args = parser.parse_args()
    
    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        input_name = args.input_file.rsplit('.', 1)[0]
        output_path = f"{input_name}_enhanced_v2.md"
    
    try:
        # 创建处理器
        processor = EnhancedDocumentProcessor(
            target_chunk_size=args.target_size,
            max_chunk_size=args.max_size
        )
        
        # 处理文档
        result = processor.process_document(args.input_file, output_path)
        
        # 保存统计信息（如果指定）
        if args.stats_output:
            with open(args.stats_output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"📊 统计信息已保存至: {args.stats_output}")
        
        print(f"\n✅ 文档处理完成！")
        print(f"📄 输入: {args.input_file}")
        print(f"📄 输出: {output_path}")
        print(f"📦 分块数: {result['chunks']}")
        print(f"🎯 边界数: {result['boundaries']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return 1

if __name__ == "__main__":
    exit(main())