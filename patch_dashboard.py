import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/screens/DashboardScreen.tsx', 'r') as f:
    content = f.read()

content = content.replace("const { color, brightness, mode, setMode, setBrightness, outputMode, setOutputMode, transport, engineConnected, analyzers } = useLightingStore();", "const { color, brightness, mode, setMode, setBrightness, outputMode, setOutputMode, power_on, setPower, transport, engineConnected, analyzers } = useLightingStore();")

content = content.replace("onClick={() => setMode(mode === 'off' ? 'movie' : 'off')}", "onClick={() => setPower(!power_on)}")
content = content.replace("mode === 'off'", "!power_on")
content = content.replace("mode === 'off' ? \"Turn On\" : \"Turn Off\"", "!power_on ? \"Turn On\" : \"Turn Off\"")

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/screens/DashboardScreen.tsx', 'w') as f:
    f.write(content)
