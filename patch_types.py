import sys

# 1. Update lighting.ts
with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/types/lighting.ts', 'r') as f:
    t_content = f.read()

t_content = t_content.replace('color: RGBColor;', 'color: RGBColor;\n  musicSettings?: any;')

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/types/lighting.ts', 'w') as f:
    f.write(t_content)


# 2. Update LightingService.ts
with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/LightingService.ts', 'r') as f:
    s_content = f.read()

s_content = s_content.replace('setColor(color: RGBColor): Promise<void>;', 'setColor(color: RGBColor): Promise<void>;\n  setMusicColors(bass?: RGBColor, mid?: RGBColor, treb?: RGBColor): Promise<void>;')

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/LightingService.ts', 'w') as f:
    f.write(s_content)


# 3. Update RealLightingService.ts
with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/RealLightingService.ts', 'r') as f:
    r_content = f.read()

r_content = r_content.replace('analyzers: p.analyzers', 'analyzers: p.analyzers,\n        musicSettings: data.payload.music_settings')
r_content = r_content.replace('async setColor(color: RGBColor): Promise<void> {', 'async setMusicColors(bass?: RGBColor, mid?: RGBColor, treb?: RGBColor): Promise<void> {\n    this.sendCommand("set_music_colors", { bass_color: bass, mid_color: mid, treb_color: treb });\n  }\n\n  async setColor(color: RGBColor): Promise<void> {')

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/RealLightingService.ts', 'w') as f:
    f.write(r_content)


# 4. Update lightingStore.ts
with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/store/lightingStore.ts', 'r') as f:
    ls_content = f.read()

ls_content = ls_content.replace('analyzers: {', 'musicSettings: any;\n  setMusicColors: (bass?: RGBColor, mid?: RGBColor, treb?: RGBColor) => void;\n  analyzers: {')
ls_content = ls_content.replace('analyzers: {},', 'musicSettings: { bass_color: {r:255,g:0,b:0}, mid_color: {r:0,g:255,b:0}, treb_color: {r:0,g:0,b:255} },\n  analyzers: {},')
ls_content = ls_content.replace('setColor: (color) => {', 'setMusicColors: (bass, mid, treb) => {\n    lightingService.setMusicColors(bass, mid, treb);\n  },\n  setColor: (color) => {')
ls_content = ls_content.replace('analyzers: state.analyzers || {},', 'analyzers: state.analyzers || {},\n        musicSettings: (state as any).musicSettings || { bass_color: {r:255,g:0,b:0}, mid_color: {r:0,g:255,b:0}, treb_color: {r:0,g:0,b:255} },')

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/store/lightingStore.ts', 'w') as f:
    f.write(ls_content)


