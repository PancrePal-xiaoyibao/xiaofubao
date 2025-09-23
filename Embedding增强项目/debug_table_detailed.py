#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocess_enhanced import (
    should_start_new_chunk, 
    is_table_title, 
    has_table_content_after,
    get_chunk_boundary_priority,
    get_chunk_char_count
)

def debug_table_title_chunking():
    """详细调试表格标题分块逻辑"""
    
    # 模拟实际文档内容
    lines = [
        "复发转移性乳腺癌的治疗，如果连续3种化疗方案无缓解，或患者ECOG体力状态评分≥3分，则不再建议化疗，可以考虑给予最佳支持治疗或参加新药临床研究。化疗方案无缓解，指未曾从以往化疗方案中获益，甚至从未获得过缓解，而不包括在化疗后获得缓解停药后再出现病情进展。",
        "",
        "复发或转移性乳腺癌常用的单药化疗方案",
        "",
        "<table><tr><td>方案</td><td>剂量</td><td>用药时间</td><td>时间及周期</td></tr><tr><td>白蛋白紫杉醇</td><td>100~150mg/m²</td><td>d1</td><td>1/7d</td></tr></table>"
    ]
    
    # 模拟当前chunk状态（包含前面的内容）
    current_chunk_lines = [
        "11维持治疗",
        "",
        "复发转移性乳腺癌的治愈很难，需要采取\"细水长流、延年益寿\"的策略，选择最佳的一线治疗，有效患者可以考虑合理的维持治疗。联合化疗有效的患者，如果因为不良反应不能继续耐受联合化疗者，可以考虑原先联合方案中其中一个单行维持治疗，以尽量延长疾病控制时间。维持化疗的理想选择，应该是单药治疗有效、相对低毒、便于长期使用，如口服的化疗药物卡培他滨、长春瑞滨等。激素受体阳性的患者的后续治疗还可以选择内分泌治疗作为维持手段。",
        "",
        "12姑息治疗",
        "",
        "复发转移性乳腺癌的治疗，如果连续3种化疗方案无缓解，或患者ECOG体力状态评分≥3分，则不再建议化疗，可以考虑给予最佳支持治疗或参加新药临床研究。化疗方案无缓解，指未曾从以往化疗方案中获益，甚至从未获得过缓解，而不包括在化疗后获得缓解停药后再出现病情进展。"
    ]
    
    # 测试表格标题行
    table_title_line = "复发或转移性乳腺癌常用的单药化疗方案"
    table_title_index = 2
    max_chars_per_chunk = 1000
    
    print("=== 表格标题分块详细调试 ===")
    print(f"表格标题: {table_title_line}")
    print(f"当前chunk大小: {get_chunk_char_count(current_chunk_lines)} 字符")
    print(f"30%阈值: {max_chars_per_chunk * 0.3} 字符")
    print()
    
    # 步骤1：检查30%阈值
    current_size = get_chunk_char_count(current_chunk_lines)
    threshold_30 = max_chars_per_chunk * 0.3
    print(f"步骤1 - 30%阈值检查:")
    print(f"  当前大小: {current_size}")
    print(f"  30%阈值: {threshold_30}")
    print(f"  是否超过30%: {current_size >= threshold_30}")
    
    if current_size < threshold_30:
        print("  结果: 不分块（未达到30%阈值）")
        return
    
    print()
    
    # 步骤2：表格标题检查
    print(f"步骤2 - 表格标题检查:")
    is_title = is_table_title(table_title_line)
    print(f"  是否为表格标题: {is_title}")
    
    if is_title:
        has_content = has_table_content_after(lines, table_title_index)
        print(f"  后续是否有表格内容: {has_content}")
        
        if has_content:
            print("  结果: 不分块（表格标题与内容应保持一致）")
            return
    
    print()
    
    # 步骤3：边界优先级检查
    print(f"步骤3 - 边界优先级检查:")
    priority = get_chunk_boundary_priority(table_title_line)
    print(f"  边界优先级: {priority}")
    
    if priority == 0:
        print("  结果: 不分块（非边界行）")
        return
    
    print()
    
    # 最终决策
    should_split = should_start_new_chunk(
        table_title_line, 
        current_chunk_lines, 
        max_chars_per_chunk,
        lines,
        table_title_index
    )
    
    print(f"最终决策: {'分块' if should_split else '不分块'}")
    
    # 如果仍然分块，说明有其他逻辑覆盖了我们的修复
    if should_split:
        print("\n⚠️  警告: 表格标题仍然被分块！")
        print("可能的原因:")
        print("1. 表格标题检查逻辑没有正确执行")
        print("2. 其他条件覆盖了表格标题检查")
        print("3. 边界优先级检查在表格标题检查之后执行")
    else:
        print("\n✅ 修复生效: 表格标题不会被分块")

if __name__ == "__main__":
    debug_table_title_chunking()