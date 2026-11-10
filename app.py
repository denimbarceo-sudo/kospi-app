from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 웹 페이지 설정
st.set_page_config(
    page_title="코스피 장기 주가기대수익률 & 밸류에이션 진단 앱", layout="wide"
)

st.title("📈 코스피 5년 주가기대수익률(EY) & 실시간 밸류에이션 진단")
st.markdown(
    "코스피 지수 및 PER 데이터를 바탕으로 산출한 주가기대수익률(Earnings Yield)"
    " 추이를 확인하고 현재 시장의 과매수·과매도 구간을 진단합니다."
)


@st.cache_data
def load_data():
  target_files = ["kospi_data.csv", "kospi_eps_data.csv"]
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

  if df is None or df.empty:
    # 파일이 없을 경우 안전한 샘플 데이터 생성
    dates = pd.date_range(end=datetime.today(), periods=60, freq="ME")
    np.random.seed(42)
    sample_per = np.linspace(10, 12, 60) + np.random.normal(0, 1, 60)
    sample_close = np.linspace(2500, 3000, 60) + np.random.normal(0, 50, 60)
    df_sample = pd.DataFrame({
        "Date": dates,
        "Close": sample_close,
        "PER": sample_per,
    })
    df_sample.set_index("Date", inplace=True)
    df_sample["Earnings_Yield"] = (1 / df_sample["PER"]) * 100
    return df_sample, "현재 업로드된 파일이 없어 가상 샘플 데이터로 구동 중입니다."

  df.columns = df.columns.str.strip()

  # KOSIS 가로 나열형(날짜가 컬럼인 경우) 자동 감지
  date_like_cols = [
      c for c in df.columns if "." in str(c) and len(str(c).strip()) == 7
  ]

  if len(date_like_cols) > 5:
    kospi_row = None
    for idx, row in df.iterrows():
      row_str = str(row.values)
      if "KOSPI" in row_str and "소계" in row_str:
        kospi_row = row
        break
    if kospi_row is None:
      kospi_row = df.iloc[0]

    dates = []
    pers = []
    for col in date_like_cols:
      val = kospi_row[col]
      try:
        num_val = float(str(val).replace(",", ""))
        d = pd.to_datetime(str(col).strip().replace(".", "-") + "-01")
        dates.append(d)
        pers.append(num_val)
      except ValueError:
        continue

    clean_df = pd.DataFrame({"Date": dates, "PER": pers})
    clean_df = clean_df.dropna().sort_values("Date")
    clean_df.set_index("Date", inplace=True)
    clean_df["Close"] = 0.0
    clean_df["Earnings_Yield"] = (1 / clean_df["PER"]) * 100
    return clean_df, None
  else:
    # 일반 세로형 구조 처리
    date_col = next(
        (
            col
            for col in df.columns
            if "일자" in col or "시점" in col or "date" in col.lower()
        ),
        df.columns[0],
    )
    per_col = next(
        (
            col
            for col in df.columns
            if "per" in col.lower() or "주가이익비율" in col
        ),
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

    if not per_col:
      return (
          pd.DataFrame(),
          f"데이터 파일에서 PER 컬럼을 찾을 수 없습니다. (현재 컬럼명:"
          f" {list(df.columns)})",
      )

    clean_df = pd.DataFrame()
    clean_df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
    clean_df["PER"] = pd.to_numeric(
        df[per_col].astype(str).str.replace(",", ""), errors="coerce"
    )
    clean_df["Close"] = (
        pd.to_numeric(
            df[close_col].astype(str).str.replace(",", ""), errors="coerce"
        )
        if close_col
        else 0.0
    )

    clean_df = clean_df.dropna(subset=["Date", "PER"]).sort_values("Date")
    clean_df.set_index("Date", inplace=True)
    clean_df["Earnings_Yield"] = (1 / clean_df["PER"]) * 100
    return clean_df, None


df, warning_msg = load_data()
if warning_msg:
  st.warning(warning_msg)

if not df.empty:
  latest_date = df.index[-1].strftime("%Y-%m-%d")
  latest_per = df["PER"].iloc[-1]
  latest_ey = df["Earnings_Yield"].iloc[-1]
  ey_mean = df["Earnings_Yield"].mean()
  ey_std = df["Earnings_Yield"].std()

  st.subheader(f"📌 코스피 핵심 밸류에이션 지표 (기준일: {latest_date})")
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("코스피 PER", f"{latest_per:.2f}")
  col2.metric("주가 기대수익률 (EY)", f"{latest_ey:.2f}%")
  col3.metric("역사적 평균 EY", f"{ey_mean:.2f}%")
  col4.metric("역사적 평균 대비", f"{latest_ey - ey_mean:+.2f}%")

  st.divider()

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

  st.subheader("💡 현재 시장 위치 진단")
  if latest_ey >= (ey_mean + ey_std):
    st.success(
        "🟢 **현재 구간: 과매도 (강력한 저평가 매수 기회 구간)**\n- 역사적으로"
        " 기대수익률이 평균보다 높아 밸류에이션 매력도가 매우 높은 국면입니다."
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
