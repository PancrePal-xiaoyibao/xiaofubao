#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医学知识库模块
提供医学术语同义词扩展、标准化和相关概念推荐功能
"""

import json
import re
import os
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class MedicalTerm:
    """
    医学术语数据类
    
    Attributes:
        standard_name: 标准名称
        synonyms: 同义词列表
        category: 术语类别（疾病、药物、症状等）
        related_terms: 相关术语
        description: 描述
    """
    standard_name: str
    synonyms: List[str]
    category: str
    related_terms: List[str]
    description: str = ""


class MedicalKnowledgeBase:
    """
    医学知识库
    
    提供医学术语的标准化、同义词扩展和相关概念推荐功能
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化医学知识库
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.terms_db: Dict[str, MedicalTerm] = {}
        self.synonym_index: Dict[str, str] = {}  # 同义词到标准名称的映射
        self.category_index: Dict[str, List[str]] = defaultdict(list)
        
        # 初始化知识库
        self._init_knowledge_base()
    
    def _load_config(self, config_path: str) -> Dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict: 配置字典
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _init_knowledge_base(self):
        """
        初始化医学知识库
        """
        # 从配置文件加载基础同义词
        self._load_basic_synonyms()
        
        # 加载扩展医学术语
        self._load_extended_medical_terms()
        
        # 构建索引
        self._build_indexes()
    
    def _load_basic_synonyms(self):
        """
        从配置文件加载基础同义词
        """
        medical_config = self.config.get('medical_knowledge', {})
        
        # 疾病同义词
        disease_synonyms = medical_config.get('disease_synonyms', {})
        for standard_name, synonyms in disease_synonyms.items():
            term = MedicalTerm(
                standard_name=standard_name,
                synonyms=synonyms,
                category="疾病",
                related_terms=[]
            )
            self.terms_db[standard_name] = term
        
        # 药物同义词
        drug_synonyms = medical_config.get('drug_synonyms', {})
        for standard_name, synonyms in drug_synonyms.items():
            term = MedicalTerm(
                standard_name=standard_name,
                synonyms=synonyms,
                category="药物",
                related_terms=[]
            )
            self.terms_db[standard_name] = term
        
        # 症状同义词
        symptom_synonyms = medical_config.get('symptom_synonyms', {})
        for standard_name, synonyms in symptom_synonyms.items():
            term = MedicalTerm(
                standard_name=standard_name,
                synonyms=synonyms,
                category="症状",
                related_terms=[]
            )
            self.terms_db[standard_name] = term
    
    def _load_extended_medical_terms(self):
        """
        加载扩展的医学术语库
        """
        # 肿瘤相关术语
        cancer_terms = {
            "肺癌": {
                "synonyms": ["肺部恶性肿瘤", "支气管癌", "肺部癌症", "原发性肺癌"],
                "related_terms": ["非小细胞肺癌", "小细胞肺癌", "肺腺癌", "肺鳞癌", "化疗", "放疗", "靶向治疗"],
                "description": "起源于肺部的恶性肿瘤"
            },
            "乳腺癌": {
                "synonyms": ["乳癌", "乳房癌", "乳腺恶性肿瘤"],
                "related_terms": ["乳腺增生", "乳腺结节", "内分泌治疗", "HER2", "三阴性乳腺癌"],
                "description": "女性最常见的恶性肿瘤之一"
            },
            "胃癌": {
                "synonyms": ["胃部恶性肿瘤", "胃腺癌", "胃部癌症"],
                "related_terms": ["胃炎", "胃溃疡", "幽门螺杆菌", "胃镜检查", "胃切除术"],
                "description": "起源于胃黏膜的恶性肿瘤"
            },
            "肝癌": {
                "synonyms": ["肝细胞癌", "肝部恶性肿瘤", "原发性肝癌", "肝脏癌"],
                "related_terms": ["肝硬化", "乙肝", "丙肝", "肝移植", "介入治疗", "射频消融"],
                "description": "起源于肝脏的恶性肿瘤"
            }
        }
        
        # 化疗药物
        chemo_drugs = {
            "顺铂": {
                "synonyms": ["DDP", "cisplatin", "顺氯氨铂"],
                "related_terms": ["铂类药物", "肾毒性", "听力损害", "恶心呕吐"],
                "description": "铂类抗肿瘤药物"
            },
            "紫杉醇": {
                "synonyms": ["paclitaxel", "泰素"],
                "related_terms": ["微管抑制剂", "过敏反应", "周围神经病变"],
                "description": "微管稳定剂类抗肿瘤药物"
            },
            "阿霉素": {
                "synonyms": ["doxorubicin", "多柔比星", "阿德里亚霉素"],
                "related_terms": ["蒽环类", "心脏毒性", "脱发", "骨髓抑制"],
                "description": "蒽环类抗肿瘤抗生素"
            }
        }
        
        # 症状和并发症
        symptoms_complications = {
            "骨髓抑制": {
                "synonyms": ["造血功能抑制", "血细胞减少"],
                "related_terms": ["白细胞减少", "血小板减少", "贫血", "感染", "出血"],
                "description": "化疗常见副作用"
            },
            "恶心呕吐": {
                "synonyms": ["胃肠道反应", "消化道反应"],
                "related_terms": ["止吐药", "5-HT3受体拮抗剂", "地塞米松", "食欲不振"],
                "description": "化疗常见胃肠道副作用"
            },
            "周围神经病变": {
                "synonyms": ["神经毒性", "末梢神经炎"],
                "related_terms": ["手足麻木", "感觉异常", "疼痛", "功能障碍"],
                "description": "某些化疗药物引起的神经系统副作用"
            }
        }
        
        # 治疗方法
        treatments = {
            "靶向治疗": {
                "synonyms": ["分子靶向治疗", "精准治疗"],
                "related_terms": ["EGFR抑制剂", "HER2抑制剂", "血管生成抑制剂", "免疫检查点抑制剂"],
                "description": "针对特定分子靶点的治疗方法"
            },
            "免疫治疗": {
                "synonyms": ["免疫检查点抑制剂治疗", "PD-1/PD-L1抑制剂"],
                "related_terms": ["PD-1", "PD-L1", "CTLA-4", "免疫相关不良反应"],
                "description": "激活机体免疫系统抗肿瘤的治疗方法"
            },
            "介入治疗": {
                "synonyms": ["血管介入", "导管介入"],
                "related_terms": ["栓塞", "化疗栓塞", "射频消融", "微波消融"],
                "description": "通过血管途径进行的微创治疗"
            }
        }
        
        # 合并所有术语
        all_terms = {
            **cancer_terms,
            **chemo_drugs, 
            **symptoms_complications,
            **treatments
        }
        
        # 添加到知识库
        for standard_name, term_data in all_terms.items():
            if standard_name not in self.terms_db:
                # 确定类别
                category = "疾病"
                if standard_name in chemo_drugs:
                    category = "药物"
                elif standard_name in symptoms_complications:
                    category = "症状"
                elif standard_name in treatments:
                    category = "治疗"
                
                term = MedicalTerm(
                    standard_name=standard_name,
                    synonyms=term_data.get("synonyms", []),
                    category=category,
                    related_terms=term_data.get("related_terms", []),
                    description=term_data.get("description", "")
                )
                self.terms_db[standard_name] = term
    
    def _build_indexes(self):
        """
        构建索引以提高查询效率
        """
        self.synonym_index.clear()
        self.category_index.clear()
        
        for standard_name, term in self.terms_db.items():
            # 构建同义词索引
            self.synonym_index[standard_name] = standard_name
            for synonym in term.synonyms:
                self.synonym_index[synonym] = standard_name
            
            # 构建类别索引
            self.category_index[term.category].append(standard_name)
    
    def standardize_term(self, term: str) -> Optional[str]:
        """
        标准化医学术语
        
        Args:
            term: 输入术语
            
        Returns:
            Optional[str]: 标准化后的术语，如果未找到则返回None
        """
        # 直接匹配
        if term in self.synonym_index:
            return self.synonym_index[term]
        
        # 模糊匹配
        for synonym, standard_name in self.synonym_index.items():
            if term in synonym or synonym in term:
                return standard_name
        
        return None
    
    def get_synonyms(self, term: str) -> List[str]:
        """
        获取术语的所有同义词
        
        Args:
            term: 输入术语
            
        Returns:
            List[str]: 同义词列表
        """
        standard_name = self.standardize_term(term)
        if standard_name and standard_name in self.terms_db:
            return self.terms_db[standard_name].synonyms
        return []
    
    def get_related_terms(self, term: str) -> List[str]:
        """
        获取相关术语
        
        Args:
            term: 输入术语
            
        Returns:
            List[str]: 相关术语列表
        """
        standard_name = self.standardize_term(term)
        if standard_name and standard_name in self.terms_db:
            return self.terms_db[standard_name].related_terms
        return []
    
    def expand_keywords(self, keywords: List[str], include_related: bool = True, max_expansions: int = 3) -> List[str]:
        """
        扩展关键词列表
        
        Args:
            keywords: 原始关键词列表
            include_related: 是否包含相关术语
            max_expansions: 每个关键词的最大扩展数量
            
        Returns:
            List[str]: 扩展后的关键词列表
        """
        expanded = set(keywords)  # 保留原始关键词
        
        for keyword in keywords:
            # 添加同义词
            synonyms = self.get_synonyms(keyword)
            expanded.update(synonyms[:max_expansions])
            
            # 添加相关术语
            if include_related:
                related = self.get_related_terms(keyword)
                expanded.update(related[:max_expansions])
        
        return list(expanded)
    
    def get_term_info(self, term: str) -> Optional[MedicalTerm]:
        """
        获取术语的完整信息
        
        Args:
            term: 输入术语
            
        Returns:
            Optional[MedicalTerm]: 术语信息，如果未找到则返回None
        """
        standard_name = self.standardize_term(term)
        if standard_name and standard_name in self.terms_db:
            return self.terms_db[standard_name]
        return None
    
    def search_by_category(self, category: str) -> List[str]:
        """
        按类别搜索术语
        
        Args:
            category: 术语类别
            
        Returns:
            List[str]: 该类别下的术语列表
        """
        return self.category_index.get(category, [])
    
    def add_custom_term(self, standard_name: str, synonyms: List[str], category: str, 
                       related_terms: List[str] = None, description: str = ""):
        """
        添加自定义术语
        
        Args:
            standard_name: 标准名称
            synonyms: 同义词列表
            category: 类别
            related_terms: 相关术语列表
            description: 描述
        """
        if related_terms is None:
            related_terms = []
        
        term = MedicalTerm(
            standard_name=standard_name,
            synonyms=synonyms,
            category=category,
            related_terms=related_terms,
            description=description
        )
        
        self.terms_db[standard_name] = term
        
        # 更新索引
        self.synonym_index[standard_name] = standard_name
        for synonym in synonyms:
            self.synonym_index[synonym] = standard_name
        
        self.category_index[category].append(standard_name)
    
    def extract_medical_terms_from_text(self, text: str) -> List[Tuple[str, str]]:
        """
        从文本中提取医学术语
        
        Args:
            text: 输入文本
            
        Returns:
            List[Tuple[str, str]]: (原始术语, 标准化术语) 的列表
        """
        found_terms = []
        
        # 按长度排序，优先匹配长术语
        sorted_synonyms = sorted(self.synonym_index.keys(), key=len, reverse=True)
        
        for synonym in sorted_synonyms:
            if synonym in text:
                standard_name = self.synonym_index[synonym]
                found_terms.append((synonym, standard_name))
        
        # 去重，保留第一次匹配的结果
        seen_standards = set()
        unique_terms = []
        for original, standard in found_terms:
            if standard not in seen_standards:
                unique_terms.append((original, standard))
                seen_standards.add(standard)
        
        return unique_terms
    
    def suggest_keywords_for_chunk(self, chunk_text: str, max_suggestions: int = 5) -> List[str]:
        """
        为chunk建议关键词
        
        Args:
            chunk_text: chunk文本
            max_suggestions: 最大建议数量
            
        Returns:
            List[str]: 建议的关键词列表
        """
        # 提取文本中的医学术语
        found_terms = self.extract_medical_terms_from_text(chunk_text)
        
        # 按重要性排序
        term_scores = []
        for original, standard in found_terms:
            score = self._calculate_term_importance(original, standard, chunk_text)
            term_scores.append((standard, score))
        
        # 排序并返回top N
        term_scores.sort(key=lambda x: x[1], reverse=True)
        return [term for term, score in term_scores[:max_suggestions]]
    
    def _calculate_term_importance(self, original_term: str, standard_term: str, text: str) -> float:
        """
        计算术语在文本中的重要性
        
        Args:
            original_term: 原始术语
            standard_term: 标准术语
            text: 文本内容
            
        Returns:
            float: 重要性评分
        """
        score = 0.0
        
        # 频率权重
        frequency = text.count(original_term)
        score += frequency * 2.0
        
        # 长度权重
        score += len(original_term) * 0.1
        
        # 位置权重（出现在开头的更重要）
        position = text.find(original_term)
        if position < len(text) * 0.3:
            score += 1.0
        
        # 类别权重
        term_info = self.get_term_info(standard_term)
        if term_info:
            category_weights = {
                "疾病": 3.0,
                "药物": 2.5,
                "治疗": 2.0,
                "症状": 1.5
            }
            score += category_weights.get(term_info.category, 1.0)
        
        return score
    
    def export_knowledge_base(self, output_path: str):
        """
        导出知识库到JSON文件
        
        Args:
            output_path: 输出文件路径
        """
        export_data = {}
        for standard_name, term in self.terms_db.items():
            export_data[standard_name] = {
                "synonyms": term.synonyms,
                "category": term.category,
                "related_terms": term.related_terms,
                "description": term.description
            }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    def import_knowledge_base(self, input_path: str):
        """
        从JSON文件导入知识库
        
        Args:
            input_path: 输入文件路径
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        for standard_name, term_data in import_data.items():
            self.add_custom_term(
                standard_name=standard_name,
                synonyms=term_data.get("synonyms", []),
                category=term_data.get("category", "其他"),
                related_terms=term_data.get("related_terms", []),
                description=term_data.get("description", "")
            )
    
    def print_statistics(self):
        """
        打印知识库统计信息
        """
        print("=" * 50)
        print("医学知识库统计信息")
        print("=" * 50)
        
        total_terms = len(self.terms_db)
        total_synonyms = sum(len(term.synonyms) for term in self.terms_db.values())
        
        print(f"标准术语数量: {total_terms}")
        print(f"同义词总数: {total_synonyms}")
        print(f"平均每个术语的同义词数: {total_synonyms/total_terms:.1f}")
        print()
        
        print("按类别统计:")
        for category, terms in self.category_index.items():
            print(f"  {category}: {len(terms)} 个术语")
        
        print("=" * 50)


def main():
    """
    主函数，用于测试医学知识库
    """
    # 初始化知识库
    kb = MedicalKnowledgeBase()
    
    # 打印统计信息
    kb.print_statistics()
    
    # 测试功能
    print("\n测试功能:")
    
    # 测试术语标准化
    test_terms = ["肺部恶性肿瘤", "乳癌", "发烧", "阿德里亚霉素"]
    print("\n术语标准化测试:")
    for term in test_terms:
        standard = kb.standardize_term(term)
        print(f"  {term} -> {standard}")
    
    # 测试同义词扩展
    print("\n同义词扩展测试:")
    keywords = ["肺癌", "化疗"]
    expanded = kb.expand_keywords(keywords)
    print(f"  原始: {keywords}")
    print(f"  扩展: {expanded}")
    
    # 测试文本术语提取
    print("\n文本术语提取测试:")
    test_text = "患者诊断为肺癌，给予顺铂联合紫杉醇化疗，出现恶心呕吐等副作用。"
    found_terms = kb.extract_medical_terms_from_text(test_text)
    print(f"  文本: {test_text}")
    print(f"  提取的术语: {found_terms}")


if __name__ == "__main__":
    main()