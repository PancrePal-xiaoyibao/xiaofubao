#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医学文档预处理脚本 - 最终优化版本 (V3)
专门针对医学指南文档的智能分块处理

主要改进：
1. 解决V2分块过大问题，目标分块大小400-600字符
2. 强制分割超过1500字符的分块
3. 优化数字标题检测的置信度阈值
4. 增加更多语义边界检测规则
5. 改进引用文献处理逻辑

功能：
1. 智能识别医学文档结构
2. 基于语义的分块策略
3. 优化的边界检测算法
4. 分块质量评估
5. 详细的处理统计

作者: RAG预处理专家
版本: 3.0
"""

import re
import json
import argparse
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass

@dataclass
class ChunkInfo:
    """分块信息类"""
    content: str
    start_line: int
    end_line: int
    boundary_type: str
    quality_score: float
    size: int

class MedicalDocumentProcessor:
    """医学文档处理器 - 最终优化版本"""
    
    def __init__(self, target_chunk_size: int = 500, max_chunk_size: int = 1500):
        """
        初始化处理器
        
        Args:
            target_chunk_size (int): 目标分块大小（字符数）
            max_chunk_size (int): 最大分块大小（字符数）
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = 200
        
        # 编译正则表达式模式
        self._compile_patterns()
        
        # 统计信息
        self.stats = {
            'total_lines': 0,
            'boundary_candidates': 0,
            'chunks_created': 0,
            'forced_splits': 0,
            'quality_scores': []
        }
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        # 数字标题模式（优化置信度）
        self.number_title_patterns = [
            (re.compile(r'^<(\d+)>(\d+)\.(\d+)\.(\d+)\s+(.+)$'), 0.95),  # 三级数字标题
            (re.compile(r'^<(\d+)>(\d+)\.(\d+)\s+(.+)$'), 0.90),        # 二级数字标题
            (re.compile(r'^<(\d+)>(\d+)\.\s+(.+)$'), 0.85),             # 一级数字标题
            (re.compile(r'^<(\d+)>(\d+)\s+(.+)$'), 0.80),               # 纯数字标题
        ]
        
        # 中文序号模式
        self.chinese_patterns = [
            (re.compile(r'^<(\d+)>([一二三四五六七八九十]+)[、．]\s*(.+)$'), 0.90),
            (re.compile(r'^<(\d+)>（([一二三四五六七八九十]+)）\s*(.+)$'), 0.85),
        ]
        
        # Markdown标题模式
        self.markdown_patterns = [
            (re.compile(r'^<(\d+)>(#{1,6})\s+(.+)$'), 0.95),
        ]
        
        # 特殊结构模式
        self.special_patterns = [
            (re.compile(r'^<(\d+)>【(.+?)】'), 0.85),                    # 【标题】
            (re.compile(r'^<(\d+)>\*\*(.+?)\*\*'), 0.80),               # **粗体标题**
            (re.compile(r'^<(\d+)>表\s*\d+'), 0.75),                    # 表格标题
            (re.compile(r'^<(\d+)>图\s*\d+'), 0.75),                    # 图片标题
            (re.compile(r'^<(\d+)>附录'), 0.85),                        # 附录
            (re.compile(r'^<(\d+)>参考文献'), 0.90),                     # 参考文献
        ]
        
        # 引用文献模式
        self.reference_patterns = [
            (re.compile(r'^<(\d+)>\[\d+\]'), 0.70),                     # [1] 格式引用
            (re.compile(r'^<(\d+)>\d+\.\s*[A-Z]'), 0.75),               # 1. Author 格式
        ]
        
        # 段落结束模式
        self.paragraph_end_patterns = [
            re.compile(r'[。！？]$'),                                    # 中文句号结尾
            re.compile(r'[.!?]$'),                                      # 英文句号结尾
            re.compile(r'：$'),                                         # 冒号结尾
        ]
    
    def load_document(self, file_path: str) -> List[str]:
        """
        加载文档
        
        Args:
            file_path (str): 文档路径
            
        Returns:
            List[str]: 文档行列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 移除换行符并过滤空行
            lines = [line.rstrip('\n\r') for line in lines if line.strip()]
            
            self.stats['total_lines'] = len(lines)
            print(f"📄 文档加载成功: {len(lines)} 行")
            
            return lines
            
        except Exception as e:
            print(f"❌ 文档加载失败: {e}")
            raise
    
    def detect_boundary_candidates(self, lines: List[str]) -> List[Tuple[int, str, float]]:
        """
        检测边界候选点
        
        Args:
            lines (List[str]): 文档行列表
            
        Returns:
            List[Tuple[int, str, float]]: (行号, 边界类型, 置信度) 列表
        """
        candidates = []
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # 检查各种模式
            confidence = 0.0
            boundary_type = "unknown"
            
            # 数字标题检测
            for pattern, conf in self.number_title_patterns:
                if pattern.match(line):
                    confidence = max(confidence, conf)
                    boundary_type = "number_title"
                    break
            
            # 中文序号检测
            if confidence < 0.8:
                for pattern, conf in self.chinese_patterns:
                    if pattern.match(line):
                        confidence = max(confidence, conf)
                        boundary_type = "chinese_title"
                        break
            
            # Markdown标题检测
            if confidence < 0.8:
                for pattern, conf in self.markdown_patterns:
                    if pattern.match(line):
                        confidence = max(confidence, conf)
                        boundary_type = "markdown_title"
                        break
            
            # 特殊结构检测
            if confidence < 0.8:
                for pattern, conf in self.special_patterns:
                    if pattern.match(line):
                        confidence = max(confidence, conf)
                        boundary_type = "special_structure"
                        break
            
            # 引用文献检测
            if confidence < 0.7:
                for pattern, conf in self.reference_patterns:
                    if pattern.match(line):
                        confidence = max(confidence, conf)
                        boundary_type = "reference"
                        break
            
            # 段落边界检测（较低优先级）
            if confidence < 0.5 and i > 0:
                prev_line = lines[i-1].strip()
                if any(pattern.search(prev_line) for pattern in self.paragraph_end_patterns):
                    if len(line) > 10:  # 避免短行
                        confidence = 0.4
                        boundary_type = "paragraph"
            
            # 记录候选点
            if confidence > 0.3:  # 降低阈值以获得更多候选点
                candidates.append((i, boundary_type, confidence))
        
        self.stats['boundary_candidates'] = len(candidates)
        print(f"🔍 发现 {len(candidates)} 个边界候选点")
        
        return candidates
    
    def calculate_chunk_quality(self, content: str, boundary_type: str, confidence: float) -> float:
        """
        计算分块质量分数
        
        Args:
            content (str): 分块内容
            boundary_type (str): 边界类型
            confidence (float): 边界置信度
            
        Returns:
            float: 质量分数 (0-1)
        """
        score = 0.0
        
        # 边界类型权重
        type_weights = {
            "number_title": 0.4,
            "chinese_title": 0.35,
            "markdown_title": 0.4,
            "special_structure": 0.3,
            "reference": 0.25,
            "paragraph": 0.15,
            "forced_split": 0.1
        }
        
        # 边界质量分数
        score += type_weights.get(boundary_type, 0.1) * confidence
        
        # 大小质量分数
        size = len(content)
        if self.min_chunk_size <= size <= self.target_chunk_size:
            size_score = 0.4
        elif size <= self.max_chunk_size:
            # 线性衰减
            size_score = 0.4 * (1 - (size - self.target_chunk_size) / (self.max_chunk_size - self.target_chunk_size))
        else:
            size_score = 0.1  # 超大分块
        
        score += size_score
        
        # 内容完整性分数
        content_score = 0.0
        if content.strip().endswith(('。', '.', '！', '!', '？', '?')):
            content_score += 0.1
        if len(content.strip()) > 50:
            content_score += 0.1
        
        score += content_score
        
        return min(score, 1.0)
    
    def force_split_large_chunk(self, content: str, start_line: int) -> List[ChunkInfo]:
        """
        强制分割超大分块
        
        Args:
            content (str): 分块内容
            start_line (int): 起始行号
            
        Returns:
            List[ChunkInfo]: 分割后的分块列表
        """
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_size = 0
        current_start = start_line
        
        for i, line in enumerate(lines):
            line_size = len(line)
            
            # 检查是否需要分割
            if current_size + line_size > self.target_chunk_size and current_chunk:
                # 创建当前分块
                chunk_content = '\n'.join(current_chunk)
                quality = self.calculate_chunk_quality(chunk_content, "forced_split", 0.5)
                
                chunks.append(ChunkInfo(
                    content=chunk_content,
                    start_line=current_start,
                    end_line=current_start + len(current_chunk) - 1,
                    boundary_type="forced_split",
                    quality_score=quality,
                    size=len(chunk_content)
                ))
                
                # 重置
                current_chunk = [line]
                current_size = line_size
                current_start = start_line + i
                self.stats['forced_splits'] += 1
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # 处理最后一个分块
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            quality = self.calculate_chunk_quality(chunk_content, "forced_split", 0.5)
            
            chunks.append(ChunkInfo(
                content=chunk_content,
                start_line=current_start,
                end_line=current_start + len(current_chunk) - 1,
                boundary_type="forced_split",
                quality_score=quality,
                size=len(chunk_content)
            ))
        
        return chunks
    
    def create_chunks(self, lines: List[str], candidates: List[Tuple[int, str, float]]) -> List[ChunkInfo]:
        """
        创建分块
        
        Args:
            lines (List[str]): 文档行列表
            candidates (List[Tuple[int, str, float]]): 边界候选点
            
        Returns:
            List[ChunkInfo]: 分块列表
        """
        chunks = []
        
        # 添加文档开始和结束边界
        all_boundaries = [(0, "document_start", 1.0)] + candidates + [(len(lines), "document_end", 1.0)]
        all_boundaries.sort(key=lambda x: x[0])
        
        # 动态选择边界点
        selected_boundaries = [all_boundaries[0]]  # 总是包含开始
        current_size = 0
        
        for i in range(1, len(all_boundaries)):
            boundary_line, boundary_type, confidence = all_boundaries[i]
            
            # 计算到当前边界的内容大小
            chunk_lines = lines[selected_boundaries[-1][0]:boundary_line]
            chunk_size = sum(len(line) for line in chunk_lines)
            
            # 决策逻辑
            should_split = False
            
            # 强制分割条件
            if chunk_size > self.max_chunk_size:
                should_split = True
            # 目标大小条件
            elif chunk_size >= self.target_chunk_size and confidence > 0.6:
                should_split = True
            # 高质量边界条件
            elif confidence > 0.85:
                should_split = True
            # 最后一个边界
            elif i == len(all_boundaries) - 1:
                should_split = True
            
            if should_split:
                selected_boundaries.append((boundary_line, boundary_type, confidence))
        
        # 创建分块
        for i in range(len(selected_boundaries) - 1):
            start_line = selected_boundaries[i][0]
            end_line = selected_boundaries[i + 1][0]
            boundary_type = selected_boundaries[i + 1][1]
            confidence = selected_boundaries[i + 1][2]
            
            chunk_lines = lines[start_line:end_line]
            chunk_content = '\n'.join(chunk_lines)
            
            if chunk_content.strip():
                # 检查是否需要强制分割
                if len(chunk_content) > self.max_chunk_size:
                    # 强制分割
                    sub_chunks = self.force_split_large_chunk(chunk_content, start_line)
                    chunks.extend(sub_chunks)
                else:
                    # 正常分块
                    quality = self.calculate_chunk_quality(chunk_content, boundary_type, confidence)
                    
                    chunk_info = ChunkInfo(
                        content=chunk_content,
                        start_line=start_line,
                        end_line=end_line - 1,
                        boundary_type=boundary_type,
                        quality_score=quality,
                        size=len(chunk_content)
                    )
                    
                    chunks.append(chunk_info)
                    self.stats['quality_scores'].append(quality)
        
        self.stats['chunks_created'] = len(chunks)
        print(f"📦 创建 {len(chunks)} 个分块")
        
        return chunks
    
    def save_enhanced_document(self, chunks: List[ChunkInfo], output_path: str, include_metadata: bool = True):
        """
        保存增强文档
        
        Args:
            chunks (List[ChunkInfo]): 分块列表
            output_path (str): 输出路径
            include_metadata (bool): 是否包含元数据信息
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if include_metadata:
                    f.write("====== 文档开始 ======\n\n")
                
                for i, chunk in enumerate(chunks):
                    if include_metadata:
                        f.write(f"[CHUNK_{i+1:03d}]\n")
                        f.write(f"边界类型: {chunk.boundary_type}\n")
                        f.write(f"质量分数: {chunk.quality_score:.2f}\n")
                        f.write(f"大小: {chunk.size} 字符\n")
                        f.write(f"行范围: {chunk.start_line+1}-{chunk.end_line+1}\n")
                        f.write("-" * 50 + "\n")
                    
                    f.write(chunk.content)
                    
                    if include_metadata:
                        f.write("\n\n[CHUNK_BOUNDARY]\n\n")
                    else:
                        # 纯内容模式下，分块之间用双换行分隔
                        if i < len(chunks) - 1:  # 不是最后一个分块
                            f.write("\n\n")
                
                if include_metadata:
                    f.write("====== 文档结束 ======\n")
            
            print(f"💾 增强文档已保存至: {output_path}")
            
        except Exception as e:
            print(f"❌ 保存增强文档失败: {e}")
            raise
    
    def generate_statistics(self) -> Dict[str, Any]:
        """
        生成处理统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        if not self.stats['quality_scores']:
            avg_quality = 0
            boundary_quality = 0
        else:
            avg_quality = sum(self.stats['quality_scores']) / len(self.stats['quality_scores'])
            # 边界质量基于高质量分块的比例
            high_quality_count = sum(1 for score in self.stats['quality_scores'] if score > 0.7)
            boundary_quality = high_quality_count / len(self.stats['quality_scores'])
        
        # 分块大小分布
        chunk_sizes = [chunk.size for chunk in getattr(self, 'chunks', [])]
        size_distribution = {
            'small': sum(1 for size in chunk_sizes if size < 400),
            'medium': sum(1 for size in chunk_sizes if 400 <= size <= 800),
            'large': sum(1 for size in chunk_sizes if 800 < size <= 1500),
            'extra_large': sum(1 for size in chunk_sizes if size > 1500)
        }
        
        return {
            'processing_info': {
                'total_lines_processed': self.stats['total_lines'],
                'boundary_candidates_found': self.stats['boundary_candidates'],
                'chunks_created': self.stats['chunks_created'],
                'forced_splits': self.stats['forced_splits']
            },
            'statistics': {
                'total_chunks': self.stats['chunks_created'],
                'average_chunk_size': sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
                'average_quality_score': avg_quality,
                'boundary_quality_score': boundary_quality,
                'size_distribution': size_distribution
            },
            'quality_analysis': {
                'high_quality_chunks': sum(1 for score in self.stats['quality_scores'] if score > 0.7),
                'medium_quality_chunks': sum(1 for score in self.stats['quality_scores'] if 0.5 <= score <= 0.7),
                'low_quality_chunks': sum(1 for score in self.stats['quality_scores'] if score < 0.5),
                'quality_scores': self.stats['quality_scores']
            }
        }
    
    def save_statistics(self, stats: Dict[str, Any], output_path: str):
        """
        保存统计信息
        
        Args:
            stats (Dict[str, Any]): 统计信息
            output_path (str): 输出路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            print(f"📊 统计信息已保存至: {output_path}")
            
        except Exception as e:
            print(f"❌ 保存统计信息失败: {e}")
            raise
    
    def process_document(self, input_path: str, output_path: str, stats_path: str = None, include_metadata: bool = True):
        """
        处理文档的主函数
        
        Args:
            input_path (str): 输入文档路径
            output_path (str): 输出文档路径
            stats_path (str): 统计信息输出路径（可选）
            include_metadata (bool): 是否在输出文档中包含元数据信息
        """
        print("🚀 开始处理医学文档...")
        print(f"📋 目标分块大小: {self.target_chunk_size} 字符")
        print(f"📋 最大分块大小: {self.max_chunk_size} 字符")
        print(f"📋 包含元数据: {'是' if include_metadata else '否'}")
        
        # 加载文档
        lines = self.load_document(input_path)
        
        # 检测边界候选点
        candidates = self.detect_boundary_candidates(lines)
        
        # 创建分块
        self.chunks = self.create_chunks(lines, candidates)
        
        # 保存增强文档
        self.save_enhanced_document(self.chunks, output_path, include_metadata)
        
        # 生成并保存统计信息
        stats = self.generate_statistics()
        if stats_path:
            self.save_statistics(stats, stats_path)
        
        # 打印处理摘要
        print("\n" + "="*50)
        print("📊 处理摘要:")
        print(f"  总行数: {stats['processing_info']['total_lines_processed']}")
        print(f"  边界候选点: {stats['processing_info']['boundary_candidates_found']}")
        print(f"  创建分块数: {stats['processing_info']['chunks_created']}")
        print(f"  强制分割次数: {stats['processing_info']['forced_splits']}")
        print(f"  平均分块大小: {stats['statistics']['average_chunk_size']:.0f} 字符")
        print(f"  平均质量分数: {stats['statistics']['average_quality_score']:.2f}")
        print(f"  边界质量分数: {stats['statistics']['boundary_quality_score']:.2f}")
        print(f"  大小分布: 小({stats['statistics']['size_distribution']['small']}) "
              f"中({stats['statistics']['size_distribution']['medium']}) "
              f"大({stats['statistics']['size_distribution']['large']}) "
              f"超大({stats['statistics']['size_distribution']['extra_large']})")
        print("="*50)
        
        print("✅ 文档处理完成!")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='医学文档预处理脚本 - 最终优化版本')
    parser.add_argument('input_file', help='输入文档路径')
    parser.add_argument('--output', '-o', required=True, help='输出文档路径')
    parser.add_argument('--stats-output', help='统计信息输出路径')
    parser.add_argument('--target-size', type=int, default=500, help='目标分块大小（默认500字符）')
    parser.add_argument('--max-size', type=int, default=1500, help='最大分块大小（默认1500字符）')
    parser.add_argument('--no-metadata', action='store_true', help='生成不包含元数据的纯内容版本')
    
    args = parser.parse_args()
    
    try:
        # 创建处理器
        processor = MedicalDocumentProcessor(
            target_chunk_size=args.target_size,
            max_chunk_size=args.max_size
        )
        
        # 处理文档
        processor.process_document(
            input_path=args.input_file,
            output_path=args.output,
            stats_path=args.stats_output,
            include_metadata=not args.no_metadata
        )
        
        return 0
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return 1

if __name__ == "__main__":
    exit(main())