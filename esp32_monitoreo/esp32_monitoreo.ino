#include <SPI.h>
#include <LoRa.h>

// Pines ESP32
#define LORA_SCK   18
#define LORA_MISO  19
#define LORA_MOSI  23
#define LORA_CS     5
#define LORA_RST   14
#define LORA_DIO0  26

// Flags
#define FLAG_BME280  (1 << 0)
#define FLAG_MPU9250 (1 << 1)
#define FLAG_GPS     (1 << 2)
#define FLAG_SD_OK   (1 << 3)
#define FRAME_SYNC   0xAD57

// Frame — coincide con frame.h del STM32 (40 bytes)
struct __attribute__((packed)) Frame_t {
    uint16_t sync;           // 2
    uint32_t pkt_id;         // 4
    uint32_t uptime_s;       // 4
    uint8_t  flags;          // 1
    int16_t  temp_cdeg;      // 2
    uint16_t press_hpax10;   // 2
    int16_t  accel_x;        // 2
    int16_t  accel_y;        // 2
    int16_t  accel_z;        // 2
    int16_t  gyro_x;         // 2
    int16_t  gyro_y;         // 2
    int16_t  gyro_z;         // 2
    int32_t  lat_1e5;        // 4
    int32_t  lon_1e5;        // 4
    int16_t  alt_m;          // 2
    uint8_t  gps_fix;        // 1
    uint16_t crc16;          // 2
};                           // = 40 bytes

uint16_t crc16_compute(const uint8_t *data, uint16_t len) {
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 1) crc = (crc >> 1) ^ 0xA001;
            else         crc >>= 1;
        }
    }
    return crc;
}

void setup() {
    Serial.begin(115200);
    while (!Serial);
    

    SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS);
    LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);

    if (!LoRa.begin(433E6)) {
        Serial.println("LoRa init failed!");
        while (true);
    }

    LoRa.setSpreadingFactor(9);
    LoRa.setSignalBandwidth(125E3);
    LoRa.setCodingRate4(5);
    LoRa.enableCrc();

    Serial.print("Frame size: ");
    Serial.print(sizeof(Frame_t));
    Serial.println(" bytes");
    Serial.println("RX listo, esperando tramas...");
    Serial.println("─────────────────────────────────────────────");
}

void loop() {
    int packetSize = LoRa.parsePacket();

    if (packetSize == sizeof(Frame_t)) {

        Frame_t f;
        uint8_t *buf = (uint8_t *)&f;
        for (int i = 0; i < (int)sizeof(Frame_t); i++) {
            buf[i] = LoRa.read();
        }

        // Validar SYNC
        if (f.sync != FRAME_SYNC) {
            Serial.println("[DESCARTADO] SYNC inválido");
            return;
        }

        // Validar CRC
        uint16_t crc_calc = crc16_compute(buf, sizeof(Frame_t) - 2);
        if (crc_calc != f.crc16) {
            Serial.println("[DESCARTADO] CRC inválido");
            return;
        }

        // Decodificar sensores
        float temp_c    = f.temp_cdeg    / 100.0f;
        float press_hpa = f.press_hpax10 / 10.0f;
        float ax = f.accel_x / 4096.0f;
        float ay = f.accel_y / 4096.0f;
        float az = f.accel_z / 4096.0f;
        float gx = f.gyro_x  / 65.5f;
        float gy = f.gyro_y  / 65.5f;
        float gz = f.gyro_z  / 65.5f;

        // Decodificar GPS
        float lat = f.lat_1e5 / 1e5f;
        float lon = f.lon_1e5 / 1e5f;

        // Imprimir
        Serial.print("PKT:");      Serial.print(f.pkt_id);
        Serial.print(" UP:");      Serial.print(f.uptime_s); Serial.print("s");
        Serial.print(" FLAGS:0x"); Serial.print(f.flags, HEX);

        if (f.flags & FLAG_BME280) {
            Serial.print(" TEMP:");  Serial.print(temp_c, 2);    Serial.print("C");
            Serial.print(" PRES:");  Serial.print(press_hpa, 1); Serial.print("hPa");
        }

        if (f.flags & FLAG_MPU9250) {
            Serial.print(" AX:"); Serial.print(ax, 3);
            Serial.print(" AY:"); Serial.print(ay, 3);
            Serial.print(" AZ:"); Serial.print(az, 3); Serial.print("g");
            Serial.print(" GX:"); Serial.print(gx, 1);
            Serial.print(" GY:"); Serial.print(gy, 1);
            Serial.print(" GZ:"); Serial.print(gz, 1); Serial.print("d/s");
        }

        if (f.flags & FLAG_GPS) {
            Serial.print(" LAT:"); Serial.print(lat, 5);
            Serial.print(" LON:"); Serial.print(lon, 5);
            Serial.print(" ALT:"); Serial.print(f.alt_m);  Serial.print("m");
            Serial.print(" SATS:"); Serial.print(f.gps_fix);
        } else {
            Serial.print(" GPS:NO_FIX");
        }

        Serial.print(" SD:"); Serial.print((f.flags & FLAG_SD_OK) ? "OK" : "FAIL");

        Serial.print(" RSSI:"); Serial.print(LoRa.packetRssi()); Serial.print("dBm");
        Serial.print(" SNR:");  Serial.println(LoRa.packetSnr());

    } else if (packetSize > 0) {
        Serial.print("[DESCARTADO] Tamanio inesperado: ");
        Serial.print(packetSize);
        Serial.print(" (esperado: ");
        Serial.print(sizeof(Frame_t));
        Serial.println(")");
        while (LoRa.available()) LoRa.read();
    }
}
