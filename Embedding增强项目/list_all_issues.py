#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
问题列表提取器 - 从质量报告中提取并格式化显示所有问题
用于详细查看文档分块过程中发现的所有问题

功能：
- 从quality_report.json中提取所有问题
- 按严重程度分类显示
- 提供问题统计和分析
- 生成可读性强的问题列表

作者: RAG预处理专家
版本: 1.0
"""

import json
import argparse
from collections import Counter
from typing import List, Dict

def load_quality_report(file_path: str) -> Dict:
    """
    加载质量报告JSON文件
    
    Args:
        file_path (str): 质量报告文件路径
        
    Returns:
        Dict: 质量报告数据
        
    Raises:
        Exception: 文件加载失败时抛出异常
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载报告失败: {e}")
        return {}

def categorize_issues_by_severity(issues: List[Dict]) -> Dict[str, List[Dict]]:
    """
    按严重程度分类问题
    
    Args:
        issues (List[Dict]): 问题列表
        
    Returns:
        Dict[str, List[Dict]]: 按严重程度分类的问题字典
    """
    categorized = {
        'high': [],
        'medium': [],
        'low': []
    }
    
    for issue in issues:
        severity = issue.get('severity', 'low')
        if severity in categorized:
            categorized[severity].append(issue)
    
    return categorized

def categorize_issues_by_type(issues: List[Dict]) -> Dict[str, List[Dict]]:
    """
    按问题类型分类问题
    
    Args:
        issues (List[Dict]): 问题列表
        
    Returns:
        Dict[str, List[Dict]]: 按问题类型分类的问题字典
    """
    categorized = {}
    
    for issue in issues:
        issue_type = issue.get('type', 'unknown')
        if issue_type not in categorized:
            categorized[issue_type] = []
        categorized[issue_type].append(issue)
    
    return categorized

def get_severity_icon(severity: str) -> str:
    """
    获取严重程度对应的图标
    
    Args:
        severity (str): 严重程度
        
    Returns:
        str: 对应的图标
    """
    icons = {
        'high': '🔴',
        'medium': '🟡', 
        'low': '🟢'
    }
    return icons.get(severity, '⚪')

def get_type_description(issue_type: str) -> str:
    """
    获取问题类型的中文描述
    
    Args:
        issue_type (str): 问题类型
        
    Returns:
        str: 中文描述
    """
    descriptions = {
        'too_small': '分块过小',
        'too_large': '分块过大',
        'empty_chunk': '空分块',
        'poor_boundary': '边界质量差'
    }
    return descriptions.get(issue_type, issue_type)

def print_issues_summary(issues: List[Dict]):
    """
    打印问题总结
    
    Args:
        issues (List[Dict]): 问题列表
    """
    print("📊 问题统计总览")
    print("=" * 50)
    
    # 按严重程度统计
    severity_counts = Counter([issue.get('severity', 'low') for issue in issues])
    print(f"🔴 严重问题: {severity_counts.get('high', 0)} 个")
    print(f"🟡 中等问题: {severity_counts.get('medium', 0)} 个")
    print(f"🟢 轻微问题: {severity_counts.get('low', 0)} 个")
    print(f"📝 总计: {len(issues)} 个问题")
    
    # 按类型统计
    type_counts = Counter([issue.get('type', 'unknown') for issue in issues])
    print(f"\n📋 问题类型分布:")
    for issue_type, count in type_counts.most_common():
        type_desc = get_type_description(issue_type)
        print(f"   • {type_desc}: {count} 个")

def print_issues_by_severity(issues: List[Dict]):
    """
    按严重程度打印问题详情
    
    Args:
        issues (List[Dict]): 问题列表
    """
    categorized = categorize_issues_by_severity(issues)
    
    for severity in ['high', 'medium', 'low']:
        severity_issues = categorized[severity]
        if not severity_issues:
            continue
            
        severity_names = {
            'high': '严重问题',
            'medium': '中等问题', 
            'low': '轻微问题'
        }
        
        icon = get_severity_icon(severity)
        print(f"\n{icon} {severity_names[severity]} ({len(severity_issues)} 个)")
        print("-" * 40)
        
        for i, issue in enumerate(severity_issues, 1):
            chunk_index = issue.get('chunk_index', 0)
            description = issue.get('description', '未知问题')
            preview = issue.get('chunk_preview', '')
            
            print(f"{i:3d}. 分块 {chunk_index + 1}: {description}")
            if preview:
                # 限制预览长度
                preview_text = preview[:60] + "..." if len(preview) > 60 else preview
                print(f"     预览: {preview_text}")

def print_issues_by_type(issues: List[Dict]):
    """
    按问题类型打印问题详情
    
    Args:
        issues (List[Dict]): 问题列表
    """
    categorized = categorize_issues_by_type(issues)
    
    print(f"\n📋 按问题类型分类")
    print("=" * 50)
    
    for issue_type, type_issues in categorized.items():
        type_desc = get_type_description(issue_type)
        print(f"\n🔸 {type_desc} ({len(type_issues)} 个)")
        print("-" * 30)
        
        for i, issue in enumerate(type_issues, 1):
            chunk_index = issue.get('chunk_index', 0)
            severity = issue.get('severity', 'low')
            icon = get_severity_icon(severity)
            preview = issue.get('chunk_preview', '')
            
            print(f"{i:3d}. {icon} 分块 {chunk_index + 1}")
            if preview:
                preview_text = preview[:50] + "..." if len(preview) > 50 else preview
                print(f"     预览: {preview_text}")

def print_chunk_range_analysis(issues: List[Dict]):
    """
    打印分块范围分析
    
    Args:
        issues (List[Dict]): 问题列表
    """
    chunk_indices = [issue.get('chunk_index', 0) for issue in issues]
    
    if not chunk_indices:
        return
    
    print(f"\n📍 问题分块分布分析")
    print("=" * 50)
    print(f"问题分块范围: 第 {min(chunk_indices) + 1} - {max(chunk_indices) + 1} 块")
    
    # 分析问题集中的区域
    chunk_counts = Counter(chunk_indices)
    most_problematic = chunk_counts.most_common(5)
    
    print(f"\n🎯 问题最多的分块:")
    for chunk_index, count in most_problematic:
        print(f"   分块 {chunk_index + 1}: {count} 个问题")

def main():
    """
    主函数 - 处理命令行参数并执行问题列表提取
    
    Returns:
        int: 程序退出码，0表示成功，1表示失败
    """
    parser = argparse.ArgumentParser(description='问题列表提取器')
    parser.add_argument('--report', '-r', default='quality_report.json', 
                       help='质量报告JSON文件路径')
    parser.add_argument('--by-severity', '-s', action='store_true',
                       help='按严重程度分类显示')
    parser.add_argument('--by-type', '-t', action='store_true',
                       help='按问题类型分类显示')
    parser.add_argument('--summary-only', action='store_true',
                       help='仅显示统计总览')
    parser.add_argument('--output', '-o', help='输出到文件')
    
    args = parser.parse_args()
    
    # 加载质量报告
    report = load_quality_report(args.report)
    if not report:
        return 1
    
    issues = report.get('issues', [])
    if not issues:
        print("✅ 未发现任何问题！")
        return 0
    
    # 重定向输出到文件（如果指定）
    output_file = None
    if args.output:
        output_file = open(args.output, 'w', encoding='utf-8')
        import sys
        sys.stdout = output_file
    
    try:
        print("🔍 乳腺癌诊疗指南2025 - 详细问题列表")
        print("=" * 60)
        
        # 显示统计总览
        print_issues_summary(issues)
        
        if not args.summary_only:
            # 显示分块分布分析
            print_chunk_range_analysis(issues)
            
            # 按用户选择的方式显示详细问题
            if args.by_type:
                print_issues_by_type(issues)
            elif args.by_severity:
                print_issues_by_severity(issues)
            else:
                # 默认按严重程度显示
                print_issues_by_severity(issues)
        
        print(f"\n{'=' * 60}")
        print("✅ 问题列表生成完成")
        
    finally:
        if output_file:
            output_file.close()
            import sys
            sys.stdout = sys.__stdout__
            print(f"问题列表已保存至: {args.output}")
    
    return 0

if __name__ == "__main__":
    exit(main())