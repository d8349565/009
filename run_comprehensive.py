#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行综合报告生成功能
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from main import ResearchAgentSystem

if __name__ == '__main__':
    system = ResearchAgentSystem()
    requirement = '2025年中国汽车产销分析与2026年产销预测，尽可能的使用数据对比和表格'
    print(f"用户需求: {requirement}\n")
    system.comprehensive_report_mode(user_input=requirement)
