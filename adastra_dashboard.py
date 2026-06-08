"""
AdAstra — Ground Station Dashboard  v2.1
Dashboard funcional de telemetría en tiempo real.
Recibe datos del ESP32 vía Serial USB y los visualiza.
Mejoras: st.fragment anti-flicker, media móvil altitud, stats, tasa de recepción.
"""

import streamlit as st
import numpy as np
import pandas as pd
import time
import io
from pathlib import Path
from datetime import datetime, timedelta

from serial_reader import SerialReader, ConnectionState, list_available_ports, detect_esp32_port
from telemetry_parser import TelemetryPacket, PacketAlert, validate_packet_sequence


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
# SESSION STATE — Persistencia entre reruns
# ─────────────────────────────────────────────
if "serial_reader" not in st.session_state:
    st.session_state.serial_reader = SerialReader()
if "selected_port" not in st.session_state:
    st.session_state.selected_port = None

reader: SerialReader = st.session_state.serial_reader


# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────
def moving_average(values: list, window: int = 5) -> list:
    """Calcula media móvil simple con ventana dada."""
    if len(values) < window:
        return values
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(sum(values[start:i+1]) / (i - start + 1))
    return result


def format_duration(seconds: float) -> str:
    """Formatea segundos a HH:MM:SS."""
    s = int(seconds)
    hrs, remainder = divmod(s, 3600)
    mins, secs = divmod(remainder, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


# ─────────────────────────────────────────────
# ESTILO COMPACTO Y PROFESIONAL
# ─────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Fuente importada ── */
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');

  /* Reset de márgenes para pantalla completa */
  .block-container { padding: 0.6rem 1.2rem 0.5rem 1.2rem !important; }

  /* Fondo general */
  .stApp { background-color: #0b0f18; color: #cdd9e5; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
      background-color: #131929;
      border-right: 1px solid #1e2a3a;
      min-width: 240px !important;
      max-width: 240px !important;
  }
  section[data-testid="stSidebar"] > div { padding-top: 0.5rem; }

  /* Título */
  h1 {
      color: #4d9de0 !important;
      font-family: 'JetBrains Mono', 'Consolas', monospace !important;
      font-size: 1.1rem !important;
      letter-spacing: 1.5px;
      margin-bottom: 0 !important;
      padding-bottom: 0 !important;
  }
  h4 {
      color: #5b8db8 !important;
      font-family: 'JetBrains Mono', 'Consolas', monospace !important;
      font-size: 0.72rem !important;
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
      font-family: 'JetBrains Mono', 'Consolas', monospace !important;
  }
  div[data-testid="metric-container"] > div > div:first-child {
      color: #e6edf3 !important;
      font-size: 1.25rem !important;
      font-weight: 600;
      font-family: 'JetBrains Mono', 'Consolas', monospace !important;
  }
  [data-testid="stMetricDelta"] {
      font-size: 10px !important;
  }

  /* Código / Consola */
  code, pre {
      background-color: #070b12 !important;
      color: #3fb950 !important;
      font-family: 'JetBrains Mono', 'Consolas', monospace !important;
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
      font-family: 'JetBrains Mono', 'Consolas', monospace;
      font-size: 11px;
      padding: 6px 10px;
      text-align: left;
      letter-spacing: 0.5px;
      transition: all 0.2s ease;
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
      font-family: 'JetBrains Mono', 'Consolas', monospace;
      font-size: 9px;
      color: #3a5570;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      margin: 6px 0 3px 0;
  }

  /* Badge de estado — conectado */
  .status-ok {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #071a12;
      border: 1px solid #1a5c32;
      border-radius: 4px;
      padding: 4px 10px;
      font-family: 'JetBrains Mono', 'Consolas', monospace;
      font-size: 10px;
      color: #3fb950;
      letter-spacing: 0.8px;
      margin-top: 6px;
      width: 100%;
  }
  .dot-green { width: 6px; height: 6px; background: #3fb950;
          border-radius: 50%; display:inline-block;
          box-shadow: 0 0 6px #3fb950;
          animation: pulse-green 2s infinite; }
  @keyframes pulse-green {
      0%, 100% { box-shadow: 0 0 4px #3fb950; }
      50% { box-shadow: 0 0 12px #3fb950, 0 0 20px #3fb95044; }
  }

  /* Badge de estado — desconectado */
  .status-off {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #1a1208;
      border: 1px solid #5c4a1a;
      border-radius: 4px;
      padding: 4px 10px;
      font-family: 'JetBrains Mono', 'Consolas', monospace;
      font-size: 10px;
      color: #c4a035;
      letter-spacing: 0.8px;
      margin-top: 6px;
      width: 100%;
  }
  .dot-yellow { width: 6px; height: 6px; background: #c4a035;
          border-radius: 50%; display:inline-block;
          box-shadow: 0 0 6px #c4a035; }

  /* Badge de estado — error */
  .status-err {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #1a0808;
      border: 1px solid #5c1a1a;
      border-radius: 4px;
      padding: 4px 10px;
      font-family: 'JetBrains Mono', 'Consolas', monospace;
      font-size: 10px;
      color: #e3595c;
      letter-spacing: 0.8px;
      margin-top: 6px;
      width: 100%;
  }
  .dot-red { width: 6px; height: 6px; background: #e3595c;
          border-radius: 50%; display:inline-block;
          box-shadow: 0 0 6px #e3595c;
          animation: pulse-red 1.5s infinite; }
  @keyframes pulse-red {
      0%, 100% { box-shadow: 0 0 4px #e3595c; }
      50% { box-shadow: 0 0 12px #e3595c, 0 0 20px #e3595c44; }
  }

  /* Recuadro gráfica */
  .chart-box {
      background: #0f1620;
      border: 1px solid #1e2a3a;
      border-radius: 6px;
      padding: 8px 12px 4px 12px;
      margin-bottom: 4px;
  }
  .chart-title {
      font-family: 'JetBrains Mono', 'Consolas', monospace;
      font-size: 11px;
      color: #5b8db8;
      letter-spacing: 1px;
      text-transform: uppercase;
      margin-bottom: 2px;
  }
  .chart-sub {
      font-family: 'JetBrains Mono', 'Consolas', monospace;
      font-size: 9px;
      color: #2d4a66;
      margin-top: 0px;
  }

  /* Alerta inline */
  .alert-warn {
      background: #1a1208;
      border-left: 3px solid #c4a035;
      padding: 4px 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      color: #c4a035;
      margin: 2px 0;
      border-radius: 0 4px 4px 0;
  }
  .alert-err {
      background: #1a0808;
      border-left: 3px solid #e3595c;
      padding: 4px 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      color: #e3595c;
      margin: 2px 0;
      border-radius: 0 4px 4px 0;
  }

  /* Stat badges */
  .stat-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin: 2px 0 4px 0;
  }
  .stat-badge {
      font-family: 'JetBrains Mono', monospace;
      font-size: 9px;
      color: #3a5570;
      background: #0b1018;
      border: 1px solid #1a2535;
      border-radius: 3px;
      padding: 2px 6px;
      display: inline-block;
  }
  .stat-badge b { color: #6b8fad; }

  /* Footer */
  .footer {
      font-family: 'JetBrains Mono', 'Consolas', monospace;
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

  /* ── Ocultar barra superior de Streamlit ── */
  header[data-testid="stHeader"]          { display: none !important; }
  #MainMenu                               { display: none !important; }
  div[data-testid="stToolbar"]            { display: none !important; }
  div[data-testid="stDecoration"]         { display: none !important; }
  footer                                  { display: none !important; }
  .viewerBadge_container__1QSob          { display: none !important; }

  /* Selectbox styling */
  .stSelectbox label {
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 10px !important;
      color: #5b8db8 !important;
      text-transform: uppercase;
      letter-spacing: 1px;
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR (estático — no se refresca con fragment)
# ─────────────────────────────────────────────
with st.sidebar:
    # Logo
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

    # ── Enlace Serial ──
    st.markdown('<p class="sec-label">Enlace Serial</p>', unsafe_allow_html=True)

    # Auto-detección de puertos
    available_ports = list_available_ports()
    port_options = [f"{p[0]}  —  {p[1]}" for p in available_ports]

    if not port_options:
        st.markdown(
            '<div class="alert-warn">⚠ No se detectaron puertos COM</div>',
            unsafe_allow_html=True,
        )
        selected_port_str = None
    else:
        # Intentar auto-detectar ESP32
        auto_port = detect_esp32_port()
        default_idx = 0
        if auto_port:
            for i, (port, desc) in enumerate(available_ports):
                if port == auto_port:
                    default_idx = i
                    break

        selected_port_str = st.selectbox(
            "Puerto COM",
            port_options,
            index=default_idx,
            key="port_selector",
        )

    # Botones de conexión
    col_conn, col_disc = st.columns(2)
    with col_conn:
        btn_connect = st.button("▶ Conectar", key="btn_connect", use_container_width=True)
    with col_disc:
        btn_disconnect = st.button("✕ Desconectar", key="btn_disconnect", use_container_width=True)

    # Lógica de conexión
    if btn_connect and selected_port_str and not reader.is_connected:
        port_name = selected_port_str.split("  —  ")[0].strip()
        success = reader.connect(port_name)
        if success:
            st.rerun()
        else:
            st.error(f"Error: {reader.error_message}")

    if btn_disconnect and reader.is_connected:
        reader.disconnect()
        st.rerun()

    # ── Control ──
    st.markdown('<p class="sec-label">Control</p>', unsafe_allow_html=True)

    if reader.is_connected:
        btn_reset_alt = st.button("↻ Reset Altitud Base", key="btn_reset_alt", use_container_width=True)
        if btn_reset_alt:
            reader.reset_baseline_pressure()
            st.rerun()

    # ── Exportar ──
    st.markdown('<p class="sec-label">Exportar</p>', unsafe_allow_html=True)

    packets_snapshot = reader.get_packets_snapshot()
    if packets_snapshot:
        # Preparar datos para Excel
        export_data = []
        for pkt in packets_snapshot:
            export_data.append({
                "PKT": pkt.pkt,
                "Uptime (s)": pkt.uptime,
                "FLAGS": f"0x{pkt.flags:X}",
                "Temp (°C)": pkt.temp,
                "Presión (hPa)": pkt.pres,
                "Alt Rel (m)": round(pkt.alt_rel, 2) if pkt.alt_rel is not None else None,
                "AX (g)": pkt.ax,
                "AY (g)": pkt.ay,
                "AZ (g)": pkt.az,
                "GX (°/s)": pkt.gx,
                "GY (°/s)": pkt.gy,
                "GZ (°/s)": pkt.gz,
                "RSSI (dBm)": pkt.rssi,
                "SNR (dB)": pkt.snr,
                "Accel Total (g)": round(pkt.accel_total, 4) if pkt.accel_total else None,
                "Timestamp": pkt.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            })
        df_export = pd.DataFrame(export_data)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_export.to_excel(writer, sheet_name="Telemetría", index=False)
        buffer.seek(0)

        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="↓ Guardar Excel (.xlsx)",
            data=buffer,
            file_name=f"adastra_telemetry_{ts_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.button("↓ Sin datos para exportar", disabled=True, use_container_width=True)

    # ── Estado de conexión ──
    st.markdown("---")

    if reader.state == ConnectionState.CONNECTED:
        st.markdown(
            f'<div class="status-ok"><span class="dot-green"></span>ENLACE ACTIVO  —  {reader.port_name}</div>',
            unsafe_allow_html=True,
        )
    elif reader.state == ConnectionState.ERROR:
        st.markdown(
            f'<div class="status-err"><span class="dot-red"></span>ERROR  —  {reader.error_message or "Desconocido"}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-off"><span class="dot-yellow"></span>SIN CONEXIÓN</div>',
            unsafe_allow_html=True,
        )

    # Info del GS
    pps = reader.packets_per_second
    session_dur = format_duration(reader.session_duration_s)
    st.markdown(
        f"""<div style="font-family:'JetBrains Mono',Consolas,monospace; font-size:9px; color:#2d4a66; margin-top:8px; line-height:1.7;">
        GS v2.1.0 &nbsp;|&nbsp; 433.92 MHz<br>
        LoRa SF9 BW125 &nbsp;|&nbsp; 115200 baud<br>
        Paquetes: {reader.total_received} &nbsp;|&nbsp; {pps:.2f} pkt/s<br>
        Sesión: {session_dur} &nbsp;|&nbsp; {datetime.now().strftime("%H:%M:%S")}
        </div>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# ENCABEZADO (estático)
# ─────────────────────────────────────────────
st.title("PANEL DE CONTROL  //  MISIÓN ADASTRA  —  ESTACIÓN TERRENA")
st.markdown(
    '<span style="font-family:\'JetBrains Mono\',Consolas,monospace; font-size:10px; color:#2d4a66; letter-spacing:1px;">'
    'PDR 2026  ·  Equipo AdAstra  ·  Pontificia Universidad Católica del Perú (PUCP)'
    '</span>',
    unsafe_allow_html=True,
)
st.markdown("---")


# ─────────────────────────────────────────────
# FRAGMENT — Contenido dinámico (se refresca
# cada 1s SIN parpadeo del resto de la UI)
# ─────────────────────────────────────────────
@st.fragment(run_every=timedelta(seconds=1))
def live_telemetry():
    """Fragment que se auto-refresca cada segundo sin recargar toda la página."""

    latest = reader.get_latest_packet()
    previous = reader.get_previous_packet()
    all_packets = reader.get_packets_snapshot()

    # ── MÉTRICAS — Fila 1 ──
    st.markdown("#### TELEMETRÍA EN TIEMPO REAL")

    if latest:
        # Calcular deltas
        d_temp = round(latest.temp - previous.temp, 2) if previous else None
        d_pres = round(latest.pres - previous.pres, 2) if previous else None
        d_alt = round((latest.alt_rel or 0) - (previous.alt_rel or 0), 2) if previous else None

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(
                "TEMP — Temperatura",
                f"{latest.temp:.2f} °C",
                f"{d_temp:+.2f} °C" if d_temp is not None else None,
            )
            # Stats
            temps = [p.temp for p in all_packets]
            st.markdown(
                f'<div class="stat-row">'
                f'<span class="stat-badge">Min <b>{min(temps):.1f}°</b></span>'
                f'<span class="stat-badge">Max <b>{max(temps):.1f}°</b></span>'
                f'<span class="stat-badge">Avg <b>{sum(temps)/len(temps):.1f}°</b></span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with c2:
            alt_display = f"{latest.alt_rel:.1f} m" if latest.alt_rel is not None else "— m"
            st.metric(
                "ALT — Altitud Relativa",
                alt_display,
                f"{d_alt:+.1f} m" if d_alt is not None else None,
            )
            alts = [p.alt_rel for p in all_packets if p.alt_rel is not None]
            if alts:
                st.markdown(
                    f'<div class="stat-row">'
                    f'<span class="stat-badge">Min <b>{min(alts):.1f}m</b></span>'
                    f'<span class="stat-badge">Max <b>{max(alts):.1f}m</b></span>'
                    f'<span class="stat-badge">Avg <b>{sum(alts)/len(alts):.1f}m</b></span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with c3:
            st.metric(
                "PRES — Presión",
                f"{latest.pres:.1f} hPa",
                f"{d_pres:+.1f} hPa" if d_pres is not None else None,
            )
            pressures = [p.pres for p in all_packets]
            st.markdown(
                f'<div class="stat-row">'
                f'<span class="stat-badge">Min <b>{min(pressures):.1f}</b></span>'
                f'<span class="stat-badge">Max <b>{max(pressures):.1f}</b></span>'
                f'<span class="stat-badge">Δ <b>{pressures[-1]-pressures[0]:+.2f}</b></span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with c4:
            rssi_color = "inverse" if latest.rssi_weak else "normal"
            st.metric(
                "RF — RSSI / SNR",
                f"{latest.rssi} dBm",
                f"SNR: {latest.snr:.1f} dB  |  {latest.signal_quality}",
                delta_color=rssi_color,
            )
            rssis = [p.rssi for p in all_packets]
            snrs = [p.snr for p in all_packets]
            st.markdown(
                f'<div class="stat-row">'
                f'<span class="stat-badge">RSSI avg <b>{sum(rssis)/len(rssis):.0f}</b></span>'
                f'<span class="stat-badge">SNR avg <b>{sum(snrs)/len(snrs):.1f}</b></span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── MÉTRICAS — Fila 2 ──
        c5, c6, c7, c8 = st.columns(4)
        with c5:
            st.metric(
                "ACCEL — Aceleración Total",
                f"{latest.accel_total:.3f} g",
                f"AZ: {latest.az:.3f} g",
            )
            accels = [p.accel_total for p in all_packets if p.accel_total]
            st.markdown(
                f'<div class="stat-row">'
                f'<span class="stat-badge">Min <b>{min(accels):.3f}g</b></span>'
                f'<span class="stat-badge">Max <b>{max(accels):.3f}g</b></span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with c6:
            pps = reader.packets_per_second
            st.metric(
                "PKT — Recibidos",
                f"{reader.total_received}",
                f"#{latest.pkt}  |  {pps:.2f} pkt/s",
            )
        with c7:
            loss_pct = reader.loss_percentage
            loss_delta = f"{reader.packets_lost} ({loss_pct:.1f}%)" if reader.packets_lost > 0 else "0"
            st.metric(
                "LOSS — Paquetes Perdidos",
                loss_delta,
                f"-{reader.packets_lost}" if reader.packets_lost > 0 else "Sin pérdida",
                delta_color="inverse" if reader.packets_lost > 0 else "off",
            )
        with c8:
            uptime_str = format_duration(latest.uptime)
            flags_str = "✓ ALL OK" if latest.all_sensors_ok else f"⚠ 0x{latest.flags:X}"
            st.metric("UP — Uptime STM32", uptime_str, f"FLAGS: {flags_str}")

    else:
        # Sin datos — mostrar placeholders
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("TEMP — Temperatura", "— °C", None)
        with c2:
            st.metric("ALT — Altitud Relativa", "— m", None)
        with c3:
            st.metric("PRES — Presión", "— hPa", None)
        with c4:
            st.metric("RF — RSSI / SNR", "— dBm", None)

        c5, c6, c7, c8 = st.columns(4)
        with c5:
            st.metric("ACCEL — Aceleración Total", "— g", None)
        with c6:
            st.metric("PKT — Recibidos", "0", None)
        with c7:
            st.metric("LOSS — Paquetes Perdidos", "0", None)
        with c8:
            st.metric("UP — Uptime STM32", "—:—", "Esperando datos...")

    st.markdown("---")

    # ── GRÁFICAS ──
    st.markdown("#### VISUALIZACIÓN DE TELEMETRÍA")

    if len(all_packets) >= 2:
        times = [p.uptime for p in all_packets]

        # Fila 1: Altitud (con media móvil) + Temperatura
        g1, g2 = st.columns(2)

        with g1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.markdown('<p class="chart-title">ALT RELATIVA (m) — con media móvil 5</p>', unsafe_allow_html=True)
            alt_raw = [p.alt_rel if p.alt_rel is not None else 0 for p in all_packets]
            alt_smooth = moving_average(alt_raw, window=5)
            df_alt = pd.DataFrame({
                "Raw": alt_raw,
                "Suavizada": alt_smooth,
            }, index=times)
            st.line_chart(df_alt, color=["#1e3a5f", "#4d9de0"], height=180)
            last_alt = all_packets[-1].alt_rel
            st.markdown(
                f'<p class="chart-sub">Último: {last_alt:.1f} m  |  Suav: {alt_smooth[-1]:.2f} m  |  '
                f'Muestras: {len(all_packets)}  |  P_base: {reader._p_base:.1f} hPa</p>'
                if last_alt is not None and reader._p_base
                else '<p class="chart-sub">Calculando...</p>',
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with g2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.markdown('<p class="chart-title">TEMPERATURA (°C) vs UPTIME (s)</p>', unsafe_allow_html=True)
            df_temp = pd.DataFrame({
                "Temp (°C)": [p.temp for p in all_packets],
            }, index=times)
            st.line_chart(df_temp, color=["#e3795c"], height=180)
            temps = [p.temp for p in all_packets]
            avg_t = sum(temps) / len(temps)
            st.markdown(
                f'<p class="chart-sub">Último: {temps[-1]:.2f} °C  |  '
                f'Min: {min(temps):.2f}  |  Max: {max(temps):.2f}  |  Avg: {avg_t:.2f}</p>',
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # Fila 2: Presión + Aceleración
        g3, g4 = st.columns(2)

        with g3:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.markdown('<p class="chart-title">PRESIÓN (hPa) vs UPTIME (s)</p>', unsafe_allow_html=True)
            df_pres = pd.DataFrame({
                "Pres (hPa)": [p.pres for p in all_packets],
            }, index=times)
            st.line_chart(df_pres, color=["#3fb950"], height=180)
            pres_vals = [p.pres for p in all_packets]
            st.markdown(
                f'<p class="chart-sub">Último: {pres_vals[-1]:.1f} hPa  |  '
                f'Min: {min(pres_vals):.1f}  |  Max: {max(pres_vals):.1f}  |  '
                f'Δ total: {pres_vals[-1] - pres_vals[0]:+.2f} hPa</p>',
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with g4:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.markdown('<p class="chart-title">ACELERACIÓN (g) vs UPTIME — XYZ</p>', unsafe_allow_html=True)
            df_accel = pd.DataFrame({
                "AX": [p.ax for p in all_packets],
                "AY": [p.ay for p in all_packets],
                "AZ": [p.az for p in all_packets],
            }, index=times)
            st.line_chart(df_accel, color=["#e3595c", "#3fb950", "#4d9de0"], height=180)
            st.markdown(
                f'<p class="chart-sub">AX:{all_packets[-1].ax:+.3f}  AY:{all_packets[-1].ay:+.3f}  '
                f'AZ:{all_packets[-1].az:+.3f}  |  |A|={all_packets[-1].accel_total:.3f}g</p>',
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # Fila 3: Giroscopio + RSSI/SNR
        g5, g6 = st.columns(2)

        with g5:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.markdown('<p class="chart-title">GIROSCOPIO (°/s) vs UPTIME — XYZ</p>', unsafe_allow_html=True)
            df_gyro = pd.DataFrame({
                "GX": [p.gx for p in all_packets],
                "GY": [p.gy for p in all_packets],
                "GZ": [p.gz for p in all_packets],
            }, index=times)
            st.line_chart(df_gyro, color=["#e3595c", "#3fb950", "#4d9de0"], height=180)
            st.markdown(
                f'<p class="chart-sub">GX:{all_packets[-1].gx:+.1f}  GY:{all_packets[-1].gy:+.1f}  '
                f'GZ:{all_packets[-1].gz:+.1f} °/s</p>',
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with g6:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            st.markdown('<p class="chart-title">SEÑAL RF — RSSI (dBm) + SNR (dB)</p>', unsafe_allow_html=True)
            df_rf = pd.DataFrame({
                "RSSI (dBm)": [p.rssi for p in all_packets],
                "SNR (dB)": [p.snr for p in all_packets],
            }, index=times)
            st.line_chart(df_rf, color=["#c4a035", "#8b5cf6"], height=180)

            weak_count = sum(1 for p in all_packets if p.rssi_weak)
            warn_str = f"  |  ⚠ {weak_count} < -120dBm" if weak_count > 0 else ""
            rssis = [p.rssi for p in all_packets]
            st.markdown(
                f'<p class="chart-sub">RSSI: {rssis[-1]} dBm (avg {sum(rssis)/len(rssis):.0f})  |  '
                f'SNR: {all_packets[-1].snr:.1f} dB{warn_str}</p>',
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown(
            '<div style="text-align:center; padding:40px; border:1px dashed #1e2a3a; '
            'border-radius:8px; margin:10px 0;">'
            '<p style="font-family:\'JetBrains Mono\',monospace; color:#2d4a66; font-size:12px;">'
            '📡 Conecta el ESP32 y espera al menos 2 paquetes para ver las gráficas<br>'
            '<span style="font-size:10px;">Selecciona un puerto COM en el sidebar y presiona Conectar</span>'
            '</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── ALERTAS ──
    if all_packets:
        recent = all_packets[-20:] if len(all_packets) > 20 else all_packets
        alerts = validate_packet_sequence(recent)

        if alerts:
            st.markdown("#### ALERTAS")
            for alert in alerts[-5:]:
                css_class = "alert-err" if alert.level == "ERROR" else "alert-warn"
                icon = "🔴" if alert.level == "ERROR" else "⚠️"
                st.markdown(
                    f'<div class="{css_class}">{icon} PKT:{alert.pkt_num} — {alert.message}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("---")

    # ── CONSOLA SERIAL ──
    st.markdown("#### CONSOLA SERIAL  —  TRAMAS RAW ESP32")
    st.markdown(
        '<span style="font-family:\'JetBrains Mono\',Consolas,monospace; font-size:9px; color:#2d4a66;">'
        'Formato: PKT:{n} UP:{s}s FLAGS:0x{f} TEMP:{t}°C PRES:{p}hPa AX AY AZ GX GY GZ RSSI SNR'
        '</span>',
        unsafe_allow_html=True,
    )

    raw_lines = reader.get_raw_lines_snapshot()
    if raw_lines:
        display_lines = raw_lines[-30:]
        console_text = ""
        for ts, line in display_lines:
            time_str = ts.strftime("%H:%M:%S")
            prefix = ""
            if "FLAGS:0x1" in line or "FLAGS:0x0" in line:
                prefix = "⚠ "
            console_text += f"[{time_str}] {prefix}{line}\n"

        console_text += "─" * 80 + "\n"
        loss_pct = reader.loss_percentage
        console_text += (
            f"Tramas: {reader.total_received}  |  "
            f"Errores: {reader.total_errors}  |  "
            f"Perdidos: {reader.packets_lost} ({loss_pct:.1f}%)  |  "
            f"Buffer: {len(all_packets)}/{reader.MAX_PACKETS}  |  "
            f"Rate: {reader.packets_per_second:.2f} pkt/s"
        )
        st.code(console_text, language=None)
    else:
        if reader.is_connected:
            st.code("Esperando tramas del ESP32...\nConectado — escuchando puerto serial", language=None)
        else:
            st.code(
                "Sin conexión serial.\n"
                "1. Conecta el ESP32 por USB\n"
                "2. Selecciona el puerto COM en el sidebar\n"
                "3. Presiona 'Conectar'\n\n"
                "El dashboard auto-detectará el puerto del ESP32.",
                language=None,
            )


# ─────────────────────────────────────────────
# EJECUTAR FRAGMENT
# ─────────────────────────────────────────────
live_telemetry()


# ─────────────────────────────────────────────
# PIE DE PÁGINA (estático)
# ─────────────────────────────────────────────
st.markdown(
    '<p class="footer">'
    'AdAstra CubeSat Mission  ·  Ground Station Software v2.1.0  ·  PDR 2026  ·  '
    'Equipo AdAstra  —  Pontificia Universidad Católica del Perú (PUCP)'
    '</p>',
    unsafe_allow_html=True,
)
