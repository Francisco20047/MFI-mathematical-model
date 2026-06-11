import streamlit as st
import plotly.graph_objects as go
import numpy as np

# ── Parámetros ──────────────────────────────────────────────────────
MFI_V     = 8.64    # Virgen
MFI_S     = 12.0    # Scrap
MFI_N     = 10.8    # Negro
MFI_C     = 9.6     # Color
MFI_LIM   = 10.5    # Límite
PRICE     = 1.01    # USD/kg
BAT_MES   = 1728000 # baterías/mes
KG_CAJA   = 0.760   # kg por caja
KG_TAPA   = 0.235   # kg por tapa
KG_CAJAS  = BAT_MES * KG_CAJA   # 1,313,280 kg/mes
KG_TAPAS  = BAT_MES * KG_TAPA   # 406,080 kg/mes
BASE_CAJ  = 0.10    # baseline virgen cajas
BASE_TAP  = 1.00    # baseline virgen tapas (100% virgen actualmente)

# ── Modelos Bingham ─────────────────────────────────────────────────
def mfi_caja(xv, xs):
    xn = 1 - xv - xs
    if xn < 0: return None
    return 1 / (xv/MFI_V + xs/MFI_S + xn/MFI_N)

def mfi_tapa(xv):
    xc = 1 - xv
    return 1 / (xv/MFI_V + xc/MFI_C)

def virgen_opt_caja(xs):
    return (1/MFI_LIM - xs/MFI_S - (1-xs)/MFI_N) / (1/MFI_V - 1/MFI_N)

def virgen_opt_tapa(x_color_disponible):
    # color disponible cubre x_color_disponible fracción de tapas
    # el resto lo cubre virgen
    return 1 - x_color_disponible

# ── Página ──────────────────────────────────────────────────────────
st.set_page_config(page_title="Clarios · Dashboard PP", layout="wide")
st.title("Dashboard PP — Cajas y Tapas")
st.caption(f"Modelo Bingham · Límite MFI ≤ {MFI_LIM} g/10min · Planta Ciénega")

# ── Sliders ─────────────────────────────────────────────────────────
st.markdown("### Parámetros de entrada")
col1, col2, col3 = st.columns(3)

with col1:
    scrap_pct  = st.slider("% Scrap en cajas", 0.0, 8.0, 5.0, step=0.5,
                            help="Piezas defectuosas recirculadas · MFI=12")
with col2:
    virgin_pct = st.slider("% Virgen en cajas", 0.0, 20.0, 10.0, step=0.5,
                            help="Formolene · MFI=8.64")
with col3:
    color_disp = st.slider("% Color disponible de García para tapas", 0.0, 100.0, 30.0, step=5.0,
                            help="% del requerimiento de tapas que puede cubrir el color de García")

xs  = scrap_pct  / 100
xv  = virgin_pct / 100
xcd = color_disp / 100

# ── Cálculos ────────────────────────────────────────────────────────
# Cajas
mfi_c      = mfi_caja(xv, xs)
xv_opt_c   = virgen_opt_caja(xs)
en_spec    = mfi_c is not None and mfi_c <= MFI_LIM
costo_extra_cajas = (xv_opt_c - BASE_CAJ) * KG_CAJAS * PRICE * 12

# Tapas
xv_tap     = virgen_opt_tapa(xcd)
mfi_t      = mfi_tapa(xv_tap)
ahorro_tap = (BASE_TAP - xv_tap) * KG_TAPAS * PRICE * 12

# Neto
ahorro_neto = ahorro_tap - costo_extra_cajas

# ── KPIs ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Resultados")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("MFI Cajas", 
              f"{mfi_c:.3f}" if mfi_c else "—",
              delta="✓ En spec" if en_spec else "✗ Fuera de spec",
              delta_color="normal" if en_spec else "inverse")
with c2:
    st.metric("Virgen óptimo cajas",
              f"{xv_opt_c*100:.2f}%",
              delta=f"{(xv_opt_c-BASE_CAJ)*100:+.2f}% vs baseline",
              delta_color="inverse" if xv_opt_c > BASE_CAJ else "normal")
with c3:
    st.metric("Virgen en tapas",
              f"{xv_tap*100:.1f}%",
              delta=f"{(xv_tap-BASE_TAP)*100:+.1f}% vs baseline 100%",
              delta_color="normal" if xv_tap < BASE_TAP else "inverse")
with c4:
    st.metric("Costo extra cajas/año",
              f"${abs(costo_extra_cajas):,.0f}",
              delta="costo adicional" if costo_extra_cajas > 0 else "ahorro",
              delta_color="inverse" if costo_extra_cajas > 0 else "normal")
with c5:
    st.metric("Ahorro NETO/año",
              f"${ahorro_neto:,.0f}",
              delta="✓ Proyecto rentable" if ahorro_neto > 0 else "✗ No rentable aún",
              delta_color="normal" if ahorro_neto > 0 else "inverse")

st.markdown("---")

# ── Gráficas ─────────────────────────────────────────────────────────
g1, g2 = st.columns(2)

# Gráfica 1: MFI cajas vs % virgen
with g1:
    st.subheader(f"MFI Cajas vs % Virgen  (scrap={scrap_pct}%)")
    v_range = np.arange(0, 20.5, 0.5)
    mfi_vals = [mfi_caja(v/100, xs) for v in v_range]

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=v_range, y=mfi_vals, mode="lines",
                              line=dict(color="#58a6ff", width=2.5), name="MFI cajas"))
    fig1.add_hline(y=MFI_LIM, line_dash="dash", line_color="#f85149",
                   annotation_text="Límite 10.5")
    fig1.add_vline(x=virgin_pct, line_dash="dot", line_color="#58a6ff",
                   annotation_text=f"Actual {virgin_pct}%")
    fig1.add_vline(x=xv_opt_c*100, line_dash="dot", line_color="#3fb950",
                   annotation_text=f"Óptimo {xv_opt_c*100:.1f}%")
    fig1.update_layout(xaxis_title="% Virgen", yaxis_title="MFI (g/10min)",
                       yaxis=dict(range=[8, 13]), height=320,
                       plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                       font=dict(color="#e6edf3"))
    st.plotly_chart(fig1, use_container_width=True)

# Gráfica 2: MFI cajas vs % scrap
with g2:
    st.subheader(f"MFI Cajas vs % Scrap  (virgen={virgin_pct}%)")
    s_range = np.arange(0, 8.5, 0.5)
    mfi_scrap = [mfi_caja(xv, s/100) for s in s_range]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=s_range, y=mfi_scrap, mode="lines",
                              line=dict(color="#f85149", width=2.5), name="MFI cajas"))
    fig2.add_hline(y=MFI_LIM, line_dash="dash", line_color="#f85149",
                   annotation_text="Límite 10.5")
    fig2.add_vline(x=scrap_pct, line_dash="dot", line_color="#f85149",
                   annotation_text=f"Actual {scrap_pct}%")
    fig2.update_layout(xaxis_title="% Scrap", yaxis_title="MFI (g/10min)",
                       yaxis=dict(range=[8, 13]), height=320,
                       plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                       font=dict(color="#e6edf3"))
    st.plotly_chart(fig2, use_container_width=True)

g3, g4 = st.columns(2)

# Gráfica 3: Ahorro neto vs % color disponible
with g3:
    st.subheader("Ahorro Neto vs % Color disponible de García")
    cd_range = np.arange(0, 105, 5)
    ahorros  = []
    for cd in cd_range:
        xv_t = virgen_opt_tapa(cd/100)
        xv_c = virgen_opt_caja(xs)
        ah_t = (BASE_TAP - xv_t) * KG_TAPAS * PRICE * 12
        ce_c = (xv_c - BASE_CAJ) * KG_CAJAS * PRICE * 12
        ahorros.append(ah_t - ce_c)

    colors = ["#3fb950" if a >= 0 else "#f85149" for a in ahorros]
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=cd_range, y=ahorros, marker_color=colors, name="Ahorro neto"))
    fig3.add_hline(y=0, line_color="#484f58")
    fig3.add_vline(x=color_disp, line_dash="dot", line_color="#d2a8ff",
                   annotation_text=f"Actual {color_disp}%")
    fig3.update_layout(xaxis_title="% Color disponible", yaxis_title="USD/año",
                       height=320, plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                       font=dict(color="#e6edf3"), xaxis=dict(ticksuffix="%"))
    st.plotly_chart(fig3, use_container_width=True)

# Gráfica 4: Ahorro neto vs % scrap (color fijo)
with g4:
    st.subheader(f"Ahorro Neto vs % Scrap  (color={color_disp}%)")
    s_range2 = np.arange(0, 8.5, 0.5)
    ahorros2 = []
    for s in s_range2:
        xv_c = virgen_opt_caja(s/100)
        xv_t = virgen_opt_tapa(xcd)
        ah_t = (BASE_TAP - xv_t) * KG_TAPAS * PRICE * 12
        ce_c = (xv_c - BASE_CAJ) * KG_CAJAS * PRICE * 12
        ahorros2.append(ah_t - ce_c)

    colors2 = ["#3fb950" if a >= 0 else "#f85149" for a in ahorros2]
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(x=s_range2, y=ahorros2, marker_color=colors2, name="Ahorro neto"))
    fig4.add_hline(y=0, line_color="#484f58")
    fig4.add_vline(x=scrap_pct, line_dash="dot", line_color="#f85149",
                   annotation_text=f"Actual {scrap_pct}%")
    fig4.update_layout(xaxis_title="% Scrap", yaxis_title="USD/año",
                       height=320, plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                       font=dict(color="#e6edf3"), xaxis=dict(ticksuffix="%"))
    st.plotly_chart(fig4, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────────────
st.markdown("---")
st.caption(f"Cajas: {KG_CAJAS:,.0f} kg/mes · Tapas: {KG_TAPAS:,.0f} kg/mes · Precio virgen: ${PRICE}/kg · Baseline cajas: {BASE_CAJ*100:.0f}% · Baseline tapas: {BASE_TAP*100:.0f}%")
