#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词提取模块
支持本地化处理和LLM两种方式为医学文档chunk提取关键词
"""

import re
import json
import os
import logging
import requests
import time
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import Counter
from dataclasses import dataclass
from chunk_evaluator import ChunkEvaluator, ChunkEvaluationResult


@dataclass
class KeywordExtractionResult:
    """
    关键词提取结果数据类
    
    Attributes:
        chunk_id: chunk标识
        original_chunk: 原始chunk内容
        keywords: 提取的关键词列表
        synonyms: 扩展的同义词
        extraction_method: 提取方法（local/llm）
        confidence_score: 置信度评分
        processing_time: 处理时间
    """
    chunk_id: int
    original_chunk: str
    keywords: List[str]
    synonyms: List[str]
    extraction_method: str
    confidence_score: float
    processing_time: float


class MedicalKeywordExtractor:
    """
    医学关键词提取器
    
    支持本地化处理（正则表达式、词频分析、医学词典）和LLM两种方式
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化关键词提取器
        
        Args:
            config_path: 配置文件路径
            
        Raises:
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: 配置文件格式错误
        """
        self.config = self._load_config(config_path)
        self.logger = self._setup_logger()
        
        # 初始化医学词典
        self.medical_patterns = self._init_medical_patterns()
        self.synonym_dict = self._load_synonym_dict()
        
        # LLM客户端配置
        self.llm_client = None
        self._init_llm_client()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict[str, Any]: 配置字典
            
        Raises:
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: 配置文件格式错误
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"配置文件格式错误: {e}")
    
    def _setup_logger(self) -> logging.Logger:
        """
        设置日志记录器
        
        Returns:
            logging.Logger: 日志记录器
        """
        logger = logging.getLogger('keyword_extractor')
        logger.setLevel(getattr(logging, self.config['output']['log_level']))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_medical_patterns(self) -> Dict[str, str]:
        """
        初始化医学术语正则表达式模式
        
        Returns:
            Dict[str, str]: 医学模式字典
        """
        return {
            # 疾病名称
            'diseases': r'(?:[A-Za-z\u4e00-\u9fff]*(?:癌|瘤|病|症|炎|综合征|综合症))',
            
            # 药物名称
            'drugs': r'(?:[A-Za-z\u4e00-\u9fff]*(?:酸|素|胺|醇|酮|肽|霉素|西林|沙星|替尼|单抗|利珠单抗))',
            
            # 治疗方法
            'treatments': r'(?:化疗|放疗|手术|免疫治疗|靶向治疗|介入治疗|中医治疗|针灸|推拿)',
            
            # 症状
            'symptoms': r'(?:发热|疼痛|恶心|呕吐|腹泻|便秘|乏力|食欲不振|体重下降|咳嗽|呼吸困难)',
            
            # 检查项目
            'examinations': r'(?:CT|MRI|PET|B超|X线|血常规|生化|肿瘤标志物|病理|活检)',
            
            # 剂量和用法
            'dosage': r'(?:\d+(?:mg|g|ml|μg|IU)(?:/(?:日|次|kg))?)',
            
            # 医学数值
            'medical_values': r'(?:\d+(?:\.\d+)?(?:%|℃|mmHg|mg/dl|μmol/L))',
            
            # 解剖部位
            'anatomy': r'(?:肺|肝|胃|肠|心|肾|脑|骨|血管|淋巴结|脾|胰腺|甲状腺)',
        }
    
    def _load_synonym_dict(self) -> Dict[str, List[str]]:
        """
        加载同义词词典
        
        Returns:
            Dict[str, List[str]]: 同义词词典
        """
        synonym_dict = {}
        
        # 从配置文件加载同义词
        medical_config = self.config.get('medical_knowledge', {})
        
        for category in ['disease_synonyms', 'drug_synonyms', 'symptom_synonyms']:
            if category in medical_config:
                synonym_dict.update(medical_config[category])
        
        return synonym_dict
    
    def _init_llm_client(self):
        """
        初始化LLM客户端
        """
        llm_config = self.config.get('llm_config', {})
        default_provider = llm_config.get('default_provider', 'glm')
        
        if default_provider in llm_config.get('providers', {}):
            provider_config = llm_config['providers'][default_provider]
            self.llm_client = {
                'provider': default_provider,
                'config': provider_config
            }
            self.logger.info(f"初始化LLM客户端: {default_provider}")
        else:
            self.logger.warning("未找到有效的LLM配置，将仅使用本地方法")
    
    def extract_keywords_from_file(self, file_path: str, output_path: str = None) -> List[KeywordExtractionResult]:
        """
        从文件中提取关键词并添加到chunks
        
        Args:
            file_path: 输入文件路径
            output_path: 输出文件路径（可选）
            
        Returns:
            List[KeywordExtractionResult]: 提取结果列表
            
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
        
        # 分割chunks
        chunks = self._split_chunks(content)
        self.logger.info(f"文件 {file_path} 包含 {len(chunks)} 个chunks")
        
        # 提取关键词
        results = []
        for i, chunk in enumerate(chunks):
            if chunk.strip():  # 跳过空chunks
                result = self.extract_keywords_from_chunk(chunk, chunk_id=i)
                results.append(result)
        
        # 生成带关键词的文档
        if output_path:
            self._save_document_with_keywords(results, output_path)
        
        return results
    
    def extract_keywords_from_chunk(self, chunk: str, chunk_id: int = 0) -> KeywordExtractionResult:
        """
        从单个chunk中提取关键词
        
        Args:
            chunk: chunk内容
            chunk_id: chunk标识
            
        Returns:
            KeywordExtractionResult: 提取结果
        """
        start_time = time.time()
        
        # 获取提取配置
        extraction_config = self.config.get('keyword_extraction', {})
        local_enabled = extraction_config.get('extraction_methods', {}).get('local', {}).get('enabled', True)
        llm_enabled = extraction_config.get('extraction_methods', {}).get('llm', {}).get('enabled', True)
        
        keywords = []
        extraction_method = "none"
        confidence_score = 0.0
        
        # 尝试LLM提取
        if llm_enabled and self.llm_client:
            try:
                llm_keywords = self._extract_keywords_with_llm(chunk)
                if llm_keywords:
                    keywords = llm_keywords
                    extraction_method = "llm"
                    confidence_score = 0.9
                    self.logger.debug(f"LLM提取成功，chunk {chunk_id}")
            except Exception as e:
                self.logger.warning(f"LLM提取失败，chunk {chunk_id}: {e}")
        
        # 如果LLM失败或未启用，使用本地方法
        if not keywords and local_enabled:
            keywords = self._extract_keywords_locally(chunk)
            extraction_method = "local"
            confidence_score = 0.7
            self.logger.debug(f"本地提取完成，chunk {chunk_id}")
        
        # 扩展同义词
        synonyms = []
        if extraction_config.get('enable_synonyms', True):
            synonyms = self._expand_synonyms(keywords)
        
        # 限制关键词数量
        max_keywords = extraction_config.get('max_keywords_per_chunk', 8)
        keywords = keywords[:max_keywords]
        
        processing_time = time.time() - start_time
        
        return KeywordExtractionResult(
            chunk_id=chunk_id,
            original_chunk=chunk,
            keywords=keywords,
            synonyms=synonyms,
            extraction_method=extraction_method,
            confidence_score=confidence_score,
            processing_time=processing_time
        )
    
    def _split_chunks(self, content: str) -> List[str]:
        """
        分割文档为chunks
        
        Args:
            content: 文档内容
            
        Returns:
            List[str]: chunks列表
        """
        boundary_marker = self.config.get('chunk_processing', {}).get('chunk_boundary_marker', '[CHUNK_BOUNDARY]')
        chunks = content.split(boundary_marker)
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    
    def _extract_keywords_with_llm(self, chunk: str) -> List[str]:
        """
        使用LLM提取关键词
        
        Args:
            chunk: chunk内容
            
        Returns:
            List[str]: 关键词列表
            
        Raises:
            Exception: LLM调用失败
        """
        if not self.llm_client:
            raise Exception("LLM客户端未初始化")
        
        provider = self.llm_client['provider']
        config = self.llm_client['config']
        
        # 构建提示词
        prompt_template = self.config.get('keyword_extraction', {}).get('extraction_methods', {}).get('llm', {}).get('prompt_template', '')
        prompt = prompt_template.format(chunk_content=chunk[:2000])  # 限制长度
        
        # 构建请求
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config["api_key"]}'
        }
        
        if provider == 'glm':
            data = {
                'model': config['model'],
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': config.get('max_tokens', 1000),
                'temperature': config.get('temperature', 0.3)
            }
            url = f"{config['base_url'].rstrip('/')}/chat/completions"
        
        elif provider == 'deepseek':
            data = {
                'model': config['model'],
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': config.get('max_tokens', 1000),
                'temperature': config.get('temperature', 0.3)
            }
            url = f"{config['base_url'].rstrip('/')}/chat/completions"
        
        else:  # openai格式
            data = {
                'model': config['model'],
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': config.get('max_tokens', 1000),
                'temperature': config.get('temperature', 0.3)
            }
            url = f"{config['base_url'].rstrip('/')}/chat/completions"
        
        # 发送请求
        try:
            response = requests.post(
                url, 
                headers=headers, 
                json=data, 
                timeout=config.get('timeout', 30)
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 解析关键词
            keywords = self._parse_llm_keywords(content)
            return keywords
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM请求失败: {e}")
        except (KeyError, IndexError) as e:
            raise Exception(f"LLM响应格式错误: {e}")
    
    def _parse_llm_keywords(self, content: str) -> List[str]:
        """
        解析LLM返回的关键词
        
        Args:
            content: LLM返回内容
            
        Returns:
            List[str]: 关键词列表
        """
        # 清理内容
        content = content.strip()
        
        # 尝试多种分隔符
        separators = [',', '，', ';', '；', '\n', '、']
        keywords = []
        
        for sep in separators:
            if sep in content:
                keywords = [kw.strip() for kw in content.split(sep)]
                break
        
        if not keywords:
            # 如果没有分隔符，尝试提取中文词汇
            keywords = re.findall(r'[\u4e00-\u9fff]+', content)
        
        # 过滤和清理关键词
        filtered_keywords = []
        min_length = self.config.get('keyword_extraction', {}).get('min_keyword_length', 2)
        max_length = self.config.get('keyword_extraction', {}).get('max_keyword_length', 20)
        
        for kw in keywords:
            kw = kw.strip('。，！？；：""''()（）[]【】')
            if min_length <= len(kw) <= max_length and kw:
                filtered_keywords.append(kw)
        
        return filtered_keywords[:8]  # 限制数量
    
    def _extract_keywords_locally(self, chunk: str) -> List[str]:
        """
        使用本地方法提取关键词
        
        Args:
            chunk: chunk内容
            
        Returns:
            List[str]: 关键词列表
        """
        keywords = set()
        
        # 1. 正则表达式提取医学术语
        if self.config.get('keyword_extraction', {}).get('extraction_methods', {}).get('local', {}).get('use_regex', True):
            regex_keywords = self._extract_with_regex(chunk)
            keywords.update(regex_keywords)
        
        # 2. 词频分析
        if self.config.get('keyword_extraction', {}).get('extraction_methods', {}).get('local', {}).get('use_frequency', True):
            freq_keywords = self._extract_with_frequency(chunk)
            keywords.update(freq_keywords)
        
        # 3. 医学词典匹配
        if self.config.get('keyword_extraction', {}).get('extraction_methods', {}).get('local', {}).get('use_medical_dict', True):
            dict_keywords = self._extract_with_medical_dict(chunk)
            keywords.update(dict_keywords)
        
        # 转换为列表并排序
        keyword_list = list(keywords)
        
        # 按重要性排序（优先医学术语）
        keyword_list.sort(key=lambda x: self._calculate_keyword_importance(x, chunk), reverse=True)
        
        return keyword_list[:8]  # 限制数量
    
    def _extract_with_regex(self, chunk: str) -> Set[str]:
        """
        使用正则表达式提取关键词
        
        Args:
            chunk: chunk内容
            
        Returns:
            Set[str]: 关键词集合
        """
        keywords = set()
        
        for category, pattern in self.medical_patterns.items():
            matches = re.findall(pattern, chunk)
            for match in matches:
                if len(match) >= 2:  # 最小长度过滤
                    keywords.add(match)
        
        return keywords
    
    def _extract_with_frequency(self, chunk: str) -> Set[str]:
        """
        使用词频分析提取关键词
        
        Args:
            chunk: chunk内容
            
        Returns:
            Set[str]: 关键词集合
        """
        # 提取中文词汇
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', chunk)
        
        # 过滤停用词
        stopwords = {'的', '了', '在', '是', '有', '和', '与', '或', '但', '而', '因为', '所以', '如果', '那么', '这样', '那样'}
        filtered_words = [word for word in chinese_words if word not in stopwords]
        
        # 计算词频
        word_freq = Counter(filtered_words)
        
        # 返回高频词
        keywords = set()
        for word, freq in word_freq.most_common(5):
            if freq >= 2:  # 至少出现2次
                keywords.add(word)
        
        return keywords
    
    def _extract_with_medical_dict(self, chunk: str) -> Set[str]:
        """
        使用医学词典匹配关键词
        
        Args:
            chunk: chunk内容
            
        Returns:
            Set[str]: 关键词集合
        """
        keywords = set()
        
        # 从同义词词典中匹配
        for main_term, synonyms in self.synonym_dict.items():
            if main_term in chunk:
                keywords.add(main_term)
            
            for synonym in synonyms:
                if synonym in chunk:
                    keywords.add(main_term)  # 使用主术语
        
        return keywords
    
    def _calculate_keyword_importance(self, keyword: str, chunk: str) -> float:
        """
        计算关键词重要性
        
        Args:
            keyword: 关键词
            chunk: chunk内容
            
        Returns:
            float: 重要性评分
        """
        score = 0.0
        
        # 长度权重
        score += len(keyword) * 0.1
        
        # 医学术语权重
        for category, pattern in self.medical_patterns.items():
            if re.search(pattern, keyword):
                score += 2.0
                break
        
        # 频率权重
        frequency = chunk.count(keyword)
        score += frequency * 0.5
        
        # 位置权重（开头的词更重要）
        position = chunk.find(keyword)
        if position < len(chunk) * 0.3:
            score += 1.0
        
        return score
    
    def _expand_synonyms(self, keywords: List[str]) -> List[str]:
        """
        扩展同义词
        
        Args:
            keywords: 原始关键词列表
            
        Returns:
            List[str]: 扩展后的同义词列表
        """
        synonyms = []
        
        for keyword in keywords:
            if keyword in self.synonym_dict:
                synonyms.extend(self.synonym_dict[keyword])
        
        return list(set(synonyms))  # 去重
    
    def _save_document_with_keywords(self, results: List[KeywordExtractionResult], output_path: str):
        """
        保存带关键词的文档
        
        Args:
            results: 提取结果列表
            output_path: 输出路径
        """
        # 构建文档内容
        content_parts = []
        
        chunk_config = self.config.get('chunk_processing', {})
        boundary_marker = chunk_config.get('chunk_boundary_marker', '[CHUNK_BOUNDARY]')
        keyword_prefix = self.config.get('keyword_extraction', {}).get('keyword_prefix', '#')
        add_at_beginning = chunk_config.get('add_keywords_at_beginning', True)
        max_display = chunk_config.get('max_keywords_display', 6)
        
        for result in results:
            chunk_content = result.original_chunk
            
            if result.keywords:
                # 格式化关键词
                display_keywords = result.keywords[:max_display]
                keyword_line = ' '.join([f"{keyword_prefix}{kw}" for kw in display_keywords])
                
                if add_at_beginning:
                    chunk_content = f"{keyword_line}\n\n{chunk_content}"
                else:
                    chunk_content = f"{chunk_content}\n\n{keyword_line}"
            
            content_parts.append(chunk_content)
        
        # 合并内容
        final_content = f"\n{boundary_marker}\n".join(content_parts)
        
        # 保存文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            self.logger.info(f"带关键词的文档已保存到: {output_path}")
            
        except Exception as e:
            self.logger.error(f"保存文档失败: {e}")
            raise
    
    def evaluate_and_extract(self, file_path: str, output_path: str = None) -> Tuple[ChunkEvaluationResult, List[KeywordExtractionResult]]:
        """
        评估chunk质量并提取关键词
        
        Args:
            file_path: 输入文件路径
            output_path: 输出文件路径
            
        Returns:
            Tuple[ChunkEvaluationResult, List[KeywordExtractionResult]]: 评估结果和提取结果
        """
        # 1. 评估chunk质量
        evaluator = ChunkEvaluator()
        evaluation_result = evaluator.evaluate_file(file_path)
        
        # 2. 提取关键词
        extraction_results = self.extract_keywords_from_file(file_path, output_path)
        
        # 3. 打印报告
        evaluator.print_evaluation_report(evaluation_result, file_path)
        self._print_extraction_report(extraction_results)
        
        return evaluation_result, extraction_results
    
    def _print_extraction_report(self, results: List[KeywordExtractionResult]):
        """
        打印关键词提取报告
        
        Args:
            results: 提取结果列表
        """
        print("\n" + "=" * 60)
        print("关键词提取报告")
        print("=" * 60)
        
        total_chunks = len(results)
        successful_extractions = len([r for r in results if r.keywords])
        avg_keywords = sum(len(r.keywords) for r in results) / total_chunks if total_chunks > 0 else 0
        avg_processing_time = sum(r.processing_time for r in results) / total_chunks if total_chunks > 0 else 0
        
        print(f"总chunk数量: {total_chunks}")
        print(f"成功提取关键词的chunk: {successful_extractions}")
        print(f"成功率: {successful_extractions/total_chunks*100:.1f}%")
        print(f"平均关键词数量: {avg_keywords:.1f}")
        print(f"平均处理时间: {avg_processing_time:.3f}秒")
        print()
        
        # 方法统计
        method_stats = Counter(r.extraction_method for r in results)
        print("提取方法统计:")
        for method, count in method_stats.items():
            print(f"  {method}: {count} ({count/total_chunks*100:.1f}%)")
        print()
        
        # 显示前几个示例
        print("关键词提取示例:")
        for i, result in enumerate(results[:3]):
            if result.keywords:
                print(f"  Chunk {result.chunk_id}:")
                print(f"    关键词: {', '.join(result.keywords)}")
                print(f"    方法: {result.extraction_method}")
                print(f"    置信度: {result.confidence_score:.2f}")
                print()
        
        print("=" * 60)


def main():
    """
    主函数，用于测试关键词提取器
    """
    # 测试文件路径
    test_file = "/Users/qinxiaoqiang/Downloads/xiaofubao/output/恶性肿瘤并发症治疗_optimized.md"
    output_file = "/Users/qinxiaoqiang/Downloads/xiaofubao/output/恶性肿瘤并发症治疗_with_keywords.md"
    
    try:
        extractor = MedicalKeywordExtractor()
        evaluation_result, extraction_results = extractor.evaluate_and_extract(test_file, output_file)
        
        print(f"\n处理完成！")
        print(f"输入文件: {test_file}")
        print(f"输出文件: {output_file}")
        
    except Exception as e:
        print(f"处理失败: {e}")


if __name__ == "__main__":
    main()