import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 웹 페이지 설정
st.set_page_config(
    page_title="코스피 장기 주가기대수익률 뷰어", layout="wide"
)

st.title("📈 코스피 역사적 주가기대수익률 & 밸류에이션 진단 앱")
st.markdown(
    "KRX 공식 통계 데이터를 바탕으로 현재 시장의 과매수·과매도 구간과"
    " 기대수익률을 직관적으로 확인하세요."
)


# 데이터 불러오기 (로컬 CSV 파일 활용으로 서버 차단 원천 차단)
@st.cache_data
def load_data():
  try:
    # 2단계에서 저장한 CSV 파일 읽기
    # 파일에는 적어도 'Date', 'Close'(지수), 'PER' 컬럼이 포함되어야 합니다.
    df = pd.read_csv("kospi_data.csv")

    # 날짜 형식 변환 및 정렬
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").set_index("Date")

    # 핵심 공식: 주가기대수익률(Earnings Yield, %) = (1 / PER) * 100
    df["Earnings_Yield"] = (1 / df["PER"]) * 100

    return df, None
  except Exception as e:
    return pd.DataFrame(), str(e)


# 데이터 로드 실행
df, err = load_data()

if not df.empty:
  # 최신 지표 추출
  latest_date = df.index[-1].strftime("%Y-%m-%d")
  latest_per = df["PER"].iloc[-1]
  latest_ey = df["Earnings_Yield"].iloc[-1]

  ey_mean = df["Earnings_Yield"].mean()
  ey_std = df["Earnings_Yield"].std()

  # 상단 요약 지표 카드 배치
  col1, col2, col3 = st.columns(3)
  col1.metric("기준일자", latest_date)
  col2.metric("코스피 PER", f"{latest_per:.2f}")
  col3.metric(
      "주가 기대수익률 (EY)",
      f"{latest_ey:.2f}%",
      delta=f"역사적 평균 대비 ({latest_ey - ey_mean:+.2f}%)",
  )

  st.divider()

  # 차트 그리기 (Plotly 활용)
  st.subheader("📊 코스피 역사적 주가기대수익률(Earnings Yield) 추이")

  fig = go.Figure()
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["Earnings_Yield"],
          mode="lines",
          name="주가 기대수익률(%)",
          line=dict(color="#1f77b4", width=2),
      )
  )

  # 역사적 평균선 및 과매수/과매도 밴드 추가
  fig.add_hline(
      y=ey_mean,
      line_dash="dash",
      line_color="green",
      annotation_text=f"평균 기대수익률 ({ey_mean:.2f}%)",
  )
  fig.add_hline(
      y=ey_mean + ey_std,
      line_dash="dot",
      line_color="red",
      annotation_text="과매수(고평가) 영역 경계",
  )
  fig.add_hline(
      y=ey_mean - ey_std,
      line_dash="dot",
      line_color="blue",
      annotation_text="과매도(저평가) 영역 경계",
  )

  fig.update_layout(
      xaxis_title="연도",
      yaxis_title="기대수익률 (%)",
      hovermode="x unified",
      height=550,
  )

  st.plotly_chart(fig, use_container_width=True)

  # 투자자 가이드 메시지 판정
  st.subheader("💡 현재 시장 위치 진단")
  if latest_ey >= (ey_mean + ey_std):
    st.success(
        "🟢 **현재 구간: 과매도 (강력한 저평가 매수 기회 구간)**\n- 역사적으로"
        " 기대수익률이 평균보다 1 표준편차 이상 높아 주식의 매력도가 매우 높은"
        " 국면입니다."
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
        " 범위 내에서 움직이고 있습니다."
    )
else:
  st.error("데이터 파일을 읽어오지 못했습니다.")
  if err:
    st.write("에러 내용:", err)
