import streamlit as st
import requests
from lxml import html
import re
from urllib.parse import quote

# 페이지 설정
st.set_page_config(page_title="도서관 통합 검색", page_icon="📚")

# 도서관 데이터 설정
libraries = [
    {"name": "성남시 전자도서관", "url": "https://vodbook.snlib.go.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "경기대학교", "url": "https://ebook.kyonggi.ac.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "용인시 전자책도서관", "url": "https://ebook.yongin.go.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "수원시 전자도서관", "url": "https://ebook.suwonlib.go.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "고양시 도서관센터", "url": "https://ebook.goyanglib.or.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "강남구 전자도서관", "url": "https://ebook.gangnam.go.kr/elibbook/book_info.asp", "key_param": "strSearch", "xpath": '//*[@id="container"]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/strong/text()', "encoding": "euc-kr", "type": "gangnam"},
    # 서초구는 특별 처리를 위해 리스트에서 제외하고 별도 로직으로 검색합니다.
]

def get_count(tree, xpath_query):
    try:
        nodes = tree.xpath(xpath_query)
        if nodes:
            combined_text = "".join(nodes)
            count_match = re.findall(r'\d+', combined_text)
            return int(count_match[0]) if count_match else 0
    except:
        pass
    return 0

def search_all_libraries(book_name):
    results = []
    progress_bar = st.progress(0)
    
    # 서초구를 제외한 일반 도서관들 처리
    for i, lib in enumerate(libraries):
        progress_bar.progress((i + 1) / (len(libraries) + 1))
        try:
            encoded_query = quote(book_name.encode(lib["encoding"]))
            if lib["type"] == "gangnam":
                search_url = f"{lib['url']}?{lib['key_param']}={encoded_query}&search=title"
            else:
                search_url = f"{lib['url']}?{lib['key_param']}={encoded_query}&schClst=ctts%2Cautr&schDvsn=001"

            resp = requests.get(search_url, timeout=7)
            count = get_count(html.fromstring(resp.content), lib["xpath"]) if resp.status_code == 200 else 0
            display = f"[{count}권 발견]({search_url})" if count > 0 else "없음"
            results.append({"도서관": lib['name'], "결과": display})
        except:
            results.append({"도서관": lib['name'], "결과": "에러발생"})

    # 서초구 전자도서관 특별 처리 (전자책/구독형 구분)
    try:
        seocho_url = f"https://e-book.seocholib.or.kr/search?keyword={quote(book_name)}"
        resp = requests.get(seocho_url, timeout=7)
        if resp.status_code == 200:
            tree = html.fromstring(resp.content)
            
            # 서초구 소장형(전자책) 추출 - 보통 첫 번째 탭 혹은 특정 클래스
            # 웹사이트 구조상 '소장형'과 '구독형' 텍스트를 포함한 요소를 찾습니다.
            eb_count = get_count(tree, '//li[contains(., "소장형")]//span/text() | //div[contains(@class, "search-result-count")]//strong/text()')
            # 서초구 구독형 추출 (구조에 따라 XPath 조정 필요할 수 있음)
            sub_count = get_count(tree, '//li[contains(., "구독형")]//span/text()')
            
            results.append({"도서관": "서초구 도서관(전자책)", "결과": f"[{eb_count}권 발견]({seocho_url})" if eb_count > 0 else "없음"})
            results.append({"도서관": "서초구 도서관(구독형)", "결과": f"[{sub_count}권 발견]({seocho_url}&contentType=SUBS)" if sub_count > 0 else "없음"})
        else:
            results.append({"도서관": "서초구 도서관", "결과": "접속불가"})
    except:
        results.append({"도서관": "서초구 도서관", "결과": "에러발생"})

    progress_bar.empty()
    return results

# 화면 구성
st.title("📚 도서관 통합 검색기")
st.write("책 제목을 입력하고 **엔터(Enter)**를 누르세요.")
st.markdown("---")

keyword = st.text_input("책 제목을 입력하세요", placeholder="예: 행복의 기원", key="search_input")

if keyword:
    with st.spinner(f"'{keyword}' 검색 중..."):
        res = search_all_libraries(keyword)
        
        st.success(f"'{keyword}' 검색 결과입니다.")
        col1, col2 = st.columns([2, 1])
        col1.write("**도서관 이름**")
        col2.write("**소장 현황 (클릭 시 이동)**")
        st.divider()

        for item in res:
            c1, c2 = st.columns([2, 1])
            c1.write(item["도서관"])
            c2.markdown(item["결과"])
