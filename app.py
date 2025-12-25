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

def search_books(book_name):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(libraries)

    for i, lib in enumerate(libraries):
        status_text.text(f"{lib['name']}에서 찾는 중...")
        progress_bar.progress((i + 1) / total)
        
        try:
            # 검색 페이지 링크 생성
            if lib["name"] == "강남구 전자도서관":
                encoded = quote(book_name.encode('euc-kr'))
                search_url = f"{lib['url']}?{lib['key_param']}={encoded}&search=title"
            else:
                encoded = quote(book_name.encode('utf-8'))
                search_url = f"{lib['url']}?{lib['key_param']}={encoded}&schClst=ctts%2Cautr&schDvsn=001"

            resp = requests.get(search_url, timeout=5)

            if resp.status_code == 200:
                tree = html.fromstring(resp.content)
                texts = tree.xpath(lib["xpath"])
                if texts:
                    count_match = re.findall(r'\d+', texts[0].strip())
                    count = int(count_match[0]) if count_match else 0
                    
                    val = f"{count}권"
                    link_str = f"[바로가기]({search_url})" if count > 0 else "-"
                    results.append({"도서관": lib['name'], "결과": val, "링크": link_str})
                else:
                    results.append({"도서관": lib['name'], "결과": "없음", "링크": "-"})
            else:
                results.append({"도서관": lib['name'], "결과": "접속불가", "링크": "-"})
        except:
            results.append({"도서관": lib['name'], "결과": "에러", "링크": "-"})
            
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
        # 링크가 포함된 마크다운을 렌더링하기 위해 st.table 대신 st.dataframe 또는 반복문 사용
        # 여기서는 링크를 클릭 가능하게 하기 위해 간단한 반복문(column) 방식을 사용합니다.
        
        st.success(f"'{keyword}' 검색 결과입니다.")
        
        # 헤더 출력
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.write("**도서관 이름**")
        col2.write("**검색 결과**")
        col3.write("**이동**")
        st.divider()

        for item in res:
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(item["도서관"])
            c2.write(item["결과"])
            c3.markdown(item["링크"]) # 마크다운 형식으로 링크 출력
