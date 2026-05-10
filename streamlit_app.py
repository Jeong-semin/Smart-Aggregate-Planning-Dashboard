# -*- coding: utf-8 -*-
"""
Created on Fri May  8 11:11:33 2026

@author: 정세민
"""

# -*- coding: utf-8 -*-

import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# 한글 그래프 설정
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

st.set_page_config(
    page_title="총괄생산계획 대시보드",
    layout="wide"
)


# -----------------------------
# 입력값 처리 함수
# -----------------------------
def parse_demand_input(demand_text: str):
    try:
        values = [int(x.strip()) for x in demand_text.split(",") if x.strip() != ""]
        if len(values) == 0:
            raise ValueError("수요를 최소 1개 이상 입력해야 합니다.")
        if any(v < 0 for v in values):
            raise ValueError("수요는 음수일 수 없습니다.")
        return values, None
    except Exception as e:
        return None, str(e)


# -----------------------------
# KPI 계산 함수
# -----------------------------
def build_kpi_dict(df: pd.DataFrame):
    return {
        "총비용": float(df["Total Cost"].sum()),
        "평균재고": float(df["Ending Inventory"].mean()),
        "최대재고": float(df["Ending Inventory"].max()),
        "총고용": float(df["Hire"].sum()),
        "총해고": float(df["Fire"].sum()),
        "평균인력": float(df["Workers"].mean()),
        "인력변동폭": float(df["Workers"].diff().abs().fillna(0).sum()),
    }


# -----------------------------
# 전략 1: 수요추종 전략
# -----------------------------
def calculate_chase_strategy(
    demand,
    prod_per_worker,
    init_workers,
    init_inventory,
    hire_cost,
    fire_cost,
    prod_cost,
    inv_cost
):
    records = []
    current_workers = init_workers
    current_inventory = init_inventory

    for t, d in enumerate(demand, start=1):
        required_production = max(0, d - current_inventory)
        required_workers = math.ceil(required_production / prod_per_worker)

        hire = max(0, required_workers - current_workers)
        fire = max(0, current_workers - required_workers)

        current_workers = required_workers
        production = current_workers * prod_per_worker

        available = current_inventory + production
        ending_inventory = max(0, available - d)

        cost = (
            hire * hire_cost
            + fire * fire_cost
            + production * prod_cost
            + ending_inventory * inv_cost
        )

        records.append({
            "Month": t,
            "Demand": d,
            "Production": production,
            "Workers": current_workers,
            "Hire": hire,
            "Fire": fire,
            "Beginning Inventory": current_inventory,
            "Ending Inventory": ending_inventory,
            "Total Cost": cost,
            "Strategy": "수요추종 전략"
        })

        current_inventory = ending_inventory

    return pd.DataFrame(records)


# -----------------------------
# 전략 2: 평준화 전략
# -----------------------------
def calculate_level_strategy(
    demand,
    prod_per_worker,
    init_workers,
    init_inventory,
    hire_cost,
    fire_cost,
    prod_cost,
    inv_cost
):
    avg_demand = np.mean(demand)
    target_workers = math.ceil(avg_demand / prod_per_worker)

    records = []
    current_inventory = init_inventory

    first_hire = max(0, target_workers - init_workers)
    first_fire = max(0, init_workers - target_workers)

    for t, d in enumerate(demand, start=1):
        hire = first_hire if t == 1 else 0
        fire = first_fire if t == 1 else 0

        production = target_workers * prod_per_worker
        available = current_inventory + production
        ending_inventory = max(0, available - d)

        cost = (
            hire * hire_cost
            + fire * fire_cost
            + production * prod_cost
            + ending_inventory * inv_cost
        )

        records.append({
            "Month": t,
            "Demand": d,
            "Production": production,
            "Workers": target_workers,
            "Hire": hire,
            "Fire": fire,
            "Beginning Inventory": current_inventory,
            "Ending Inventory": ending_inventory,
            "Total Cost": cost,
            "Strategy": "평준화 전략"
        })

        current_inventory = ending_inventory

    return pd.DataFrame(records)


# -----------------------------
# 자동 해석 함수
# -----------------------------
def evaluate_plan(chase_df, level_df):
    chase_kpi = build_kpi_dict(chase_df)
    level_kpi = build_kpi_dict(level_df)

    comments = []

    if chase_kpi["총비용"] < level_kpi["총비용"]:
        comments.append(
            f"비용 측면에서는 수요추종 전략이 더 유리합니다. "
            f"수요추종 총비용은 {chase_kpi['총비용']:.0f}, "
            f"평준화 총비용은 {level_kpi['총비용']:.0f}입니다."
        )
    elif chase_kpi["총비용"] > level_kpi["총비용"]:
        comments.append(
            f"비용 측면에서는 평준화 전략이 더 유리합니다. "
            f"평준화 총비용은 {level_kpi['총비용']:.0f}, "
            f"수요추종 총비용은 {chase_kpi['총비용']:.0f}입니다."
        )
    else:
        comments.append("두 전략의 총비용은 동일합니다.")

    if chase_kpi["총고용"] + chase_kpi["총해고"] > level_kpi["총고용"] + level_kpi["총해고"]:
        comments.append("수요추종 전략은 고용과 해고가 많아 인력 운영 안정성이 낮을 수 있습니다.")
    else:
        comments.append("평준화 전략은 인력 변동이 적어 운영 안정성이 높습니다.")

    if level_kpi["평균재고"] > chase_kpi["평균재고"]:
        comments.append("평준화 전략은 평균 재고가 높아 재고 유지비 부담이 커질 수 있습니다.")
    else:
        comments.append("수요추종 전략은 재고 수준을 상대적으로 낮게 유지합니다.")

    return comments, chase_kpi, level_kpi


# -----------------------------
# 그래프 함수
# -----------------------------
def make_line_chart(x, y1, y2, label1, label2, title, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x, y1, marker="o", linewidth=2, label=label1)
    ax.plot(x, y2, marker="s", linewidth=2, label=label2)
    ax.set_title(title, fontsize=13)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig


def make_demand_production_chart(months, demand, chase_prod, level_prod):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(months, demand, marker="o", linewidth=2, label="월별 수요")
    ax.plot(months, chase_prod, marker="s", linewidth=2, label="수요추종 전략 생산량")
    ax.plot(months, level_prod, marker="^", linewidth=2, label="평준화 전략 생산량")
    ax.set_title("월별 수요와 생산량 비교", fontsize=13)
    ax.set_xlabel("월")
    ax.set_ylabel("수량")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig


def make_cost_bar_chart(chase_kpi, level_kpi):
    fig, ax = plt.subplots(figsize=(7, 4))
    strategies = ["수요추종 전략", "평준화 전략"]
    costs = [chase_kpi["총비용"], level_kpi["총비용"]]

    ax.bar(strategies, costs)
    ax.set_title("전략별 총비용 비교", fontsize=13)
    ax.set_xlabel("전략")
    ax.set_ylabel("총비용")
    ax.grid(True, axis="y", alpha=0.3)

    for i, v in enumerate(costs):
        ax.text(i, v, f"{v:.0f}", ha="center", va="bottom")

    return fig


def make_cost_trend_chart(months, chase_cost, level_cost):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(months, chase_cost, marker="o", linewidth=2, label="수요추종 전략 비용")
    ax.plot(months, level_cost, marker="s", linewidth=2, label="평준화 전략 비용")
    ax.set_title("월별 비용 변화 비교", fontsize=13)
    ax.set_xlabel("월")
    ax.set_ylabel("비용")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig


# -----------------------------
# 앱 화면
# -----------------------------
st.title("원예장비 제조업체 총괄생산계획 의사결정 대시보드")

st.write(
    """
    이 웹앱은 월별 수요와 비용 파라미터를 바탕으로 원예장비 제조업체의 총괄생산계획을 수립하고,
    수요추종 전략과 평준화 전략을 비교하여 현재 계획의 적절성을 판단하는 데 도움을 줍니다.
    """
)

with st.sidebar:
    st.header("입력 파라미터")

    demand_text = st.text_area(
        "월별 수요 입력",
        value="120, 150, 180, 160, 140, 170",
        help="쉼표로 구분해서 입력하세요. 예: 120, 150, 180"
    )

    prod_per_worker = st.number_input("인력 1명당 월 생산량", min_value=1, value=10, step=1)
    init_workers = st.number_input("초기 인력 수", min_value=0, value=15, step=1)
    init_inventory = st.number_input("초기 재고량", min_value=0, value=0, step=1)

    st.subheader("비용 파라미터")
    prod_cost = st.number_input("단위 생산비용", min_value=0.0, value=20.0, step=1.0)
    inv_cost = st.number_input("단위 재고유지비용", min_value=0.0, value=5.0, step=1.0)
    hire_cost = st.number_input("1인당 고용비용", min_value=0.0, value=500.0, step=10.0)
    fire_cost = st.number_input("1인당 해고비용", min_value=0.0, value=700.0, step=10.0)

    st.subheader("수요 시나리오")
    scenario = st.selectbox(
        "시나리오 선택",
        ["기본 수요", "수요 10% 증가", "수요 10% 감소"]
    )

demand, error = parse_demand_input(demand_text)

if error:
    st.error(f"수요 입력 오류: {error}")
    st.stop()

if scenario == "수요 10% 증가":
    demand = [math.ceil(x * 1.1) for x in demand]
elif scenario == "수요 10% 감소":
    demand = [math.floor(x * 0.9) for x in demand]

chase_df = calculate_chase_strategy(
    demand, prod_per_worker, init_workers, init_inventory,
    hire_cost, fire_cost, prod_cost, inv_cost
)

level_df = calculate_level_strategy(
    demand, prod_per_worker, init_workers, init_inventory,
    hire_cost, fire_cost, prod_cost, inv_cost
)

comments, chase_kpi, level_kpi = evaluate_plan(chase_df, level_df)

# -----------------------------
# KPI 카드
# -----------------------------
st.subheader("핵심 KPI 비교")

c1, c2, c3, c4 = st.columns(4)
c1.metric("수요추종 총비용", f"{chase_kpi['총비용']:.0f}")
c2.metric("평준화 총비용", f"{level_kpi['총비용']:.0f}")
c3.metric("수요추종 평균재고", f"{chase_kpi['평균재고']:.1f}")
c4.metric("평준화 평균재고", f"{level_kpi['평균재고']:.1f}")

c5, c6, c7, c8 = st.columns(4)
c5.metric("수요추종 총고용", f"{chase_kpi['총고용']:.0f}")
c6.metric("평준화 총고용", f"{level_kpi['총고용']:.0f}")
c7.metric("수요추종 총해고", f"{chase_kpi['총해고']:.0f}")
c8.metric("평준화 총해고", f"{level_kpi['총해고']:.0f}")

# -----------------------------
# 자동 판단
# -----------------------------
st.subheader("계획 적절성 자동 판단")

for comment in comments:
    st.info(comment)

# -----------------------------
# 계획표
# -----------------------------
st.subheader("전략별 총괄생산계획표")

tab1, tab2 = st.tabs(["수요추종 전략", "평준화 전략"])

with tab1:
    st.write("수요 변화에 맞추어 인력을 조정하는 전략입니다.")
    st.dataframe(chase_df, use_container_width=True)

with tab2:
    st.write("평균 수요 수준에 맞추어 인력을 일정하게 유지하는 전략입니다.")
    st.dataframe(level_df, use_container_width=True)

# -----------------------------
# 대시보드
# -----------------------------
st.subheader("시각화 대시보드")

months = chase_df["Month"].tolist()

g1, g2 = st.columns(2)

with g1:
    fig1 = make_demand_production_chart(
        months,
        demand,
        chase_df["Production"],
        level_df["Production"]
    )
    st.pyplot(fig1)

with g2:
    fig2 = make_line_chart(
        months,
        chase_df["Workers"],
        level_df["Workers"],
        "수요추종 전략 인력",
        "평준화 전략 인력",
        "월별 인력 변화 비교",
        "월",
        "인력 수"
    )
    st.pyplot(fig2)

g3, g4 = st.columns(2)

with g3:
    fig3 = make_line_chart(
        months,
        chase_df["Ending Inventory"],
        level_df["Ending Inventory"],
        "수요추종 전략 재고",
        "평준화 전략 재고",
        "월별 재고 수준 비교",
        "월",
        "재고량"
    )
    st.pyplot(fig3)

with g4:
    fig4 = make_cost_trend_chart(
        months,
        chase_df["Total Cost"],
        level_df["Total Cost"]
    )
    st.pyplot(fig4)

st.pyplot(make_cost_bar_chart(chase_kpi, level_kpi))

# -----------------------------
# 결과 다운로드
# -----------------------------
st.subheader("결과 다운로드")

combined_df = pd.concat([chase_df, level_df], ignore_index=True)
csv_data = combined_df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="전략 비교 결과 CSV 다운로드",
    data=csv_data,
    file_name="aggregate_planning_results.csv",
    mime="text/csv"
)