import streamlit as st
import plotly.graph_objects as go
import numpy as np

# ── Constantes ──────────────────────────────────────────────────────────────
MFI_V    = 8.64    # Virgen Formolene
MFI_S    = 12.0    # Scrap interno
MFI_N    = 10.8    # Negro reciclado
MFI_C    = 9.6     # Color reciclado (tapas)
MFI_LIM  = 10.5    # Límite de especificación
PRICE    = 1.01    # USD/kg virgen
BAT_MES  = 1_728_000
KG_CAJA  = 0.760 #kg / bateria
KG_TAPA  = 0.235 #kg / bateria
KG_CAJAS = BAT_MES * KG_CAJA    # 1,313,280 kg/mes
KG_TAPAS = BAT_MES * KG_TAPA    #   406,080 kg/mes
BASE_CAJ = 0.10
BASE_TAP = 1.00

LAYOUT_BASE = dict(
    plot_bgcolor="#0d1117",
    paper_bgcolor="#161b22",
    font=dict(color="#e6edf3", size=12),
    margin=dict(t=40, b=40, l=50, r=20),
    height=340,
)

# ── Modelos ─────────────────────────────────────────────────────────────────
def mfi_caja(xv, xs):
    xn = 1 - xv - xs
    if xn < 0 or xv < 0 or xs < 0:
        return None
    return 1 / (xv / MFI_V + xs / MFI_S + xn / MFI_N)

def mfi_tapa(xv):
    xc = 1 - xv
    return 1 / (xv / MFI_V + xc / MFI_C)

def virgen_opt_caja(xs):
    """Mínimo virgen para que MFI_caja = MFI_LIM dado xs."""
    return (1 / MFI_LIM - xs / MFI_S - (1 - xs) / MFI_N) / (1 / MFI_V - 1 / MFI_N)

def ahorro_neto(xv_c_base, xs, xcd):
    xv_t  = 1 - xcd
    xv_c  = virgen_opt_caja(xs)
    ah_t  = (BASE_TAP - xv_t) * KG_TAPAS * price * 12
    ce_c  = (xv_c - xv_c_base) * KG_CAJAS * price * 12
    return ah_t - ce_c

# ── Config página ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Clarios · Control PP",
    layout="wide",
)

st.markdown(
    "<h1 style='color:#58a6ff;margin-bottom:0'>Clarios — Control de Calidad PP</h1>",
    unsafe_allow_html=True,
)

# ── Sliders en sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Parámetros")
    scrap_pct  = st.slider("% Scrap en cajas",         0.0,   8.0,   5.0, 0.5,
                            help="Piezas defectuosas · MFI=12")
    virgin_pct = st.slider("% Virgen en cajas",        0.0,  20.0,  10.0, 0.5,
                            help="Formolene · MFI=8.64")
    color_disp = st.slider("% Color García (tapas)",   0.0, 100.0,  30.0, 5.0,
                            help="Fracción del polipropileno de color usado en tapa")
    price      = st.slider("Precio virgen (USD/kg)",   0.70,  3.00,  1.01, 0.01,
                            help="Precio de mercado del PP virgen Formolene")
    st.markdown("---")
    st.caption(
        f"Modelo Bingham · Planta Ciénega · Límite MFI ≤ {MFI_LIM} g/10min\n\n"
        f"Cajas: {KG_CAJAS:,.0f} kg/mes · Tapas: {KG_TAPAS:,.0f} kg/mes"
    )

xs  = scrap_pct  / 100
xv  = virgin_pct / 100
xcd = color_disp / 100

# ── Cálculos del punto actual ────────────────────────────────────────────────
mfi_c_act  = mfi_caja(xv, xs)
xv_opt_c   = virgen_opt_caja(xs)
xv_tap_act = 1 - xcd
mfi_t_act  = mfi_tapa(xv_tap_act)
en_spec    = mfi_c_act is not None and mfi_c_act <= MFI_LIM

costo_extra_cajas = (xv - BASE_CAJ) * KG_CAJAS * price * 12 #anualizado
ahorro_tap_anual  = (BASE_TAP - xv_tap_act) * KG_TAPAS * price * 12 #anualizado
ahorro_neto_anual = ahorro_tap_anual - costo_extra_cajas

# ── KPIs ─────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("MFI Cajas",
          f"{mfi_c_act:.3f} g/10min" if mfi_c_act else "—",
          delta="✓ En spec" if en_spec else "✗ Fuera de spec",
          delta_color="normal" if en_spec else "inverse")
k2.metric("Virgen óptimo cajas",
          f"{xv_opt_c*100:.2f}%",
          delta=f"{(xv_opt_c - BASE_CAJ)*100:+.2f}pp vs baseline",
          delta_color="inverse" if xv_opt_c > BASE_CAJ else "normal")
k3.metric("Virgen en tapas",
          f"{xv_tap_act*100:.1f}%",
          delta=f"{(xv_tap_act - BASE_TAP)*100:+.1f}pp vs baseline 100%",
          delta_color="normal" if xv_tap_act < BASE_TAP else "inverse")
k4.metric("Costo extra cajas/año",
          f"${abs(costo_extra_cajas):,.0f}",
          delta=f"{'costo' if costo_extra_cajas > 0 else 'ahorro'} · óptimo mín: {xv_opt_c*100:.1f}%",
          delta_color="inverse" if costo_extra_cajas > 0 else "normal")
k5.metric("Ahorro NETO/año",
          f"${ahorro_neto_anual:,.0f}",
          delta="✓ Rentable" if ahorro_neto_anual > 0 else "✗ No rentable",
          delta_color="normal" if ahorro_neto_anual > 0 else "inverse")

st.markdown("---")
g1, g2 = st.columns(2)

# Gráfica: MFI vs % virgen
with g1:
    st.subheader(f"MFI Cajas vs % Virgen  (scrap={scrap_pct}%)")
    v_rng   = np.arange(0, 20.5, 0.5)
    mfi_v_v = [mfi_caja(v/100, xs) for v in v_rng]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v_rng, y=mfi_v_v, mode="lines",
                             line=dict(color="#58a6ff", width=2.5), name="MFI cajas"))
    fig.add_hline(y=MFI_LIM, line_dash="dash", line_color="#f85149",
                  annotation_text="Límite 10.5")
    fig.add_vline(x=virgin_pct, line_dash="dot", line_color="#58a6ff",
                  annotation_text=f"Actual {virgin_pct}%")
    fig.add_vline(x=xv_opt_c*100, line_dash="dot", line_color="#3fb950",
                  annotation_text=f"Óptimo {xv_opt_c*100:.1f}%")
    fig.update_layout(**LAYOUT_BASE,
                      xaxis_title="% Virgen", yaxis_title="MFI (g/10min)",
                      yaxis=dict(range=[8, 13]))
    st.plotly_chart(fig, use_container_width=True)

# Gráfica: MFI vs % scrap
with g2:
    st.subheader(f"MFI Cajas vs % Scrap  (virgen={virgin_pct}%)")
    s_rng   = np.arange(0, 8.5, 0.5)
    mfi_s_v = [mfi_caja(xv, s/100) for s in s_rng]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=s_rng, y=mfi_s_v, mode="lines",
                              line=dict(color="#f85149", width=2.5), name="MFI cajas"))
    fig2.add_hline(y=MFI_LIM, line_dash="dash", line_color="#f85149",
                   annotation_text="Límite 10.5")
    fig2.add_vline(x=scrap_pct, line_dash="dot", line_color="#f85149",
                   annotation_text=f"Actual {scrap_pct}%")
    fig2.update_layout(**LAYOUT_BASE,
                       xaxis_title="% Scrap", yaxis_title="MFI (g/10min)",
                       yaxis=dict(range=[8, 13]))
    st.plotly_chart(fig2, use_container_width=True)

g3, g4 = st.columns(2)

# Gráfica: Ahorro neto vs % color
with g3:
    st.subheader("Ahorro Neto vs % Color García")
    cd_rng = np.arange(0, 105, 5)
    ahs = []
    for cd in cd_rng:
        xv_t_ = 1 - cd/100
        ahs.append((BASE_TAP - xv_t_)*KG_TAPAS*price*12 - (xv - BASE_CAJ)*KG_CAJAS*price*12)

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=cd_rng, y=ahs,
                          marker_color=["#3fb950" if a >= 0 else "#f85149" for a in ahs]))
    fig3.add_hline(y=0, line_color="#484f58")
    fig3.add_vline(x=color_disp, line_dash="dot", line_color="#d2a8ff",
                   annotation_text=f"Actual {color_disp}%")
    fig3.update_layout(**LAYOUT_BASE,
                       xaxis_title="% Color disponible", yaxis_title="USD/año",
                       xaxis=dict(ticksuffix="%"))
    st.plotly_chart(fig3, use_container_width=True)

# Gráfica: Ahorro neto vs % virgen cajas (scrap y color fijos)
with g4:
    st.subheader(f"Ahorro Neto vs % Virgen Cajas  (scrap={scrap_pct}%)")
    v_rng2 = np.arange(0, 20.5, 0.5)
    ahs2, colors2 = [], []
    for v in v_rng2:
        xv_t_ = 1 - xcd
        ah = (BASE_TAP - xv_t_)*KG_TAPAS*price*12 - (v/100 - BASE_CAJ)*KG_CAJAS*price*12
        ahs2.append(ah)
        # Gris si está por debajo del virgen óptimo (infactible — fuera de spec)
        if v/100 < xv_opt_c:
            colors2.append("#484f58")
        else:
            colors2.append("#3fb950" if ah >= 0 else "#f85149")
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(x=v_rng2, y=ahs2, marker_color=colors2,
                          name="Ahorro neto"))
    fig4.add_hline(y=0, line_color="#484f58")
    fig4.add_vline(x=xv_opt_c*100, line_dash="dash", line_color="#e3b341",
                   annotation_text=f"Óptimo mín {xv_opt_c*100:.1f}%")
    fig4.add_vline(x=virgin_pct, line_dash="dot", line_color="#58a6ff",
                   annotation_text=f"Actual {virgin_pct}%")
    fig4.update_layout(**LAYOUT_BASE,
                       xaxis_title="% Virgen cajas", yaxis_title="USD/año",
                       xaxis=dict(ticksuffix="%"))
    st.plotly_chart(fig4, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    f"Producción: {BAT_MES:,} baterías/mes · Cajas: {KG_CAJAS:,.0f} kg/mes · "
    f"Tapas: {KG_TAPAS:,.0f} kg/mes · Precio virgen: ${price}/kg"
)
