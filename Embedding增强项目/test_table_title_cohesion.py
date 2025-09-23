#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
表格标题与内容关联性测试套件

测试标题+冒号与后续表格内容保持在同一chunk中的功能。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocess_enhanced import (
    is_title_with_colon,
    is_table_title,
    is_related_to_title,
    has_related_content_after_title,
    has_table_content_after,
    should_start_new_chunk,
    create_chunks,
    get_chunk_char_count
)

def test_is_title_with_colon():
    """测试标题+冒号识别功能"""
    print("测试标题+冒号识别功能...")
    
    # 正面测试用例
    positive_cases = [
        "乳腺癌内分泌药物用法及用量：",
        "治疗方案：",
        "诊断标准:",
        "主要症状：",
        "用药指导：",
    ]
    
    for case in positive_cases:
        result = is_title_with_colon(case)
        assert result, f"应该识别为标题+冒号: {case}"
        print(f"✓ 正确识别: {case}")
    
    # 负面测试用例
    negative_cases = [
        "这是普通文本",
        "12:30",  # 时间格式
        "3：",    # 纯数字+冒号
        "",       # 空行
        "（1）第一项内容",
        "## 标题",
    ]
    
    for case in negative_cases:
        result = is_title_with_colon(case)
        assert not result, f"不应该识别为标题+冒号: {case}"
        print(f"✓ 正确排除: {case}")
    
    print("标题+冒号识别功能测试通过！\n")

def test_is_table_title():
    """测试表格标题识别功能（包括冒号和非冒号格式）"""
    print("测试表格标题识别功能...")
    
    # 正面测试用例
    positive_cases = [
        # 冒号结尾的标题
        "乳腺癌内分泌药物用法及用量：",
        "治疗方案：",
        "诊断标准:",
        "用药指导：",
        # 非冒号的表格标题
        "复发或转移性乳腺癌常用的单药化疗方案",
        "乳腺癌脑转移局部治疗推荐",
        "血小板生成素剂量调整",
        "手术适应症评估",
        "药物剂量标准",
        "诊断检查方案",
        "监测指标评估",
    ]
    
    for case in positive_cases:
        result = is_table_title(case)
        assert result, f"应该识别为表格标题: {case}"
        print(f"✓ 正确识别: {case}")
    
    # 负面测试用例
    negative_cases = [
        "这是普通文本内容，不包含表格相关关键词",
        "12:30",  # 时间格式
        "患者的病情稳定，无明显不适症状。",  # 长文本
        "",       # 空行
        "（1）第一项内容",
        "## 标题",
        "正常的段落内容，描述了患者的具体情况和治疗过程。",  # 包含句号的长文本
    ]
    
    for case in negative_cases:
        result = is_table_title(case)
        assert not result, f"不应该识别为表格标题: {case}"
        print(f"✓ 正确排除: {case}")
    
    print("表格标题识别功能测试通过！\n")

def test_is_related_to_title():
    """测试相关内容识别功能"""
    print("测试相关内容识别功能...")
    
    # 正面测试用例
    positive_cases = [
        "（1）枸橡酸他莫昔芬：10mg，2次/d",
        "(2) 芳香化酶抑制剂",
        "1. 手术治疗",
        "2、化疗方案",
        "- 第一项",
        "* 第二项",
        "+ 第三项",
        "a. 选项A",
        "A) 选项A",
    ]
    
    for case in positive_cases:
        result = is_related_to_title(case)
        assert result, f"应该识别为相关内容: {case}"
        print(f"✓ 正确识别: {case}")
    
    # 负面测试用例
    negative_cases = [
        "这是普通文本",
        "乳腺癌内分泌药物用法及用量：",
        "",
        "## 标题",
        "正常的段落内容",
    ]
    
    for case in negative_cases:
        result = is_related_to_title(case)
        assert not result, f"不应该识别为相关内容: {case}"
        print(f"✓ 正确排除: {case}")
    
    print("相关内容识别功能测试通过！\n")

def test_has_related_content_after_title():
    """测试标题后相关内容检测功能"""
    print("测试标题后相关内容检测功能...")
    
    # 测试用例1：标题后有相关内容
    lines1 = [
        "乳腺癌内分泌药物用法及用量：",
        "",
        "（1）枸橡酸他莫昔芬：10mg，2次/d",
        "（2）芳香化酶抑制剂：1mg，1次/d",
    ]
    
    result1 = has_related_content_after_title(lines1, 0)
    assert result1, "应该检测到标题后有相关内容"
    print("✓ 正确检测到标题后的相关内容")
    
    # 测试用例2：标题后没有相关内容
    lines2 = [
        "乳腺癌内分泌药物用法及用量：",
        "",
        "这是普通的段落内容。",
        "没有编号列表。",
    ]
    
    result2 = has_related_content_after_title(lines2, 0)
    assert not result2, "不应该检测到相关内容"
    print("✓ 正确判断标题后无相关内容")
    
    # 测试用例3：标题后紧跟其他标题
    lines3 = [
        "第一个标题：",
        "## 第二个标题",
        "普通内容",
    ]
    
    result3 = has_related_content_after_title(lines3, 0)
    assert not result3, "遇到其他标题应该停止搜索"
    print("✓ 正确处理标题后紧跟其他标题的情况")
    
    print("标题后相关内容检测功能测试通过！\n")

def test_has_table_content_after():
    """测试表格内容检测功能"""
    print("测试表格内容检测功能...")
    
    # 测试用例1：标题后有表格内容
    lines1 = [
        "复发或转移性乳腺癌常用的单药化疗方案",
        "",
        "<table>",
        "<tr><th>药物</th><th>剂量</th></tr>",
        "<tr><td>多西他赛</td><td>75mg/m²</td></tr>",
        "</table>",
    ]
    
    result1 = has_table_content_after(lines1, 0)
    assert result1, "应该检测到标题后有表格内容"
    print("✓ 正确检测到标题后的表格内容")
    
    # 测试用例2：标题后有列表内容
    lines2 = [
        "治疗方案推荐",
        "",
        "（1）一线治疗方案",
        "（2）二线治疗方案",
    ]
    
    result2 = has_table_content_after(lines2, 0)
    assert result2, "应该检测到标题后有列表内容"
    print("✓ 正确检测到标题后的列表内容")
    
    # 测试用例3：标题后没有相关内容
    lines3 = [
        "药物剂量调整",
        "",
        "这是普通的段落内容。",
        "没有表格或列表。",
    ]
    
    result3 = has_table_content_after(lines3, 0)
    assert not result3, "不应该检测到相关内容"
    print("✓ 正确判断标题后无表格内容")
    
    # 测试用例4：标题后紧跟其他标题
    lines4 = [
        "第一个表格标题",
        "## 第二个标题",
        "普通内容",
    ]
    
    result4 = has_table_content_after(lines4, 0)
    assert not result4, "遇到其他标题应该停止搜索"
    print("✓ 正确处理标题后紧跟其他标题的情况")
    
    print("表格内容检测功能测试通过！\n")

def test_title_content_cohesion_in_chunking():
    """测试标题与内容在分块中的关联性"""
    print("测试标题与内容在分块中的关联性...")
    
    # 构造测试文档
    test_content = [
        "前面的内容" * 100,  # 确保有足够的内容
        "",
        "乳腺癌内分泌药物用法及用量：",
        "",
        "（1）枸橡酸他莫昔芬：10mg，2次/d（或20mg，1次/d），口服。",
        "（2）芳香化酶抑制剂（AI）阿那曲唑：1mg，1次/d，口服。",
        "（3）氟维司群：500mg，肌内注射，每4周注射1次。",
        "（4）CDK4/6抑制剂阿贝西利，150mg，口服，2次/d。",
        "",
        "后续的其他内容" * 50,
    ]
    
    # 创建分块
    chunks = create_chunks(test_content, max_chars_per_chunk=1000, min_chars_per_chunk=200)
    
    # 查找包含标题的chunk
    title_chunk_index = -1
    for i, chunk in enumerate(chunks):
        chunk_text = '\n'.join(chunk)
        if "乳腺癌内分泌药物用法及用量：" in chunk_text:
            title_chunk_index = i
            break
    
    assert title_chunk_index != -1, "应该找到包含标题的chunk"
    
    # 检查标题和相关内容是否在同一个chunk中
    title_chunk_text = '\n'.join(chunks[title_chunk_index])
    
    # 验证标题和至少一个药物项目在同一chunk中
    assert "乳腺癌内分泌药物用法及用量：" in title_chunk_text, "标题应该在chunk中"
    assert "（1）枸橡酸他莫昔芬" in title_chunk_text, "第一个药物项目应该与标题在同一chunk中"
    
    print("✓ 标题与相关内容成功保持在同一chunk中")
    print(f"✓ 标题chunk包含 {len(chunks[title_chunk_index])} 行内容")
    
    print("标题与内容在分块中的关联性测试通过！\n")

def test_multiple_title_scenarios():
    """测试多种标题场景"""
    print("测试多种标题场景...")
    
    # 测试用例：多个标题+列表的情况
    test_content = [
        "文档开始内容" * 50,
        "",
        "## 主要治疗方案：",
        "",
        "### 一线治疗：",
        "（1）标准方案：手术+化疗",
        "（2）替代方案：放疗+靶向治疗",
        "",
        "### 二线治疗：",
        "（1）挽救治疗方案",
        "（2）姑息治疗方案",
        "",
        "药物用法及用量：",
        "1. 阿霉素：50mg/m²",
        "2. 环磷酰胺：600mg/m²",
        "3. 紫杉醇：175mg/m²",
        "",
        "注意事项：",
        "- 定期监测血常规",
        "- 注意肝肾功能",
        "- 观察不良反应",
        "",
        "文档结束内容" * 30,
    ]
    
    # 创建分块
    chunks = create_chunks(test_content, max_chars_per_chunk=800, min_chars_per_chunk=200)
    
    # 验证各个标题与其内容的关联性
    scenarios_to_check = [
        ("一线治疗：", "（1）标准方案"),
        ("二线治疗：", "（1）挽救治疗"),
        ("药物用法及用量：", "1. 阿霉素"),
        ("注意事项：", "- 定期监测"),
    ]
    
    for title, content in scenarios_to_check:
        title_found = False
        content_found = False
        same_chunk = False
        
        for chunk in chunks:
            chunk_text = '\n'.join(chunk)
            if title in chunk_text:
                title_found = True
                if content in chunk_text:
                    content_found = True
                    same_chunk = True
                    break
        
        assert title_found, f"应该找到标题: {title}"
        assert content_found, f"应该找到内容: {content}"
        assert same_chunk, f"标题和内容应该在同一chunk中: {title} <-> {content}"
        
        print(f"✓ 验证成功: {title} 与 {content} 在同一chunk中")
    
    print("多种标题场景测试通过！\n")

def test_edge_cases():
    """测试边界情况"""
    print("测试边界情况...")
    
    # 测试用例1：标题后没有相关内容
    test_content1 = [
        "前面内容" * 50,
        "这是一个标题：",
        "但是后面没有列表内容，只是普通段落。",
        "这里也是普通内容。",
        "后面内容" * 30,
    ]
    
    chunks1 = create_chunks(test_content1, max_chars_per_chunk=600, min_chars_per_chunk=200)
    print(f"✓ 处理无相关内容的标题，生成 {len(chunks1)} 个chunks")
    
    # 测试用例2：空标题
    test_content2 = [
        "前面内容" * 50,
        "：",  # 只有冒号
        "后面内容" * 50,
    ]
    
    chunks2 = create_chunks(test_content2, max_chars_per_chunk=600, min_chars_per_chunk=200)
    print(f"✓ 处理空标题情况，生成 {len(chunks2)} 个chunks")
    
    # 测试用例3：超长列表
    long_list = ["前面内容" * 30]
    long_list.append("超长药物列表：")
    for i in range(1, 21):  # 20个药物项目
        long_list.append(f"（{i}）药物{i}：用法用量详细说明" * 10)
    long_list.extend(["后面内容" * 30])
    
    chunks3 = create_chunks(long_list, max_chars_per_chunk=1000, min_chars_per_chunk=200)
    print(f"✓ 处理超长列表，生成 {len(chunks3)} 个chunks")
    
    # 验证标题仍然与部分内容在一起
    title_chunk_found = False
    for chunk in chunks3:
        chunk_text = '\n'.join(chunk)
        if "超长药物列表：" in chunk_text and "（1）药物1" in chunk_text:
            title_chunk_found = True
            break
    
    assert title_chunk_found, "即使是超长列表，标题也应该与部分内容在一起"
    print("✓ 超长列表中标题与内容关联性保持正确")
    
    print("边界情况测试通过！\n")

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("表格标题与内容关联性测试套件")
    print("=" * 60)
    
    tests = [
        test_is_title_with_colon,
        test_is_table_title,
        test_is_related_to_title,
        test_has_related_content_after_title,
        test_has_table_content_after,
        test_title_content_cohesion_in_chunking,
        test_multiple_title_scenarios,
        test_edge_cases,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ 测试失败: {test_func.__name__}")
            print(f"错误信息: {str(e)}")
            failed += 1
    
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print(f"成功率: {passed / (passed + failed) * 100:.1f}%")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)