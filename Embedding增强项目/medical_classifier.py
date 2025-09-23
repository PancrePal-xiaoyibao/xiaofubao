#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医学知识分类器
实现基于配置的动态标签识别和chunk分类功能
"""

import json
import re
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import logging

class MedicalKnowledgeClassifier:
    """
    医学知识分类器
    
    功能：
    1. 基于配置文件进行chunk分类
    2. 动态标签识别
    3. 同义词扩展
    4. 医学术语标准化
    """
    
    def __init__(self, config_path: str):
        """
        初始化分类器
        
        参数:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.medical_config = self.config.get('medical_knowledge', {})
        self.classification_config = self.medical_config.get('chunk_classification', {})
        self.category_hierarchy = self.classification_config.get('category_hierarchy', {})
        
        # 构建同义词映射
        self.synonym_maps = self._build_synonym_maps()
        
        # 构建分类关键词索引
        self.category_keywords = self._build_category_keywords()
        
        # 配置参数
        self.confidence_threshold = self.classification_config.get('classification_confidence_threshold', 0.7)
        self.max_categories = self.classification_config.get('max_categories_per_chunk', 3)
        
        logging.info("医学知识分类器初始化完成")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        加载配置文件
        
        参数:
            config_path: 配置文件路径
            
        返回:
            配置字典
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            return {}
    
    def _build_synonym_maps(self) -> Dict[str, Dict[str, Set[str]]]:
        """
        构建同义词映射表
        
        返回:
            同义词映射字典
        """
        synonym_maps = {}
        
        # 处理各类同义词
        synonym_types = [
            'disease_synonyms', 'drug_synonyms', 'symptom_synonyms',
            'treatment_synonyms', 'examination_synonyms'
        ]
        
        for synonym_type in synonym_types:
            synonym_maps[synonym_type] = {}
            synonyms = self.medical_config.get(synonym_type, {})
            
            for main_term, synonym_list in synonyms.items():
                # 主词条映射到自己
                synonym_maps[synonym_type][main_term] = {main_term}
                
                # 同义词映射到主词条
                for synonym in synonym_list:
                    if synonym not in synonym_maps[synonym_type]:
                        synonym_maps[synonym_type][synonym] = set()
                    synonym_maps[synonym_type][synonym].add(main_term)
                    synonym_maps[synonym_type][main_term].add(synonym)
        
        return synonym_maps
    
    def _build_category_keywords(self) -> Dict[str, List[str]]:
        """
        构建分类关键词索引
        
        返回:
            分类关键词字典
        """
        category_keywords = {}
        
        for category, config in self.category_hierarchy.items():
            keywords = config.get('keywords', [])
            category_keywords[category] = keywords
            
            # 添加子分类关键词
            subcategories = config.get('subcategories', {})
            for subcat, subkeywords in subcategories.items():
                full_category = f"{category}.{subcat}"
                category_keywords[full_category] = subkeywords
        
        return category_keywords
    
    def normalize_text(self, text: str) -> str:
        """
        文本标准化
        
        参数:
            text: 原始文本
            
        返回:
            标准化后的文本
        """
        # 去除多余空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 同义词替换
        for synonym_type, synonym_map in self.synonym_maps.items():
            for term, main_terms in synonym_map.items():
                if term in text:
                    # 替换为主词条（选择最短的作为主词条）
                    main_term = min(main_terms, key=len)
                    text = text.replace(term, main_term)
        
        return text
    
    def extract_medical_terms(self, text: str) -> Dict[str, List[str]]:
        """
        提取医学术语
        
        参数:
            text: 输入文本
            
        返回:
            按类型分组的医学术语
        """
        terms = {
            'diseases': [],
            'drugs': [],
            'symptoms': [],
            'treatments': [],
            'examinations': []
        }
        
        # 映射同义词类型到术语类型
        type_mapping = {
            'disease_synonyms': 'diseases',
            'drug_synonyms': 'drugs',
            'symptom_synonyms': 'symptoms',
            'treatment_synonyms': 'treatments',
            'examination_synonyms': 'examinations'
        }
        
        for synonym_type, term_type in type_mapping.items():
            synonym_map = self.synonym_maps.get(synonym_type, {})
            for term in synonym_map.keys():
                if term in text:
                    # 获取主词条
                    main_terms = synonym_map[term]
                    main_term = min(main_terms, key=len)
                    if main_term not in terms[term_type]:
                        terms[term_type].append(main_term)
        
        return terms
    
    def classify_chunk(self, chunk_text: str) -> Dict[str, float]:
        """
        对chunk进行分类
        
        参数:
            chunk_text: chunk文本内容
            
        返回:
            分类结果及置信度
        """
        # 标准化文本
        normalized_text = self.normalize_text(chunk_text)
        
        # 计算各分类的匹配分数
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = self._calculate_category_score(normalized_text, keywords)
            if score > 0:
                category_scores[category] = score
        
        # 归一化分数
        if category_scores:
            max_score = max(category_scores.values())
            for category in category_scores:
                category_scores[category] /= max_score
        
        # 过滤低置信度分类
        filtered_scores = {
            category: score for category, score in category_scores.items()
            if score >= self.confidence_threshold
        }
        
        # 限制分类数量
        if len(filtered_scores) > self.max_categories:
            sorted_categories = sorted(filtered_scores.items(), key=lambda x: x[1], reverse=True)
            filtered_scores = dict(sorted_categories[:self.max_categories])
        
        return filtered_scores
    
    def _calculate_category_score(self, text: str, keywords: List[str]) -> float:
        """
        计算分类匹配分数
        
        参数:
            text: 文本内容
            keywords: 关键词列表
            
        返回:
            匹配分数
        """
        if not keywords:
            return 0.0
        
        matched_keywords = 0
        total_matches = 0
        
        for keyword in keywords:
            # 计算关键词在文本中的出现次数
            count = len(re.findall(re.escape(keyword), text, re.IGNORECASE))
            if count > 0:
                matched_keywords += 1
                total_matches += count
        
        # 计算分数：匹配关键词比例 + 总匹配次数权重
        keyword_ratio = matched_keywords / len(keywords)
        match_weight = min(total_matches / len(text.split()), 1.0)  # 标准化匹配密度
        
        return keyword_ratio * 0.7 + match_weight * 0.3
    
    def generate_tags(self, chunk_text: str) -> List[str]:
        """
        为chunk生成标签
        
        参数:
            chunk_text: chunk文本内容
            
        返回:
            标签列表
        """
        tags = []
        
        # 添加分类标签
        classifications = self.classify_chunk(chunk_text)
        for category, confidence in classifications.items():
            # 格式化分类标签
            if '.' in category:
                main_cat, sub_cat = category.split('.', 1)
                tag = f"#{main_cat}_{sub_cat}"
            else:
                tag = f"#{category}"
            tags.append(tag)
        
        # 添加医学术语标签
        medical_terms = self.extract_medical_terms(chunk_text)
        for term_type, terms in medical_terms.items():
            for term in terms[:3]:  # 限制每类术语数量
                tag = f"#{term_type}_{term}"
                tags.append(tag)
        
        return tags
    
    def process_chunk(self, chunk_text: str) -> Dict:
        """
        处理chunk，返回完整的分析结果
        
        参数:
            chunk_text: chunk文本内容
            
        返回:
            包含分类、标签、术语等信息的字典
        """
        # 标准化文本
        normalized_text = self.normalize_text(chunk_text)
        
        # 分类
        classifications = self.classify_chunk(chunk_text)
        
        # 提取医学术语
        medical_terms = self.extract_medical_terms(chunk_text)
        
        # 生成标签
        tags = self.generate_tags(chunk_text)
        
        return {
            'original_text': chunk_text,
            'normalized_text': normalized_text,
            'classifications': classifications,
            'medical_terms': medical_terms,
            'tags': tags,
            'processing_metadata': {
                'classifier_version': '1.0',
                'confidence_threshold': self.confidence_threshold,
                'max_categories': self.max_categories
            }
        }
    
    def get_classification_summary(self) -> Dict:
        """
        获取分类器配置摘要
        
        返回:
            配置摘要信息
        """
        return {
            'total_categories': len(self.category_keywords),
            'synonym_types': list(self.synonym_maps.keys()),
            'total_synonyms': sum(len(synonyms) for synonyms in self.synonym_maps.values()),
            'confidence_threshold': self.confidence_threshold,
            'max_categories_per_chunk': self.max_categories,
            'available_categories': list(self.category_keywords.keys())
        }


def main():
    """
    测试函数
    """
    # 初始化分类器
    classifier = MedicalKnowledgeClassifier('config.json')
    
    # 测试文本
    test_chunks = [
        "根据最新的肺癌诊疗指南，对于非小细胞肺癌患者，推荐进行EGFR基因检测。",
        "患者出现恶心、呕吐症状，给予奥美拉唑40mg静脉注射，每日一次。",
        "术后疼痛评估显示VAS评分为7分，给予吗啡10mg肌肉注射进行镇痛治疗。",
        "营养评估显示患者存在营养不良，建议增加蛋白质摄入，每日2g/kg体重。",
        "患者出现焦虑情绪，建议心理干预，必要时给予抗焦虑药物治疗。",
        "患者化疗后出现CIPN，表现为手足麻木、疼痛，影响日常生活",
        "术后第3天患者出现肠梗阻，腹胀明显，停止进食，予以胃肠减压",
        "患者出现消化道出血，表现为黑便，血红蛋白下降至70g/L",
        "化疗期间发生骨髓抑制，白细胞计数降至1.5×10⁹/L，需要升白治疗",
        "患者确诊特鲁索症候群，下肢深静脉血栓形成，予以抗凝治疗",
        # 新增药物和疾病测试用例
        "胰腺癌患者使用吉西他滨联合白蛋白紫杉醇化疗方案",
        "乳腺癌HER2阳性患者接受曲妥珠单抗靶向治疗",
        "非小细胞肺癌患者EGFR突变，予奥希替尼治疗",
        "急性髓系白血病患者接受柔红霉素+阿糖胞苷诱导化疗",
        "卵巢癌患者术后予紫杉醇+卡铂辅助化疗",
        "结直肠癌肝转移患者使用贝伐珠单抗联合FOLFOX方案",
        "肝细胞癌患者接受索拉非尼分子靶向治疗",
        "胃癌患者予奥沙利铂+5-氟尿嘧啶围手术期化疗",
        "霍奇金淋巴瘤患者接受ABVD方案化疗",
        "分化型甲状腺癌术后予碘131放射性治疗"
    ]
    
    print("医学知识分类器测试")
    print("=" * 50)
    
    # 显示分类器摘要
    summary = classifier.get_classification_summary()
    print(f"分类器配置摘要:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print()
    
    # 处理测试文本
    for i, chunk in enumerate(test_chunks, 1):
        print(f"测试文本 {i}:")
        print(f"原文: {chunk}")
        
        result = classifier.process_chunk(chunk)
        
        print(f"分类结果: {result['classifications']}")
        print(f"医学术语: {result['medical_terms']}")
        print(f"生成标签: {result['tags']}")
        print("-" * 30)


if __name__ == "__main__":
    main()