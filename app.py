import streamlit as st
import requests
from lxml import html
import re
from urllib.parse import quote

# 페이지 설정
st.set_page_config(page_title="도서관 통합 검색", page_icon="📚")

# 도서관 데이터
libraries = [
    {
        "name": "성남시 전자도서관",
        "url": "https://vodbook.snlib.go.kr/elibrary-front/search/searchList.ink",
        "params": {"schClst": "ctts,autr", "schDvsn": "001"},
        "key_param": "schTxt",
        "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()',
        "encoding": "utf-8"
    },
    {
        "name": "경기대학교",
        "url": "https://ebook.kyonggi.ac.kr/elibrary-front/search/searchList.ink",
        "params": {"schClst": "ctts,autr", "schDvsn": "001"},
        "key_param": "schTxt",
        "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()',
        "encoding": "utf-8"
    },
    {
        "name": "용인시 전자책도서관",
        "url": "https://ebook.yongin.go.kr/elibrary-front/search/searchList.ink",
        "params": {"schClst": "ctts,autr", "schDvsn": "001"},
        "key_param": "schTxt",
        "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()',
        "encoding": "utf-8"
    },
    {
        "name": "수원시 전자도서관",
        "url": "https://ebook.suwonlib.go.kr/elibrary-front/search/searchList.ink",
        "params": {"schClst": "ctts,autr", "schDvsn": "001"},
        "key_param": "schTxt",
        "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()',
        "encoding": "utf-8"
    },
    {
        "name": "고양시 도서관센터",
        "url": "https://ebook.goyanglib.or.kr/elibrary-front/search/searchList.ink",
        "params": {"schClst": "ctts,autr", "schDvsn": "001"},
        "key_param": "schTxt",
        "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()',
        "encoding": "utf-8"
    },
    {
        "name": "강남구 전자도서관",
        "url": "https://ebook.gangnam.go.kr/elibbook/book_info.asp",
        "params": {"search": "title"},
        "key_param": "strSearch",
        "xpath": '//*[@id="container"]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/strong/text()',
        "encoding": "euc-kr" 
    }
]

# 검색 함수
def search_books(book_name):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(libraries)

    for i, lib in enumerate(libraries):
        status_text.text(f"{lib['name']}에서 찾는 중...")
        progress_bar.progress((i + 1) / total)
        
        try:
            params = lib["params"].copy()
            if lib["name"] == "강남구 전자도서관":
                encoded = quote(book_name.encode('euc-kr'))
                url = f"{lib['url']}?{lib['key_param']}={encoded}&search=title"
                resp = requests.get(url, timeout=5)
            else:
                params[lib["key_param"]] = book_name
                resp = requests.get(lib["url"], params=params, timeout=5)

            if resp.status_code == 200:
                tree = html.fromstring(resp.content)
                texts = tree.xpath(lib["xpath"])
                if texts:
                    count = re.findall(r'\d+', texts[0].strip())
                    val = f"{count[0]}권" if count else "0권"
                    results.append({"도서관": lib['name'], "결과": val})
                else:
                    results.append({"도서관": lib['name'], "결과": "없음"})
            else:
                results.append({"도서관": lib['name'], "결과": "접속불가"})
        except:
            results.append({"도서관": lib['name'], "결과": "에러"})
            
    progress_bar.empty()
    status_text.empty()
    return results

# 화면 구성
st.title("📚 도서관 통합 검색기")
st.markdown("---")
keyword = st.text_input("책 제목을 입력하세요", placeholder="예: 미움받을 용기")

if st.button("검색하기", type="primary"):
    if not keyword:
        st.warning("제목을 입력해주세요.")
    else:
        res = search_books(keyword)
        st.table(res)
