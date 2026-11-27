"""Airtel Telecom Analytics - Network Usage Dashboard.

Run from the repository root with:
    streamlit run dashboard/app.py

Each chart and the Detail metrics section has independent filter widgets.
All displayed dashboard data is queried from the Airtel SQLite database.
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(
    os.environ.get(
        "AIRTEL_DB",
        str(ROOT / "data" / "raw" / "airtel.db"),
    )
)

BASE_CTE = """
base AS (
    SELECT u.customer_id AS sub_id,
           u.usage_date AS usage_date,
           strftime('%Y-%m', u.usage_date) AS month,
           u.data_mb / 1024.0 AS data_gb,
           c.connection_type AS conn_type,
           c.ab_group AS grp,
           p.plan_name AS plan,
           c.device_type AS device,
           p.monthly_gb AS allowance_gb
    FROM usage_daily u
    JOIN customers c ON c.customer_id = u.customer_id
    JOIN v_plans_clean p ON p.plan_id = c.current_plan_id
    WHERE u.data_mb > 0
)
"""

GB_PER_TB = 1024

# These are the existing fixed T3 results from the project's validated analysis.
# Do not derive or modify these values from the dashboard's chart filters.
T3_TEST = "T3 test: Group B vs Group A, data per usage day"
T3_P_VALUE = 0.021
T3_TAIL = "one-tailed"
T3_DIRECTION = "increase"
T3_ALPHA = 0.05

RED = "#E40000"
DEEP_RED = "#C40000"
BLUE = "#2F5597"
SLATE = "#5B6B8C"
LIGHT_PINK = "#FDECEC"
BG = "#F4F5F8"
PANEL = "#FFFFFF"
BORDER = "#DDE1E8"
TEXT = "#1F2430"
MUTED = "#6B7280"
GREY = "#9CA3AF"
CHART_H = 280

READER = (
    "This dashboard helps the Network Capacity Planner understand data demand, "
    "subscriber usage patterns and capacity-planning needs."
)


st.set_page_config(
    page_title="Airtel Telecom Analytics",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not DB_PATH.exists():
    st.error(
        f"Database not found at `{DB_PATH}`. "
        "Set the AIRTEL_DB environment variable to a valid Airtel SQLite database."
    )
    st.stop()


@st.cache_data(show_spinner=False)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run one parameterized SQL query and return the result."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def with_base(body: str) -> str:
    return f"WITH {BASE_CTE} {body}"


def month_label(value: str) -> str:
    return datetime.strptime(value, "%Y-%m").strftime("%B %Y")


def fmt_rate(value: float, n: int, digits: int = 2) -> str:
    return f"n={n:,}" if n < 100 else f"{value:,.{digits}f}"


def where_sql(**filters: str) -> tuple[str, tuple]:
    """Combine the global sidebar filters with a section's local filters."""
    column_names = {
        "month": "month",
        "group": "grp",
        "connection": "conn_type",
        "plan": "plan",
        "device": "device",
    }
    clauses = []
    params = []
    for filter_name, value in (
        ("connection", global_connection),
        ("group", global_group),
    ):
        if value != "All":
            clauses.append(f"{column_names[filter_name]} = ?")
            params.append(value)
    for filter_name, value in filters.items():
        if value != "All":
            clauses.append(f"{column_names[filter_name]} = ?")
            params.append(value)
    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(params)


def month_selectbox(label: str, key: str, months: list[str], default_latest: bool = False) -> str:
    month_options = ["All"] + months
    index = len(month_options) - 1 if default_latest else 0
    return st.selectbox(
        label,
        month_options,
        index=index,
        key=key,
        format_func=lambda value: "All months" if value == "All" else month_label(value),
    )


def card(
    icon: str,
    title: str,
    value: str,
    caption: str,
    fixed: bool = False,
    highlight: bool = False,
) -> None:
    badge = '<span class="fixed">EXISTING VALIDATED RESULT</span>' if fixed else ""
    card_class = "card highlight" if highlight else "card"
    st.markdown(
        f'<div class="{card_class}"><div class="icon">{icon}</div>'
        f'<div><div class="card-title">{title}{badge}</div>'
        f'<div class="card-value">{value}</div>'
        f'<div class="card-caption">{caption}</div></div></div>',
        unsafe_allow_html=True,
    )


def chart_title(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<p class="chart-title">{title}</p>'
        + (f'<p class="chart-subtitle">{subtitle}</p>' if subtitle else ""),
        unsafe_allow_html=True,
    )


def style_fig(fig: go.Figure, height: int = CHART_H, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=42, r=20, t=22, b=42),
        plot_bgcolor=PANEL,
        paper_bgcolor=PANEL,
        font=dict(size=11, color=TEXT),
        showlegend=legend,
        legend=dict(orientation="h", y=1.08, x=0),
        bargap=0.24,
    )
    fig.update_xaxes(gridcolor="#EDF0F4", zeroline=False)
    fig.update_yaxes(gridcolor="#EDF0F4", zeroline=False)
    return fig


def show(fig: go.Figure) -> None:
    try:
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


st.markdown(
    f"""
    <style>
      header[data-testid="stHeader"], footer {{ display:none; }}
      [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display:none !important; }}
      .stApp {{ background:{BG}; color:{TEXT}; }}
      .block-container {{ max-width:1920px; padding:0.65rem 1.25rem 1.2rem; }}
      div[data-testid="stVerticalBlock"] {{ gap:0.8rem; }}
      [data-testid="stSidebar"] {{ background:#E9ECF2; }}
      [data-testid="stSidebar"] .block-container {{ padding-top:1.2rem; }}
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
      [data-testid="stSidebar"] [data-testid="stMetricLabel"],
      [data-testid="stSidebar"] [data-testid="stMetricValue"] {{ color:{TEXT} !important; }}
      .sidebar-brand {{ color:{RED}; font-size:1.8rem; font-weight:800; margin:0 0 2px; }}
      .sidebar-heading {{ color:{TEXT}; font-size:1rem; font-weight:800; margin:14px 0 3px; }}
      .sidebar-card {{ background:#fff; border:1px solid {BORDER}; border-radius:10px;
                       padding:10px 12px; margin:8px 0; }}
      .sidebar-card-title {{ color:{MUTED}; font-size:.68rem; font-weight:700;
                             text-transform:uppercase; letter-spacing:.04em; }}
      .sidebar-card-value {{ color:{TEXT}; font-size:1.22rem; font-weight:800; margin:2px 0 6px; }}
      .sidebar-help {{ color:{MUTED}; font-size:.72rem; line-height:1.35; }}

      .dashboard-header {{
        display:flex; align-items:center; gap:18px; padding:12px 20px;
        margin-bottom:8px; border-radius:11px; color:#fff;
        background:linear-gradient(90deg,#A8000A,{RED},#C40000);
      }}
      .brand {{ font-size:2rem; font-weight:800; line-height:1; }}
      .header-divider {{ width:1px; height:44px; background:rgba(255,255,255,.55); }}
      .header-title {{ font-size:1.55rem; font-weight:800; line-height:1.15; }}
      .header-reader {{ font-size:.8rem; opacity:.96; margin-top:3px; }}

      .card {{
        display:flex; align-items:center; gap:12px; height:110px;
        padding:10px 14px; margin-bottom:6px; background:{PANEL};
        border:1px solid {BORDER}; border-radius:12px;
        box-shadow:0 1px 3px rgba(20,25,40,.06);
      }}
      .card.highlight {{ background:{LIGHT_PINK}; border-color:#F3B1B6; }}
      .icon {{
        flex:0 0 44px; width:44px; height:44px; display:flex;
        align-items:center; justify-content:center; border-radius:50%;
        background:{LIGHT_PINK}; font-size:1.25rem;
      }}
      .card-title {{ font-size:.8rem; font-weight:700; color:{TEXT}; }}
      .card-value {{ font-size:1.48rem; font-weight:800; color:{RED}; line-height:1.2; }}
      .card-caption {{ font-size:.68rem; color:{MUTED}; line-height:1.25; }}
      .fixed {{ display:block; font-size:.55rem; color:{RED}; font-weight:700; }}

      div[data-testid="stVerticalBlockBorderWrapper"] {{
        background:{PANEL}; border:1px solid {BORDER}; border-radius:12px;
        padding:12px 14px 10px; box-shadow:0 1px 3px rgba(20,25,40,.05);
      }}
      .chart-title {{
        margin:4px 0 3px; padding-left:8px; border-left:4px solid {RED};
        color:{TEXT}; font-size:.94rem; font-weight:800; line-height:1.25;
      }}
      .chart-subtitle {{ margin:0 0 6px 12px; color:{MUTED}; font-size:.7rem; line-height:1.25; }}
      [data-testid="stWidgetLabel"] p {{ color:{TEXT}; font-weight:600; }}
      [data-baseweb="select"] > div {{ background:#fff; }}
      button[data-baseweb="tab"] {{ font-weight:700; }}
      button[data-baseweb="tab"][aria-selected="true"] {{ color:{RED}; }}
      @media (max-width: 1100px) {{
        .block-container {{ padding-left:.75rem; padding-right:.75rem; }}
        .dashboard-header {{ gap:10px; padding:10px 14px; }}
        .header-title {{ font-size:1.3rem; }}
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


# Validate the database mapping early and report an actionable error if the
# configured database differs from the project's Airtel schema.
try:
    q(with_base("SELECT 1 FROM base LIMIT 1"))
except (sqlite3.Error, pd.errors.DatabaseError) as err:
    st.error(f"Could not read the Airtel tables using the configured schema: {err}")
    st.stop()


st.markdown(
    f'<div class="dashboard-header"><div class="brand">airtel</div>'
    f'<div class="header-divider"></div><div>'
    f'<div class="header-title">Airtel Telecom Analytics</div>'
    f'<div class="header-reader">{READER}</div></div></div>',
    unsafe_allow_html=True,
)

overview_tab, detail_tab = st.tabs(["Overview", "Detail"])

months = q(with_base("SELECT DISTINCT month FROM base ORDER BY month"))["month"].tolist()
connections = q(with_base("SELECT DISTINCT conn_type FROM base WHERE conn_type IS NOT NULL ORDER BY 1"))[
    "conn_type"
].astype(str).tolist()
groups = q(with_base("SELECT DISTINCT grp FROM base WHERE grp IS NOT NULL ORDER BY 1"))["grp"].astype(str).tolist()
plans = q(with_base("SELECT DISTINCT plan FROM base WHERE plan IS NOT NULL ORDER BY 1"))["plan"].astype(str).tolist()
devices = q(with_base("SELECT DISTINCT device FROM base WHERE device IS NOT NULL ORDER BY 1"))[
    "device"
].astype(str).tolist()

month_options = ["All"] + months
connection_options = ["All"] + connections
group_options = ["All"] + groups
plan_options = ["All"] + plans
device_options = ["All"] + devices

with st.sidebar:
    st.markdown('<div class="sidebar-brand">airtel</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-heading">Telecom Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-help">Network usage and capacity-planning insights from the Airtel dataset.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("**Global filters**")
    global_connection = st.selectbox(
        "Connection Type",
        connection_options,
        key="sidebar_global_connection",
    )
    global_group = st.selectbox(
        "Experiment Group",
        group_options,
        key="sidebar_global_group",
    )
    st.markdown(
        '<div class="sidebar-help">These filters apply across all charts and Detail metrics. '
        'Use chart-level controls for additional local filtering.</div>',
        unsafe_allow_html=True,
    )
    sidebar_where, sidebar_params = where_sql()
    sidebar_summary = q(
        with_base(
            f"""SELECT COUNT(DISTINCT sub_id) AS customers,
                       COUNT(*) AS usage_records,
                       MIN(usage_date) AS first_date,
                       MAX(usage_date) AS last_date
                FROM base {sidebar_where}"""
        ),
        sidebar_params,
    ).iloc[0]
    st.markdown("---")
    st.markdown("**Database snapshot**")
    st.markdown(
        f'<div class="sidebar-card">'
        f'<div class="sidebar-card-title">Unique customers</div>'
        f'<div class="sidebar-card-value">{int(sidebar_summary["customers"]):,}</div>'
        f'<div class="sidebar-card-title">Usage records</div>'
        f'<div class="sidebar-card-value">{int(sidebar_summary["usage_records"]):,}</div>'
        f'<div class="sidebar-help">Data period: {sidebar_summary["first_date"]} to {sidebar_summary["last_date"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown(
        '<div class="sidebar-help">Choose Overview or Detail using the tabs at the top of the dashboard.</div>',
        unsafe_allow_html=True,
    )


with overview_tab:
    overview_where, overview_params = where_sql()
    overview_metrics = q(
        with_base(
            f"""SELECT COUNT(*) AS usage_days,
                      COALESCE(SUM(data_gb) * 1.0 / NULLIF(COUNT(*), 0), 0) AS per_usage_day,
                      COALESCE(
                          SUM(data_gb) * 1.0 /
                          NULLIF(COUNT(DISTINCT sub_id) * COUNT(DISTINCT usage_date), 0),
                          0
                      ) AS per_calendar_day
               FROM base {overview_where}"""
        ),
        overview_params,
    ).iloc[0]

    metric_a, metric_b, metric_c = st.columns(3, gap="large")
    with metric_a:
        card(
            "📅",
            "Usage-Days Count",
            f"{int(overview_metrics['usage_days']):,}",
            "Validated usage-days for the current sidebar selection.",
        )
    with metric_b:
        verdict = (
            f"Significant {T3_DIRECTION}"
            if T3_P_VALUE < T3_ALPHA
            else f"No evidence of {T3_DIRECTION}"
        )
        arrow = " ↑" if T3_DIRECTION == "increase" else ""
        card(
            "📊",
            "T3 Test Result",
            f"p = {T3_P_VALUE:.3f}{arrow}",
            f"{verdict} ({T3_TAIL}, alpha={T3_ALPHA}). {T3_TEST}. Association, not proof of cause.",
            fixed=True,
        )
    with metric_c:
        if int(overview_metrics["usage_days"]) == 0:
            card("🗃", "Data per Day", "No data", "No usage records for the selected sidebar filters.", highlight=True)
        else:
            card(
                "🗃",
                "Data per Day",
                f"{overview_metrics['per_usage_day']:.2f} GB / usage-day",
                f"Calendar-day average: {overview_metrics['per_calendar_day']:.2f} GB per subscriber. "
                f"Connection: {global_connection} | Group: {global_group}",
                highlight=True,
            )

    usage_col, subscriber_col, allowance_col = st.columns(
        [1.7, 1, 1.3],
        gap="large",
    )

    # Overview chart 1: usage by month and experiment group.
    with usage_col:
        with st.container(border=True):
            st.markdown("**Chart filter**")
            usage_month = month_selectbox("Month", "overview_usage_month", months)
            where, params = where_sql(month=usage_month)
            usage = q(
                with_base(
                    f"""SELECT month, grp,
                               SUM(data_gb) * 1.0 / COUNT(*) AS gb_per_usage_day,
                               COUNT(*) AS usage_days
                        FROM base {where}
                        GROUP BY month, grp
                        ORDER BY month, grp"""
                ),
                params,
            )
            if usage.empty:
                chart_title("Daily Data Usage by Month & Experiment Group")
                st.info("No data for this chart's selected filters.")
            else:
                chart_title("Daily Data Usage by Month & Experiment Group")
                fig = go.Figure()
                for group, color in zip(sorted(usage["grp"].unique()), [BLUE, RED, GREY]):
                    group_data = usage[usage["grp"] == group]
                    fig.add_bar(
                        x=[month_label(value)[:3] for value in group_data["month"]],
                        y=group_data["gb_per_usage_day"],
                        name=f"Group {group}",
                        marker_color=color,
                        text=[
                            fmt_rate(value, count)
                            for value, count in zip(
                                group_data["gb_per_usage_day"],
                                group_data["usage_days"],
                            )
                        ],
                        textposition="outside",
                        customdata=group_data["usage_days"],
                        hovertemplate=(
                            "%{x}<br>%{y:.2f} GB per usage-day"
                            "<br>%{customdata:,} usage-days"
                            f"<extra>Group {group}</extra>"
                        ),
                    )
                fig.update_layout(barmode="group")
                fig.update_xaxes(title_text="Month")
                fig.update_yaxes(title_text="GB per usage-day", rangemode="tozero")
                show(style_fig(fig, legend=True))

    # Overview chart 2: subscriber count.
    with subscriber_col:
        with st.container(border=True):
            st.markdown("**Chart filter**")
            subscriber_month = month_selectbox("Month", "overview_subscriber_month", months)
            where, params = where_sql(month=subscriber_month)
            subscribers = q(
                with_base(
                    f"""SELECT month, COUNT(DISTINCT sub_id) AS subscriber_count
                        FROM base {where}
                        GROUP BY month
                        ORDER BY month"""
                ),
                params,
            )
            chart_title("Monthly Subscriber Count")
            if subscribers.empty:
                st.info("No data for this chart's selected filters.")
            else:
                fig = go.Figure(
                    go.Scatter(
                        x=[month_label(value)[:3] for value in subscribers["month"]],
                        y=subscribers["subscriber_count"],
                        mode="lines+markers+text",
                        text=[f"{value:,}" for value in subscribers["subscriber_count"]],
                        textposition="top center",
                        line=dict(color=BLUE, width=2),
                        marker=dict(size=7, color=BLUE),
                    )
                )
                fig.update_xaxes(title_text="Month")
                fig.update_yaxes(title_text="Subscribers", rangemode="tozero")
                show(style_fig(fig))

    # Overview chart 3: plan allowance utilization.
    with allowance_col:
        with st.container(border=True):
            st.markdown("**Chart filter**")
            allowance_plan = st.selectbox(
                "Plan",
                plan_options,
                key="overview_allowance_plan",
            )
            where, params = where_sql(plan=allowance_plan)
            allowance = q(
                with_base(
                    f"""SELECT plan,
                               100.0 * SUM(used_gb) / NULLIF(SUM(allowance_gb), 0) AS utilization_pct,
                               COUNT(*) AS subscriber_months
                        FROM (
                            SELECT sub_id, month, plan,
                                   SUM(data_gb) AS used_gb,
                                   MAX(allowance_gb) AS allowance_gb
                            FROM base {where}
                            GROUP BY sub_id, month, plan
                        ) monthly_usage
                        GROUP BY plan
                        ORDER BY utilization_pct DESC"""
                ),
                params,
            )
            chart_title("Allowance Utilisation by Plan")
            if allowance.empty:
                st.info("No data for this chart's selected filters.")
            else:
                fig = go.Figure(
                    go.Bar(
                        y=allowance["plan"],
                        x=allowance["utilization_pct"],
                        orientation="h",
                        marker_color=RED,
                        text=[
                            f"{value:.0f}% (n={count:,})"
                            for value, count in zip(
                                allowance["utilization_pct"],
                                allowance["subscriber_months"],
                            )
                        ],
                        textposition="outside",
                        customdata=allowance["subscriber_months"],
                        hovertemplate=(
                            "%{y}<br>%{x:.1f}% of allowance"
                            "<br>%{customdata:,} subscriber-months<extra></extra>"
                        ),
                    )
                )
                fig.update_yaxes(autorange="reversed", automargin=True)
                fig.update_xaxes(title_text="% allowance used", rangemode="tozero")
                show(style_fig(fig))


with detail_tab:
    # This month control belongs only to the Detail metric-card section.
    st.markdown("#### Detail metrics")
    metric_month = month_selectbox(
        "Metrics month",
        "detail_metrics_month",
        months,
        default_latest=True,
    )
    metric_where, metric_params = where_sql(month=metric_month)
    detail_metrics = q(
        with_base(
            f"""SELECT COUNT(DISTINCT sub_id) AS subscribers,
                       COALESCE(SUM(data_gb), 0) / {GB_PER_TB}.0 AS terabytes,
                       COALESCE(SUM(data_gb) * 1.0 / NULLIF(COUNT(*), 0), 0) AS per_usage_day,
                       COUNT(*) AS usage_days
                FROM base {metric_where}"""
        ),
        metric_params,
    ).iloc[0]
    metric_period = "All months" if metric_month == "All" else month_label(metric_month)

    details_a, details_b, details_c = st.columns(3, gap="large")
    with details_a:
        card(
            "👥",
            f"Active Subscribers - {metric_period}",
            f"{int(detail_metrics['subscribers']):,}",
            "Distinct customers with at least one usage record in this metric period.",
        )
    with details_b:
        card(
            "🗃",
            f"Data Carried - {metric_period}",
            f"{detail_metrics['terabytes']:.2f} TB",
            f"{int(detail_metrics['usage_days']):,} usage records; "
            f"{detail_metrics['per_usage_day']:.2f} GB per usage record.",
            highlight=True,
        )
    with details_c:
        card(
            "📅",
            "Metric Period",
            metric_period,
            "This selector affects only the Detail metric cards, not the charts below.",
        )

    trend_col, ab_col, device_col = st.columns([2, 1, 1], gap="large")

    # Detail chart 1: daily load trend.
    with trend_col:
        with st.container(border=True):
            st.markdown("**Chart filters**")
            trend_month = month_selectbox(
                "Month",
                "detail_trend_month",
                months,
                default_latest=True,
            )
            trend_device = st.selectbox(
                "Device",
                device_options,
                key="detail_trend_device",
            )
            where, params = where_sql(month=trend_month, device=trend_device)
            trend = q(
                with_base(
                    f"""SELECT usage_date, SUM(data_gb) AS data_gb
                        FROM base {where}
                        GROUP BY usage_date
                        ORDER BY usage_date"""
                ),
                params,
            )
            chart_title("Daily Data Load Trend")
            if trend.empty:
                st.info("No data for this chart's selected filters.")
            else:
                peak_day = trend.loc[trend["data_gb"].idxmax()]
                st.caption(
                    f"Peak: {peak_day['usage_date']} "
                    f"({peak_day['data_gb']:,.0f} GB)"
                )
                fig = go.Figure(
                    go.Scatter(
                        x=trend["usage_date"],
                        y=trend["data_gb"],
                        mode="lines+markers",
                        line=dict(color=RED, width=2),
                        marker=dict(size=5, color=RED),
                        fill="tozeroy",
                        fillcolor="rgba(228,0,0,0.08)",
                        hovertemplate="%{x}<br>%{y:,.0f} GB<extra></extra>",
                    )
                )
                fig.update_xaxes(title_text="Date", type="date")
                fig.update_yaxes(title_text="Data carried (GB)", rangemode="tozero")
                show(style_fig(fig, height=CHART_H + 20))

    # Detail chart 2: experiment-group comparison.
    with ab_col:
        with st.container(border=True):
            st.markdown("**Chart filter**")
            ab_month = month_selectbox(
                "Month",
                "detail_ab_month",
                months,
                default_latest=True,
            )
            where, params = where_sql(month=ab_month)
            comparison = q(
                with_base(
                    f"""SELECT grp,
                               SUM(data_gb) * 1.0 / COUNT(*) AS per_usage_day,
                               COUNT(*) AS usage_days,
                               COUNT(DISTINCT sub_id) AS subscribers
                        FROM base {where}
                        GROUP BY grp
                        ORDER BY grp"""
                ),
                params,
            )
            chart_title(
                "A/B Comparison",
                "Descriptive comparison only; no new statistical result is calculated.",
            )
            if comparison.empty:
                st.info("No data for this chart's selected filters.")
            else:
                colors = [BLUE if value == "A" else RED for value in comparison["grp"]]
                fig = go.Figure(
                    go.Bar(
                        x=[f"Group {value}" for value in comparison["grp"]],
                        y=comparison["per_usage_day"],
                        marker_color=colors,
                        text=[
                            f"{fmt_rate(value, usage_days)}<br>{subscribers:,} subscribers"
                            for value, usage_days, subscribers in zip(
                                comparison["per_usage_day"],
                                comparison["usage_days"],
                                comparison["subscribers"],
                            )
                        ],
                        textposition="outside",
                        customdata=comparison["usage_days"],
                        hovertemplate=(
                            "%{x}<br>%{y:.2f} GB per usage-day"
                            "<br>%{customdata:,} usage-days<extra></extra>"
                        ),
                    )
                )
                fig.update_yaxes(title_text="GB per usage-day", rangemode="tozero")
                show(style_fig(fig, height=CHART_H + 20))

    # Detail chart 3: device-category comparison.
    with device_col:
        with st.container(border=True):
            st.markdown("**Chart filters**")
            category_col, month_col = st.columns(2, gap="medium")
            with category_col:
                device_category = st.selectbox(
                    "Device Category",
                    device_options,
                    key="detail_device_category",
                )
            with month_col:
                device_month = month_selectbox(
                    "Month",
                    "detail_device_month",
                    months,
                    default_latest=True,
                )

            where, params = where_sql(
                device=device_category,
                month=device_month,
            )
            device_data = q(
                with_base(
                    f"""SELECT device,
                               SUM(data_gb) * 1.0 / COUNT(*) AS per_usage_day,
                               COUNT(*) AS usage_days,
                               COUNT(DISTINCT sub_id) AS subscribers
                        FROM base {where}
                        GROUP BY device
                        ORDER BY per_usage_day DESC"""
                ),
                params,
            )
            chart_title(
                "Device Comparison",
                "GB per usage-day by customer device category.",
            )
            if device_data.empty:
                st.info("No data for this chart's selected filters.")
            else:
                fig = go.Figure(
                    go.Bar(
                        x=device_data["device"],
                        y=device_data["per_usage_day"],
                        marker_color=SLATE,
                        text=[
                            f"{fmt_rate(value, usage_days)}<br>{subscribers:,} subscribers"
                            for value, usage_days, subscribers in zip(
                                device_data["per_usage_day"],
                                device_data["usage_days"],
                                device_data["subscribers"],
                            )
                        ],
                        textposition="outside",
                        customdata=device_data["usage_days"],
                        hovertemplate=(
                            "%{x}<br>%{y:.2f} GB per usage-day"
                            "<br>%{customdata:,} usage-days<extra></extra>"
                        ),
                    )
                )
                fig.update_xaxes(title_text="Device category")
                fig.update_yaxes(title_text="GB per usage-day", rangemode="tozero")
                show(style_fig(fig, height=CHART_H + 20))
