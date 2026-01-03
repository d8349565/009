"""
测试年份搜索策略
"""
from agents import RequirementAnalyzer
from datetime import datetime

def test_year_search():
    """测试对2024年数据的搜索关键词生成"""
    
    analyzer = RequirementAnalyzer(system_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # 测试需求
    requirement = "2024年中国船舶涂料销售额"
    
    print("="*60)
    print(f"测试需求: {requirement}")
    print("="*60)
    
    # 分析需求
    result = analyzer.analyze(requirement)
    
    print("\n" + "="*60)
    print("关键词分析")
    print("="*60)
    
    keywords = result.get('search_keywords', [])
    
    print(f"\n生成了 {len(keywords)} 个搜索关键词：\n")
    for i, kw in enumerate(keywords, 1):
        # 检查是否包含2024或2025
        has_2024 = '2024' in kw
        has_2025 = '2025' in kw
        
        status = ""
        if has_2024 and has_2025:
            status = "✓ [包含2024+2025]"
        elif has_2024:
            status = "✓ [包含2024]"
        elif has_2025:
            status = "✓ [包含2025]"
        else:
            status = "✗ [未包含年份]"
        
        print(f"  {i}. {kw:50s} {status}")
    
    print("\n" + "="*60)
    print("搜索覆盖度检查")
    print("="*60)
    
    has_2024_kw = any('2024' in kw for kw in keywords)
    has_2025_kw = any('2025' in kw for kw in keywords)
    
    print(f"\n✓ 包含2024关键词: {'是' if has_2024_kw else '否'}")
    print(f"✓ 包含2025关键词: {'是' if has_2025_kw else '否'} (用于捕获次年发布的报告)")
    
    if has_2024_kw and has_2025_kw:
        print("\n✓✓ 搜索策略完善！能够覆盖：")
        print("   - 2024年直接数据")
        print("   - 2025年发布的2024年报告/榜单")
    elif has_2024_kw:
        print("\n⚠️ 搜索策略不完整：只能找到标题包含2024的文章")
        print("   建议：增加2025年的关键词以覆盖次年发布的报告")
    else:
        print("\n✗✗ 搜索策略有问题：缺少2024年关键词")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_year_search()
