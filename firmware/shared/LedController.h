#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include <Arduino.h>
#include <FastLED.h>

#define LED_PIN     5
#define NUM_LEDS    300
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB

class LedController {
private:
    CRGB leds[NUM_LEDS];
    int currentBrightness;
    
public:
    LedController() : currentBrightness(255) {}

    void begin() {
        FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
        FastLED.setBrightness(currentBrightness);
        // POWER MANAGEMENT: Limit maximum power to 5V, 2500mA (2.5A / 12.5W).
        // This prevents SMPS brownout trips, voltage sag, and WS2812B logic latching/freezing.
        FastLED.setMaxPowerInVoltsAndMilliamps(5, 2500);
        fill_solid(leds, NUM_LEDS, CRGB::Black);
        FastLED.show();
    }

    void clearAll() {
        fill_solid(leds, NUM_LEDS, CRGB::Black);
    }

    void applyState(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness, bool doShow = true) {
        fill_solid(leds, NUM_LEDS, CRGB(r, g, b));
        currentBrightness = brightness;
        FastLED.setBrightness(currentBrightness);
        if (doShow) {
            FastLED.show();
        }
    }

    void applyZone(uint16_t start, uint16_t end, uint8_t r, uint8_t g, uint8_t b) {
        if (start >= NUM_LEDS) return;
        if (end >= NUM_LEDS) end = NUM_LEDS - 1;
        if (start > end) return;
        fill_solid(&leds[start], end - start + 1, CRGB(r, g, b));
    }

    void applyIndexed(const uint16_t* indices, uint16_t count, uint8_t r, uint8_t g, uint8_t b) {
        for (uint16_t i = 0; i < count; i++) {
            uint16_t idx = indices[i];
            if (idx < NUM_LEDS) {
                leds[idx] = CRGB(r, g, b);
            }
        }
    }

    void setBrightness(uint8_t brightness) {
        currentBrightness = brightness;
        FastLED.setBrightness(currentBrightness);
    }

    bool parseBinaryPayload(const uint8_t* payload, size_t length) {
        if (length >= 5 && payload[0] == 0x55) {
            applyState(payload[1], payload[2], payload[3], payload[4], true);
            return true;
        }
        return false;
    }
};

#endif
