#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试分块结果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocess_enhanced import create_chunks

def debug_chunking():
    """调试分块结果"""
    
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
    
    print("原始内容:")
    for i, line in enumerate(test_content):
        print(f"{i:2d}: {line}")
    
    print("\n" + "="*60)
    
    # 创建分块
    chunks = create_chunks(test_content, max_chars_per_chunk=1000, min_chars_per_chunk=200)
    
    print(f"生成了 {len(chunks)} 个chunks:")
    
    for i, chunk in enumerate(chunks):
        chunk_text = '\n'.join(chunk)
        print(f"\nChunk {i+1} ({len(chunk)} 行, {len(chunk_text)} 字符):")
        print("-" * 40)
        for j, line in enumerate(chunk):
            print(f"  {j:2d}: {line}")
        
        # 检查是否包含标题和相关内容
        chunk_text = '\n'.join(chunk)
        has_title = "乳腺癌内分泌药物用法及用量：" in chunk_text
        has_drug1 = "（1）枸橡酸他莫昔芬" in chunk_text
        
        if has_title:
            print(f"  >>> 包含标题: {has_title}")
        if has_drug1:
            print(f"  >>> 包含第一个药物: {has_drug1}")

if __name__ == "__main__":
    debug_chunking()