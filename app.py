import streamlit as st
import requests
import pandas as pd
from lxml import html
import re
from urllib.parse import quote

# 1. 페이지 설정
st.set_page_config(page_title="전자도서관 통합검색", page_icon="📚", layout="centered")

# 2. 보안 및 데이터 소스 설정
SEOUL_API_KEY = st.secrets.get("seoul_api_key")
SEOCHO_CSV_URL = "https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003242287&fileDetailSn=1&dataNm=%EC%84%9C%EC%9A%B8%ED%8A%B9%EB%B3%84%EC%8B%9C%20%EC%84%9C%EC%B4%88%EA%B5%AC_%EC%A0%84%EC%9E%90%EB%8F%84%EC%84%9C%EA%B4%80%20%EB%8F%84%EC%84%9C%EC%A0%95%EB%B3%B4_20250909"

# 3. 서초구 데이터 캐싱 로드
@st.cache_data(ttl=86400)
def load_seocho_data():
    try:
        df = pd.read_csv(SEOCHO_CSV_URL, encoding='cp949')
        df.columns = df.columns.str.strip()
        for col in ['도서명', '저자명', '형식']:
            df[col] = df[col].astype(str).str.strip()
        return df[df['형식'].str.contains("전자책", na=False)].copy()
    except:
        return None

# 4. 도서관 목록 정의
libraries = [
    {"name": "서울도서관", "url": "http://openapi.seoul.go.kr:8088/", "type": "seoul_api"},
    {"name": "서초구", "type": "seocho_csv"},
    {"name": "강남구", "url": "https://ebook.gangnam.go.kr/elibbook/book_search_result.asp", "key_param": "sarg1", "xpath": '//*[@id="container"]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/strong/text()', "encoding": "euc-kr", "type": "gangnam"},
    {"name": "성남시", "url": "https://vodbook.snlib.go.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "용인시", "url": "https://ebook.yongin.go.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "수원시", "url": "https://ebook.suwonlib.go.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "고양시", "url": "https://ebook.goyanglib.or.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "경기대", "url": "https://ebook.kyonggi.ac.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"}
]

def search_libraries(book_name):
    results = []
    progress_bar = st.progress(0)
    df_seocho = load_seocho_data()

    for i, lib in enumerate(libraries):
        progress_bar.progress((i + 1) / len(libraries))
        try:
            # A. 서초구 CSV (캐싱 데이터 활용)
            if lib["type"] == "seocho_csv":
                count = 0
                if df_seocho is not None:
                    mask = (df_seocho['도서명'].str.contains(book_name, case=False, na=False)) | \
                           (df_seocho['저자명'].str.contains(book_name, case=False, na=False))
                    count = len(df_seocho[mask].drop_duplicates(subset=['도서명', '저자명', '출판사']))
                results.append({"name": lib['name'], "link": f"https://e-book.seocholib.or.kr/search?keyword={quote(book_name)}", "status": f"{count}권" if count > 0 else "없음"})

            # B. 서울도서관 API (공백 -> 언더바 변환 적용)
            elif lib["type"] == "seoul_api":
                if not SEOUL_API_KEY:
                    results.append({"name": lib['name'], "link": "#", "status": "키 설정 필요"})
                    continue
                unique_books = {}
                processed_name = book_name.replace(" ", "_")
                encoded_kw = quote(processed_name)
                for path in [f"1/500/{encoded_kw}/%20/%20/%20/%20", f"1/500/%20/{encoded_kw}/%20/%20/%20"]:
                    resp = requests.get(f"{lib['url']}{SEOUL_API_KEY}/json/SeoulLibraryBookSearchInfo/{path}", timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "SeoulLibraryBookSearchInfo" in data:
                            for book in data["SeoulLibraryBookSearchInfo"].get("row", []):
                                if book.get("BIB_TYPE_NAME") == "전자책":
                                    unique_books[book.get("CTRLNO")] = book
                count = len(unique_books)
                results.append({"name": lib['name'], "link": f"https://elib.seoul.go.kr/contents/search/content?t=EB&k={quote(book_name)}", "status": f"{count}권" if count > 0 else "없음"})

            # C. 기타 스크래핑 도서관
            else:
                encoded_query = quote(book_name.encode(lib["encoding"]))
                search_url = f"{lib['url']}?{lib['key_param']}={encoded_query}" if lib["type"] != "gangnam" else f"{lib['url']}?scon1=TITLE&sarg1={encoded_query}&sopr2=OR&scon2=AUTHOR&sarg2={encoded_query}"
                if lib["type"] == "ink": search_url += "&schClst=ctts%2Cautr&schDvsn=001"
                
                resp = requests.get(search_url, timeout=7)
                tree = html.fromstring(resp.content)
                nodes = tree.xpath(lib["xpath"])
                count = int(re.findall(r'\d+', "".join(nodes))[0]) if nodes and re.findall(r'\d+', "".join(nodes)) else 0
                results.append({"name": lib['name'], "link": search_url, "status": f"{count}권" if count > 0 else "없음"})
        except:
            results.append({"name": lib['name'], "link": "#", "status": "확인불가"})

    progress_bar.empty()
    return results

# --- 화면 출력부 ---
st.markdown('<h2 style="font-size:24px; margin-top:-50px;">📚 전자도서관 통합검색</h2>', unsafe_allow_html=True)
keyword = st.text_input("책 제목 또는 저자를 입력하세요", placeholder="예: 노인과 바다")

if keyword:
    with st.spinner(f"'{keyword}' 검색 중..."):
        data = search_libraries(keyword)
        html_code = """<div style="font-family:sans-serif;"><table style="width:100%; border-collapse:collapse;">
        <thead><tr style="background:#f8f9fa; border-bottom:2px solid #ddd;"><th style="text-align:left; padding:12px;">도서관</th><th style="text-align:right; padding:12px;">현황</th></tr></thead><tbody>"""
        for item in data:
            html_code += f"""<tr style="border-bottom:1px solid #eee;"><td style="padding:12px; font-weight:bold;">{item['name']}</td>
            <td style="padding:12px; text-align:right;"><a href="{item['link']}" target="_blank" style="color:#007bff; text-decoration:none; font-weight:bold;">{item['status']}</a></td></tr>"""
        st.components.v1.html(html_code + "</tbody></table></div>", height=len(data) * 52 + 60)
