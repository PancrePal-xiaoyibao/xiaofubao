#!/usr/bin/env python3
"""
验证章节分割修复效果的脚本
"""

def check_chunk_boundaries(file_path):
    """检查文档中的chunk边界是否正确分割章节"""
    print(f"检查文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    issues = []
    for i, line in enumerate(lines):
        if '[CHUNK_BOUNDARY]' in line:
            # 检查边界后的几行
            for j in range(1, min(5, len(lines) - i)):
                next_line = lines[i + j].strip()
                if next_line.startswith('<') and '># ' in next_line:
                    # 提取章节标题
                    title_part = next_line.split('># ', 1)[1] if '># ' in next_line else ''
                    # 检查是否是中文章节标题
                    if any(num in title_part for num in ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、', '十一、', '十二、']):
                        # 检查前一个chunk是否包含相关内容
                        prev_content = []
                        for k in range(max(0, i-10), i):
                            if lines[k].strip():
                                prev_content.append(lines[k].strip())
                        
                        print(f"发现章节标题在边界后: 第{i+j+1}行")
                        print(f"标题: {title_part}")
                        print(f"前面内容: {prev_content[-3:] if prev_content else '无'}")
                        print("---")
                    break
    
    return issues

def main():
    """主函数"""
    enhanced_file = "To_be_processed/乳腺癌诊疗指南2025_enhanced.md"
    
    print("=== 验证章节分割修复效果 ===\n")
    
    try:
        check_chunk_boundaries(enhanced_file)
        print("\n验证完成！")
        
        # 统计一些基本信息
        with open(enhanced_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunk_count = content.count('[CHUNK_BOUNDARY]')
        chinese_sections = len([line for line in content.split('\n') 
                              if '># ' in line and any(num in line for num in ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、', '十一、', '十二、'])])
        
        print(f"\n统计信息:")
        print(f"- 总chunk数: {chunk_count + 1}")
        print(f"- 中文章节标题数: {chinese_sections}")
        
    except Exception as e:
        print(f"验证过程中出错: {e}")

if __name__ == "__main__":
    main()