#include <Arduino.h>
#include <esp_task_wdt.h>
#include "../shared/LedController.h"

LedController ledController;
unsigned long lastPacketTime = 0;
unsigned long lastByteTime = 0;
unsigned long lastShowTime = 0;

#define ONBOARD_LED 2

// Robust State Machine States
enum RxState {
  STATE_WAIT_HEADER,
  STATE_V1_PAYLOAD,
  STATE_V2_ZONE_HEADER,
  STATE_V2_ZONE_PAYLOAD,
  STATE_V2_INDEXED_HEADER,
  STATE_V2_INDEXED_PAYLOAD,
  STATE_RESTART_PAYLOAD
};

RxState rxState = STATE_WAIT_HEADER;
uint8_t rxBuf[768];
size_t rxLen = 0;
size_t expectedLen = 0;

void setup() {
  // Allocate a 2048-byte hardware UART RX buffer so FastLED transmission never drops bytes
  Serial.setRxBufferSize(2048);
  Serial.begin(115200);
  delay(300); 
  
  pinMode(ONBOARD_LED, OUTPUT);
  digitalWrite(ONBOARD_LED, HIGH); 
  
  Serial.println("\nDEVLIGHTS ESP32 CONTROLLER V2.1");
  
  FastLED.setDither(0);
  ledController.begin();

  // Initialize hardware watchdog timer (5 second timeout)
  esp_task_wdt_init(5, true);
  esp_task_wdt_add(NULL);
}

void loop() {
  // Feed the hardware watchdog on every loop tick
  esp_task_wdt_reset();

  bool updated = false;
  unsigned long now = millis();

  // Packet inter-byte timeout:
  // If a packet was started but no new bytes arrive for > 50ms,
  // reset to STATE_WAIT_HEADER to re-sync immediately.
  if (rxState != STATE_WAIT_HEADER && (now - lastByteTime > 50)) {
    rxState = STATE_WAIT_HEADER;
    rxLen = 0;
  }

  while (Serial.available() > 0) {
    uint8_t b = Serial.read();
    lastByteTime = millis();

    switch (rxState) {
      case STATE_WAIT_HEADER:
        if (b == 0x55) {
          rxBuf[0] = 0x55;
          rxLen = 1;
          expectedLen = 5;
          rxState = STATE_V1_PAYLOAD;
        } else if (b == 0x56) {
          rxBuf[0] = 0x56;
          rxLen = 1;
          rxState = STATE_V2_ZONE_HEADER;
        } else if (b == 0x57) {
          rxBuf[0] = 0x57;
          rxLen = 1;
          rxState = STATE_V2_INDEXED_HEADER;
        } else if (b == 0x58) {
          // Hardware restart command [0x58, 0xA5, 0x5A, 0x58]
          rxBuf[0] = 0x58;
          rxLen = 1;
          expectedLen = 4;
          rxState = STATE_RESTART_PAYLOAD;
        }
        break;

      case STATE_V1_PAYLOAD:
        if (rxLen < sizeof(rxBuf)) rxBuf[rxLen++] = b;
        if (rxLen >= 5) {
          ledController.applyState(rxBuf[1], rxBuf[2], rxBuf[3], rxBuf[4], false);
          updated = true;
          lastPacketTime = millis();
          rxState = STATE_WAIT_HEADER;
          rxLen = 0;
        }
        break;

      case STATE_V2_ZONE_HEADER:
        if (rxLen < sizeof(rxBuf)) rxBuf[rxLen++] = b; // zoneCount
        if (b > 42) {
          rxState = STATE_WAIT_HEADER;
          rxLen = 0;
        } else if (b == 0) {
          expectedLen = 3;
          rxState = STATE_V2_ZONE_PAYLOAD;
        } else {
          expectedLen = 2 + ((size_t)b * 7) + 1;
          rxState = STATE_V2_ZONE_PAYLOAD;
        }
        break;

      case STATE_V2_ZONE_PAYLOAD:
        if (rxLen < sizeof(rxBuf)) {
          rxBuf[rxLen++] = b;
        } else {
          rxState = STATE_WAIT_HEADER;
          rxLen = 0;
          break;
        }
        if (rxLen >= expectedLen) {
          uint8_t calcChecksum = 0;
          for (size_t i = 0; i < expectedLen - 1; i++) {
            calcChecksum ^= rxBuf[i];
          }
          if (calcChecksum == rxBuf[expectedLen - 1]) {
            uint8_t zoneCount = rxBuf[1];
            ledController.setBrightness(255);
            ledController.clearAll();
            for (uint8_t z = 0; z < zoneCount; z++) {
              size_t offset = 2 + z * 7;
              uint16_t s = ((uint16_t)rxBuf[offset] << 8) | rxBuf[offset + 1];
              uint16_t e = ((uint16_t)rxBuf[offset + 2] << 8) | rxBuf[offset + 3];
              uint8_t r = rxBuf[offset + 4];
              uint8_t g = rxBuf[offset + 5];
              uint8_t b = rxBuf[offset + 6];
              ledController.applyZone(s, e, r, g, b);
            }
            updated = true;
            lastPacketTime = millis();
          }
          rxState = STATE_WAIT_HEADER;
          rxLen = 0;
        }
        break;

      case STATE_V2_INDEXED_HEADER:
        if (rxLen < sizeof(rxBuf)) rxBuf[rxLen++] = b;
        if (rxLen >= 6) {
          uint16_t count = ((uint16_t)rxBuf[4] << 8) | rxBuf[5];
          if (count > 300) {
            rxState = STATE_WAIT_HEADER;
            rxLen = 0;
          } else {
            expectedLen = 6 + ((size_t)count * 2) + 1;
            rxState = STATE_V2_INDEXED_PAYLOAD;
          }
        }
        break;

      case STATE_V2_INDEXED_PAYLOAD:
        if (rxLen < sizeof(rxBuf)) {
          rxBuf[rxLen++] = b;
        } else {
          rxState = STATE_WAIT_HEADER;
          rxLen = 0;
          break;
        }
        if (rxLen >= expectedLen) {
          uint8_t calcChecksum = 0;
          for (size_t i = 0; i < expectedLen - 1; i++) {
            calcChecksum ^= rxBuf[i];
          }
          if (calcChecksum == rxBuf[expectedLen - 1]) {
            ledController.setBrightness(255);
            uint8_t r = rxBuf[1];
            uint8_t g = rxBuf[2];
            uint8_t b = rxBuf[3];
            uint16_t count = ((uint16_t)rxBuf[4] << 8) | rxBuf[5];
            for (uint16_t i = 0; i < count; i++) {
              size_t offset = 6 + i * 2;
              uint16_t ledIdx = ((uint16_t)rxBuf[offset] << 8) | rxBuf[offset + 1];
              ledController.applyIndexed(&ledIdx, 1, r, g, b);
            }
            updated = true;
            lastPacketTime = millis();
          }
          rxState = STATE_WAIT_HEADER;
          rxLen = 0;
        }
        break;

      case STATE_RESTART_PAYLOAD:
        if (rxLen < sizeof(rxBuf)) rxBuf[rxLen++] = b;
        if (rxLen >= 4) {
          if (rxBuf[1] == 0xA5 && rxBuf[2] == 0x5A && rxBuf[3] == 0x58) {
            Serial.println("RESTARTING_ESP32");
            ledController.clearAll();
            FastLED.show();
            delay(50);
            ESP.restart();
          }
          rxState = STATE_WAIT_HEADER;
          rxLen = 0;
        }
        break;
    }
  }

  // Non-blocking rate-limited show:
  // Shows whenever a valid packet updated the leds, but no faster than every 15ms (~66 FPS).
  // Crucially: NO blocking delay(), so Serial UART FIFO never overflows!
  if (updated && (millis() - lastShowTime >= 15)) {
    FastLED.show();
    lastShowTime = millis();
  }

  // SLEEP DETECTION & TIMEOUT:
  // If no serial packets arrive for > 5 seconds, shut off strip
  if (lastPacketTime > 0 && (millis() - lastPacketTime > 5000)) {
    ledController.clearAll();
    FastLED.show();
    lastPacketTime = 0;
  }
}
