"""
AdAstra — Telemetry Parser
Parsea tramas del ESP32 con formato:
  PKT:{n} UP:{s}s FLAGS:0x{f} TEMP:{t}°C PRES:{p}hPa AX:{ax} AY:{ay} AZ:{az}g GX:{gx} GY:{gy} GZ:{gz}°/s RSSI:{r}dBm SNR:{snr}
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
    pkt: int            # Contador de paquetes
    uptime: int         # Segundos desde boot del STM32
    flags: int          # 0x1=BME280, 0x3=BME280+MPU9250
    temp: float         # °C
    pres: float         # hPa
    ax: float           # g
    ay: float           # g
    az: float           # g
    gx: float           # °/s
    gy: float           # °/s
    gz: float           # °/s
    rssi: int           # dBm
    snr: float          # dB
    timestamp: datetime = field(default_factory=datetime.now)
    raw_line: str = ""

    # Campos calculados
    alt_rel: Optional[float] = None       # metros (relativa al ground)
    accel_total: Optional[float] = None   # g (magnitud total)

    def __post_init__(self):
        self.accel_total = math.sqrt(self.ax**2 + self.ay**2 + self.az**2)

    @property
    def bme280_active(self) -> bool:
        return bool(self.flags & 0x1)

    @property
    def mpu9250_active(self) -> bool:
        return bool(self.flags & 0x2)

    @property
    def all_sensors_ok(self) -> bool:
        return self.flags == 0x3

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


# ─────────────────────────────────────────────
# REGEX — Patrón de la trama
# ─────────────────────────────────────────────
_PACKET_PATTERN = re.compile(
    r"PKT:(\d+)\s+"
    r"UP:(\d+)s\s+"
    r"FLAGS:0x([0-9a-fA-F]+)\s+"
    r"TEMP:([-\d.]+)°?C?\s+"
    r"PRES:([-\d.]+)hPa\s+"
    r"AX:([-\d.]+)\s+"
    r"AY:([-\d.]+)\s+"
    r"AZ:([-\d.]+)g?\s+"
    r"GX:([-\d.]+)\s+"
    r"GY:([-\d.]+)\s+"
    r"GZ:([-\d.]+)°?/?s?\s+"
    r"RSSI:([-\d]+)dBm\s+"
    r"SNR:([-\d.]+)"
)


# ─────────────────────────────────────────────
# PARSER
# ─────────────────────────────────────────────
def parse_line(line: str) -> Optional[TelemetryPacket]:
    """
    Parsea una línea de telemetría del ESP32.
    Retorna TelemetryPacket si es válida, None si no.
    """
    line = line.strip()
    if not line.startswith("PKT:"):
        return None

    match = _PACKET_PATTERN.search(line)
    if not match:
        return None

    try:
        return TelemetryPacket(
            pkt=int(match.group(1)),
            uptime=int(match.group(2)),
            flags=int(match.group(3), 16),
            temp=float(match.group(4)),
            pres=float(match.group(5)),
            ax=float(match.group(6)),
            ay=float(match.group(7)),
            az=float(match.group(8)),
            gx=float(match.group(9)),
            gy=float(match.group(10)),
            gz=float(match.group(11)),
            rssi=int(match.group(12)),
            snr=float(match.group(13)),
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


def validate_packet_sequence(
    packets: List[TelemetryPacket],
) -> List[PacketAlert]:
    """
    Valida la secuencia de paquetes y genera alertas.
    """
    alerts: List[PacketAlert] = []

    for i in range(1, len(packets)):
        prev = packets[i - 1]
        curr = packets[i]

        # Pérdida de paquetes
        expected_pkt = prev.pkt + 1
        if curr.pkt != expected_pkt:
            lost = curr.pkt - prev.pkt - 1
            alerts.append(PacketAlert(
                level="WARNING",
                message=f"Pérdida de {lost} paquete(s): PKT:{prev.pkt} → PKT:{curr.pkt}",
                pkt_num=curr.pkt,
            ))

        # FLAGS incompletos
        if not curr.all_sensors_ok:
            missing = []
            if not curr.bme280_active:
                missing.append("BME280")
            if not curr.mpu9250_active:
                missing.append("MPU9250")
            alerts.append(PacketAlert(
                level="WARNING",
                message=f"Sensor(es) inactivo(s): {', '.join(missing)} (FLAGS=0x{curr.flags:X})",
                pkt_num=curr.pkt,
            ))

        # RSSI muy débil
        if curr.rssi_weak:
            alerts.append(PacketAlert(
                level="ERROR",
                message=f"Señal MUY DÉBIL: RSSI={curr.rssi} dBm",
                pkt_num=curr.pkt,
            ))

    # Validar el primer paquete también
    if packets:
        first = packets[0]
        if not first.all_sensors_ok:
            missing = []
            if not first.bme280_active:
                missing.append("BME280")
            if not first.mpu9250_active:
                missing.append("MPU9250")
            alerts.append(PacketAlert(
                level="WARNING",
                message=f"Sensor(es) inactivo(s): {', '.join(missing)} (FLAGS=0x{first.flags:X})",
                pkt_num=first.pkt,
            ))
        if first.rssi_weak:
            alerts.append(PacketAlert(
                level="ERROR",
                message=f"Señal MUY DÉBIL: RSSI={first.rssi} dBm",
                pkt_num=first.pkt,
            ))

    return alerts
