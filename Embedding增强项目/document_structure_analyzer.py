#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档结构分析器 - 统一语义模型实现
解决原有分块逻辑的系统性问题
"""

import re
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum

class SectionType(Enum):
    """章节类型枚举"""
    CHINESE_MAJOR = "chinese_major"  # 中文一级序号（一、二、三）
    CHINESE_MINOR = "chinese_minor"  # 中文二级序号（1、2、3）
    MARKDOWN_H1 = "markdown_h1"     # Markdown一级标题
    MARKDOWN_H2 = "markdown_h2"     # Markdown二级标题
    MARKDOWN_H3 = "markdown_h3"     # Markdown三级标题
    TABLE = "table"                 # 表格
    CONTENT = "content"             # 普通内容

@dataclass
class DocumentSection:
    """文档章节结构"""
    line_number: int
    content: str
    section_type: SectionType
    level: int  # 层级深度
    parent_section: Optional['DocumentSection'] = None
    children: List['DocumentSection'] = None
    semantic_boundary_score: float = 0.0  # 语义边界分数
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

class DocumentStructureAnalyzer:
    """文档结构分析器"""
    
    def __init__(self):
        # 中文序号模式
        self.chinese_major_pattern = re.compile(r'^<\d+>\s*([一二三四五六七八九十]+)、\s*(.+)$')
        self.chinese_minor_pattern = re.compile(r'^<\d+>\s*(\d+)、\s*(.+)$')
        
        # Markdown标题模式
        self.markdown_h1_pattern = re.compile(r'^<\d+>\s*#\s+(.+)$')
        self.markdown_h2_pattern = re.compile(r'^<\d+>\s*##\s+(.+)$')
        self.markdown_h3_pattern = re.compile(r'^<\d+>\s*###\s+(.+)$')
        
        # 表格模式
        self.table_pattern = re.compile(r'^<\d+>\s*\|.*\|.*$')
        
        # 动态优先级权重
        self.priority_weights = {
            SectionType.CHINESE_MAJOR: 1.0,   # 最高优先级
            SectionType.MARKDOWN_H1: 0.9,
            SectionType.CHINESE_MINOR: 0.8,
            SectionType.MARKDOWN_H2: 0.7,
            SectionType.MARKDOWN_H3: 0.6,
            SectionType.TABLE: 0.5,
            SectionType.CONTENT: 0.1
        }
    
    def analyze_document_structure(self, lines: List[str]) -> List[DocumentSection]:
        """分析文档结构，返回章节列表"""
        sections = []
        section_stack = []  # 用于维护层级关系
        
        for i, line in enumerate(lines):
            section = self._classify_line(i, line)
            if section:
                # 计算语义边界分数
                section.semantic_boundary_score = self._calculate_boundary_score(
                    section, lines, i
                )
                
                # 建立层级关系
                self._establish_hierarchy(section, section_stack)
                sections.append(section)
        
        return sections
    
    def _classify_line(self, line_number: int, line: str) -> Optional[DocumentSection]:
        """分类单行内容"""
        line = line.strip()
        if not line:
            return None
        
        # 检查中文一级序号
        if match := self.chinese_major_pattern.match(line):
            return DocumentSection(
                line_number=line_number,
                content=line,
                section_type=SectionType.CHINESE_MAJOR,
                level=1
            )
        
        # 检查Markdown一级标题
        if match := self.markdown_h1_pattern.match(line):
            return DocumentSection(
                line_number=line_number,
                content=line,
                section_type=SectionType.MARKDOWN_H1,
                level=1
            )
        
        # 检查中文二级序号
        if match := self.chinese_minor_pattern.match(line):
            return DocumentSection(
                line_number=line_number,
                content=line,
                section_type=SectionType.CHINESE_MINOR,
                level=2
            )
        
        # 检查Markdown二级标题
        if match := self.markdown_h2_pattern.match(line):
            return DocumentSection(
                line_number=line_number,
                content=line,
                section_type=SectionType.MARKDOWN_H2,
                level=2
            )
        
        # 检查Markdown三级标题
        if match := self.markdown_h3_pattern.match(line):
            return DocumentSection(
                line_number=line_number,
                content=line,
                section_type=SectionType.MARKDOWN_H3,
                level=3
            )
        
        # 检查表格
        if self.table_pattern.match(line):
            return DocumentSection(
                line_number=line_number,
                content=line,
                section_type=SectionType.TABLE,
                level=4
            )
        
        # 普通内容
        return DocumentSection(
            line_number=line_number,
            content=line,
            section_type=SectionType.CONTENT,
            level=5
        )
    
    def _calculate_boundary_score(self, section: DocumentSection, 
                                lines: List[str], current_index: int) -> float:
        """计算语义边界分数"""
        base_score = self.priority_weights[section.section_type]
        
        # 上下文相关性调整
        context_bonus = 0.0
        
        # 检查前后文的语义连续性
        if current_index > 0:
            prev_line = lines[current_index - 1].strip()
            if self._is_content_continuation(prev_line, section.content):
                context_bonus -= 0.2  # 降低边界分数
        
        # 检查是否是章节开始
        if self._is_section_start(section):
            context_bonus += 0.3
        
        # 检查表格-标题关联
        if section.section_type == SectionType.TABLE:
            if self._has_related_title_nearby(lines, current_index):
                context_bonus -= 0.4  # 表格与标题强关联，降低分块倾向
        
        return min(1.0, max(0.0, base_score + context_bonus))
    
    def _establish_hierarchy(self, section: DocumentSection, 
                           section_stack: List[DocumentSection]):
        """建立章节层级关系"""
        # 清理栈中层级更深的章节
        while section_stack and section_stack[-1].level >= section.level:
            section_stack.pop()
        
        # 设置父子关系
        if section_stack:
            parent = section_stack[-1]
            section.parent_section = parent
            parent.children.append(section)
        
        # 只有标题类型的章节才加入栈
        if section.section_type in [
            SectionType.CHINESE_MAJOR, SectionType.CHINESE_MINOR,
            SectionType.MARKDOWN_H1, SectionType.MARKDOWN_H2, SectionType.MARKDOWN_H3
        ]:
            section_stack.append(section)
    
    def _is_content_continuation(self, prev_line: str, current_line: str) -> bool:
        """判断是否是内容延续"""
        # 简单的启发式规则
        if not prev_line or prev_line.endswith('：') or prev_line.endswith(':'):
            return True
        if current_line.startswith('（') or current_line.startswith('('):
            return True
        return False
    
    def _is_section_start(self, section: DocumentSection) -> bool:
        """判断是否是章节开始"""
        return section.section_type in [
            SectionType.CHINESE_MAJOR, SectionType.MARKDOWN_H1
        ]
    
    def _has_related_title_nearby(self, lines: List[str], table_index: int) -> bool:
        """检查表格附近是否有相关标题"""
        # 检查前后5行
        search_range = 5
        start = max(0, table_index - search_range)
        end = min(len(lines), table_index + search_range + 1)
        
        for i in range(start, end):
            if i == table_index:
                continue
            line = lines[i].strip()
            if (self.markdown_h1_pattern.match(line) or 
                self.markdown_h2_pattern.match(line) or
                self.chinese_major_pattern.match(line)):
                return True
        
        return False
    
    def get_optimal_chunk_boundaries(self, sections: List[DocumentSection], 
                                   max_chunk_size: int = 3000,
                                   max_token_count: int = 1000) -> List[int]:
        """获取最优分块边界，支持基于token数的智能合并"""
        boundaries = []
        current_chunk_size = 0
        current_token_count = 0
        last_boundary = 0
        
        for i, section in enumerate(sections):
            section_size = len(section.content)
            section_tokens = self._estimate_token_count(section.content)
            
            # 检查子标题合并机会
            if self._should_merge_subtitle_sections(sections, i, current_token_count, max_token_count):
                current_chunk_size += section_size
                current_token_count += section_tokens
                continue
            
            # 检查是否需要强制分块
            if (section.semantic_boundary_score > 0.8 and 
                current_chunk_size > max_chunk_size * 0.3):
                boundaries.append(section.line_number)
                current_chunk_size = section_size
                current_token_count = section_tokens
                last_boundary = section.line_number
            
            # 检查是否超过最大大小或token数
            elif (current_chunk_size + section_size > max_chunk_size or
                  current_token_count + section_tokens > max_token_count):
                # 寻找最近的合适边界
                best_boundary = self._find_best_boundary_before(
                    sections, section.line_number, last_boundary
                )
                if best_boundary > last_boundary:
                    boundaries.append(best_boundary)
                    current_chunk_size = self._calculate_size_after_boundary(
                        sections, best_boundary, section.line_number
                    )
                    current_token_count = self._calculate_tokens_after_boundary(
                        sections, best_boundary, section.line_number
                    )
                    last_boundary = best_boundary
                else:
                    boundaries.append(section.line_number)
                    current_chunk_size = section_size
                    current_token_count = section_tokens
                    last_boundary = section.line_number
            else:
                current_chunk_size += section_size
                current_token_count += section_tokens
        
        return boundaries
    
    def _find_best_boundary_before(self, sections: List[DocumentSection], 
                                 current_line: int, last_boundary: int) -> int:
        """在指定位置前找到最佳边界"""
        best_score = 0.0
        best_boundary = last_boundary
        
        for section in sections:
            if last_boundary < section.line_number < current_line:
                if section.semantic_boundary_score > best_score:
                    best_score = section.semantic_boundary_score
                    best_boundary = section.line_number
        
        return best_boundary
    
    def _calculate_size_after_boundary(self, sections: List[DocumentSection], 
                                     boundary: int, current_line: int) -> int:
        """计算边界后到当前位置的大小"""
        total_size = 0
        for section in sections:
            if boundary < section.line_number <= current_line:
                total_size += len(section.content)
        return total_size
    
    def _calculate_tokens_after_boundary(self, sections: List[DocumentSection], 
                                       boundary: int, current_line: int) -> int:
        """计算边界后到当前位置的token数"""
        total_tokens = 0
        for section in sections:
            if boundary < section.line_number <= current_line:
                total_tokens += self._estimate_token_count(section.content)
        return total_tokens
    
    def _estimate_token_count(self, text: str) -> int:
        """估算文本的token数量"""
        # 简单的token估算：中文字符按1个token，英文单词按平均4个字符1个token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        other_chars = len(text) - chinese_chars - english_chars
        
        # 估算公式：中文字符*1 + 英文字符/4 + 其他字符/2
        estimated_tokens = chinese_chars + (english_chars // 4) + (other_chars // 2)
        return max(1, estimated_tokens)  # 至少1个token
    
    def _should_merge_subtitle_sections(self, sections: List[DocumentSection], 
                                      current_index: int, current_tokens: int, 
                                      max_tokens: int) -> bool:
        """判断是否应该合并子标题章节"""
        if current_index >= len(sections):
            return False
            
        current_section = sections[current_index]
        
        # 只考虑合并子标题（二级、三级标题）
        if current_section.section_type not in [
            SectionType.MARKDOWN_H2, SectionType.MARKDOWN_H3, 
            SectionType.CHINESE_MINOR
        ]:
            return False
        
        # 检查当前chunk的token数是否还有合并空间
        section_tokens = self._estimate_token_count(current_section.content)
        if current_tokens + section_tokens > max_tokens:
            return False
        
        # 检查是否有相关的后续子标题可以一起合并
        merge_candidate_count = 0
        total_merge_tokens = section_tokens
        
        for i in range(current_index + 1, min(current_index + 4, len(sections))):
            next_section = sections[i]
            
            # 如果遇到主标题，停止合并
            if next_section.section_type in [SectionType.CHINESE_MAJOR, SectionType.MARKDOWN_H1]:
                break
                
            # 如果是同级或更低级的子标题，考虑合并
            if (next_section.section_type in [
                SectionType.MARKDOWN_H2, SectionType.MARKDOWN_H3, 
                SectionType.CHINESE_MINOR, SectionType.CONTENT
            ]):
                next_tokens = self._estimate_token_count(next_section.content)
                if total_merge_tokens + next_tokens <= max_tokens * 0.8:  # 留20%缓冲
                    merge_candidate_count += 1
                    total_merge_tokens += next_tokens
                else:
                    break
        
        # 如果有2个或以上的相关章节可以合并，且总token数合理，则合并
        return (merge_candidate_count >= 1 and 
                current_tokens + total_merge_tokens <= max_tokens * 0.9)

def main():
    """测试函数"""
    analyzer = DocumentStructureAnalyzer()
    
    # 测试数据
    test_lines = [
        "<1696># 4.特殊时期的患者管理",
        "<1697>",
        "<1698>在重大突发公共卫生事件期间，医疗机构应当制定相应的应急预案...",
        "<1699>",
        "<1700>十二、循环肿瘤标志物检测和临床应用",
        "<1701>",
        "<1702>循环肿瘤标志物是指..."
    ]
    
    sections = analyzer.analyze_document_structure(test_lines)
    boundaries = analyzer.get_optimal_chunk_boundaries(sections)
    
    print("文档结构分析结果：")
    for section in sections:
        print(f"行{section.line_number}: {section.section_type.value} "
              f"(分数: {section.semantic_boundary_score:.2f}) - {section.content[:50]}...")
    
    print(f"\n推荐分块边界: {boundaries}")

if __name__ == "__main__":
    main()