"""
测试改进后的多样化关键词生成
"""
from agents import RequirementAnalyzer
from datetime import datetime

def test_keyword_diversity():
    """测试关键词的多样性和覆盖度"""
    
    analyzer = RequirementAnalyzer(system_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    requirement = "2024年中国船舶涂料销售额"
    
    print("="*70)
    print(f"测试需求: {requirement}")
    print("="*70)
    
    result = analyzer.analyze(requirement)
    
    keywords = result.get('search_keywords', [])
    
    print("\n" + "="*70)
    print(f"生成了 {len(keywords)} 个搜索关键词")
    print("="*70)
    
    # 分类检查
    categories = {
        '榜单/排名': ['榜单', '排行', '品牌', '十大', 'top'],
        '报告/研究': ['报告', '研究', '分析', '白皮书'],
        '销售/数据': ['销售额', '营收', '数据', '业绩', '市场规模'],
        '地域限定': ['中国', '国内', '全国'],  # 新增地域检查
        '2024年份': ['2024'],
        '2025年份': ['2025'],
    }
    
    print("\n关键词列表:")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i:2d}. {kw}")
    
    print("\n" + "="*70)
    print("关键词覆盖度分析")
    print("="*70)
    
    for category, terms in categories.items():
        matches = []
        for kw in keywords:
            kw_lower = kw.lower()
            if any(term in kw_lower for term in terms):
                matches.append(kw)
        
        status = "✅" if matches else "❌"
        print(f"\n{status} [{category}] 覆盖: {len(matches)}/{len(keywords)}")
        if matches:
            for m in matches[:3]:  # 只显示前3个
                print(f"     - {m}")
    
    # 检查目标文章可能的匹配
    print("\n" + "="*70)
    print("目标文章匹配度分析")
    print("="*70)
    
    target_title = "【聚焦】2025中国十大船舶涂料品牌榜单揭晓：垄断全国93%的市场份额"
    target_keywords = ['2025', '中国', '船舶涂料', '榜单', '品牌', '十大']  # 增加"中国"
    
    print(f"\n目标文章: {target_title}")
    print(f"目标关键词: {', '.join(target_keywords)}")
    
    # 检查地域限定
    has_region = any('中国' in kw or '国内' in kw for kw in keywords)
    print(f"\n✓ 包含地域限定（中国/国内）: {'是 ✅' if has_region else '否 ❌（会匹配到全球数据）'}")
    
    best_matches = []
    for kw in keywords:
        match_count = sum(1 for tk in target_keywords if tk in kw)
        if match_count >= 2:  # 至少匹配2个目标关键词
            best_matches.append((kw, match_count))
    
    best_matches.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n可能匹配目标文章的关键词 ({len(best_matches)} 个):")
    if best_matches:
        for kw, count in best_matches[:5]:
            print(f"  ✅ {kw:45s} (匹配 {count} 个目标关键词)")
        print(f"\n✅✅ 搜索策略改进成功！能够找到榜单类文章")
    else:
        print("  ❌ 无法有效匹配目标文章")
        print(f"  建议：需要包含'2025 船舶涂料 榜单'或'2025 十大品牌'类关键词")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    test_keyword_diversity()
