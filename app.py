from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 웹 페이지 설정
st.set_page_config(
    page_title="코스피 장기 주가기대수익률 & 밸류에이션 진단 앱", layout="wide"
)

st.title("📈 코스피 장기 주가기대수익률(EY) & 밸류에이션 진단 앱")
st.markdown(
    "KOSIS 공식 월별 통계 데이터(가로 나열 형태)를 바탕으로 산출한 주가기대수익률과"
    " 현재 시장의 과매수·과매도 구간을 직관적으로 확인하세요."
)


# 데이터 로드 및 전처리 함수 (가로 형태 엑셀 구조 완벽 대응)
@st.cache_data
def load_data():
  try:
    # 1. ANSI(cp949) 인코딩으로 CSV 읽기 시도
    try:
      df = pd.read_csv("kospi_data.csv", encoding="cp949")
    except UnicodeDecodeError:
      df = pd.read_csv("kospi_data.csv", encoding="utf-8-sig")

    # 컬럼명 공백 제거
    df.columns = df.columns.str.strip()

    # 2. 'KOSPI' (소계) 행 데이터만 골라내기 (A열, B열 이름에 관계없이 첫 번째 행 또는 KOSPI 소계 탐색)
    # 이미지 상 첫 번째 행(KOSPI / 소계)이 전체 시장 대표 값이므로 이를 타겟으로 잡습니다.
    kospi_row = None
    for idx, row in df.iterrows():
      row_str = str(row.values)
      if "KOSPI" in row_str and (
          "소계" in row_str or "지수종류" not in str(row.iloc[1])
      ):
        # 만약 정확히 'KOSPI'와 '소계'가 포함된 행이라면 선택
        if "KOSPI" == str(row.iloc[0]).strip() and "소계" in str(
            row.iloc[1]
        ).strip():
          kospi_row = row
          break

    # 만약 위 조건으로 못 찾았다면 첫 번째 행(KOSPI 소계)을 기본으로 강제 지정
    if kospi_row is None:
      kospi_row = df.iloc[0]

    # 3. 날짜 컬럼들(YYYY.MM 형태)과 PER 값들을 세로 형태로 변환 (Melt)
    # A열, B열(분류 이름들)을 제외한 나머지 컬럼들이 날짜별 PER 값입니다.
    date_columns = []
    per_values = []

    for col in df.columns[2:]:  # C열부터 끝까지 탐색
      # 컬럼명이 연도.월 형태인지 확인 (예: 2017.01)
      col_clean = str(col).strip()
      if "." in col_clean or len(col_clean) == 6:
        val = kospi_row[col]
        try:
          # 숫자로 변환 가능한 경우만 추가
          num_val = float(str(val).replace(",", ""))
          date_columns.append(col_clean)
          per_values.append(num_val)
        except ValueError:
          continue

    # 변환된 데이터를 DataFrame으로 재구성
    clean_df = pd.DataFrame()
    # '2017.01' 형식을 파이썬 날짜(Datetime)로 변환 (2017-01-01로 매핑)
    clean_df["Date"] = pd.to_datetime(
        pd.Series(date_columns).str.replace(".", "-") + "-01", errors="coerce"
    )
    clean_df["PER"] = per_values

    # 결측치 제거 및 날짜 오름차순 정렬
    clean_df = clean_df.dropna(subset=["Date", "PER"]).sort_values("Date")
    clean_df.set_index("Date", inplace=True)

    # 4. 핵심 공식 적용: 주가기대수익률(Earnings Yield, %) = (1 / PER) * 100
    clean_df["Earnings_Yield"] = (1 / clean_df["PER"]) * 100

    return clean_df, None
  except Exception as e:
    return pd.DataFrame(), str(e)


# 데이터 로드 실행
df, err = load_data()

if not df.empty:
  # 최신 지표 추출
  latest_date = df.index[-1].strftime("%Y-%m")
  latest_per = df["PER"].iloc[-1]
  latest_ey = df["Earnings_Yield"].iloc[-1]

  ey_mean = df["Earnings_Yield"].mean()
  ey_std = df["Earnings_Yield"].std()

  # 상단 요약 지표 카드 배치
  col1, col2, col3 = st.columns(3)
  col1.metric("최신 기준월", latest_date)
  col2.metric("코스피 공식 PER", f"{latest_per:.2f}")
  col3.metric(
      "주가 기대수익률 (EY)",
      f"{latest_ey:.2f}%",
      delta=f"역사적 평균 대비 ({latest_ey - ey_mean:+.2f}%)",
  )

  st.divider()

  # 차트 시각화 (Plotly)
  st.subheader("📊 코스피 월별 주가기대수익률(Earnings Yield) 추이")

  fig = go.Figure()
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["Earnings_Yield"],
          mode="lines+markers",
          name="주가 기대수익률(%)",
          line=dict(color="#1f77b4", width=2),
      )
  )

  # 평균선 및 표준편차 밴드 추가
  fig.add_hline(
      y=ey_mean,
      line_dash="dash",
      line_color="green",
      annotation_text=f"역사적 평균 ({ey_mean:.2f}%)",
  )
  fig.add_hline(
      y=ey_mean + ey_std,
      line_dash="dot",
      line_color="red",
      annotation_text="과매수(고평가) 경계 (+1SD)",
  )
  fig.add_hline(
      y=ey_mean - ey_std,
      line_dash="dot",
      line_color="blue",
      annotation_text="과매도(저평가) 경계 (-1SD)",
  )

  fig.update_layout(
      xaxis_title="연도-월",
      yaxis_title="기대수익률 (%)",
      hovermode="x unified",
      height=550,
  )

  st.plotly_chart(fig, use_container_width=True)

  # 시장 진단 메시지
  st.subheader("💡 현재 시장 위치 진단")
  if latest_ey >= (ey_mean + ey_std):
    st.success(
        "🟢 **현재 구간: 과매도 (강력한 저평가 매수 기회 구간)**\n- 역사적으로"
        " 기대수익률이 평균보다 1 표준편차 이상 높아 주식의 밸류에이션 매력도가"
        " 매우 높은 국면입니다."
    )
  elif latest_ey <= (ey_mean - ey_std):
    st.error(
        "🔴 **현재 구간: 과매수 (고평가 경계 구간)**\n- 역사적으로 기대수익률이"
        " 낮아진 구간으로, 주가가 기업 실적 대비 고평가되어 있을 가능성이"
        " 높습니다."
    )
  else:
    st.info(
        "🟡 **현재 구간: 중립 (역사적 평균 영역)**\n- 시장이 통상적인 밸류에이션"
        " 범위 내에서 안정적으로 움직이고 있습니다."
    )
else:
  st.error(
      "데이터 파일을 올바르게 읽지 못했습니다. 'kospi_data.csv' 파일이 ANSI(cp949)"
      " 인코딩으로 저장되었는지 확인해주세요."
  )
  if err:
    st.info(f"기술적 에러 내용: {err}")
