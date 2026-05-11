import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9'
}
res = requests.get('https://search.naver.com/search.naver',
    params={'where':'news','query':'삼성전자 주식','sort':1},
    headers=headers)
res.encoding = 'utf-8'
soup = BeautifulSoup(res.text, 'html.parser')

# Check data-sds-comp links
inf = soup.select_one('ul._infinite_list')
print('inf found:', bool(inf))

# Get all a tags with substantial text linking to external pages
results = []
if inf:
    for a in inf.find_all('a', href=True):
        txt = a.get_text(strip=True)
        href = a['href']
        if len(txt) > 15 and href.startswith('http') and 'naver' not in href:
            results.append((txt[:100], href[:80]))

print('Found:', len(results))
for r in results[:10]:
    print(r[0])
    print(r[1])
    print()
