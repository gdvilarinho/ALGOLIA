import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Search Dashboard 2025", layout="wide")

st.title("📊 Dashboard Search & Conversão 2025")

# -----------------------------
# Funções
# -----------------------------

@st.cache_data
def load_excel(file):
    df_dados = pd.read_excel(file, sheet_name="Dados")
    df_mom = pd.read_excel(file, sheet_name="MoM")
    return df_dados, df_mom


def clean_value(series):
    s = series.astype(str).str.strip()
    is_pct = s.str.contains("%", na=False)

    out = pd.to_numeric(
        s.str.replace("%", "", regex=False)
         .str.replace(".", "", regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce"
    )

    out = np.where(is_pct, out / 100.0, out)
    return pd.Series(out, index=series.index)


def to_long(df_wide, value_name):
    df = df_wide.copy()
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={df.columns[0]: "Indicador"})
    long = df.melt(id_vars=["Indicador"], var_name="Mês", value_name=value_name)
    return long


def month_key(m):
    months_pt = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
        "abril": 4, "maio": 5, "junho": 6, "julho": 7,
        "agosto": 8, "setembro": 9, "outubro": 10,
        "novembro": 11, "dezembro": 12
    }

    m = str(m).strip().lower()
    parts = re.split(r"\s+", m)
    mon = months_pt.get(parts[0], 0)
    yr = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return (yr, mon)


def format_value(ind, v):
    if pd.isna(v):
        return "-"

    if "Rate" in ind or "CTR" in ind or "Click" in ind or "Conversion" in ind or "No Results" in ind:
        return f"{v*100:.2f}%"

    if "Revenue" in ind or "AOV" in ind:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if "Searches" in ind or "Users" in ind:
        return f"{int(round(v)):,}".replace(",", ".")

    return f"{v:.2f}"


# -----------------------------
# Upload
# -----------------------------

uploaded = st.file_uploader("Envie o Excel consolidado (com abas 'Dados' e 'MoM')", type=["xlsx"])

if not uploaded:
    st.info("Faça upload do arquivo para visualizar o dashboard.")
    st.stop()

df_dados_w, df_mom_w = load_excel(uploaded)

dados_long = to_long(df_dados_w, "Valor")
mom_long = to_long(df_mom_w, "MoM")

dados_long["Valor_num"] = clean_value(dados_long["Valor"])
mom_long["MoM_num"] = pd.to_numeric(mom_long["MoM"], errors="coerce")

meses_ord = sorted(dados_long["Mês"].unique(), key=month_key)

dados_long["Mês"] = pd.Categorical(dados_long["Mês"], categories=meses_ord, ordered=True)
mom_long["Mês"] = pd.Categorical(mom_long["Mês"], categories=meses_ord, ordered=True)

indicadores = sorted(dados_long["Indicador"].unique())

# -----------------------------
# Sidebar
# -----------------------------

with st.sidebar:
    st.header("Filtros")

    ind_sel = st.multiselect("Indicadores", indicadores, default=indicadores)

    mes_ini, mes_fim = st.select_slider(
        "Período",
        options=meses_ord,
        value=(meses_ord[0], meses_ord[-1])
    )

# Filtros aplicados
dados_f = dados_long[
    (dados_long["Indicador"].isin(ind_sel)) &
    (dados_long["Mês"] >= mes_ini) &
    (dados_long["Mês"] <= mes_fim)
]

mom_f = mom_long[
    (mom_long["Indicador"].isin(ind_sel)) &
    (mom_long["Mês"] >= mes_ini) &
    (mom_long["Mês"] <= mes_fim)
]

# -----------------------------
# KPIs
# -----------------------------

st.subheader(f"KPIs - {mes_fim}")

kpi_base = dados_long[dados_long["Mês"] == mes_fim].copy()
kpi_base = kpi_base.set_index("Indicador")

cols = st.columns(5)

for i, ind in enumerate(ind_sel[:10]):
    if ind in kpi_base.index:
        v = kpi_base.loc[ind, "Valor_num"]
        cols[i % 5].metric(ind, format_value(ind, v))

st.divider()

# -----------------------------
# Série temporal
# -----------------------------

st.subheader("Evolução Mensal")

fig = px.line(
    dados_f.sort_values("Mês"),
    x="Mês",
    y="Valor_num",
    color="Indicador",
    markers=True
)

fig.update_layout(legend_title_text="Indicador")
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Heatmap MoM
# -----------------------------

st.subheader("Variação MoM (%)")

hm = mom_f.pivot_table(
    index="Indicador",
    columns="Mês",
    values="MoM_num",
    aggfunc="mean"
)

fig_hm = px.imshow(
    hm,
    aspect="auto",
    color_continuous_scale="RdYlGn",
)

st.plotly_chart(fig_hm, use_container_width=True)

# -----------------------------
# Tabela
# -----------------------------

with st.expander("Ver tabela detalhada"):
    merged = dados_f.merge(
        mom_f[["Indicador", "Mês", "MoM_num"]],
        on=["Indicador", "Mês"],
        how="left"
    )

    st.dataframe(merged, use_container_width=True)
