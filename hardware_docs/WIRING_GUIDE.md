# Hardware Wiring Guide (Phase 0)

## Components
- ESP32 Development Board
- WS2812B Addressable RGB LED Strip
- 5V Power Supply
- Connecting Wires

## Wiring Diagram

**WARNING**: Do NOT power a long LED strip directly from the ESP32's 5V pin. The ESP32 cannot handle the high current drawn by many LEDs and will be damaged. Always use an external 5V power supply for the LEDs.

```text
External 5V Power Supply
   │
   ├──────────► WS2812B +5V (VCC)
   │
   └──────────► WS2812B GND
                     │
ESP32 GND ───────────┘  <-- IMPORTANT: Common Ground

ESP32 GPIO 2 (or any data pin) ────────► WS2812B DIN (Data In)
```

## Checklist before powering on:
1. [ ] ESP32 is connected to the computer via USB for programming.
2. [ ] External 5V supply is connected to the LED strip's 5V and GND.
3. [ ] ESP32 GND is connected to the LED strip GND (Common Ground).
4. [ ] ESP32 Data pin (e.g., GPIO 2) is connected to the LED strip's DIN (Data In) pin. (A 330-470 ohm resistor on the data line is recommended for protection).
5. [ ] Ensure voltage is exactly 5V. Do not use a 12V supply for WS2812B.
