import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/firmware/esp32_controller/esp32_controller.ino', 'r') as f:
    content = f.read()

content = content.replace("LedController ledController;", "LedController ledController;\nunsigned long lastPacketTime = 0;")
content = content.replace("updated = true;", "updated = true;\n           lastPacketTime = millis();")

timeout_logic = """  if (updated) {
    FastLED.show();
    // HARDWARE FIX: Force a 15ms delay after every frame to allow the 3.3V 
    // electrical data line to completely discharge and latch. This prevents 
    // high-frequency static/color corruption down long LED strips!
    delay(15);
  }
  
  // SLEEP DETECTION:
  // If the PC goes to sleep, it stops sending USB serial packets.
  // If we haven't received a packet in 2.5 seconds, automatically turn the LEDs off!
  if (lastPacketTime > 0 && millis() - lastPacketTime > 2500) {
      ledController.applyState(0, 0, 0, 0, false);
      FastLED.show();
      lastPacketTime = 0; // Prevent constant clearing
  }"""

content = content.replace("""  if (updated) {
    FastLED.show();
    // HARDWARE FIX: Force a 15ms delay after every frame to allow the 3.3V 
    // electrical data line to completely discharge and latch. This prevents 
    // high-frequency static/color corruption down long LED strips!
    delay(15);
  }""", timeout_logic)

with open('/Users/aryandubey/project/personal/Automation/light_sync/firmware/esp32_controller/esp32_controller.ino', 'w') as f:
    f.write(content)
