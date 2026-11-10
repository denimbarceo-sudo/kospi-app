from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from pykrx import stock
import streamlit as st

# 웹 페이지 설정
st.set_page_config(
    page_title="코스피 주가기대수익률 & 밸류에이션 뷰어", layout="wide"
)

st.title("📈 코스피 장기 주가기대수익률 & 밸류에이션 진단 앱")
st.markdown(
    "코스피 역사적 PER/PBR 데이터를 바탕으로 현재 시장의 과매수·과매도 구간과"
    " 기대수익률을 직관적으로 확인하세요."
)


# 데이터 캐싱 (로딩 속도 개선)
@st.cache_data
def load_data():
  start_year = 2006
  current_year = datetime.now().year
  current_date_str = datetime.now().strftime("%Y%m%d")

  df_list = []
  kospi_ticker = "1001"

  for year in range(start_year, current_year + 1):
    s_date = f"{year}0101"
    e_date = f"{year}1231"
    if year == current_year:
      e_date = current_date_str

    try:
      df = stock.get_index_fundamental(s_date, e_date, kospi_ticker)
      if not df.empty:
        df_list.append(df)
    except:
      pass

  if df_list:
    kospi_df = pd.concat(df_list)
    kospi_df = kospi_df.dropna(subset=["PER", "PBR"])
    # 주가기대수익률(Earnings Yield, %) 계산
    kospi_df["Earnings_Yield"] = (1 / kospi_df["PER"]) * 100
    return kospi_df
  else:
    return pd.DataFrame()


# 데이터 로드 실행
with st.spinner(
    "KRX에서 코스피 20년치 데이터를 불러오는 중입니다... 잠시만 기다려주세요!"
):
  df = load_data()

if not df.empty:
  # 최신 지표 추출
  latest_date = df.index[-1].strftime("%Y-%m-%d")
  latest_close = df["종가"].iloc[-1] if "종가" in df.columns else 0
  latest_per = df["PER"].iloc[-1]
  latest_pbr = df["PBR"].iloc[-1]
  latest_ey = df["Earnings_Yield"].iloc[-1]

  ey_mean = df["Earnings_Yield"].mean()
  ey_std = df["Earnings_Yield"].std()

  # 상단 요약 지표 카드 배치
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("기준일자", latest_date)
  col2.metric("코스피 PER", f"{latest_per:.2f}")
  col3.metric("코스피 PBR", f"{latest_pbr:.2f}")
  col4.metric(
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

  # 역사적 평균선 추가
  fig.add_hline(
      y=ey_mean,
      line_dash="dash",
      line_color="green",
      annotation_text=f"평균 기대수익률 ({ey_mean:.2f}%)",
  )
  # 과매도(저평가) / 과매수(고평가) 기준선 (+1SD, -1SD)
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
  st.error("데이터를 불러오지 못했습니다. 네트워크 상태를 확인해주세요.")
