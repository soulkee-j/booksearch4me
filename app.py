if keyword:
    with st.spinner(f"'{keyword}' 검색 중..."):
        data = search_libraries(keyword)
        df = pd.DataFrame(data)
        
        # [해결 방법] 
        # 1. '소장 현황' 컬럼에는 '1권', '없음' 같은 텍스트를 담습니다. (현재 display_text에 있는 값)
        # 2. 'URL' 컬럼에 실제 주소를 담아두고, 링크 기능을 연결합니다.
        
        # 데이터프레임 구조 재정비
        display_df = pd.DataFrame({
            "도서관 이름": [item["도서관 이름"] for item in data],
            "소장 현황": [item["display_text"] for item in data], # '1권', '링크 확인' 등이 들어감
            "url": [item["소장 현황"] for item in data]         # 실제 주소가 들어감
        })

        st.data_editor(
            display_df,
            column_config={
                "도서관 이름": st.column_config.TextColumn("도서관 이름", width="medium"),
                "소장 현황": st.column_config.LinkColumn(
                    "소장 현황", 
                    help="클릭하면 해당 도서관으로 이동합니다",
                    validate=r"^http",
                    display_text=None, # None으로 설정하면 해당 셀의 텍스트가 그대로 링크가 됩니다.
                ),
                "url": None # url 컬럼은 화면에서 숨깁니다.
            },
            # 화면에 보여줄 컬럼 순서 (url 제외)
            column_order=("도서관 이름", "소장 현황"),
            hide_index=True,
            use_container_width=True,
            disabled=True
        )
