"""
测试网页内容获取功能
"""
from search_engine import SearchEngine

def test_fetch_content():
    """测试从指定URL获取内容"""
    
    # 初始化搜索引擎
    search_engine = SearchEngine(engine_type='searxng')
    
    # 测试URL
    test_url = "https://www.sohu.com/a/940360459_425738"
    
    print("="*60)
    print(f"测试URL: {test_url}")
    print("="*60)
    
    # 获取网页内容
    print("\n正在获取网页内容...")
    content = search_engine.fetch_content(test_url)
    
    if content:
        print(f"\n✓ 成功获取网页内容")
        print(f"  内容长度: {len(content)} 字符")
        print(f"\n--- 内容前1000字符预览 ---")
        print(content[:1000])
        print("\n--- 内容后500字符预览 ---")
        print(content[-500:])
        
        # 查找关键数据
        print("\n" + "="*60)
        print("关键词检测")
        print("="*60)
        
        keywords = [
            "115亿", "115亿元", 
            "船舶涂料", "销售额", "市场规模",
            "2024", "2023", "2022", "2021", "2020",
            "涂界", "中远佐敦", "佐敦"
        ]
        
        found_keywords = []
        for keyword in keywords:
            if keyword in content:
                # 找到关键词的上下文
                idx = content.find(keyword)
                context_start = max(0, idx - 50)
                context_end = min(len(content), idx + len(keyword) + 100)
                context = content[context_start:context_end]
                found_keywords.append({
                    'keyword': keyword,
                    'context': context
                })
        
        if found_keywords:
            print(f"\n✓ 找到 {len(found_keywords)} 个关键词:")
            for item in found_keywords:
                print(f"\n  [{item['keyword']}]")
                print(f"  上下文: ...{item['context']}...")
        else:
            print("\n✗ 未找到任何关键词")
        
    else:
        print("\n✗ 获取网页内容失败")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_fetch_content()
