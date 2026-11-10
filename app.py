from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="코스피 단기 주가기대수익률 & 밸류에이션 진단", layout="wide"
)

st.title("📈 코스피 단기 주가기대수익률(EY) & 밸류에이션 분석")
st.markdown(
    "최근 시장 데이터를 바탕으로 산출한 주가기대수익률(Earnings Yield) 추이와"
    " 현재 밸류에이션 위치를 확인합니다."
)


@st.cache_data
def load_short_term_data():
  try:
    # 1. 단기 데이터 CSV 읽기 시도
    df = pd.read_csv("kospi_data.csv", encoding="cp949")
  except Exception:
    try:
      df = pd.read_csv("kospi_data.csv", encoding="utf-8-sig")
    except Exception:
      # 파일이 없을 경우 최근 1년(12개월) 기준 샘플 데이터 자동 생성
      dates = pd.date_range(end=datetime.today(), periods=12, freq="ME")
      np.random.seed(10)
      sample_per = np.linspace(10.0, 11.5, 12) + np.random.normal(0, 0.2, 12)
      sample_close = np.linspace(2500, 2700, 12) + np.random.normal(0, 20, 12)

      clean_df = pd.DataFrame(
          {"Close": sample_close, "PER": sample_per}, index=dates
      )
      clean_df["Earnings_Yield"] = (1 / clean_df["PER"]) * 100
      return (
          clean_df,
          "현재 업로드된 파일이 없어 최근 1년 샘플 데이터로 구동 중입니다.",
      )

  # 데이터 전처리
  df.columns = df.columns.str.strip()
  # 세로형 또는 가로형 유연하게 대응
  if "PER" in df.columns:
    df["Date"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    df["PER"] = pd.to_numeric(
        df["PER"].astype(str).str.replace(",", ""), errors="coerce"
    )
    df.set_index("Date", inplace=True)
  else:
    # 가로형 구조 처리 (KOSIS/엑셀 형태)
    date_cols = [
        c for c in df.columns if "." in str(c) and len(str(c).strip()) == 7
    ]
    if len(date_cols) > 0:
      row = df.iloc[0]
      dates, pers = [], []
      for c in date_cols:
        try:
          val = float(str(row[c]).replace(",", ""))
          d = pd.to_datetime(str(c).strip().replace(".", "-") + "-01")
          dates.append(d)
          pers.append(val)
        except:
          continue
      df = pd.DataFrame({"PER": pers}, index=dates)

  df = df.dropna().sort_index()
  df["Earnings_Yield"] = (1 / df["PER"]) * 100
  return df, None


df, warning_msg = load_short_term_data()
if warning_msg:
  st.warning(warning_msg)

if not df.empty:
  latest_date = df.index[-1].strftime("%Y-%m-%d")
  latest_per = df["PER"].iloc[-1]
  latest_ey = df["Earnings_Yield"].iloc[-1]
  mean_ey = df["Earnings_Yield"].mean()

  # 상단 지표 카드
  st.subheader(f"📌 단기 핵심 밸류에이션 지표 (기준일: {latest_date})")
  c1, c2, c3 = st.columns(3)
  c1.metric("코스피 PER", f"{latest_per:.2f}")
  c2.metric("주가 기대수익률 (EY)", f"{latest_ey:.2f}%")
  c3.metric("기간 평균 EY", f"{mean_ey:.2f}%")

  st.divider()

  # 차트
  st.subheader("📊 단기 주가기대수익률 추이")
  fig = go.Figure()
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["Earnings_Yield"],
          mode="lines+markers",
          name="기대수익률(%)",
          line=dict(color="#2ca02c", width=3),
      )
  )
  fig.add_hline(
      y=mean_ey,
      line_dash="dash",
      line_color="gray",
      annotation_text=f"평균 ({mean_ey:.2f}%)",
  )
  fig.update_layout(xaxis_title="기간", yaxis_title="기대수익률 (%)", height=450)
  st.plotly_chart(fig, use_container_width=True)
else:
  st.error("데이터를 처리할 수 없습니다.")
