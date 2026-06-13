"""
AdAstra — Telemetry Parser
Parsea tramas del ESP32 con campos condicionales.
Formato (campos opcionales entre corchetes):

  PKT:{n} UP:{s}s FLAGS:0x{f}
    [TEMP:{t}C PRES:{p}hPa]                           ← si FLAG_BME280
    [AX:{ax} AY:{ay} AZ:{az}g GX:{gx} GY:{gy} GZ:{gz}d/s]  ← si FLAG_MPU9250
    [LAT:{lat} LON:{lon} ALT:{alt}m SATS:{sats}]      ← si FLAG_GPS
    [GPS:NO_FIX]                                        ← si no FLAG_GPS
    SD:{OK|FAIL}
    RSSI:{r}dBm SNR:{snr}
"""

import re
import math
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


# ─────────────────────────────────────────────
# DATACLASS — Paquete de telemetría
# ─────────────────────────────────────────────
@dataclass
class TelemetryPacket:
    """Un paquete parseado de telemetría."""
    pkt: int                                # Contador de paquetes
    uptime: int                             # Segundos desde boot del STM32
    flags: int                              # Bitfield de sensores activos

    # BME280 (opcionales si sensor inactivo)
    temp: Optional[float] = None            # °C
    pres: Optional[float] = None            # hPa

    # MPU9250
    ax: float = 0.0                         # g
    ay: float = 0.0                         # g
    az: float = 0.0                         # g
    gx: float = 0.0                         # °/s
    gy: float = 0.0                         # °/s
    gz: float = 0.0                         # °/s

    # GPS
    lat: Optional[float] = None             # grados
    lon: Optional[float] = None             # grados
    alt_gps: Optional[int] = None           # metros
    gps_sats: Optional[int] = None          # nº satélites

    # SD Card
    sd_ok: bool = False                     # True si SD operativa

    # RF
    rssi: int = 0                           # dBm
    snr: float = 0.0                        # dB

    # Metadatos
    timestamp: datetime = field(default_factory=datetime.now)
    raw_line: str = ""

    # Campos calculados
    alt_rel: Optional[float] = None         # metros (relativa al ground, barométrica)
    accel_total: Optional[float] = None     # g (magnitud total)

    def __post_init__(self):
        self.accel_total = math.sqrt(self.ax**2 + self.ay**2 + self.az**2)

    # ── Flags de sensores ──

    @property
    def bme280_active(self) -> bool:
        return bool(self.flags & 0x1)

    @property
    def mpu9250_active(self) -> bool:
        return bool(self.flags & 0x2)

    @property
    def gps_active(self) -> bool:
        return bool(self.flags & 0x4)

    @property
    def sd_active(self) -> bool:
        return bool(self.flags & 0x8)

    @property
    def all_sensors_ok(self) -> bool:
        """BME280 + MPU9250 operativos (mínimo para telemetría básica)."""
        return (self.flags & 0x3) == 0x3

    @property
    def rssi_weak(self) -> bool:
        return self.rssi < -120

    @property
    def signal_quality(self) -> str:
        if self.rssi >= -100:
            return "EXCELENTE"
        elif self.rssi >= -110:
            return "BUENA"
        elif self.rssi >= -116:
            return "ACEPTABLE"
        elif self.rssi >= -120:
            return "DÉBIL"
        else:
            return "MUY DÉBIL"

    @property
    def has_gps_fix(self) -> bool:
        """True si hay fix GPS con coordenadas válidas."""
        return self.gps_active and self.lat is not None and self.lon is not None


# ─────────────────────────────────────────────
# PARSER — Basado en tokens individuales
# ─────────────────────────────────────────────

# Patrones compilados para cada campo
_RE_PKT   = re.compile(r'PKT:(\d+)')
_RE_UP    = re.compile(r'UP:(\d+)s')
_RE_FLAGS = re.compile(r'FLAGS:0x([0-9a-fA-F]+)')
_RE_TEMP  = re.compile(r'TEMP:([-\d.]+)')
_RE_PRES  = re.compile(r'PRES:([-\d.]+)')
_RE_AX    = re.compile(r'AX:([-\d.]+)')
_RE_AY    = re.compile(r'AY:([-\d.]+)')
_RE_AZ    = re.compile(r'AZ:([-\d.]+)')
_RE_GX    = re.compile(r'GX:([-\d.]+)')
_RE_GY    = re.compile(r'GY:([-\d.]+)')
_RE_GZ    = re.compile(r'GZ:([-\d.]+)')
_RE_LAT   = re.compile(r'LAT:([-\d.]+)')
_RE_LON   = re.compile(r'LON:([-\d.]+)')
_RE_ALT   = re.compile(r'ALT:([-\d]+)m')
_RE_SATS  = re.compile(r'SATS:(\d+)')
_RE_RSSI  = re.compile(r'RSSI:([-\d]+)')
_RE_SNR   = re.compile(r'SNR:([-\d.]+)')


def _match_int(pattern: re.Pattern, line: str) -> Optional[int]:
    m = pattern.search(line)
    return int(m.group(1)) if m else None


def _match_float(pattern: re.Pattern, line: str) -> Optional[float]:
    m = pattern.search(line)
    return float(m.group(1)) if m else None


def _match_hex(pattern: re.Pattern, line: str) -> Optional[int]:
    m = pattern.search(line)
    return int(m.group(1), 16) if m else None


def parse_line(line: str) -> Optional[TelemetryPacket]:
    """
    Parsea una línea de telemetría del ESP32.
    Retorna TelemetryPacket si es válida, None si no.
    Usa tokens individuales — robusto ante campos opcionales.
    """
    line = line.strip()
    if not line.startswith("PKT:"):
        return None

    # Campos obligatorios
    pkt   = _match_int(_RE_PKT, line)
    up    = _match_int(_RE_UP, line)
    flags = _match_hex(_RE_FLAGS, line)

    if pkt is None or up is None or flags is None:
        return None

    try:
        return TelemetryPacket(
            pkt=pkt,
            uptime=up,
            flags=flags,
            # BME280 (opcionales)
            temp=_match_float(_RE_TEMP, line),
            pres=_match_float(_RE_PRES, line),
            # MPU9250 (default 0.0 si ausente)
            ax=_match_float(_RE_AX, line) or 0.0,
            ay=_match_float(_RE_AY, line) or 0.0,
            az=_match_float(_RE_AZ, line) or 0.0,
            gx=_match_float(_RE_GX, line) or 0.0,
            gy=_match_float(_RE_GY, line) or 0.0,
            gz=_match_float(_RE_GZ, line) or 0.0,
            # GPS (opcionales)
            lat=_match_float(_RE_LAT, line),
            lon=_match_float(_RE_LON, line),
            alt_gps=_match_int(_RE_ALT, line),
            gps_sats=_match_int(_RE_SATS, line),
            # SD
            sd_ok='SD:OK' in line,
            # RF
            rssi=_match_int(_RE_RSSI, line) or 0,
            snr=_match_float(_RE_SNR, line) or 0.0,
            raw_line=line,
        )
    except (ValueError, IndexError):
        return None


# ─────────────────────────────────────────────
# ALTITUD RELATIVA
# ─────────────────────────────────────────────
def compute_relative_altitude(p_actual: float, p_base: float) -> float:
    """
    Calcula altitud relativa en metros usando la fórmula barométrica.
    p_actual: presión actual en hPa
    p_base: presión base (ground level) en hPa
    """
    if p_base <= 0 or p_actual <= 0:
        return 0.0
    return 44330.0 * (1.0 - (p_actual / p_base) ** (1.0 / 5.255))


# ─────────────────────────────────────────────
# ALERTAS Y VALIDACIÓN
# ─────────────────────────────────────────────
@dataclass
class PacketAlert:
    """Alerta asociada a un paquete."""
    level: str       # "WARNING", "ERROR", "INFO"
    message: str
    pkt_num: int


def _check_single_packet(pkt: TelemetryPacket) -> List[PacketAlert]:
    """Genera alertas para un solo paquete."""
    alerts: List[PacketAlert] = []

    # FLAGS — sensores básicos inactivos
    if not pkt.all_sensors_ok:
        missing = []
        if not pkt.bme280_active:
            missing.append("BME280")
        if not pkt.mpu9250_active:
            missing.append("MPU9250")
        if missing:
            alerts.append(PacketAlert(
                level="WARNING",
                message=f"Sensor(es) inactivo(s): {', '.join(missing)} (FLAGS=0x{pkt.flags:X})",
                pkt_num=pkt.pkt,
            ))

    # SD — tarjeta con fallo
    if not pkt.sd_ok:
        alerts.append(PacketAlert(
            level="WARNING",
            message="SD card no operativa (SD:FAIL)",
            pkt_num=pkt.pkt,
        ))

    # RSSI muy débil
    if pkt.rssi_weak:
        alerts.append(PacketAlert(
            level="ERROR",
            message=f"Señal MUY DÉBIL: RSSI={pkt.rssi} dBm",
            pkt_num=pkt.pkt,
        ))

    return alerts


def validate_packet_sequence(
    packets: List[TelemetryPacket],
) -> List[PacketAlert]:
    """
    Valida la secuencia de paquetes y genera alertas.
    """
    alerts: List[PacketAlert] = []

    if not packets:
        return alerts

    # Validar primer paquete
    alerts.extend(_check_single_packet(packets[0]))

    for i in range(1, len(packets)):
        prev = packets[i - 1]
        curr = packets[i]

        # Pérdida de paquetes
        expected_pkt = prev.pkt + 1
        if curr.pkt != expected_pkt and curr.pkt > prev.pkt:
            lost = curr.pkt - prev.pkt - 1
            alerts.append(PacketAlert(
                level="WARNING",
                message=f"Pérdida de {lost} paquete(s): PKT:{prev.pkt} → PKT:{curr.pkt}",
                pkt_num=curr.pkt,
            ))

        # Alertas del paquete individual
        alerts.extend(_check_single_packet(curr))

        # SD perdida entre paquetes consecutivos
        if prev.sd_ok and not curr.sd_ok:
            alerts.append(PacketAlert(
                level="ERROR",
                message="SD card perdida (estaba OK → ahora FAIL)",
                pkt_num=curr.pkt,
            ))

        # GPS perdido entre paquetes consecutivos
        if prev.gps_active and not curr.gps_active:
            alerts.append(PacketAlert(
                level="WARNING",
                message="GPS fix perdido",
                pkt_num=curr.pkt,
            ))

    return alerts
