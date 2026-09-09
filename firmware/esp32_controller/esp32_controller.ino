#include <Arduino.h>
#include "../shared/LedController.h"

LedController ledController;

#define ONBOARD_LED 2

void setup() {
  Serial.begin(115200);
  delay(1000); // Power-up safety delay
  
  pinMode(ONBOARD_LED, OUTPUT);
  digitalWrite(ONBOARD_LED, HIGH); // Turn on blue LED to indicate power/status
  
  Serial.println("\nDEVLIGHTS ESP32");
  Serial.println("----------------");
  Serial.println("Firmware: esp32_controller");
  Serial.println("Serial: OK");
  
  ledController.begin();
  
  Serial.println("LED controller: OK");
  Serial.println("Waiting for commands...");
}

#define DEV_DEBUG 1

void loop() {
  if (Serial.available() >= 5) {
    uint8_t buffer[5];
    // Peek at first byte to see if it's the magic byte
    if (Serial.peek() == 0x55) {
      Serial.readBytes(buffer, 5);
      if (ledController.parseBinaryPayload(buffer, 5)) {
#if DEV_DEBUG
        Serial.println("PACKET OK");
        Serial.print("R="); Serial.print(buffer[1]);
        Serial.print(" G="); Serial.print(buffer[2]);
        Serial.print(" B="); Serial.print(buffer[3]);
        Serial.print(" BRIGHTNESS="); Serial.println(buffer[4]);
#endif
      }
    } else {
      // Discard invalid bytes
      Serial.read();
    }
  }
}
