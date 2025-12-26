import streamlit as st
import requests
from lxml import html
import re
from urllib.parse import quote
import pandas as pd  # 데이터프레임 활용을 위해 추가

# 페이지 설정
st.set_page_config(page_title="전자도서관 통합검색", page_icon="📚")

# (중략: libraries 데이터 및 search_libraries 함수는 사용자님의 최종 버전 유지)
# 단, search_libraries 결과에서 HTML 태그(<a href...>)를 제거하고 순수 텍스트와 링크 URL만 반환하도록 수정하는 것이 좋습니다.

def search_libraries(book_name):
    results = []
    progress_bar = st.progress(0)
    total = len(libraries)

    for i, lib in enumerate(libraries):
        progress_bar.progress((i + 1) / total)
        try:
            encoded_query = quote(book_name.encode(lib["encoding"]))
            search_url = f"{lib['url']}?{lib['key_param']}={encoded_query}"
            if lib["type"] == "standard" or lib["type"] == "ink": 
                search_url += "&schClst=ctts%2Cautr&schDvsn=001"
            elif lib["type"] == "gangnam": 
                search_url += "&search=title"

            resp = requests.get(search_url, timeout=5)
            count = 0
            if resp.status_code == 200:
                tree = html.fromstring(resp.content)
                nodes = tree.xpath(lib["xpath"])
                if nodes:
                    count_match = re.findall(r'\d+', "".join(nodes))
                    count = int(count_match[0]) if count_match else 0
            
            display = f"{count}권" if count > 0 else "없음"
            results.append({"도서관": lib['name'], "상태": display, "링크": search_url})
        except:
            results.append({"도서관": lib['name'], "상태": "확인불가", "링크": "#"})

    # 직접 확인 도서관 추가
    encoded_utf8 = quote(book_name.encode("utf-8"))
    direct_links = [
        {"도서관": "서울도서관", "상태": "링크 확인", "링크": f"https://elib.seoul.go.kr/contents/search/content?t=EB&k={encoded_utf8}"},
        {"도서관": "서초구", "상태": "링크 확인", "링크": f"https://e-book.seocholib.or.kr/search?keyword={encoded_utf8}"},
        {"도서관": "부천시", "상태": "링크 확인", "링크": f"https://ebook.bcl.go.kr:444/elibrary-front/search/searchList.ink?schTxt={encoded_utf8}&schClst=ctts%2Cautr&schDvsn=001"}
    ]
    results.extend(direct_links)
    
    progress_bar.empty()
    return results

# 화면 구성
st.title("📚 전자도서관 통합검색")
query_params = st.query_params
url_keyword = query_params.get("search", "")
keyword = st.text_input("책 제목을 입력하세요", value=url_keyword, placeholder="예: 행복의 기원", key="search_input")

if keyword:
    with st.spinner(f"'{keyword}' 검색 중..."):
        data = search_libraries(keyword)
        
        # 1. 데이터프레임 생성
        df = pd.DataFrame(data)
        
        # 2. 컬럼명 변경 (화면 표시용)
        df.columns = ["도서관 이름", "소장 현황", "URL"]
        
        # 3. 데이터프레임 출력 (st.column_config 사용)
        # 이 방식은 모바일에서도 가로 레이아웃이 깨지지 않고 '링크'를 버튼처럼 만들어줍니다.
        st.data_editor(
            df,
            column_config={
                "도서관 이름": st.column_config.TextColumn("도서관 이름", width="medium"),
                "소장 현황": st.column_config.TextColumn("소장 현황", width="small"),
                "URL": st.column_config.LinkColumn("이동", display_text="열기"),
            },
            hide_index=True,
            use_container_width=True,
            disabled=True # 편집 불가능하게 설정
        )
