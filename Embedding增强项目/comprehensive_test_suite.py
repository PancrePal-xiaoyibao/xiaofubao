#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面测试套件
解决原有测试逻辑的系统性问题，提供端到端的验证能力
"""

import unittest
import tempfile
import os
from typing import List, Dict
from document_structure_analyzer import DocumentStructureAnalyzer, SectionType
from preprocess_enhanced import EnhancedDocumentPreprocessor

class TestDocumentStructureAnalyzer(unittest.TestCase):
    """文档结构分析器测试"""
    
    def setUp(self):
        self.analyzer = DocumentStructureAnalyzer()
    
    def test_chinese_major_section_detection(self):
        """测试中文一级序号检测"""
        test_lines = [
            "<1696># 4.特殊时期的患者管理",
            "<1700>十二、循环肿瘤标志物检测和临床应用",
            "<1705>十三、乳腺癌的预防"
        ]
        
        sections = self.analyzer.analyze_document_structure(test_lines)
        
        # 验证中文序号被正确识别
        chinese_sections = [s for s in sections if s.section_type == SectionType.CHINESE_MAJOR]
        self.assertEqual(len(chinese_sections), 2)
        self.assertIn("十二、循环肿瘤标志物检测", chinese_sections[0].content)
        self.assertIn("十三、乳腺癌的预防", chinese_sections[1].content)
    
    def test_markdown_title_detection(self):
        """测试Markdown标题检测"""
        test_lines = [
            "<1696># 4.特殊时期的患者管理",
            "<1697>## 4.1 应急预案制定",
            "<1698>### 4.1.1 具体措施"
        ]
        
        sections = self.analyzer.analyze_document_structure(test_lines)
        
        # 验证不同级别的Markdown标题
        h1_sections = [s for s in sections if s.section_type == SectionType.MARKDOWN_H1]
        h2_sections = [s for s in sections if s.section_type == SectionType.MARKDOWN_H2]
        h3_sections = [s for s in sections if s.section_type == SectionType.MARKDOWN_H3]
        
        self.assertEqual(len(h1_sections), 1)
        self.assertEqual(len(h2_sections), 1)
        self.assertEqual(len(h3_sections), 1)
    
    def test_priority_calculation(self):
        """测试优先级计算"""
        test_lines = [
            "<1696># 4.特殊时期的患者管理",
            "<1697>在重大突发公共卫生事件期间，医疗机构应当制定相应的应急预案...",
            "<1700>十二、循环肿瘤标志物检测和临床应用"
        ]
        
        sections = self.analyzer.analyze_document_structure(test_lines)
        
        # 中文序号应该有最高的语义边界分数
        chinese_section = next(s for s in sections if s.section_type == SectionType.CHINESE_MAJOR)
        markdown_section = next(s for s in sections if s.section_type == SectionType.MARKDOWN_H1)
        
        self.assertGreater(chinese_section.semantic_boundary_score, 
                          markdown_section.semantic_boundary_score)
    
    def test_table_title_association(self):
        """测试表格-标题关联"""
        test_lines = [
            "<1696># 表1 患者基本信息",
            "<1697>| 姓名 | 年龄 | 诊断 |",
            "<1698>|------|------|------|",
            "<1699>| 张三 | 45   | 乳腺癌 |",
            "<1700>",
            "<1701>十二、循环肿瘤标志物检测"
        ]
        
        sections = self.analyzer.analyze_document_structure(test_lines)
        
        # 表格行的语义边界分数应该较低（因为与标题关联）
        table_sections = [s for s in sections if s.section_type == SectionType.TABLE]
        for table_section in table_sections:
            self.assertLess(table_section.semantic_boundary_score, 0.6)

class TestEnhancedDocumentPreprocessor(unittest.TestCase):
    """增强版文档预处理器测试"""
    
    def setUp(self):
        self.processor = EnhancedDocumentPreprocessor()
    
    def test_boundary_placement_accuracy(self):
        """测试边界放置准确性"""
        test_content = """<1696># 4.特殊时期的患者管理

<1698>在重大突发公共卫生事件期间，医疗机构应当制定相应的应急预案，确保乳腺癌患者能够得到及时、有效的诊疗服务。

<1700>十二、循环肿瘤标志物检测和临床应用

<1702>循环肿瘤标志物是指在血液、淋巴液等体液中可以检测到的与肿瘤相关的分子标志物。"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            input_file = f.name
        
        try:
            output_file = input_file.replace('.md', '_processed.md')
            stats = self.processor.process_file(input_file, output_file)
            
            # 验证边界位置
            with open(output_file, 'r', encoding='utf-8') as f:
                processed_content = f.read()
            
            lines = processed_content.split('\n')
            boundary_positions = [i for i, line in enumerate(lines) 
                                if line.strip() == "[CHUNK_BOUNDARY]"]
            
            # 应该在"十二、循环肿瘤标志物检测"之前有边界
            self.assertTrue(any(
                i < len(lines) - 1 and "十二、循环肿瘤标志物检测" in lines[i + 1]
                for i in boundary_positions
            ))
            
        finally:
            # 清理临时文件
            if os.path.exists(input_file):
                os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_semantic_continuity_preservation(self):
        """测试语义连续性保护"""
        test_content = """<1696>乳腺癌的治疗方案包括：

<1697>（1）手术治疗
<1698>（2）化疗
<1699>（3）放疗

<1700>十二、循环肿瘤标志物检测"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            input_file = f.name
        
        try:
            output_file = input_file.replace('.md', '_processed.md')
            self.processor.process_file(input_file, output_file)
            
            # 验证质量
            validation = self.processor.validate_chunking_quality(output_file)
            
            # 不应该在列表中间分块
            issues = []
            for result in validation['boundary_validations']:
                issues.extend(result['issues'])
            
            self.assertNotIn("可能在列表中间分块", issues)
            
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_table_integrity_preservation(self):
        """测试表格完整性保护"""
        test_content = """<1696># 表1 患者信息

<1697>| 姓名 | 年龄 | 诊断 |
<1698>|------|------|------|
<1699>| 张三 | 45   | 乳腺癌 |
<1700>| 李四 | 52   | 乳腺癌 |

<1701>十二、循环肿瘤标志物检测"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            input_file = f.name
        
        try:
            output_file = input_file.replace('.md', '_processed.md')
            self.processor.process_file(input_file, output_file)
            
            # 验证质量
            validation = self.processor.validate_chunking_quality(output_file)
            
            # 不应该在表格中间分块
            issues = []
            for result in validation['boundary_validations']:
                issues.extend(result['issues'])
            
            self.assertNotIn("可能在表格中间分块", issues)
            
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)

class TestRealWorldScenarios(unittest.TestCase):
    """真实场景测试"""
    
    def setUp(self):
        self.processor = EnhancedDocumentPreprocessor()
    
    def test_mixed_section_types(self):
        """测试混合章节类型处理"""
        test_content = """<1696># 4.特殊时期的患者管理

<1697>## 4.1 应急预案

<1698>在重大突发公共卫生事件期间，医疗机构应当制定相应的应急预案。

<1699>1、制定应急预案
<1700>2、建立绿色通道

<1701>十二、循环肿瘤标志物检测和临床应用

<1702>### 12.1 检测原理

<1703>循环肿瘤标志物检测是一种新兴的诊断技术。"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            input_file = f.name
        
        try:
            output_file = input_file.replace('.md', '_processed.md')
            stats = self.processor.process_file(input_file, output_file)
            
            # 验证处理结果
            self.assertGreater(stats['semantic_quality_score'], 0.6)
            self.assertGreater(len(stats['boundaries']), 0)
            
            # 验证中文序号优先级
            validation = self.processor.validate_chunking_quality(output_file)
            self.assertGreater(validation['overall_quality'], 0.6)
            
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_complex_medical_document(self):
        """测试复杂医学文档处理"""
        # 模拟真实的医学文档结构
        test_content = """<1696># 4.特殊时期的患者管理

<1697>在重大突发公共卫生事件期间，医疗机构应当制定相应的应急预案，确保乳腺癌患者能够得到及时、有效的诊疗服务。应急预案应包括以下内容：

<1698>（1）建立乳腺癌患者绿色通道，优先保障急危重症患者的诊疗需求。
<1699>（2）制定分级诊疗策略，合理分流患者，避免医疗资源过度集中。
<1700>（3）加强远程医疗服务，为无法到院的患者提供在线咨询和指导。

<1701>| 风险等级 | 处理策略 | 预期效果 |
<1702>|----------|----------|----------|
<1703>| 高风险   | 立即住院 | 及时救治 |
<1704>| 中风险   | 门诊观察 | 密切监测 |
<1705>| 低风险   | 居家管理 | 定期随访 |

<1706>十二、循环肿瘤标志物检测和临床应用

<1707>循环肿瘤标志物（Circulating Tumor Markers, CTMs）是指在血液、淋巴液等体液中可以检测到的与肿瘤相关的分子标志物。这些标志物包括循环肿瘤细胞（CTCs）、循环肿瘤DNA（ctDNA）、外泌体等。

<1708>## 12.1 检测技术原理

<1709>### 12.1.1 循环肿瘤细胞检测

<1710>循环肿瘤细胞是从原发肿瘤或转移灶脱落并进入血液循环的肿瘤细胞。"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            input_file = f.name
        
        try:
            output_file = input_file.replace('.md', '_processed.md')
            stats = self.processor.process_file(input_file, output_file)
            
            # 验证处理统计
            self.assertGreater(stats['total_chunks'], 1)
            self.assertLess(stats['max_chunk_size'], 4000)  # 不应超过最大限制
            
            # 验证语义质量
            validation = self.processor.validate_chunking_quality(output_file)
            self.assertGreater(validation['overall_quality'], 0.5)
            
            # 验证边界位置合理性
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 应该在"十二、循环肿瘤标志物检测"前有边界
            self.assertIn("[CHUNK_BOUNDARY]\n<1706>十二、循环肿瘤标志物检测", content)
            
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)

class TestPerformanceAndRobustness(unittest.TestCase):
    """性能和鲁棒性测试"""
    
    def test_large_document_processing(self):
        """测试大文档处理性能"""
        # 生成大文档
        large_content = []
        for i in range(1000):
            large_content.extend([
                f"<{i*10}># 章节 {i}",
                f"<{i*10+1}>这是章节 {i} 的内容。" * 50,  # 长内容
                f"<{i*10+2}>",
                f"<{i*10+3}>{i+1}、下一个章节",
                f"<{i*10+4}>更多内容。" * 30
            ])
        
        test_content = '\n'.join(large_content)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            input_file = f.name
        
        try:
            output_file = input_file.replace('.md', '_processed.md')
            
            # 测试处理时间（应该在合理范围内）
            import time
            start_time = time.time()
            stats = self.processor.process_file(input_file, output_file)
            processing_time = time.time() - start_time
            
            # 验证处理结果
            self.assertLess(processing_time, 30)  # 应该在30秒内完成
            self.assertGreater(stats['total_chunks'], 10)  # 应该有多个分块
            
        finally:
            if os.path.exists(input_file):
                os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_edge_cases(self):
        """测试边缘情况"""
        edge_cases = [
            "",  # 空文档
            "<1>单行文档",  # 单行文档
            "\n\n\n",  # 只有空行
            "<1># 标题\n<2>\n<3># 另一个标题",  # 只有标题
        ]
        
        for i, test_content in enumerate(edge_cases):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(test_content)
                input_file = f.name
            
            try:
                output_file = input_file.replace('.md', f'_processed_{i}.md')
                
                # 应该能够处理而不崩溃
                stats = self.processor.process_file(input_file, output_file)
                self.assertIsInstance(stats, dict)
                
            except Exception as e:
                self.fail(f"边缘情况 {i} 处理失败: {e}")
            finally:
                if os.path.exists(input_file):
                    os.unlink(input_file)
                if os.path.exists(output_file):
                    os.unlink(output_file)

def run_comprehensive_tests():
    """运行全面测试套件"""
    print("开始运行全面测试套件...")
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestDocumentStructureAnalyzer,
        TestEnhancedDocumentPreprocessor,
        TestRealWorldScenarios,
        TestPerformanceAndRobustness
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出测试结果摘要
    print(f"\n=== 测试结果摘要 ===")
    print(f"运行测试数: {result.testsRun}")
    print(f"失败数: {len(result.failures)}")
    print(f"错误数: {len(result.errors)}")
    print(f"成功率: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n=== 失败的测试 ===")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n=== 错误的测试 ===")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)