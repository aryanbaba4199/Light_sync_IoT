import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/MockLightingService.ts', 'r') as f:
    content = f.read()

content = content.replace("transport: 'none'", "transport: 'none',\n    outputMode: 'auto',\n    power_on: true")
content = content.replace("async setOutputMode(mode: string): Promise<void> {", "async setPower(isOn: boolean): Promise<void> {\n    this.state.power_on = isOn;\n    this.notifyState();\n  }\n\n  async setOutputMode(mode: string): Promise<void> {")

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/MockLightingService.ts', 'w') as f:
    f.write(content)
