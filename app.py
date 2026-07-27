import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="나의 통합 가계부", layout="wide")
st.title("📊 통합 가계부 대시보드")

# 데이터 불러오기 함수
@st.cache_data
def load_data():
    file_path = "목표, 할일 !.xlsx"
    all_data = []
    
    # 시트별 검색 키워드와 컬럼 매핑 (자동 줄찾기 기능 추가)
    sheets = {
        '현대카드': ('이용가맹점', {'이용가맹점': '사용처', '이용금액': '이용금액', '결제후잔액': '남은잔액'}),
        '신한카드': ('이용가맹점', {'이용가맹점': '사용처', '이용금액': '이용금액', '결제 후 잔액': '남은잔액'}),
        '롯데카드': ('이용가맹점', {'이용가맹점': '사용처', '이용총액': '이용금액', '결제 후 잔액': '남은잔액'}),
        '삼성카드': ('가맹점', {'가맹점': '사용처', '이용금액': '이용금액', '입금후잔액': '남은잔액'}),
        '국민카드': ('가맹점', {'이용하신 가맹점': '사용처', '이용금액': '이용금액', '결제 후 잔액': '남은잔액'}),
        '그외고정현금매월사용분': ('사용처', {'사용처': '사용처', '금액': '이용금액'})
    }
    
    for sheet, (keyword, cols) in sheets.items():
        try:
            # 1. 알아서 표가 시작하는 줄 번호 찾기
            temp = pd.read_excel(file_path, sheet_name=sheet)
            header_idx = 0
            for i, row in temp.iterrows():
                row_str = ' '.join([str(x) for x in row.values])
                if keyword in row_str:
                    header_idx = i + 1
                    break
                    
            # 2. 정확한 줄부터 데이터 가져오기
            df = pd.read_excel(file_path, sheet_name=sheet, header=header_idx)
            
            # 3. 필요한 정보만 정리
            found_cols = {orig: new for orig, new in cols.items() if orig in df.columns}
            df = df.rename(columns=found_cols)
            df['결제수단'] = sheet
            
            if '이용금액' not in df.columns: df['이용금액'] = 0
            if '남은잔액' not in df.columns: df['남은잔액'] = 0
            if '사용처' not in df.columns: df['사용처'] = '알수없음'
            
            # 롯데카드 텍스트 금액 수정
            if sheet == '롯데카드':
                df['이용금액'] = df['이용금액'].astype(str).str.replace(',', '').str.replace('원', '')
                
            all_data.append(df[['결제수단', '사용처', '이용금액', '남은잔액']].dropna(subset=['사용처']))
        except Exception as e:
            pass
            
    # 전체 데이터 합치기
    master_df = pd.concat(all_data, ignore_index=True)
    master_df['이용금액'] = pd.to_numeric(master_df['이용금액'], errors='coerce').fillna(0)
    master_df['남은잔액'] = pd.to_numeric(master_df['남은잔액'], errors='coerce').fillna(0)
    
    # 불필요한 내용(소계 등) 제거
    master_df = master_df[master_df['사용처'] != '알수없음']
    master_df = master_df[~master_df['사용처'].astype(str).str.contains('소계', na=False, case=False)]
    master_df = master_df[master_df['이용금액'] != 0]
    
    # 카테고리 분류 함수
    def categorize(m):
        m = str(m).lower()
        if any(k in m for k in ['쿠팡', '쇼핑', '신세계', '홈쇼핑', '띵샵', '무신사']): return '쇼핑/생활'
        if any(k in m for k in ['유치원', '학원', '교육', '다온']): return '교육/보육'
        if any(k in m for k in ['주유', '교통', '택시', 'sk', 'gs']): return '교통/차량'
        if any(k in m for k in ['식당', '카페', '커피', '배달']): return '식비'
        if any(k in m for k in ['병원', '약국', '치과']): return '건강/의료'
        if any(k in m for k in ['연회비', '보험', '알림서비스', '오션넷', '테일러타운']): return '금융/통신'
        return '기타(미분류)'
        
    master_df['분류'] = master_df['사용처'].apply(categorize)
    return master_df

try:
    df = load_data()
    
    if df.empty:
        st.warning("데이터를 불러오지 못했습니다. 파일 양식을 다시 확인해주세요.")
    else:
        total_spent = df['이용금액'].sum()
        total_rem = df['남은잔액'].sum()
        
        # 상단 요약 지표
        col1, col2 = st.columns(2)
        col1.metric("이번 달 총 결제금액", f"{int(total_spent):,} 원")
        col2.metric("남은 할부 잔액 총합", f"{int(total_rem):,} 원")
        
        st.divider()
        
        # 차트 영역
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("카테고리별 지출 비중")
            cat_sum = df.groupby('분류')['이용금액'].sum().reset_index()
            fig_pie = px.pie(cat_sum, values='이용금액', names='분류', hole=0.3)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            st.subheader("결제수단별 지출액")
            card_sum = df.groupby('결제수단')['이용금액'].sum().reset_index()
            fig_bar = px.bar(card_sum, x='결제수단', y='이용금액', text_auto='.2s')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.divider()
        
        # 세부 결제 내역 표
        st.subheader("📝 세부 결제 내역")
        st.dataframe(df[['결제수단', '사용처', '분류', '이용금액', '남은잔액']].reset_index(drop=True), use_container_width=True)

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
