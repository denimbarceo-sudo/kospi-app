from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from pykrx import stock
import streamlit as st

# 웹 페이지 설정
st.set_page_config(
    page_title="코스피 주가기대수익률 & 밸류에이션 진단 앱", layout="wide"
)

st.title("📈 PyKrx 기반 코스피 주가기대수익률(EY) & 밸류에이션 진단")
st.markdown(
    "한국거래소(KRX) 공식 통계 데이터를 바탕으로 산출한 주가기대수익률 추이를"
    " 확인하고, 현재 시장의 고평가·저평가 구간을 진단합니다."
)


# 데이터 수집 및 전처리 함수 (캐싱 적용)
@st.cache_data(ttl=3600)
def load_pykrx_data():
  try:
    # 최근 3년~5년치 데이터 수집 설정
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m%d")

    # 코스피 지수(1001)의 펀더멘털 데이터(PER, EPS, PBR 등) 조회
    df = stock.get_index_fundamental(start_date, end_date, "1001")

    if df is not None and not df.empty:
      df = df.reset_index()
      # 날짜 컬럼 정돈
      date_col = [c for c in df.columns if "날짜" in c or "date" in c.lower()]
      if date_col:
        df["Date"] = pd.to_datetime(df[date_col[0]])
        df.set_index("Date", inplace=True)

      # 필수 컬럼 확인 및 정리
      if "PER" in df.columns and "EPS" in df.columns:
        df["PER"] = pd.to_numeric(df["PER"], errors="coerce")
        df["EPS"] = pd.to_numeric(df["EPS"], errors="coerce")

        # 핵심 공식: 주가기대수익률(Earnings Yield, %) = (1 / PER) * 100
        df["Earnings_Yield"] = (1 / df["PER"]) * 100
        return df.dropna(subset=["Earnings_Yield"]), None

    raise Exception("데이터가 비어 있거나 조회되지 않았습니다.")

  except Exception as e:
    # 만약 KRX 서버 접속 제한 등으로 데이터를 못 가져올 경우 샘플/대체 데이터로 앱 생존 보장
    dates = pd.date_range(end=datetime.today(), periods=60, freq="ME")
    np.random.seed(42)
    sample_per = np.linspace(10, 13, 60) + np.random.normal(0, 0.8, 60)
    sample_eps = np.linspace(250, 300, 60)
    df_sample = pd.DataFrame(
        {"PER": sample_per, "EPS": sample_eps}, index=dates
    )
    df_sample["Earnings_Yield"] = (1 / df_sample["PER"]) * 100
    return (
        df_sample,
        f"KRX 실시간 연동 중 제한이 발생하여 시뮬레이션 데이터로 구동 중입니다."
        f" (에러내용: {e})",
    )


# 데이터 로드 실행
df, warning_msg = load_pykrx_data()

if warning_msg:
  st.warning(warning_msg)

if not df.empty:
  # 최신 지표 추출
  latest_date = df.index[-1].strftime("%Y-%m-%d")
  latest_per = df["PER"].iloc[-1]
  latest_eps = df["EPS"].iloc[-1]
  latest_ey = df["Earnings_Yield"].iloc[-1]

  # 통계적 밴드 계산 (평균, 표준편차)
  ey_mean = df["Earnings_Yield"].mean()
  ey_std = df["Earnings_Yield"].std()
  upper_band = ey_mean + ey_std  # 고평가 경계 (+1SD)
  lower_band = ey_mean - ey_std  # 저평가 경계 (-1SD)

  # 상단 핵심 요약 지표 카드
  st.subheader(f"📌 코스피 핵심 밸류에이션 지표 (기준일: {latest_date})")
  col1, col2, col3, col4, col5 = st.columns(5)
  col1.metric("코스피 PER", f"{latest_per:.2f}")
  col2.metric("코스피 EPS (환산)", f"{latest_eps:,.1f}")
  col3.metric("주가 기대수익률 (EY)", f"{latest_ey:.2f}%")
  col4.metric("역사적 평균 EY", f"{ey_mean:.2f}%")
  col5.metric("평균 대비 격차", f"{latest_ey - ey_mean:+.2f}%")

  st.divider()

  # Plotly 차트 시각화 (기대수익률 + 고평가/저평가 밴드)
  st.subheader("📊 코스피 주가기대수익률(EY) & 과매수/과매도 밴드 차트")

  fig = go.Figure()

  # 기대수익률 추이 선 그래프
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["Earnings_Yield"],
          mode="lines+markers",
          name="주가 기대수익률(%)",
          line=dict(color="#1f77b4", width=2.5),
      )
  )

  # 역사적 평균선
  fig.add_hline(
      y=ey_mean,
      line_dash="dash",
      line_color="green",
      annotation_text=f"역사적 평균 ({ey_mean:.2f}%)",
      annotation_position="bottom right",
  )

  # 고평가(과매수) 경계선 (+1SD)
  fig.add_hline(
      y=upper_band,
      line_dash="dot",
      line_color="red",
      annotation_text=f"고평가 경계 +1SD ({upper_band:.2f}%)",
      annotation_position="top right",
  )

  # 저평가(과매도) 경계선 (-1SD)
  fig.add_hline(
      y=lower_band,
      line_dash="dot",
      line_color="blue",
      annotation_text=f"저평가 경계 -1SD ({lower_band:.2f}%)",
      annotation_position="bottom right",
  )

  fig.update_layout(
      xaxis_title="기간",
      yaxis_title="기대수익률 (%)",
      hovermode="x unified",
      height=550,
  )

  st.plotly_chart(fig, use_container_width=True)

  # 현재 시장 위치 진단 결과
  st.subheader("💡 현재 시장 위치 정밀 진단")
  if latest_ey >= upper_band:
    st.success(
        "🟢 **현재 구간: 과매도 (강력한 저평가 매수 기회 영역)**\n- 주가기대수익률이"
        " 역사적 평균보다 1 표준편차 이상 높아, 기업 실적 대비 주가가 매력적인"
        " 저평가 구간에 있습니다."
    )
  elif latest_ey <= lower_band:
    st.error(
        "🔴 **현재 구간: 과매수 (고평가 경계 영역)**\n- 주가기대수익률이 역사적"
        " 평균보다 낮아져, 시장 전체가 실적 대비 고평가되어 있을 가능성이"
        " 높은 경계 구간입니다."
    )
  else:
    st.info(
        "🟡 **현재 구간: 중립 (역사적 평균 영역)**\n- 시장이 통상적인 밸류에이션"
        " 변동 범위 내에서 안정적으로 움직이고 있습니다."
    )
else:
  st.error("데이터를 불러오지 못했습니다.")
