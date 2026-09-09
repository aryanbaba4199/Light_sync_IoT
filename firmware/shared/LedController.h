#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include <Arduino.h>
#include <FastLED.h>

#define LED_PIN     2
#define NUM_LEDS    60
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB

class LedController {
private:
    CRGB leds[NUM_LEDS];
    int currentBrightness;
    
public:
    LedController() : currentBrightness(128) {}

    void begin() {
        FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
        FastLED.setMaxPowerInVoltsAndMilliamps(5, 1000); // 1A max for safety
        FastLED.setBrightness(currentBrightness);
        fill_solid(leds, NUM_LEDS, CRGB::Black);
        FastLED.show();
    }

    void applyState(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
        fill_solid(leds, NUM_LEDS, CRGB(r, g, b));
        currentBrightness = brightness;
        FastLED.setBrightness(currentBrightness);
        FastLED.show();
    }

    // Binary protocol parser: [0x55, R, G, B, Brightness]
    // Returns true if a valid packet was parsed
    bool parseBinaryPayload(const uint8_t* payload, size_t length) {
        if (length >= 5 && payload[0] == 0x55) {
            applyState(payload[1], payload[2], payload[3], payload[4]);
            return true;
        }
        return false;
    }
};

#endif
