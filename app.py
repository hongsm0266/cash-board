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
    
    # 엑셀 시트별 데이터 추출 로직
    sheets = {
        '현대카드': (2, {'이용가맹점': '사용처', '이용금액': '이용금액', '결제후잔액': '남은잔액'}),
        '신한카드': (1, {'이용가맹점': '사용처', '이용금액': '이용금액', '결제 후 잔액': '남은잔액'}),
        '롯데카드': (1, {'이용가맹점': '사용처', '이용총액': '이용금액', '결제 후 잔액': '남은잔액'}),
        '삼성카드': (0, {'가맹점': '사용처', '이용금액': '이용금액', '입금후잔액': '남은잔액'}),
        '국민카드': (1, {'이용하신 가맹점': '사용처', '이용금액': '이용금액', '결제 후 잔액': '남은잔액'}),
        '그외고정현금매월사용분': (1, {'사용처': '사용처', '금액': '이용금액'})
    }
    
    for sheet, (hdr, cols) in sheets.items():
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, header=hdr)
            df = df.rename(columns=cols)
            df['결제수단'] = sheet
            if '이용금액' not in df.columns: df['이용금액'] = 0
            if '남은잔액' not in df.columns: df['남은잔액'] = 0
            if sheet == '롯데카드':
                df['이용금액'] = df['이용금액'].astype(str).str.replace(',', '').str.replace('원', '')
            all_data.append(df[['결제수단', '사용처', '이용금액', '남은잔액']].dropna(subset=['사용처']))
        except Exception as e:
            pass
            
    master_df = pd.concat(all_data, ignore_index=True)
    master_df['이용금액'] = pd.to_numeric(master_df['이용금액'], errors='coerce').fillna(0)
    master_df['남은잔액'] = pd.to_numeric(master_df['남은잔액'], errors='coerce').fillna(0)
    
    # 데이터 클리닝
    master_df = master_df[~master_df['사용처'].str.contains('소계|알수없음', na=False, case=False)]
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
    st.dataframe(df[['결제수단', '사용처', '분류', '이용금액', '남은잔액']], use_container_width=True)

except Exception as e:
    st.error("데이터 파일을 찾을 수 없거나 양식이 다릅니다. '목표, 할일 !.xlsx' 파일이 깃허브에 잘 올라갔는지 확인해주세요.")