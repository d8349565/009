import requests
from urllib.parse import quote

query = "2024年中国船舶涂料销售额"
url = f"https://s.jina.ai/{quote(query)}"

headers = {
    "Accept": "application/json",
    "Authorization": "Bearer jina_501331b44d4b4d80bd7db87b79139c08MIjdpx9-Ywl5j07iIvfmsdu1vNEu",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

resp = requests.get(url, headers=headers, timeout=30)
print(resp.status_code)
data = resp.json()

for item in data.get("data", []):
    print("标题:", item.get("title"))
    print("来源:", item.get("url"))
    print("摘要:", item.get("content", "")[:200])
    print("-" * 40)