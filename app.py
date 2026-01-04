import streamlit as st
import requests
import pandas as pd
from lxml import html
import re
from urllib.parse import quote

# 1. 페이지 설정
st.set_page_config(page_title="전자도서관 통합검색", page_icon="📚", layout="centered")

# 2. 데이터 소셜 및 API 설정
SEOUL_API_KEY = st.secrets.get("seoul_api_key")
SEOCHO_CSV_URL = "https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003242287&fileDetailSn=1&dataNm=%EC%84%9C%EC%9A%B8%ED%8A%B9%EB%B3%84%EC%8B%9C%20%EC%84%9C%EC%B4%88%EA%B5%AC_%EC%A0%84%EC%9E%90%EB%8F%84%EC%84%9C%EA%B4%80%20%EB%8F%84%EC%84%9C%EC%A0%95%EB%B3%B4_20250909"

# 3. 서초구 데이터 로드 (백그라운드 캐싱)
@st.cache_data(ttl=86400, show_spinner=False)
def load_seocho_data():
    try:
        df = pd.read_csv(SEOCHO_CSV_URL, encoding='cp949')
        df.columns = df.columns.str.strip()
        for col in ['도서명', '저자명', '형식']:
            df[col] = df[col].astype(str).str.strip()
        return df[df['형식'].str.contains("전자책", na=False)].copy()
    except:
        return None

df_seocho_cached = load_seocho_data()

# 4. 도서관 목록 정의
libraries = [
    {"name": "성남시", "url": "https://vodbook.snlib.go.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "용인시", "url": "https://ebook.yongin.go.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "수원시", "url": "https://ebook.suwonlib.go.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "고양시", "url": "https://ebook.goyanglib.or.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "경기대", "url": "https://ebook.kyonggi.ac.kr/elibrary-front/search/searchList.ink", "key_param": "schTxt", "xpath": '//*[@id="container"]/div/div[4]/p/strong[2]/text()', "encoding": "utf-8", "type": "ink"},
    {"name": "구독형", "url": "https://lib.yongin.go.kr/intro/menu/10003/program/30012/plusSearchResultList.do", "key_param": "searchKeyword", "xpath": '//*[@id="searchForm"]/div/div[2]/div[1]/div[1]/strong[2]/text()', "encoding": "utf-8", "type": "subscription"},
    {"name": "서울시", "url": "http://openapi.seoul.go.kr:8088/", "type": "seoul_api"},
    {"name": "강남구", "url": "https://ebook.gangnam.go.kr/elibbook/book_search_result.asp", "key_param": "sarg1", "xpath": '//*[@id="container"]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/strong/text()', "encoding": "euc-kr", "type": "gangnam"},
    {"name": "서초구", "type": "seocho_csv"},
]

def search_libraries(book_name):
    results = []
    progress_bar = st.progress(0)
    
    # 보안 차단 회피용 헤더
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for i, lib in enumerate(libraries):
        progress_bar.progress((i + 1) / len(libraries))
        try:
            # A. 서초구 CSV 검색
            if lib["type"] == "seocho_csv":
                count = 0
                if df_seocho_cached is not None:
                    mask = (df_seocho_cached['도서명'].str.contains(book_name, case=False, na=False)) | \
                           (df_seocho_cached['저자명'].str.contains(book_name, case=False, na=False))
                    count = len(df_seocho_cached[mask].drop_duplicates(subset=['도서명', '저자명', '출판사']))
                results.append({"name": lib['name'], "link": f"https://e-book.seocholib.or.kr/search?keyword={quote(book_name)}", "status": f"{count}권" if count > 0 else "없음"})

            # B. 서울도서관 API 검색 (공백 -> 언더바)
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

            # C. 스크래핑 방식 (용인 구독형 포함)
            else:
                encoded_query = quote(book_name.encode(lib["encoding"]))
                if lib["type"] == "subscription":
                    search_url = f"{lib['url']}?searchType=SIMPLE&searchCategory=EBOOK2&searchKey=ALL&searchKeyword={encoded_query}"
                elif lib["type"] == "gangnam":
                    search_url = f"{lib['url']}?scon1=TITLE&sarg1={encoded_query}&sopr2=OR&scon2=AUTHOR&sarg2={encoded_query}"
                else:
                    search_url = f"{lib['url']}?{lib['key_param']}={encoded_query}&schClst=ctts%2Cautr&schDvsn=001"
                
                # 헤더 정보를 포함하여 요청 (차단 방지)
                resp = requests.get(search_url, timeout=10, headers=headers)
                tree = html.fromstring(resp.content)
                nodes = tree.xpath(lib["xpath"])
                
                # 정규식을 이용해 텍스트 내 숫자만 추출
                raw_text = "".join(nodes).strip()
                count_match = re.findall(r'\d+', raw_text)
                count = int(count_match[0]) if count_match else 0
                results.append({"name": lib['name'], "link": search_url, "status": f"{count}권" if count > 0 else "없음"})
        except:
            results.append({"name": lib['name'], "link": "#", "status": "확인불가"})

    progress_bar.empty()
    return results

# --- 메인 화면 UI ---
st.markdown('<h2 style="font-size:24px; margin-top:-50px;">📚 전자도서관 통합검색</h2>', unsafe_allow_html=True)
keyword = st.text_input("책 제목 또는 저자를 입력하세요", placeholder="예: 노인과 바다")

if keyword:
    with st.spinner(f"검색 중입니다..."):
        data = search_libraries(keyword)
        
        # 테이블 생성
        html_code = """<div style="font-family:sans-serif;"><table style="width:100%; border-collapse:collapse;">
        <thead><tr style="background:#f8f9fa; border-bottom:2px solid #ddd;"><th style="text-align:left; padding:12px;">도서관</th><th style="text-align:right; padding:12px;">현황</th></tr></thead><tbody>"""
        for item in data:
            html_code += f"""<tr style="border-bottom:1px solid #eee;"><td style="padding:12px; font-weight:bold;">{item['name']}</td>
            <td style="padding:12px; text-align:right;"><a href="{item['link']}" target="_blank" style="color:#007bff; text-decoration:none; font-weight:bold;">{item['status']}</a></td></tr>"""
        
        st.components.v1.html(html_code + "</tbody></table></div>", height=len(data) * 52 + 60)
        
        # 테이블 하단 서초구 고정 메시지
        st.markdown("---")
        st.info("📢 서초구 데이터 업데이트 예정일 : 2026.3.4")
