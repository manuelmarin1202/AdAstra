"""
AdAstra — Serial Reader
Hilo de lectura serial con auto-detección de puertos COM.
Conecta al ESP32 a 115200 baud y pushea datos a un buffer thread-safe.
"""

import threading
import time
from collections import deque
from typing import Optional, List, Tuple
from datetime import datetime

import serial
import serial.tools.list_ports

from telemetry_parser import parse_line, TelemetryPacket, compute_relative_altitude


# ─────────────────────────────────────────────
# AUTO-DETECCIÓN DE PUERTOS COM
# ─────────────────────────────────────────────
def list_available_ports() -> List[Tuple[str, str]]:
    """
    Lista todos los puertos COM disponibles.
    Retorna lista de (puerto, descripción).
    """
    ports = serial.tools.list_ports.comports()
    return [(p.device, p.description) for p in sorted(ports, key=lambda x: x.device)]


def detect_esp32_port() -> Optional[str]:
    """
    Intenta detectar automáticamente el puerto del ESP32.
    Busca por descripción típica (CP210x, CH340, FTDI, Silicon Labs).
    """
    keywords = ["CP210", "CH340", "FTDI", "Silicon Labs", "USB Serial", "ESP32", "USB-SERIAL"]
    ports = serial.tools.list_ports.comports()
    for port in ports:
        desc_upper = port.description.upper()
        for kw in keywords:
            if kw.upper() in desc_upper:
                return port.device
    # Si no detecta por descripción, retorna el primer puerto disponible
    if ports:
        return ports[0].device
    return None


# ─────────────────────────────────────────────
# ESTADO DE CONEXIÓN
# ─────────────────────────────────────────────
class ConnectionState:
    DISCONNECTED = "DESCONECTADO"
    CONNECTING = "CONECTANDO"
    CONNECTED = "CONECTADO"
    ERROR = "ERROR"


# ─────────────────────────────────────────────
# SERIAL READER — Hilo de lectura
# ─────────────────────────────────────────────
class SerialReader:
    """
    Lee datos del puerto serial en un hilo separado.
    Parsea las tramas y las almacena en buffers thread-safe.
    """

    BAUD_RATE = 115200
    MAX_PACKETS = 512       # Buffer máximo de paquetes parseados
    MAX_RAW_LINES = 200     # Buffer máximo de líneas raw

    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Buffers thread-safe
        self.packets: deque[TelemetryPacket] = deque(maxlen=self.MAX_PACKETS)
        self.raw_lines: deque[Tuple[datetime, str]] = deque(maxlen=self.MAX_RAW_LINES)

        # Estado
        self.state = ConnectionState.DISCONNECTED
        self.port_name: Optional[str] = None
        self.error_message: Optional[str] = None
        self.total_received = 0
        self.total_errors = 0
        self.packets_lost = 0
        self._last_pkt_num: Optional[int] = None
        self._p_base: Optional[float] = None  # Presión de referencia (ground level)
        self._connect_time: Optional[float] = None  # time.time() al conectar

    @property
    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED

    @property
    def packets_per_second(self) -> float:
        """Calcula la tasa de recepción de paquetes (pkt/s)."""
        if self._connect_time is None or self.total_received == 0:
            return 0.0
        elapsed = time.time() - self._connect_time
        if elapsed <= 0:
            return 0.0
        return self.total_received / elapsed

    @property
    def loss_percentage(self) -> float:
        """Calcula el porcentaje de paquetes perdidos."""
        total = self.total_received + self.packets_lost
        if total == 0:
            return 0.0
        return (self.packets_lost / total) * 100.0

    @property
    def session_duration_s(self) -> float:
        """Segundos desde que se conectó."""
        if self._connect_time is None:
            return 0.0
        return time.time() - self._connect_time

    def connect(self, port: str) -> bool:
        """
        Conecta al puerto serial especificado.
        """
        if self.is_connected:
            self.disconnect()

        self.state = ConnectionState.CONNECTING
        self.error_message = None

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=self.BAUD_RATE,
                timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            self.port_name = port
            self.state = ConnectionState.CONNECTED

            # Reset contadores
            self.total_received = 0
            self.total_errors = 0
            self.packets_lost = 0
            self._last_pkt_num = None
            self._p_base = None
            self._connect_time = time.time()
            self.packets.clear()
            self.raw_lines.clear()

            # Iniciar hilo de lectura
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()

            return True

        except serial.SerialException as e:
            self.state = ConnectionState.ERROR
            self.error_message = str(e)
            self._serial = None
            return False

    def disconnect(self):
        """
        Desconecta del puerto serial.
        """
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None

        self.state = ConnectionState.DISCONNECTED
        self.port_name = None

    def _read_loop(self):
        """
        Loop de lectura serial que corre en hilo separado.
        """
        while self._running and self._serial and self._serial.is_open:
            try:
                raw = self._serial.readline()
                if not raw:
                    continue

                try:
                    line = raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    continue

                if not line:
                    continue

                now = datetime.now()

                with self._lock:
                    self.raw_lines.append((now, line))

                # Intentar parsear
                packet = parse_line(line)
                if packet is None:
                    # Línea no reconocida, pero la guardamos en raw
                    continue

                # Calcular altitud relativa
                if self._p_base is None:
                    self._p_base = packet.pres  # Primera presión = ground level
                packet.alt_rel = compute_relative_altitude(packet.pres, self._p_base)

                # Detectar pérdida de paquetes
                if self._last_pkt_num is not None:
                    expected = self._last_pkt_num + 1
                    if packet.pkt != expected and packet.pkt > self._last_pkt_num:
                        lost = packet.pkt - self._last_pkt_num - 1
                        self.packets_lost += lost
                self._last_pkt_num = packet.pkt

                with self._lock:
                    self.packets.append(packet)
                    self.total_received += 1

            except serial.SerialException:
                self.state = ConnectionState.ERROR
                self.error_message = "Puerto serial desconectado"
                self._running = False
                break
            except Exception as e:
                self.total_errors += 1
                continue

    def get_packets_snapshot(self) -> List[TelemetryPacket]:
        """Retorna una copia del buffer de paquetes."""
        with self._lock:
            return list(self.packets)

    def get_raw_lines_snapshot(self) -> List[Tuple[datetime, str]]:
        """Retorna una copia del buffer de líneas raw."""
        with self._lock:
            return list(self.raw_lines)

    def get_latest_packet(self) -> Optional[TelemetryPacket]:
        """Retorna el último paquete recibido."""
        with self._lock:
            return self.packets[-1] if self.packets else None

    def get_previous_packet(self) -> Optional[TelemetryPacket]:
        """Retorna el penúltimo paquete (para calcular deltas)."""
        with self._lock:
            return self.packets[-2] if len(self.packets) >= 2 else None

    def reset_baseline_pressure(self):
        """Resetea la presión base al último valor recibido."""
        latest = self.get_latest_packet()
        if latest:
            self._p_base = latest.pres
