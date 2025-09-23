#!/usr/bin/env python3
"""
调试表格标题分块问题的脚本
"""

from preprocess_enhanced import (
    is_table_title, 
    has_table_content_after, 
    should_start_new_chunk,
    get_chunk_char_count
)

def debug_real_document():
    """调试实际文档中的表格分块问题"""
    
    # 模拟实际文档中的情况（从"11维持治疗"开始）
    lines = [
        "11维持治疗",
        "",
        "复发转移性乳腺癌的治愈很难，需要采取\"细水长流、延年益寿\"的策略，选择最佳的一线治疗，有效患者可以考虑合理的维持治疗。联合化疗有效的患者，如果因为不良反应不能继续耐受联合化疗者，可以考虑原先联合方案中其中一个单行维持治疗，以尽量延长疾病控制时间。维持化疗的理想选择，应该是单药治疗有效、相对低毒、便于长期使用，如口服的化疗药物卡培他滨、长春瑞滨等。激素受体阳性的患者的后续治疗还可以选择内分泌治疗作为维持手段。",
        "",
        "12姑息治疗",
        "",
        "复发转移性乳腺癌的治疗，如果连续3种化疗方案无缓解，或患者ECOG体力状态评分≥3分，则不再建议化疗，可以考虑给予最佳支持治疗或参加新药临床研究。化疗方案无缓解，指未曾从以往化疗方案中获益，甚至从未获得过缓解，而不包括在化疗后获得缓解停药后再出现病情进展。",
        "",
        "复发或转移性乳腺癌常用的单药化疗方案",
        "",
        "<table><tr><td>方案</td><td>剂量</td><td>用药时间</td><td>时间及周期</td></tr><tr><td>白蛋白紫杉醇</td><td>100~150mg/m²</td><td>d1</td><td>1/7d</td></tr><tr><td>多西他赛</td><td>75mg/m²</td><td>d1</td><td>1/21d</td></tr></table>",
        "",
        "复发或转移性乳腺癌常用的单药化疗方案（续）",
        "",
        "<table><tr><td>方案</td><td>剂量</td><td>用药时间</td><td>时间及周期</td></tr><tr><td>艾立布林</td><td>1.4mg/m²</td><td>d1、d8</td><td>1/21d</td></tr></table>"
    ]
    
    print("=== 调试实际文档中的表格标题分块问题 ===\n")
    
    # 模拟到达表格标题时的chunk状态
    title_index = 8  # "复发或转移性乳腺癌常用的单药化疗方案"的索引
    title_line = lines[title_index]
    
    # 当前chunk包含从开始到标题前的所有内容
    current_chunk = lines[:title_index]
    current_size = get_chunk_char_count(current_chunk)
    max_chars = 1000
    
    print(f"1. 标题行: '{title_line}'")
    print(f"   是否识别为表格标题: {is_table_title(title_line)}")
    
    print(f"\n2. 标题后是否有表格内容:")
    print(f"   结果: {has_table_content_after(lines, title_index)}")
    
    print(f"\n3. 当前chunk大小: {current_size} 字符")
    print(f"   最大限制: {max_chars} 字符")
    print(f"   30%阈值: {max_chars * 0.3} 字符")
    print(f"   是否超过30%阈值: {current_size >= max_chars * 0.3}")
    
    # 测试是否应该在标题处分块
    should_split = should_start_new_chunk(
        title_line, 
        current_chunk, 
        max_chars, 
        all_lines=lines, 
        current_index=title_index
    )
    
    print(f"\n4. 在标题处是否应该分块: {should_split}")
    
    # 分析为什么会分块
    print(f"\n=== 详细分析 ===")
    print(f"当前chunk内容:")
    for i, line in enumerate(current_chunk):
        if line.strip():
            print(f"  {i}: {line[:50]}{'...' if len(line) > 50 else ''}")
    
    print(f"\n问题分析:")
    if current_size >= max_chars * 0.3:
        print(f"✓ chunk大小 ({current_size}) 已超过30%阈值 ({max_chars * 0.3})")
        print(f"✓ 标题被识别为表格标题: {is_table_title(title_line)}")
        print(f"✓ 标题后有表格内容: {has_table_content_after(lines, title_index)}")
        print(f"❌ 但仍然在标题处分块了，这说明逻辑有问题")
    else:
        print(f"chunk大小还未达到30%阈值，不应该分块")

if __name__ == "__main__":
    debug_real_document()