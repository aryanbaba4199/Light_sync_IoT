#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include "../shared/LedController.h"

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const int udpPort = 4210;

LedController ledController;
WiFiUDP udp;
unsigned long lastWiFiCheck = 0;

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

#define ONBOARD_LED 2

void setup() {
  Serial.begin(115200);
  delay(1000); // Power-up safety delay
  
  pinMode(ONBOARD_LED, OUTPUT);
  digitalWrite(ONBOARD_LED, HIGH); // Turn on blue LED to indicate power/status
  
  ledController.begin();
  
  WiFi.mode(WIFI_STA);
  connectWiFi();
  udp.begin(udpPort);
}

void loop() {
  // Reconnect logic
  if (millis() - lastWiFiCheck >= 10000) {
    lastWiFiCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi disconnected, attempting to reconnect...");
      WiFi.disconnect();
      connectWiFi();
    }
  }

  int packetSize = udp.parsePacket();
  if (packetSize >= 5) {
    uint8_t packetBuffer[256];
    // Read up to buffer size to prevent overflow
    int len = udp.read(packetBuffer, sizeof(packetBuffer));
    
    // Process binary payload
    ledController.parseBinaryPayload(packetBuffer, len);
  } else if (packetSize > 0) {
    // Flush bad packets
    udp.flush();
  }
}
