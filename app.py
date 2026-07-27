import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="나의 통합 가계부", layout="wide")
st.title("📊 통합 가계부 대시보드")

@st.cache_data
def load_data():
    file_path = "목표, 할일 !.xlsx"
    all_data = []
    
    # 각 카드사별 헤더 키워드와 가져올 컬럼 정의
    # '당월청구' 항목을 최대한 찾아서 이번 달 실제 나갈 돈만 계산합니다.
    sheets = {
        '현대카드': ('이용가맹점', {'이용가맹점': '사용처', '이용금액': '총이용금액', '결제원금': '당월청구금액', '결제후잔액': '남은잔액', '할부/회차': '할부정보'}),
        '신한카드': ('이용가맹점', {'이용가맹점': '사용처', '이용금액': '총이용금액', '이번달 납부금액': '당월청구금액', '결제 후 잔액': '남은잔액', '회차': '현재회차', '할부기간': '전체할부'}),
        '롯데카드': ('이용가맹점', {'이용가맹점': '사용처', '이용총액': '총이용금액', '이번 달 입금하실 금액': '당월청구금액', '결제 후 잔액': '남은잔액', '회차': '현재회차', '할부': '전체할부'}),
        '삼성카드': ('가맹점', {'가맹점': '사용처', '이용금액': '총이용금액', '원금': '당월청구금액', '입금후잔액': '남은잔액', '회차': '현재회차', '개월': '전체할부'}),
        '국민카드': ('가맹점', {'이용하신 가맹점': '사용처', '이용금액': '총이용금액', '이번달 결제금액': '당월청구금액', '결제 후 잔액': '남은잔액', '할부개월': '전체할부'}),
        '그외고정현금매월사용분': ('사용처', {'사용처': '사용처', '금액': '당월청구금액'})
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
            
            # 컬럼 이름 유연하게 매핑
            found_cols = {}
            for col in df.columns:
                for k, v in cols.items():
                    if k in str(col):
                        found_cols[col] = v
            df = df.rename(columns=found_cols)
            df['결제수단'] = sheet
            
            # 현금 시트는 총이용금액 = 당월청구금액
            if '총이용금액' not in df.columns and '당월청구금액' in df.columns:
                df['총이용금액'] = df['당월청구금액']
                
            # 필수 컬럼 빈값 채우기
            for c in ['총이용금액', '당월청구금액', '남은잔액']:
                if c not in df.columns: df[c] = 0
            if '사용처' not in df.columns: df['사용처'] = '알수없음'
            
            # 롯데카드 등 문자열(콤마, '원') 섞인 금액을 숫자로 변환
            for c in ['총이용금액', '당월청구금액', '남은잔액']:
                df[c] = df[c].astype(str).str.replace(',', '').str.replace('원', '').str.replace('nan', '0')
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                
            # 할부 정보 텍스트 조합 (카드사마다 표기가 달라서 하나로 합침)
            if '현재회차' in df.columns and '전체할부' in df.columns:
                df['할부상태'] = df['현재회차'].astype(str).str.replace('\.0', '', regex=True) + " / " + df['전체할부'].astype(str).str.replace('\.0', '', regex=True) + "개월"
            elif '할부정보' in df.columns:
                df['할부상태'] = df['할부정보'].astype(str)
            else:
                df['할부상태'] = "일시불"
                
            # 남은 잔액이 있는 경우 문자열 정리 (nan 방지)
            df['할부상태'] = df['할부상태'].replace({'nan / nan개월': '일시불', 'nan': '일시불', '0 / 0개월': '일시불'})

            all_data.append(df[['결제수단', '사용처', '총이용금액', '당월청구금액', '남은잔액', '할부상태']].dropna(subset=['사용처']))
        except Exception as e:
            pass
            
    master_df = pd.concat(all_data, ignore_index=True)
    master_df = master_df[master_df['사용처'] != '알수없음']
    master_df = master_df[~master_df['사용처'].astype(str).str.contains('소계', na=False, case=False)]
    
    # 일시불인 경우 당월청구금액이 비어있으면 총이용금액을 그대로 가져옴
    master_df['당월청구금액'] = np.where(master_df['당월청구금액'] == 0, master_df['총이용금액'], master_df['당월청구금액'])
    master_df = master_df[master_df['당월청구금액'] != 0] # 당월 0원 제외
    
    def categorize(m):
        m_clean = str(m).replace(" ", "").lower()
        if '넥스트에디션' in m_clean: return '캠핏'
        if '혜성종합관리' in m_clean: return '회사주차비'
        if '신성통상' in m_clean: return '옷구매'
        if '마트' in m_clean: return '마트'
        
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
    
    # 남은 잔액이 0보다 크면 무조건 할부로 표기 보정
    master_df.loc[(master_df['남은잔액'] > 0) & (master_df['할부상태'] == '일시불'), '할부상태'] = '할부진행중'
    
    return master_df

try:
    df = load_data()
    
    if df.empty:
        st.warning("데이터를 불러오지 못했습니다. 파일 양식을 다시 확인해주세요.")
    else:
        # 1. 이제 '당월청구금액' 기준으로 합산합니다!
        total_billed = df['당월청구금액'].sum()
        total_rem = df['남은잔액'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("이번 달 실제 청구 총액", f"{int(total_billed):,} 원")
        col2.metric("앞으로 갚아야 할 할부 총잔액", f"{int(total_rem):,} 원")
        
        st.divider()
        
        # 2. 차트도 모두 '당월청구금액' 기준
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("이번 달 카테고리별 지출 비중")
            cat_sum = df.groupby('분류')['당월청구금액'].sum().reset_index()
            fig_pie = px.pie(cat_sum, values='당월청구금액', names='분류', hole=0.3)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            st.subheader("이번 달 결제수단별 청구액")
            card_sum = df.groupby('결제수단')['당월청구금액'].sum().reset_index()
            fig_bar = px.bar(card_sum, x='결제수단', y='당월청구금액', text='당월청구금액')
            fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.divider()
        
        # 3. 이번 달 일반 지출 요약표
        st.subheader("📝 이번 달 분류별 & 결제수단별 청구 요약")
        pivot_df = df.pivot_table(index='분류', columns='결제수단', values='당월청구금액', aggfunc='sum', fill_value=0)
        pivot_df['총액(원)'] = pivot_df.sum(axis=1)
        pivot_df = pivot_df.sort_values(by='총액(원)', ascending=False).reset_index()
        st.dataframe(pivot_df.style.format(subset=pivot_df.columns[1:], formatter="{:,.0f}"), use_container_width=True)

        st.divider()
        
        # 4. 🚨 강력 요청하신 [할부 집중 관리 코너]
        st.subheader("💳 내 빚 현황 (할부 집중 관리)")
        # 남은 잔액이 0보다 큰 '할부' 항목만 필터링
        installment_df = df[df['남은잔액'] > 0].copy()
        
        if not installment_df.empty:
            installment_df = installment_df[['결제수단', '분류', '사용처', '총이용금액', '당월청구금액', '남은잔액', '할부상태']]
            # 보기 편하게 카드사별로 정렬
            installment_df = installment_df.sort_values(by=['결제수단', '남은잔액'], ascending=[True, False]).reset_index(drop=True)
            
            st.dataframe(
                installment_df.style.format({
                    '총이용금액': '{:,.0f}',
                    '당월청구금액': '{:,.0f}', 
                    '남은잔액': '{:,.0f}'
                }), 
                use_container_width=True
            )
        else:
            st.success("현재 남은 할부 잔액이 없습니다! 아주 훌륭합니다 👍")

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
