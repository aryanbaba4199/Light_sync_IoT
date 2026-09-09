# DevLights IoT

DevLights is a high-performance, real-time ambient lighting system that synchronizes your physical environment with your digital experiences. 

Built with a headless Python engine for ultra-low latency screen/audio analysis, a sleek React/Electron Desktop UI for control, and high-speed serial communication to an ESP32 controlling WS2812B LEDs.

## Architecture
- **Desktop UI**: Built with React, Vite, Tailwind v4, and Zustand. Uses Electron to spawn the Python engine seamlessly.
- **Python Engine**: A headless high-speed engine running at 60Hz. It processes screen colors (via `mss`), captures audio, manages lighting priorities, and streams data.
- **ESP32 Firmware**: Written in C++ using `FastLED`. It receives highly optimized binary payloads via USB Serial or Wi-Fi (UDP) to drive the LED strip.

---

## ESP32 Hardware & Pinout Guide

If you are using a standard **38-pin ESP32 Development Board** (ESP32-WROOM-32 DevKitC V4), here is a complete cheat sheet for what the pins do and which ones are safe to use for LEDs.

### 🟢 1. The Power Pins (Crucial)
These pins handle electricity. You will use these constantly.
*   **VIN (or 5V):** Outputs the 5 Volts coming directly from your USB cable. You can use this to power very small 5V things, but **DO NOT** use this to power a long LED strip (the strip will pull too much power and fry the board). 
*   **3V3:** Outputs exactly 3.3 Volts. Used for powering small sensors.
*   **GND (Ground):** The negative side of the circuit. There are usually 3 or 4 GND pins on the board. **Important:** Your LED Strip's Ground wire MUST connect to one of these GND pins!

### 🟢 2. The "Safe" Data Pins (The Best Ones)
These pins (often labeled with a **`D`** for Digital or **`G`** for GPIO) are 100% safe to use for anything: LED strips, buttons, motors, or sensors.
*   **D4, D13, D14, D16 (RX2), D17 (TX2), D18, D19, D21, D22, D23, D25, D26, D27, D32, D33**
*   *Note:* In this project, we recommend using **D5** for the LED Strip data line.

### 🟡 3. The "Input Only" Pins (Read Only)
These pins are physically missing the internal hardware required to push electricity *out*. They can only *listen* (e.g., read a button or a temperature sensor). 
*   **D34, D35, VP (D36), VN (D39)**
*   *Never try to connect your LED strip to these! They cannot send the data signal out.*

### 🔴 4. The "Strapping" Pins (DANGER ZONES)
When you plug the ESP32 into USB, it spends the first millisecond checking the voltage on these specific pins to decide how to boot up. If you have something wired to these pins that accidentally feeds electricity into them during boot-up, **the ESP32 will crash and refuse to turn on.**
*   **D0, D2, D5, D12, D15**
*   *Why do we use D5 for LEDs?* An LED strip data wire is passive, meaning it doesn't feed electricity backward into the pin, so D5 is perfectly safe for LEDs. But never wire a *button* to D5.
*   *What about D2?* **D2** is hardwired to the small blue LED on the physical board itself.

### 🔴 5. The USB Serial Pins (DO NOT TOUCH)
These pins are physically wired to the USB port on the board. They are currently talking to your computer (receiving the Python commands 60 times a second).
*   **TX (D1) and RX (D3)**
*   *If you wire anything to these, you will block the communication between your computer and the ESP32!*

### 🔴 6. The Internal Flash Pins (DO NOT TOUCH)
These 6 pins are secretly wired to the memory chip hiding under the metal shield on the board. 
*   **CMD, CLK, SD0, SD1, SD2, SD3** (Usually GPIOs 6 through 11)
*   *If you use these, the ESP32 will instantly crash because you are interrupting its brain from reading its own code.*

---

## Getting Started

### 1. Flash the ESP32
1. Install the **PlatformIO** extension in VS Code.
2. Open `firmware/esp32_controller` as a root folder in VS Code.
3. Plug in your ESP32 and click the PlatformIO **Upload (→)** button.
4. The onboard blue LED (GPIO 2) will turn on, indicating the firmware is successfully running.

### 2. Wiring the LEDs
1. Connect **GND** of the LED strip to a **GND** pin on the ESP32.
2. Connect **Data (DIN)** of the LED strip to **D5** on the ESP32.
3. Power the LED strip directly with a high-amperage 5V power supply.

### 3. Run the Desktop App
```bash
cd desktop_app
npm install
npm run dev
```
The desktop app will automatically launch the Python engine, auto-discover your ESP32 on the USB port, and immediately start syncing your screen/audio to the physical lights.
