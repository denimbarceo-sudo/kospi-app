from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 웹 페이지 설정
st.set_page_config(
    page_title="코스피 주가기대수익률 & 밸류에이션 진단 앱", layout="wide"
)

st.title("📈 코스피 장기 주가기대수익률(EY) & 밸류에이션 진단 앱")
st.markdown(
    "KRX(한국거래소) 공식 통계 데이터를 바탕으로 산출한 코스피 주가기대수익률과"
    " 현재 시장의 과매수·과매도 구간을 직관적으로 확인하세요."
)


# 데이터 로드 및 전처리 함수 (인코딩 및 컬럼 자동 감지 기능 포함)
@st.cache_data
def load_data():
  try:
    # 1. CSV 파일 읽기 (한글 인코딩 자동 대응)
    try:
      df = pd.read_csv("kospi_data.csv", encoding="utf-8-sig")
    except UnicodeDecodeError:
      df = pd.read_csv("kospi_data.csv", encoding="cp949")

    # 컬럼명 앞뒤 공백 제거
    df.columns = df.columns.str.strip()

    # 필수 컬럼 자동 탐색
    date_col = next(
        (col for col in df.columns if "일자" in col or "date" in col.lower()),
        None,
    )
    per_col = next((col for col in df.columns if "per" in col.lower()), None)
    close_col = next(
        (
            col
            for col in df.columns
            if "종가" in col or "지수" in col or "close" in col.lower()
        ),
        None,
    )

    if not date_col or not per_col:
      return (
          pd.DataFrame(),
          "CSV 파일에 '일자(Date)' 또는 'PER' 컬럼이 존재하지 않습니다.",
      )

    # 데이터 프레임 정돈
    clean_df = pd.DataFrame()
    clean_df["Date"] = pd.to_datetime(df[date_col])
    clean_df["PER"] = pd.to_numeric(
        df[per_col].astype(str).str.replace(",", ""), errors="coerce"
    )

    if close_col:
      clean_df["Close"] = pd.to_numeric(
          df[close_col].astype(str).str.replace(",", ""), errors="coerce"
      )
    else:
      clean_df["Close"] = 0.0

    clean_df = clean_df.dropna(subset=["Date", "PER"]).sort_values("Date")
    clean_df.set_index("Date", inplace=True)

    # 핵심 공식: 주가기대수익률(Earnings Yield, %) = (1 / PER) * 100
    clean_df["Earnings_Yield"] = (1 / clean_df["PER"]) * 100

    return clean_df, None
  except Exception as e:
    return pd.DataFrame(), str(e)


# 데이터 로드 실행
df, err = load_data()

if not df.empty:
  # 최신 지표 추출
  latest_date = df.index[-1].strftime("%Y-%m-%d")
  latest_per = df["PER"].iloc[-1]
  latest_close = df["Close"].iloc[-1] if "Close" in df.columns else 0
  latest_ey = df["Earnings_Yield"].iloc[-1]

  ey_mean = df["Earnings_Yield"].mean()
  ey_std = df["Earnings_Yield"].std()

  # 상단 요약 지표 카드 배치
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("기준일자", latest_date)
  if latest_close > 0:
    col2.metric("코스피 지수(종가)", f"{latest_close:,.2f}")
  else:
    col2.metric("코스피 지수", "데이터 없음")
  col3.metric("KRX 공식 PER", f"{latest_per:.2f}")
  col4.metric(
      "주가 기대수익률 (EY)",
      f"{latest_ey:.2f}%",
      delta=f"역사적 평균 대비 ({latest_ey - ey_mean:+.2f}%)",
  )

  st.divider()

  # 차트 시각화 (Plotly)
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

  # 역사적 평균선 및 표준편차 밴드 추가
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
      xaxis_title="연도",
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
      "데이터 파일을 불러오지 못했습니다. 앱 폴더에 'kospi_data.csv' 파일이"
      " 올바르게 위치해 있는지 확인해주세요."
  )
  if err:
    st.info(f"기술적 에러 내용: {err}")
