# Developer Ambient Lighting System — Project Plan

## 1. Project Vision

Build a real-time ambient lighting system for **developers, gamers, and movie/music lovers**.

The system uses a computer/mobile device to analyze screen content and/or audio locally, then sends compact lighting commands to an **ESP32**, which controls an addressable **WS2812B LED strip**.

### Core principle

- **Movie Mode:** Video/screen determines color; audio intensity determines brightness.
- **Music Mode:** Frequency bands determine colors; audio intensity determines brightness.
- **Developer Mode:** Development events determine lighting states, with screen color as the fallback.
- **Game Mode:** Screen/video determines color; audio intensity determines brightness.
- **Custom Mode:** User controls color, brightness, effects, and behavior.

### Important architecture decision

The first version will have **no backend, database, cloud service, or AI dependency**.

All real-time analysis runs locally on the host device.

```text
Host Device
  ├── Screen Analyzer ──────┐
  ├── Audio Analyzer ───────┤
  ├── Developer Events ─────┤
  └── User Controls ────────┤
                            ▼
                     Lighting Engine
                            │
                    USB / Wi-Fi / BLE
                            │
                            ▼
                          ESP32
                            │
                            ▼
                       WS2812B LEDs
```

---

# Phase 0 — Hardware Verification

**Goal:** Confirm the purchased hardware is suitable before building software.

### Hardware

- ESP32 development board
- WS2812B addressable RGB LED strip
- 3-pin connector
- Existing 5V power supply
- USB cable for ESP32
- Wires/connectors as required

### Tasks

- [ ] Identify exact ESP32 board/model
- [ ] Identify exact LED strip type and LED density
- [ ] Verify 5V power supply voltage/current rating
- [ ] Confirm connector pinout
- [ ] Confirm LED strip power requirements
- [ ] Prepare safe wiring
- [ ] Do not power the complete strip directly from the ESP32

### Deliverable

A safely powered LED strip connected to ESP32.

---

# Phase 1 — ESP32 LED Controller

**Goal:** Make the ESP32 reliably control the LED strip.

### Tasks

- [ ] Install ESP32 development environment
- [ ] Flash first firmware
- [ ] Control one LED
- [ ] Control complete strip
- [ ] Implement RGB color
- [ ] Implement brightness
- [ ] Implement smooth fade
- [ ] Implement power ON/OFF
- [ ] Implement basic effects
- [ ] Add safe maximum-brightness limit
- [ ] Add startup/default state
- [ ] Add connection/reconnection handling

### Basic command model

```json
{
  "r": 255,
  "g": 40,
  "b": 10,
  "brightness": 0.75
}
```

### Deliverable

Mac sends a command and the LED strip changes accordingly.

---

# Phase 2 — Host ↔ ESP32 Communication

**Goal:** Establish reliable low-latency communication.

### Initial transport

Use **USB serial** first.

Later evaluate Wi-Fi for the product version.

```text
Mac
 │
 │ USB Serial
 ▼
ESP32
 │
 ▼
LED Strip
```

### Tasks

- [ ] Define communication protocol
- [ ] Implement serial command parser
- [ ] Add acknowledgements/status where useful
- [ ] Handle malformed commands
- [ ] Handle reconnects
- [ ] Measure command-to-light latency
- [ ] Determine practical update rate

### Future transport

```text
USB
 ↓
Wi-Fi
 ↓
WebSocket/UDP depending on latency and reliability testing
```

### Deliverable

Stable real-time communication between host and ESP32.

---

# Phase 3 — Lighting Engine

**Goal:** Create one central software component that converts inputs into lighting commands.

### Input

```text
screenColor
audioIntensity
audioBands
developerEvent
userSettings
mode
```

### Output

```text
RGB
brightness
effect
transition
```

### Tasks

- [ ] Create normalized internal representation
- [ ] Implement color interpolation
- [ ] Implement brightness smoothing
- [ ] Implement transition timing
- [ ] Implement event priority
- [ ] Implement brightness ceiling
- [ ] Implement fallback behavior
- [ ] Prevent flickering
- [ ] Prevent sudden color jumps
- [ ] Add debug logging

### Suggested event priority

```text
Critical developer event
        ↓
Developer status event
        ↓
User-selected effect
        ↓
Screen color
        ↓
Audio brightness
```

### Deliverable

A reusable lighting engine independent of the UI and hardware transport.

---

# Phase 4 — Screen / Video Color Sync

**Goal:** Make LED color follow the current screen/video.

### Initial implementation

Use local screen capture and pixel analysis.

```text
Screen
  ↓
Capture
  ↓
Downsample
  ↓
Color analysis
  ↓
RGB
  ↓
Lighting Engine
```

### Tasks

- [ ] Implement screen capture on macOS
- [ ] Capture only required region where possible
- [ ] Downsample frames
- [ ] Calculate average/dominant color
- [ ] Ignore insignificant/noisy colors where useful
- [ ] Test different color extraction algorithms
- [ ] Add temporal smoothing
- [ ] Measure processing time
- [ ] Tune update rate

### Future enhancement

Split the screen into zones.

```text
Screen                 LED zones

[ BLUE ][ RED ]        [ BLUE ][ RED ]
[ ORANGE ][ GREEN ]    [ ORANGE ][ GREEN ]
```

### Deliverable

Play a movie/video and have the LED color follow the screen smoothly.

---

# Phase 5 — Audio Analysis

**Goal:** Use audio intensity to control brightness.

### Important design

For Movie/Game mode:

```text
Audio intensity → Brightness
```

Not:

```text
Frequency → Color
```

### Tasks

- [ ] Capture system audio locally
- [ ] Obtain PCM/audio samples
- [ ] Calculate RMS/amplitude
- [ ] Normalize intensity to 0–1
- [ ] Apply smoothing
- [ ] Implement brightness ceiling
- [ ] Add Auto mode
- [ ] Add 50% mode
- [ ] Add 80% mode
- [ ] Add 100% mode
- [ ] Add manual brightness slider
- [ ] Test dialogue vs action scenes
- [ ] Tune response curve

### Brightness model

```text
audioIntensity × userLimit = finalBrightness
```

Example:

```text
audioIntensity = 0.80
userLimit = 0.50

finalBrightness = 0.40
```

### Deliverable

Video color controls LED color while sound controls LED brightness.

---

# Phase 6 — Music Mode

**Goal:** Make music visually reactive using frequency bands.

### Concept

```text
Bass       → Red
Mid/Vocal  → Green
High/Hihat → Blue
Other      → blended/secondary colors

Overall intensity → Brightness
```

### Tasks

- [ ] Implement FFT
- [ ] Divide spectrum into useful frequency bands
- [ ] Normalize each band
- [ ] Tune bass range
- [ ] Tune mid/vocal range
- [ ] Tune high/hihat range
- [ ] Blend multiple active bands
- [ ] Add brightness based on overall intensity
- [ ] Add smoothing
- [ ] Test different music genres
- [ ] Tune visual response

### Deliverable

Music produces dynamic colors while loudness controls brightness.

---

# Phase 7 — Developer Mode

**Goal:** Make the product genuinely useful/fun for developers.

### Base behavior

```text
Normal coding → Screen-sync color
```

### Development events

```text
Building       → Blue
Tests running  → Purple
Warning        → Yellow
Build success  → Green
Build failure  → Red
Deployment     → Blue/animation
Deployment OK  → Green
Deployment fail→ Red
```

### Tasks

- [ ] Define developer event protocol
- [ ] Create local event listener
- [ ] Create CLI command/API for events
- [ ] Add build status integration
- [ ] Add test status integration
- [ ] Add Git status integration
- [ ] Add GitHub Actions integration later
- [ ] Add VS Code integration later
- [ ] Implement temporary event effects
- [ ] Return to previous lighting state after event

### Example

```text
Build failed
    ↓
Red pulse for 2 seconds
    ↓
Return to previous screen color
```

### Deliverable

Developer workflow visibly changes the environment.

---

# Phase 8 — Game Mode

**Goal:** Provide a simple gaming experience without requiring game-specific integrations initially.

### V1

```text
Game screen → Color
Game audio → Brightness
```

### Tasks

- [ ] Reuse screen analyzer
- [ ] Reuse audio analyzer
- [ ] Add gaming-specific smoothing
- [ ] Add stronger flash effects
- [ ] Add optional high-intensity effects
- [ ] Add user intensity control
- [ ] Test FPS/gameplay impact

### Future

Game-specific integrations can be added later if there is a strong use case.

### Deliverable

Game screen and sound drive the lighting with minimal perceived latency.

---

# Phase 9 — Custom Mode

**Goal:** Give power users control without making normal users configure everything.

### Controls

- Color
- Brightness
- Transition speed
- Effect
- Audio limit
- Screen sensitivity
- LED zones
- Event behavior

### Deliverable

A power-user mode while keeping preset modes simple.

---

# Phase 10 — Desktop Control App

**Goal:** Create a simple user-facing application.

### Recommended first platform

**macOS**, because it is the development machine and easiest to validate first.

### UI

```text
DEVLIGHTS

Status: ● Connected

Mode
[ Movie ▼ ]

Sound
Auto
[──────●────────]
70%

Effects
[ Smooth ]

Developer Events
[ ON ]

[Test Red]
[Test Green]
[Test Blue]
```

### Tasks

- [ ] Device discovery/status
- [ ] Mode selection
- [ ] Brightness control
- [ ] Sound mode control
- [ ] Test colors
- [ ] Enable/disable sync
- [ ] Settings persistence
- [ ] Error/status display

### Deliverable

A normal user can operate the system without using a terminal.

---

# Phase 11 — Mobile App

**Goal:** Add phone control after the core desktop version is stable.

### Technology

React Native is a strong candidate.

### Tasks

- [ ] ESP32 discovery
- [ ] Connect to device
- [ ] Mode selection
- [ ] Brightness slider
- [ ] Manual color
- [ ] Device settings
- [ ] Developer/event controls where applicable

### Important

Mobile screen synchronization should be treated as a separate platform feature because Android/iOS have different screen/audio capture restrictions.

### Deliverable

Phone can control the same ESP32 lighting system.

---

# Phase 12 — Wi-Fi / Multi-Device Support

**Goal:** Remove the USB dependency and support multiple controllers.

### Architecture

```text
Mac / Phone
     │
    Wi-Fi
     │
 ┌───┴────┐
 ▼        ▼
ESP32-1  ESP32-2
 │        │
LEDs     LEDs
```

### Tasks

- [ ] Wi-Fi provisioning
- [ ] Device discovery
- [ ] Device identity
- [ ] Connection management
- [ ] Real-time transport
- [ ] Multi-zone synchronization
- [ ] Time/sequence synchronization
- [ ] Recovery after Wi-Fi loss

### Deliverable

Wireless whole-desk/room lighting.

---

# Phase 13 — Hardware Productization

**Only start after the prototype is proven.**

### Tasks

- [ ] Design custom controller PCB
- [ ] Improve power distribution
- [ ] Add protection circuitry
- [ ] Add proper connectors
- [ ] Design enclosure
- [ ] Thermal testing
- [ ] EMI/noise considerations
- [ ] Cable management
- [ ] Mounting system
- [ ] Power-supply selection
- [ ] Manufacturing BOM
- [ ] Assembly process

### Deliverable

A repeatable hardware unit instead of a development-board prototype.

---

# Phase 14 — Product Validation

**Goal:** Determine whether people actually want it.

### Pilot

Build approximately **5–20 units**.

### Target users

- Developers
- Gamers
- Movie lovers
- Music lovers

### Test questions

- Is setup easy?
- Is synchronization fast enough?
- Which mode is used most?
- Which effects feel useful vs annoying?
- Is the brightness behavior comfortable?
- Would users pay for it?
- What price feels reasonable?
- Would they recommend it?

### Deliverable

Real user feedback and a validated product direction.

---

# Phase 15 — Commercial Product

Only after validation.

### Product structure

Potentially:

```text
Starter
├── ESP32 controller
├── LED strip
└── Basic modes

Pro
├── Better LED density
├── All modes
├── Desktop app
├── Mobile app
└── Developer integrations

Multi-Zone / Pro+
├── Multiple controllers
├── Multiple LED zones
├── Advanced effects
└── Extended integrations
```

### Commercial requirements

- [ ] Manufacturing cost analysis
- [ ] Packaging
- [ ] Branding
- [ ] Documentation
- [ ] Setup guide
- [ ] Firmware update mechanism
- [ ] Software update mechanism
- [ ] Diagnostics
- [ ] Warranty process
- [ ] Returns process
- [ ] Safety/compliance requirements
- [ ] Marketplace/store setup
- [ ] Pricing validation

---

# Recommended Development Order

Do **not** build everything at once.

```text
PHASE 0
Hardware verification
       ↓
PHASE 1
ESP32 + LED
       ↓
PHASE 2
Mac ↔ ESP32
       ↓
PHASE 3
Lighting Engine
       ↓
PHASE 4
Screen Color
       ↓
PHASE 5
Audio Brightness
       ↓
       ★ FIRST COMPLETE MOVIE MODE
       ↓
PHASE 6
Music Mode
       ↓
PHASE 7
Developer Mode
       ↓
PHASE 8
Game Mode
       ↓
PHASE 9
Custom Mode
       ↓
PHASE 10
Desktop App
       ↓
       ★ USABLE V1
       ↓
PHASE 11
Mobile
       ↓
PHASE 12
Wi-Fi / Multi-zone
       ↓
PHASE 13
Hardware Productization
       ↓
PHASE 14
Pilot
       ↓
PHASE 15
Commercial Product
```

# MVP Definition

The first milestone should be deliberately small.

## MVP v0.1

```text
Mac
 ↓
Screen color
 ↓
Lighting Engine
 ↓
USB
 ↓
ESP32
 ↓
WS2812B
```

Success criteria:

- [ ] LED responds correctly
- [ ] Color follows video
- [ ] Transitions are smooth
- [ ] No obvious flicker
- [ ] Low perceived latency

## MVP v0.2

Add:

```text
Audio → brightness
```

Success criteria:

- [ ] Quiet audio produces low brightness
- [ ] Loud audio produces higher brightness
- [ ] User can select Auto / 50 / 80 / 100
- [ ] User can manually control the brightness ceiling

## MVP v0.3

Add:

```text
Developer events
```

Success criteria:

- [ ] Build failure → red
- [ ] Build success → green
- [ ] Tests → purple
- [ ] Warning → yellow
- [ ] System returns to previous state

## V1

```text
Movie
Music
Developer
Game
Custom
```

plus a usable desktop UI.

---

# Non-Goals for V1

Do **not** add these initially:

- AI/LLM
- Cloud backend
- Database
- User accounts
- Authentication
- Complex SaaS infrastructure
- Raspberry Pi
- Dedicated server
- TV app
- iOS screen synchronization
- Game-specific integrations
- Custom PCB
- Large-scale manufacturing

These can be evaluated after the core system works.

---

# Technical Principles

1. **Local-first:** Real-time analysis should happen locally.
2. **Low latency:** Avoid unnecessary network/server hops.
3. **ESP32 stays simple:** It should primarily control hardware.
4. **Lighting Engine stays independent:** UI, audio, video, and transport should not be tightly coupled.
5. **Preset modes for normal users:** Custom controls for power users.
6. **Smooth everything:** Raw analysis should never directly drive visible LEDs.
7. **Fail safely:** Brightness limits and power considerations are mandatory.
8. **Measure before optimizing:** Record capture, processing, transport, and LED update latency separately.
9. **Build one working path first:** Mac → ESP32 → LED.
10. **Productize only after validation.**

---

# Initial Target

### First usable demo

**Target: 2–4 focused development days**

```text
Day 1 → ESP32 + LED + communication
Day 2 → Screen color synchronization
Day 3 → Audio brightness
Day 4 → Smoothing + basic UI + developer events
```

The schedule is flexible; hardware/debugging can add time.

---

# Current Status

## Hardware

- [x] ESP32 purchased
- [x] WS2812B LED strip purchased
- [x] LED connector purchased
- [x] 5V power supply already available
- [ ] Verify exact PSU current rating
- [ ] Verify exact ESP32 model
- [ ] Verify exact LED strip model/density

## Software

- [ ] ESP32 firmware
- [ ] Mac controller
- [ ] Screen analyzer
- [ ] Audio analyzer
- [ ] Lighting engine
- [ ] Developer event engine
- [ ] Desktop UI
- [ ] Mobile app
- [ ] Wi-Fi protocol

## Product

- [ ] Prototype
- [ ] User testing
- [ ] BOM optimization
- [ ] Custom PCB
- [ ] Enclosure
- [ ] Pilot batch
- [ ] Commercial launch

---

# First Task When Hardware Arrives

Do only this:

```text
5V PSU
   │
   ├──────────► WS2812B +5V
   │
   └──────────► Common GND
                    │
ESP32 GND ──────────┘

ESP32 GPIO ────────► WS2812B DATA
```

Then:

```text
ESP32
  ↓
Set LED RED
  ↓
Set LED GREEN
  ↓
Set LED BLUE
  ↓
Set brightness
  ↓
Control entire strip
```

After that, move to **Mac → ESP32 communication**.

---

# Project Philosophy

Build it as a **developer project first**, not a startup first.

The sequence is:

**Make it work → Make it good → Use it yourself → Get others to use it → Validate demand → Productize → Sell.**

Do not optimize manufacturing cost or build a complex backend before the lights are sitting on the desk and reacting exactly the way we want.
