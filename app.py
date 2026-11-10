from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 웹 페이지 설정
st.set_page_config(
    page_title="코스피 장기 주가기대수익률 & 밸류에이션 진단 앱", layout="wide"
)

st.title("📈 코스피 5년 주가기대수익률(EY) & 실시간 밸류에이션 진단")
st.markdown(
    "코스피 지수, PER, EPS 데이터를 바탕으로 산출한 주가기대수익률(Earnings Yield)"
    " 추이를 확인하고 현재 시장의 과매수·과매도 구간을 진단합니다."
)


# 데이터 로드 함수 (오류 원인 원천 차단)
@st.cache_data
def load_data():
  # 1. 파일 읽기 시도 ('kospi_eps_data.csv' 또는 기존에 올리셨던 'kospi_data.csv' 모두 대응)
  target_files = ["kospi_eps_data.csv", "kospi_data.csv"]
  df = None

  for filename in target_files:
    try:
      df = pd.read_csv(filename, encoding="cp949")
      break
    except Exception:
      try:
        df = pd.read_csv(filename, encoding="utf-8-sig")
        break
      except Exception:
        continue

  # 2. 파일을 못 찾았을 경우 안전한 샘플 데이터 생성 (최신 판다스 호환 freq='ME')
  if df is None or df.empty:
    import numpy as np

    dates = pd.date_range(end=datetime.today(), periods=60, freq="ME")
    np.random.seed(42)
    sample_per = np.linspace(10, 12, 60) + np.random.normal(0, 1, 60)
    sample_close = np.linspace(2500, 3000, 60) + np.random.normal(0, 50, 60)
    sample_eps = sample_close / sample_per

    df_sample = pd.DataFrame({
        "Date": dates,
        "Close": sample_close,
        "PER": sample_per,
        "EPS": sample_eps,
    })
    df_sample.set_index("Date", inplace=True)
    df_sample["Earnings_Yield"] = (1 / df_sample["PER"]) * 100
    return (
        df_sample,
        "현재 업로드된 CSV 파일이 없어 가상 샘플 데이터로 구동 중입니다. 원하시는"
        " CSV 파일을 업로드하면 즉시 반영됩니다.",
    )

  # 정상적으로 파일을 읽었을 경우 전처리
  df.columns = df.columns.str.strip()

  date_col = next(
      (
          col
          for col in df.columns
          if "일자" in col or "시점" in col or "date" in col.lower()
      ),
      df.columns[0],
  )
  per_col = next(
      (col for col in df.columns if "per" in col.lower() or "주가이익비율" in col),
      None,
  )
  close_col = next(
      (
          col
          for col in df.columns
          if "종가" in col or "지수" in col or "close" in col.lower()
      ),
      None,
  )
  eps_col = next(
      (col for col in df.columns if "eps" in col.lower() or "주당순이익" in col),
      None,
  )

  clean_df = pd.DataFrame()
  clean_df["Date"] = pd.to_datetime(df[date_col], errors="coerce")

  if per_col:
    clean_df["PER"] = pd.to_numeric(
        df[per_col].astype(str).str.replace(",", ""), errors="coerce"
    )
  else:
    return pd.DataFrame(), "데이터 파일에서 PER 컬럼을 찾을 수 없습니다."

  if close_col:
    clean_df["Close"] = pd.to_numeric(
        df[close_col].astype(str).str.replace(",", ""), errors="coerce"
    )
  else:
    clean_df["Close"] = 0.0

  if eps_col:
    clean_df["EPS"] = pd.to_numeric(
        df[eps_col].astype(str).str.replace(",", ""), errors="coerce"
    )
  else:
    clean_df["EPS"] = clean_df["Close"] / clean_df["PER"]

  clean_df = clean_df.dropna(subset=["Date", "PER"]).sort_values("Date")
  clean_df.set_index("Date", inplace=True)

  # 핵심 공식: 주가기대수익률(Earnings Yield, %) = (1 / PER) * 100
  clean_df["Earnings_Yield"] = (1 / clean_df["PER"]) * 100

  return clean_df, None


# 데이터 로드 실행
df, warning_msg = load_data()

if warning_msg:
  st.warning(warning_msg)

if not df.empty:
  # 최신 지표 추출
  latest_date = df.index[-1].strftime("%Y-%m-%d")
  latest_close = df["Close"].iloc[-1]
  latest_per = df["PER"].iloc[-1]
  latest_eps = df["EPS"].iloc[-1]
  latest_ey = df["Earnings_Yield"].iloc[-1]

  ey_mean = df["Earnings_Yield"].mean()
  ey_std = df["Earnings_Yield"].std()

  # 상단 핵심 요약 지표 카드 배치
  st.subheader(f"📌 코스피 핵심 밸류에이션 지표 (기준일: {latest_date})")
  col1, col2, col3, col4, col5 = st.columns(5)
  col1.metric("코스피 지수", f"{latest_close:,.2f}" if latest_close > 0 else "정보 없음")
  col2.metric("코스피 PER", f"{latest_per:.2f}")
  col3.metric("코스피 EPS (환산)", f"{latest_eps:,.1f}")
  col4.metric("주가 기대수익률 (EY)", f"{latest_ey:.2f}%")
  col5.metric("역사적 평균 대비", f"{latest_ey - ey_mean:+.2f}%")

  st.divider()

  # 차트 시각화 (Plotly)
  st.subheader("📊 코스피 장기 주가기대수익률(Earnings Yield) 추이")

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
      annotation_text=f"평균 ({ey_mean:.2f}%)",
  )
  fig.add_hline(
      y=ey_mean + ey_std,
      line_dash="dot",
      line_color="red",
      annotation_text="고평가 경계 (+1SD)",
  )
  fig.add_hline(
      y=ey_mean - ey_std,
      line_dash="dot",
      line_color="blue",
      annotation_text="저평가 경계 (-1SD)",
  )

  fig.update_layout(
      xaxis_title="연도",
      yaxis_title="기대수익률 (%)",
      hovermode="x unified",
      height=500,
  )

  st.plotly_chart(fig, use_container_width=True)

  # 시장 진단 메시지
  st.subheader("💡 현재 시장 위치 진단")
  if latest_ey >= (ey_mean + ey_std):
    st.success(
        "🟢 **현재 구간: 과매도 (강력한 저평가 매수 기회 구간)**\n- 역사적으로"
        " 기대수익률이 평균보다 높아 주식의 밸류에이션 매력도가 매우 높은"
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
        " 범위 내에서 안정적으로 움직이고 있습니다."
    )
else:
  st.error("데이터를 불러올 수 없습니다.")
