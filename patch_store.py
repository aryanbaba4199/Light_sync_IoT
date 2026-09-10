import sys

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/store/lightingStore.ts', 'r') as f:
    content = f.read()

content = content.replace("outputMode: OutputMode;", "outputMode: OutputMode;\n  power_on: boolean;")
content = content.replace("setOutputMode: (mode: OutputMode) => void;", "setOutputMode: (mode: OutputMode) => void;\n  setPower: (isOn: boolean) => void;")
content = content.replace("outputMode: 'auto',", "outputMode: 'auto',\n  power_on: true,")
content = content.replace("setColor: (color) => {", "setPower: (isOn) => {\n    lightingService.setPower(isOn);\n    set({ power_on: isOn });\n  },\n\n  setColor: (color) => {")
content = content.replace("outputMode: state.outputMode,", "outputMode: state.outputMode,\n        power_on: state.power_on,")

with open('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/store/lightingStore.ts', 'w') as f:
    f.write(content)
