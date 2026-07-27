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
    
    # 시트별 검색 키워드와 컬럼 매핑
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
            temp = pd.read_excel(file_path, sheet_name=sheet)
            header_idx = 0
            for i, row in temp.iterrows():
                row_str = ' '.join([str(x) for x in row.values])
                if keyword in row_str:
                    header_idx = i + 1
                    break
                    
            df = pd.read_excel(file_path, sheet_name=sheet, header=header_idx)
            
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
    
    master_df = master_df[master_df['사용처'] != '알수없음']
    master_df = master_df[~master_df['사용처'].astype(str).str.contains('소계', na=False, case=False)]
    master_df = master_df[master_df['이용금액'] != 0]
    
    # 🎯 요청하신 맞춤형 카테고리 분류 함수
    def categorize(m):
        m_clean = str(m).replace(" ", "").lower() # 띄어쓰기 무시하고 인식하게 처리
        
        # 1. 콕 집어주신 특정 사용처
        if '넥스트에디션' in m_clean: return '캠핏'
        if '혜성종합관리' in m_clean: return '회사주차비'
        if '신성통상' in m_clean: return '옷구매'
        if '마트' in m_clean: return '마트'
        
        # 2. 핵심 키워드별 일반 분류
        if any(k in m_clean for k in ['cu', 'gs25', '세븐일레븐', '이마트24', '편의점']): return '편의점'
        if any(k in m_clean for k in ['커피', '카페', '투썸', '스타벅스', '빽다방', '메가커피', '컴포즈']): return '카페/간식'
        if any(k in m_clean for k in ['식당', '순대', '국밥', '치킨', '피자', '중국집', '배달', '음식', '푸드', '요식']): return '외식'
        if any(k in m_clean for k in ['쿠팡', '쇼핑', '신세계', '홈쇼핑', '띵샵', '무신사']): return '쇼핑'
        if any(k in m_clean for k in ['유치원', '학원', '교육', '다온']): return '교육/보육'
        if any(k in m_clean for k in ['주유', '교통', '택시', 'sk', 'gs']): return '교통/차량'
        if any(k in m_clean for k in ['병원', '약국', '치과', '의원']): return '건강/의료'
        if any(k in m_clean for k in ['연회비', '보험', '알림서비스', '오션넷', '테일러타운', '토스']): return '금융/통신'
        
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
            # M 단위가 아니라 원래 숫자에 콤마(,) 찍어서 보여주도록 수정
            fig_bar = px.bar(card_sum, x='결제수단', y='이용금액', text='이용금액')
            fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.divider()
        
        # 🎯 카드사별/분류별 결제 요약표 (피벗 테이블 적용)
        st.subheader("📝 카드사별 & 분류별 지출 요약표")
        
        # 분류(행)와 결제수단(열)을 기준으로 합계 생성
        pivot_df = df.pivot_table(index='분류', columns='결제수단', values='이용금액', aggfunc='sum', fill_value=0)
        
        # 행별 총액 구하고, 총액이 큰 순서대로 정렬
        pivot_df['총액(원)'] = pivot_df.sum(axis=1)
        pivot_df = pivot_df.sort_values(by='총액(원)', ascending=False)
        pivot_df = pivot_df.reset_index()
        
        # 금액에 콤마 포맷팅 씌워서 출력
        st.dataframe(pivot_df.style.format(subset=pivot_df.columns[1:], formatter="{:,.0f}"), use_container_width=True)

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
