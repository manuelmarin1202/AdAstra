import streamlit as st
import numpy as np
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURACIÓN GENERAL
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AdAstra GS | PUCP",
    page_icon="assets/LOGO_ADASTRA.jpeg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# ESTILO COMPACTO Y PROFESIONAL
# ─────────────────────────────────────────────
st.markdown("""
<style>
  /* Reset de márgenes para pantalla completa */
  .block-container { padding: 0.6rem 1.2rem 0.5rem 1.2rem !important; }

  /* Fondo general */
  .stApp { background-color: #0b0f18; color: #cdd9e5; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
      background-color: #131929;
      border-right: 1px solid #1e2a3a;
      min-width: 210px !important;
      max-width: 210px !important;
  }
  section[data-testid="stSidebar"] > div { padding-top: 0.5rem; }

  /* Título */
  h1 {
      color: #4d9de0 !important;
      font-family: 'Consolas', 'Courier New', monospace !important;
      font-size: 1.15rem !important;
      letter-spacing: 1.5px;
      margin-bottom: 0 !important;
      padding-bottom: 0 !important;
  }
  h4 {
      color: #5b8db8 !important;
      font-family: 'Consolas', monospace !important;
      font-size: 0.75rem !important;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-bottom: 4px !important;
      margin-top: 6px !important;
  }

  /* Métricas compactas */
  div[data-testid="metric-container"] {
      background-color: #131929;
      border: 1px solid #1e2a3a;
      border-left: 3px solid #4d9de0;
      border-radius: 6px;
      padding: 8px 12px !important;
  }
  div[data-testid="metric-container"] label {
      color: #5b8db8 !important;
      font-size: 10px !important;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      font-family: 'Consolas', monospace !important;
  }
  div[data-testid="metric-container"] > div > div:first-child {
      color: #e6edf3 !important;
      font-size: 1.3rem !important;
      font-weight: 600;
      font-family: 'Consolas', monospace !important;
  }
  [data-testid="stMetricDelta"] {
      font-size: 10px !important;
  }

  /* Código / Consola */
  code, pre {
      background-color: #070b12 !important;
      color: #3fb950 !important;
      font-family: 'Consolas', 'Courier New', monospace !important;
      font-size: 10.5px !important;
      line-height: 1.45 !important;
  }

  /* Botones sidebar */
  .stButton > button {
      width: 100%;
      background-color: #0f1a28;
      color: #8ba7c4;
      border: 1px solid #1e2a3a;
      border-radius: 4px;
      font-family: 'Consolas', monospace;
      font-size: 11px;
      padding: 4px 8px;
      text-align: left;
      letter-spacing: 0.5px;
      transition: all 0.15s ease;
      margin-bottom: 2px;
  }
  .stButton > button:hover {
      background-color: #1a3050;
      border-color: #4d9de0;
      color: #4d9de0;
  }

  /* Separador */
  hr { border-color: #1e2a3a; margin: 6px 0 !important; }

  /* Etiquetas de sección */
  .sec-label {
      font-family: 'Consolas', monospace;
      font-size: 9px;
      color: #3a5570;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      margin: 6px 0 3px 0;
  }

  /* Badge de estado */
  .status-ok {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #071a12;
      border: 1px solid #1a5c32;
      border-radius: 4px;
      padding: 4px 10px;
      font-family: 'Consolas', monospace;
      font-size: 10px;
      color: #3fb950;
      letter-spacing: 0.8px;
      margin-top: 6px;
      width: 100%;
  }
  .dot { width: 6px; height: 6px; background: #3fb950;
          border-radius: 50%; display:inline-block;
          box-shadow: 0 0 6px #3fb950; }

  /* Recuadro gráfica */
  .chart-box {
      background: #0f1620;
      border: 1px solid #1e2a3a;
      border-radius: 6px;
      padding: 8px 12px 4px 12px;
      margin-bottom: 4px;
  }
  .chart-title {
      font-family: 'Consolas', monospace;
      font-size: 11px;
      color: #5b8db8;
      letter-spacing: 1px;
      text-transform: uppercase;
      margin-bottom: 2px;
  }
  .chart-sub {
      font-family: 'Consolas', monospace;
      font-size: 9px;
      color: #2d4a66;
      margin-top: 0px;
  }

  /* Footer */
  .footer {
      font-family: 'Consolas', monospace;
      font-size: 9px;
      color: #2d4a66;
      text-align: center;
      margin-top: 4px;
      letter-spacing: 1px;
  }

  /* Reduce espacio entre elementos */
  .stElementContainer { margin-bottom: 0px !important; }
  .stColumns { gap: 8px !important; }
  div[data-testid="column"] { padding: 0 4px !important; }

  /* ── Ocultar barra superior de Streamlit (Deploy / hamburger) ── */
  header[data-testid="stHeader"]          { display: none !important; }
  #MainMenu                               { display: none !important; }
  div[data-testid="stToolbar"]            { display: none !important; }
  div[data-testid="stDecoration"]         { display: none !important; }
  footer                                  { display: none !important; }
  .viewerBadge_container__1QSob          { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    # Logo — compacto
    logo_path = Path(__file__).parent / "assets" / "LOGO_ADASTRA.jpeg"
    if logo_path.exists():
        st.image(str(logo_path), width=140)
    else:
        st.markdown(
            '<div style="text-align:center; border:1px dashed #1e2a3a; border-radius:6px;'
            'padding:10px; margin-bottom:6px;">'
            '<span style="font-size:10px; color:#2d4a66; font-family:Consolas,monospace;">'
            'assets/LOGO_ADASTRA.jpeg</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<p class="sec-label">Enlace Serial</p>', unsafe_allow_html=True)
    st.button("[ COM3 ]  Conectar Puerto")
    st.button("[  X  ]  Desconectar")

    st.markdown('<p class="sec-label">Recepción</p>', unsafe_allow_html=True)
    st.button("[  ▶  ]  Iniciar Recepción")

    st.markdown('<p class="sec-label">Exportar</p>', unsafe_allow_html=True)
    st.button("[  ↓  ]  Guardar a Excel (.xlsx)")

    st.markdown("---")
    st.markdown(
        '<div class="status-ok"><span class="dot"></span>ENLACE ACTIVO  1 Hz</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div style="font-family:Consolas,monospace; font-size:9px; color:#2d4a66; margin-top:8px; line-height:1.7;">
        GS v1.2.0 &nbsp;|&nbsp; 433.92 MHz<br>
        UART / CSV &nbsp;|&nbsp; 9600 baud<br>
        UTC-5 &nbsp;|&nbsp; 2026-02-24
        </div>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# ENCABEZADO
# ─────────────────────────────────────────────
st.title("PANEL DE CONTROL  //  MISIÓN ADASTRA  —  ESTACIÓN TERRENA")
st.markdown(
    '<span style="font-family:Consolas,monospace; font-size:10px; color:#2d4a66; letter-spacing:1px;">'
    'PDR 2026  ·  Equipo AdAstra  ·  Pontificia Universidad Católica del Perú (PUCP)'
    '</span>',
    unsafe_allow_html=True,
)
st.markdown("---")


# ─────────────────────────────────────────────
# MÉTRICAS
# ─────────────────────────────────────────────
st.markdown("#### TELEMETRÍA EN TIEMPO REAL")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("VBAT — Voltaje Batería", "4.10 V", "-0.02 V", delta_color="inverse")
with c2:
    st.metric("ALT — Altitud", "80.5 m", "-1.3 m", delta_color="inverse")
with c3:
    st.metric("GPS — Lat / Lon", "-12.0692°", "-77.0791°")
with c4:
    st.metric("MODE — Estado Misión", "Fase 3", "Descenso Activo")

st.markdown("---")


# ─────────────────────────────────────────────
# DATOS SIMULADOS
# ─────────────────────────────────────────────
np.random.seed(42)
N = 120
tiempo = np.arange(N)

altitud = np.linspace(100, 80, N) + np.random.normal(0, 0.4, N)
df_alt  = pd.DataFrame({"ALT (m)": altitud}, index=tiempo)

incl_x  = 15 * np.sin(np.linspace(0, 4 * np.pi, N)) + np.random.normal(0, 1.5, N)
incl_y  = 10 * np.cos(np.linspace(0, 4 * np.pi, N)) + np.random.normal(0, 1.5, N)
df_incl = pd.DataFrame({"TILT_X (°)": incl_x, "TILT_Y (°)": incl_y}, index=tiempo)


# ─────────────────────────────────────────────
# GRÁFICAS
# ─────────────────────────────────────────────
st.markdown("#### VISUALIZACIÓN DE TELEMETRÍA")
g1, g2 = st.columns(2)

with g1:
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.markdown('<p class="chart-title">ALT (m) vs TIME (s)  —  Descenso controlado</p>', unsafe_allow_html=True)
    st.line_chart(df_alt, color=["#4d9de0"], height=200)
    st.markdown('<p class="chart-sub">Simulación: 100 m → 80 m  |  Δt = 120 s  |  σ = 0.4 m</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with g2:
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.markdown('<p class="chart-title">TILT_X / TILT_Y (°) vs TIME (s)  —  Estabilidad angular</p>', unsafe_allow_html=True)
    st.line_chart(df_incl, color=["#3fb950", "#e3795c"], height=200)
    st.markdown('<p class="chart-sub">Oscilación ±20°  |  T ≈ 60 s  |  σ = 1.5°</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")


# ─────────────────────────────────────────────
# CONSOLA SERIAL  §2.3.3
# ─────────────────────────────────────────────
st.markdown("#### CONSOLA SERIAL  —  TRAMAS CSV (PROTOCOLO §2.3.3)")
st.markdown(
    '<span style="font-family:Consolas,monospace; font-size:9px; color:#2d4a66;">'
    'Campos: ID · COUNT · TIME · MODE · VBAT · ALT · TEMP · TILT_X · TILT_Y · LAT · LON · CHK'
    '</span>',
    unsafe_allow_html=True,
)

consola = """\
[14:02:05] ADA,001,50705,1,4.10,100.0,25,-14.2, 8.5,-12.0692,-77.0791,A3
[14:02:06] ADA,002,50706,1,4.10, 99.6,25,-14.4, 8.3,-12.0692,-77.0791,B1
[14:02:07] ADA,003,50707,1,4.09, 99.1,25,-14.7, 8.0,-12.0693,-77.0791,C7
[14:02:08] ADA,004,50708,1,4.09, 98.5,25,-15.0, 7.8,-12.0693,-77.0792,D2
[14:02:09] ADA,005,50709,1,4.10, 98.0,25,-15.3, 7.5,-12.0694,-77.0792,E9
[14:02:10] ADA,006,50710,1,4.10, 97.4,26,-15.5, 7.3,-12.0694,-77.0793,F4
[14:02:11] ADA,007,50711,1,4.09, 96.8,26,-15.0, 7.0,-12.0695,-77.0793,G8
[14:02:12] ADA,008,50712,1,4.09, 96.2,26,-14.6, 6.8,-12.0695,-77.0794,H5
[14:02:13] ADA,009,50713,1,4.10, 95.5,26,-14.2, 6.5,-12.0696,-77.0794,A1
[14:02:14] ADA,010,50714,1,4.10, 94.9,25,-13.8, 6.3,-12.0696,-77.0795,B6
[14:02:15] ADA,011,50715,1,4.09, 94.3,25,-13.4, 6.0,-12.0697,-77.0795,C3
[14:02:16] ADA,012,50716,1,4.09, 93.7,25,-13.0, 5.8,-12.0697,-77.0796,D9
[14:02:17] ADA,013,50717,1,4.10, 93.0,25,-12.5, 5.5,-12.0698,-77.0796,E2
[14:02:18] ADA,014,50718,1,4.10, 92.4,25,-12.0, 5.3,-12.0698,-77.0797,F7
[14:02:19] ADA,015,50719,1,4.09, 91.8,26,-11.5, 5.0,-12.0699,-77.0797,G4
[14:02:20] ADA,016,50720,1,4.09, 91.1,26,-11.0, 4.8,-12.0699,-77.0798,H1
[14:02:21] ADA,017,50721,1,4.10, 90.5,26,-10.5, 4.5,-12.0700,-77.0798,A8
[14:02:22] ADA,018,50722,1,4.10, 89.9,26,-10.0, 4.3,-12.0700,-77.0799,B3
[14:02:23] ADA,019,50723,1,4.10, 89.2,25, -9.5, 4.0,-12.0701,-77.0799,C6
[14:02:24] ADA,020,50724,1,4.09, 88.6,25, -9.0, 3.8,-12.0701,-77.0800,D4
[14:02:25] ADA,021,50725,1,4.09, 87.9,25, -8.5, 3.5,-12.0702,-77.0800,E1
[14:02:26] ADA,022,50726,1,4.10, 87.3,25, -8.0, 3.3,-12.0702,-77.0801,F9
[14:02:27] ADA,023,50727,1,4.10, 86.6,25, -7.5, 3.0,-12.0703,-77.0801,G5
[14:02:28] ADA,024,50728,1,4.09, 86.0,26, -7.0, 2.8,-12.0703,-77.0802,H2
[14:02:29] ADA,025,50729,1,4.09, 85.3,26, -6.6, 2.5,-12.0704,-77.0802,A7
[14:02:30] ADA,026,50730,1,4.10, 84.7,26, -6.1, 2.3,-12.0704,-77.0803,B9
[14:02:31] ADA,027,50731,1,4.10, 84.0,26, -5.7, 2.0,-12.0705,-77.0803,C2
[14:02:32] ADA,028,50732,1,4.10, 83.4,25, -5.2, 1.8,-12.0705,-77.0804,D8
──────────────────────────────────────────────────────────────────────────────────
Formato §2.3.3: ID,COUNT,TIME,MODE,VBAT,ALT,TEMP,TILT_X,TILT_Y,LAT,LON,CHK
Tramas recibidas: 28  |  Errores CHK: 0  |  Buffer: 28/512\
"""
st.code(consola, language=None)

# ─────────────────────────────────────────────
# PIE DE PÁGINA
# ─────────────────────────────────────────────
st.markdown(
    '<p class="footer">'
    'AdAstra CubeSat Mission  ·  Ground Station Software v1.2.0  ·  PDR 2026  ·  '
    'Equipo AdAstra  —  Pontificia Universidad Católica del Perú (PUCP)'
    '</p>',
    unsafe_allow_html=True,
)
