import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
from db import run_query, get_table_list

# ── CONFIG ─────────────────────────────────────────────────────────────────────
API_BASE_URL = "https://n10l1x6j53xl7ypp6ar5zzca.vps.boomlive.in/"

PALETTE = [
    "#4C6EF5", "#F76707", "#2F9E44", "#E03131", "#7048E8",
    "#0C8599", "#D6336C", "#F59F00", "#74C0FC", "#63E6BE",
    "#A9E34B", "#FF6B6B", "#CC5DE8", "#20C997", "#FFA94D",
]


# ── API HELPER ─────────────────────────────────────────────────────────────────
def generate_sql_via_api(natural_language_query: str) -> tuple[str | None, str | None]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-sql",
            json={"query": natural_language_query},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()["sql"], None
        detail = response.json().get("detail", response.text)
        return None, f"API error {response.status_code}: {detail}"
    except requests.exceptions.ConnectionError:
        return None, f"Could not connect to API at {API_BASE_URL}. Is FastAPI running?"
    except requests.exceptions.Timeout:
        return None, "Request timed out."
    except Exception as e:
        return None, str(e)


# ── CHART HTML (rendered inside iframe via components.html) ────────────────────
def build_chart_html(labels: list, values: list, y_label: str, chart_type: str) -> str:
    colors       = [PALETTE[i % len(PALETTE)] for i in range(len(values))]
    colors_alpha = [c + "BB" for c in colors]

    cjs_type_map = {
        "Bar": "bar", "Horizontal Bar": "bar",
        "Line": "line", "Doughnut": "doughnut",
        "Radar": "radar", "Polar Area": "polarArea",
    }
    cjs_type      = cjs_type_map.get(chart_type, "bar")
    is_horizontal = chart_type == "Horizontal Bar"
    is_multicolor = chart_type in ("Doughnut", "Polar Area", "Radar")
    has_axes      = cjs_type in ("bar", "line")

    index_axis = '"indexAxis": "y",' if is_horizontal else ""

    scales_block = ""
    if has_axes:
        scales_block = """
        scales: {
          x: {
            ticks: { color: "#aaa", maxRotation: 40, font: { size: 11 } },
            grid:  { color: "#2a2a3a" }
          },
          y: {
            ticks: { color: "#aaa", font: { size: 11 } },
            grid:  { color: "#2a2a3a" }
          }
        },"""

    datalabel_anchor = "" if is_multicolor else '"end"'
    datalabel_align  = "" if is_multicolor else '"top"'

    canvas_style = 'height:620px !important;' if is_multicolor else ''

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #0e1117;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 20px;
    }}
    .wrap {{ width: 100%; max-width: 1100px; }}
    .download-btn {{
      margin-top: 16px;
      padding: 10px 28px;
      background: #e03131;
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      letter-spacing: 0.5px;
      transition: background 0.2s;
    }}
    .download-btn:hover {{ background: #c92a2a; }}
  </style>
</head>
<body>
<div class="wrap">
  <canvas id="chart" style="{canvas_style}"></canvas>
</div>
<button class="download-btn" onclick="downloadChart()">⬇ Download Chart</button>
<script>
  Chart.register(ChartDataLabels);

  const labels      = {json.dumps(labels)};
  const values      = {json.dumps(values)};
  const colors      = {json.dumps(colors)};
  const alphas      = {json.dumps(colors_alpha)};
  const yLabel      = {json.dumps(y_label)};
  const isMulti     = {'true' if is_multicolor else 'false'};
  const showLabels  = values.length <= 20;

  function downloadChart() {{
    const canvas = document.getElementById("chart");
    // Draw on a white background so PNG looks clean
    const exportCanvas = document.createElement("canvas");
    exportCanvas.width  = canvas.width;
    exportCanvas.height = canvas.height;
    const ctx = exportCanvas.getContext("2d");
    ctx.fillStyle = "#0e1117";
    ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
    ctx.drawImage(canvas, 0, 0);
    const link = document.createElement("a");
    link.download = "chart.jpg";
    link.href = exportCanvas.toDataURL("image/jpeg", 0.95);
    link.click();
  }}

  new Chart(document.getElementById("chart"), {{
    type: "{cjs_type}",
    data: {{
      labels,
      datasets: [{{
        label: yLabel,
        data: values,
        backgroundColor: alphas,
        borderColor: colors,
        borderWidth: 2,
        tension: 0.4,
        fill: false,
        pointRadius: 5,
        pointHoverRadius: 7,
      }}]
    }},
    options: {{
      {index_axis}
      responsive: true,
      maintainAspectRatio: {'false' if is_multicolor else 'true'},
      plugins: {{
        legend: {{
          display: isMulti,
          labels: {{
            color: "#e0e0e0",
            font: {{ size: 12 }},
            padding: 16,
          }}
        }},
        tooltip: {{
          backgroundColor: "#1e1e2e",
          titleColor: "#cdd6f4",
          bodyColor: "#a6adc8",
          borderColor: "#45475a",
          borderWidth: 1,
          callbacks: {{
            label: ctx => " " + (ctx.parsed.y ?? ctx.parsed ?? ctx.formattedValue).toLocaleString()
          }}
        }},
        datalabels: {{
          display: showLabels,
          color: "#e0e0e0",
          font: {{ size: 11, weight: "bold" }},
          formatter: v => typeof v === "number" ? v.toLocaleString() : v,
          anchor: {datalabel_anchor if datalabel_anchor else '""'},
          align:  {datalabel_align  if datalabel_align  else '""'},
          offset: 4,
          clip: false,
        }},
      }},
      {scales_block}
      layout: {{ padding: {{ top: 30, right: 16, bottom: 8, left: 8 }} }},
    }}
  }});
</script>
</body>
</html>"""


# ── HELPERS ────────────────────────────────────────────────────────────────────
def format_table_name(table_name: str) -> str:
    parts = table_name.split("_")
    if len(parts) >= 2 and parts[-1].isdigit() and parts[-2].isdigit():
        year, name_parts = f"{parts[-2]}–{parts[-1]}", parts[:-2]
    else:
        year, name_parts = "", parts
    readable = " ".join(name_parts).title()
    return f"{readable} ({year})" if year else readable


# ── SQL FIXER: wrap aggregate args with numeric cast for TEXT columns ──────────
import re

def fix_sql_text_aggregates(sql: str) -> str:
    """
    Rewrites SUM(col), AVG(col), MAX(col), MIN(col) → SUM(NULLIF(col,'')::NUMERIC)
    so they work even when the column is stored as TEXT in PostgreSQL.
    Also rewrites plain ORDER BY col and comparisons like col > 100.
    """
    agg_pattern = re.compile(
        r'\b(SUM|AVG|MIN|MAX)\s*\(\s*(?!NULLIF)([^()]+?)\s*\)',
        re.IGNORECASE
    )
    def replace_agg(m):
        func, inner = m.group(1), m.group(2).strip()
        # Skip if already cast
        if '::' in inner or 'CAST(' in inner.upper():
            return m.group(0)
        return f"{func.upper()}(NULLIF({inner}, '')::NUMERIC)"

    return agg_pattern.sub(replace_agg, sql)


# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="MGNREGA Text-to-SQL", page_icon="🔍", layout="wide")

# ── CUSTOM CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .sql-box {
    background: #1e1e2e; color: #cdd6f4;
    padding: 1rem 1.2rem; border-radius: 8px;
    font-family: 'Courier New', monospace; font-size: 0.9rem;
    white-space: pre-wrap; overflow-x: auto;
  }
  .stTextArea textarea { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ─────────────────────────────────────────────────────────────────────
st.title("🔍 MGNREGA Text-to-SQL Explorer")
st.caption("Ask questions in plain English — get live data from your PostgreSQL database.")

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 Database Tables")
    tables = get_table_list()
    if tables:
        years = set()
        for t in tables:
            parts = t.split("_")
            for i in range(len(parts) - 1):
                if parts[i].isdigit() and parts[i + 1].isdigit():
                    years.add(f"{parts[i]}-{parts[i + 1]}")
        years = sorted(list(years))

        selected_year = st.selectbox("📅 Select Year Range", ["All"] + years)
        if selected_year != "All":
            s, e = selected_year.split("-")
            filtered_tables = [t for t in tables if f"{s}_{e}" in t]
        else:
            filtered_tables = tables

        st.success(f"{len(filtered_tables)} tables found")
        for t in filtered_tables:
            st.markdown(
                f"<span style='color:#FFA500;'> {format_table_name(t)}</span>",
                unsafe_allow_html=True,
            )
    else:
        st.warning("Could not load table list. Check DB connection.")

    st.divider()
    # st.markdown(f"**API:** `{API_BASE_URL}`")
    # st.markdown("**Model:** `gpt-4o`  |  **DB:** PostgreSQL")

# ── SESSION STATE INIT ─────────────────────────────────────────────────────────
for key, default in {
    "run_query_flag": False,
    "history":        [],
    "current_sql":    None,
    "current_df":     None,
    "current_error":  None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── EXAMPLE QUESTIONS ──────────────────────────────────────────────────────────
EXAMPLES = [
    "Which 5 states had the most active women workers in 2022-2023?",
    "Show total registered SC workers by state for 2023-2024",
    "Which states have more than 10 lakh registered ST workers in 2021-2022?",
    "List states where Aadhaar seeding is below 80% in 2022-2023",
    "Show job cards issued vs applied for Bihar across all years",
    "Which state had the highest number of households not issued job cards in 2020-2021?",
]

st.subheader("💡 Example Questions")
cols = st.columns(3)
for i, ex in enumerate(EXAMPLES):
    if cols[i % 3].button(ex, key=f"ex_{i}", use_container_width=True):
        st.session_state.user_query     = ex
        st.session_state.run_query_flag = True

# ── MAIN INPUT ─────────────────────────────────────────────────────────────────
st.subheader("✍️ Your Question")
st.text_area(
    label="Ask anything about MGNREGA data:",
    height=80,
    placeholder="e.g. Which state has the highest number of active workers in 2023-2024?",
    key="user_query",
)

run_btn = st.button("🚀 Generate SQL & Fetch Data", type="primary", use_container_width=True)
if run_btn:
    st.session_state.run_query_flag = True

# ── EXECUTION ──────────────────────────────────────────────────────────────────
user_query = st.session_state.get("user_query", "").strip()

if st.session_state.run_query_flag:
    st.session_state.run_query_flag = False

    if not user_query:
        st.warning("Please enter a question first.")
    else:
        st.session_state.current_sql   = None
        st.session_state.current_df    = None
        st.session_state.current_error = None

        with st.spinner("🤖 Calling Text-to-SQL API…"):
            sql, gen_error = generate_sql_via_api(user_query)

        if gen_error:
            st.session_state.current_error = f"SQL generation failed: {gen_error}"
        else:
            sql = fix_sql_text_aggregates(sql)   # ← cast TEXT cols before aggregating
            st.session_state.current_sql = sql
            with st.spinner("⚙️ Executing query…"):
                df, exec_error = run_query(sql)

            if exec_error:
                st.session_state.current_error = f"Query execution failed: {exec_error}"
                st.session_state.history.append(
                    {"question": user_query, "sql": sql, "df": None, "error": exec_error}
                )
            else:
                for col in df.columns:
                    try:
                        df[col] = pd.to_numeric(df[col])
                    except Exception:
                        pass
                st.session_state.current_df = df
                st.session_state.history.append(
                    {"question": user_query, "sql": sql, "df": df, "error": None}
                )

# ── RESULTS DISPLAY ────────────────────────────────────────────────────────────
if st.session_state.current_error:
    st.error(st.session_state.current_error)

# if st.session_state.current_sql:
#     st.subheader("📝 Generated SQL")
#     st.markdown(
#         f'<div class="sql-box">{st.session_state.current_sql}</div>',
#         unsafe_allow_html=True,
#     )

if st.session_state.current_df is not None:
    df        = st.session_state.current_df
    row_count = len(df)
    col_count = len(df.columns)

    # st.subheader("📊 Results")
    # m1, m2 = st.columns(2)
    # m1.metric("Rows returned", row_count)
    # m2.metric("Columns",       col_count)

    if row_count == 0:
        st.info("Query executed successfully but returned no rows.")
    else:
        # tab1, tab2, tab3 = st.tabs(["📋 Table", "📈 Chart", "📥 Download"])
        tab2 = st.tabs(["📈 Chart"])[0]

        # ── TABLE ──────────────────────────────────────────────────────────────
        # with tab1:
        #     st.dataframe(df, use_container_width=True, height=420)

        # ── CHART (iframe + Chart.js) ──────────────────────────────────────────
        with tab2:
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            text_cols    = df.select_dtypes(exclude="number").columns.tolist()

            if not numeric_cols or not text_cols:
                st.info("Need at least one text and one numeric column to render a chart.")
            else:
                ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 2])
                x_col      = ctrl1.selectbox("X axis (labels)",  text_cols,    key="x_col")
                y_col      = ctrl2.selectbox("Y axis (values)",  numeric_cols, key="y_col")
                chart_type = ctrl3.selectbox(
                    "Chart type",
                    ["Bar", "Horizontal Bar", "Line", "Doughnut", "Polar Area", "Radar"],
                    key="chart_type",
                )

                plot_df = df[[x_col, y_col]].dropna()
                labels  = plot_df[x_col].astype(str).tolist()
                values  = [round(float(v), 2) for v in plot_df[y_col].tolist()]

                chart_html = build_chart_html(labels, values, y_col, chart_type)
                iframe_height = 740 if chart_type in ("Doughnut", "Polar Area", "Radar") else 660
                components.html(chart_html, height=iframe_height, scrolling=False)

        # ── DOWNLOAD ───────────────────────────────────────────────────────────
        # with tab3:
        #     csv = df.to_csv(index=False).encode("utf-8")
        #     st.download_button(
        #         "⬇️ Download CSV",
        #         data=csv,
        #         file_name="query_results.csv",
        #         mime="text/csv",
        #         use_container_width=True,
        #     )

# ── QUERY HISTORY ──────────────────────────────────────────────────────────────
if st.session_state.history:
    st.divider()
    st.subheader("🕘 Query History")
    for i, item in enumerate(reversed(st.session_state.history)):
        label = f"Q{len(st.session_state.history) - i}: {item['question'][:80]}…"
        with st.expander(label):
            st.markdown(f'<div class="sql-box">{item["sql"]}</div>', unsafe_allow_html=True)
            if item["error"]:
                st.error(item["error"])
            elif item["df"] is not None:
                st.dataframe(item["df"], use_container_width=True)
