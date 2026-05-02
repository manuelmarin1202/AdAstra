# 🚀 AdAstra — Ground Station Dashboard

**Misión AdAstra CubeSat · PDR 2026 · Equipo AdAstra — PUCP**

Mockup estático del dashboard de la Estación Terrena para el satélite CubeSat AdAstra,
generado con Python + Streamlit para el Preliminary Design Review (PDR).

---

## 📁 Estructura del Proyecto

```
HUMOSAT/
├── adastra_dashboard.py   # Aplicación principal (Streamlit)
├── requirements.txt       # Dependencias Python
├── README.md              # Este archivo
└── assets/
    └── logo.png           # ← COLOCA AQUÍ el logo del Equipo AdAstra
                           #   (se mostrará automáticamente en el sidebar)
```

---

## 🔧 Instalación

```bash
pip install -r requirements.txt
```

---

## ▶️ Ejecución

```bash
python -m streamlit run adastra_dashboard.py
```

El dashboard estará disponible en: **http://localhost:8501**

---

## 🛰️ Logo del Equipo

Para mostrar el logo del Equipo AdAstra en el sidebar:

1. Crea la carpeta `assets/` (si no existe).
2. Copia el archivo de imagen del logo con el nombre exacto **`logo.png`**.
3. Reinicia el dashboard.

El logo se detecta y muestra automáticamente. Formatos soportados: PNG, JPG, SVG.

---

## 📡 Protocolo de Telemetría (§2.3.3)

Las tramas CSV que el satélite transmite siguen el formato:

```
<ID>,<COUNT>,<TIME>,<MODE>,<VBAT>,<ALT>,<TEMP>,<TILT_X>,<TILT_Y>,<LAT>,<LON>,<CHK>
```

| Campo    | Descripción                          | Unidad |
|----------|--------------------------------------|--------|
| ID       | Identificador de la misión (`ADA`)   | -      |
| COUNT    | Contador de tramas (0–65535)         | -      |
| TIME     | Tiempo de misión (ms desde boot)     | ms     |
| MODE     | Modo de operación (1=activo)         | -      |
| VBAT     | Voltaje de batería                   | V      |
| ALT      | Altitud                              | m      |
| TEMP     | Temperatura interna                  | °C     |
| TILT_X   | Inclinación eje X                    | °      |
| TILT_Y   | Inclinación eje Y                    | °      |
| LAT      | Latitud GPS                          | °      |
| LON      | Longitud GPS                         | °      |
| CHK      | Checksum (XOR hex, 2 dígitos)        | hex    |

---

*Equipo AdAstra — Pontificia Universidad Católica del Perú (PUCP) · 2026*
