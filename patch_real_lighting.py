import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/RealLightingService.ts', 'r') as f:
    content = f.read()

content = content.replace("outputMode: p.output_mode || 'auto',", "outputMode: p.output_mode || 'auto',\n        power_on: p.power_on ?? true,")
content = content.replace("async setOutputMode(outputMode: string): Promise<void> {", "async setPower(isOn: boolean): Promise<void> {\n    this.sendCommand('set_power', { power_on: isOn });\n  }\n\n  async setOutputMode(outputMode: string): Promise<void> {")

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/RealLightingService.ts', 'w') as f:
    f.write(content)
