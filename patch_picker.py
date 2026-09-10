import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/screens/ExperiencesScreen.tsx', 'r') as f:
    content = f.read()

helpers = """const rgbToHex = (r: number, g: number, b: number) => '#' + [r, g, b].map(x => {
    const hex = x.toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  }).join('');

  const hexToRgb = (hex: string) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : { r: 255, g: 255, b: 255 };
  };"""

content = content.replace("const [activeBand, setActiveBand] = useState<string>('bass');", 
                          "const [activeBand, setActiveBand] = useState<string>('bass');\n  " + helpers)

custom_presets = """            <h3 className="text-sm tracking-wide text-dev-text-secondary mb-4 uppercase">Presets</h3>
            <div className="flex gap-6 mb-12">
              <PresetColor r={255} g={0} b={0} label="Red" />
              <PresetColor r={0} g={255} b={0} label="Green" />
              <PresetColor r={0} g={0} b={255} label="Blue" />
              <PresetColor r={255} g={255} b={255} label="White" />
              <PresetColor r={0} g={0} b={0} label="Off" />
              <PresetColor r={139} g={92} b={246} label="DevLights" />
            </div>"""

new_custom_presets = """            <h3 className="text-sm tracking-wide text-dev-text-secondary mb-4 uppercase">Color Picker</h3>
            <div className="flex gap-6 mb-12 items-center">
              <input 
                type="color" 
                value={rgbToHex(color.r, color.g, color.b)}
                onChange={(e) => {
                  const {r,g,b} = hexToRgb(e.target.value);
                  handleColorChange(r, g, b);
                }}
                style={{ width: '80px', height: '80px', padding: 0, border: 'none', borderRadius: '12px', cursor: 'pointer' }}
              />
              <p className="caption">Click the square to open the OS color picker and choose any color combination!</p>
            </div>"""

content = content.replace(custom_presets, new_custom_presets)

music_presets = """            <h3 className="text-sm tracking-wide text-dev-text-secondary mb-4 uppercase">Pick a color for {activeBand}</h3>
            <div className="flex gap-6 mb-12">
              <PresetColor r={255} g={0} b={0} label="Red" onClick={() => handleMusicColorChange(255, 0, 0)} />
              <PresetColor r={255} g={165} b={0} label="Orange" onClick={() => handleMusicColorChange(255, 165, 0)} />
              <PresetColor r={255} g={255} b={0} label="Yellow" onClick={() => handleMusicColorChange(255, 255, 0)} />
              <PresetColor r={0} g={255} b={0} label="Green" onClick={() => handleMusicColorChange(0, 255, 0)} />
              <PresetColor r={0} g={255} b={255} label="Cyan" onClick={() => handleMusicColorChange(0, 255, 255)} />
              <PresetColor r={0} g={0} b={255} label="Blue" onClick={() => handleMusicColorChange(0, 0, 255)} />
              <PresetColor r={139} g={92} b={246} label="Purple" onClick={() => handleMusicColorChange(139, 92, 246)} />
              <PresetColor r={255} g={192} b={203} label="Pink" onClick={() => handleMusicColorChange(255, 192, 203)} />
            </div>"""

new_music_presets = """            <h3 className="text-sm tracking-wide text-dev-text-secondary mb-4 uppercase">Color Picker for {activeBand}</h3>
            <div className="flex gap-6 mb-12 items-center">
              <input 
                type="color" 
                value={activeBand === 'bass' ? rgbToHex(musicSettings?.bass_color?.r||255, musicSettings?.bass_color?.g||0, musicSettings?.bass_color?.b||0) : activeBand === 'mid' ? rgbToHex(musicSettings?.mid_color?.r||0, musicSettings?.mid_color?.g||255, musicSettings?.mid_color?.b||0) : rgbToHex(musicSettings?.treb_color?.r||0, musicSettings?.treb_color?.g||0, musicSettings?.treb_color?.b||255)}
                onChange={(e) => {
                  const {r,g,b} = hexToRgb(e.target.value);
                  handleMusicColorChange(r, g, b);
                }}
                style={{ width: '80px', height: '80px', padding: 0, border: 'none', borderRadius: '12px', cursor: 'pointer' }}
              />
              <p className="caption">Click the square to pick an exact color for this frequency!</p>
            </div>"""

content = content.replace(music_presets, new_music_presets)

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/screens/ExperiencesScreen.tsx', 'w') as f:
    f.write(content)
