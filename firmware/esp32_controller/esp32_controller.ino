#include <Arduino.h>
#include "../shared/LedController.h"

LedController ledController;

#define ONBOARD_LED 2

void setup() {
  Serial.begin(115200);
  delay(1000); 
  
  pinMode(ONBOARD_LED, OUTPUT);
  digitalWrite(ONBOARD_LED, HIGH); 
  
  Serial.println("\nDEVLIGHTS ESP32");
  
  FastLED.setDither(0);
  
  ledController.begin();
}

void loop() {
  bool updated = false;
  
  while (Serial.available() > 0) {
    if (Serial.peek() == 0x55) {
      if (Serial.available() >= 5) {
        uint8_t buffer[5];
        Serial.readBytes(buffer, 5);
        if (buffer[0] == 0x55) {
           ledController.applyState(buffer[1], buffer[2], buffer[3], buffer[4], false);
           updated = true;
        }
      } else {
        break; 
      }
    } else {
      Serial.read(); 
    }
  }
  
  if (updated) {
    FastLED.show();
    // HARDWARE FIX: Force a 15ms delay after every frame to allow the 3.3V 
    // electrical data line to completely discharge and latch. This prevents 
    // high-frequency static/color corruption down long LED strips!
    delay(15);
  }
}
