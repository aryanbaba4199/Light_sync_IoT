const fs = require('fs');

let content = fs.readFileSync('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/RealLightingService.ts', 'utf8');

const newProps = `  private commandQueue: Map<string, any> = new Map();
  private pingTimer: any = null;
  private pongTimeout: any = null;
`;
content = content.replace('  private maxBackoff = 5000;', '  private maxBackoff = 5000;\n' + newProps);

const newOnOpen = `        this.ws.onopen = () => {
          console.log('[LightingService] Connected to Engine');
          this.backoff = 1000; // reset
          this.notifyConnection(true);
          
          this.startHeartbeat();
          
          // Request initial state
          this.getState().catch(console.error);
          
          // Flush queue
          this.commandQueue.forEach((payload, type) => {
             this.sendCommand(type, payload, true);
          });
          this.commandQueue.clear();
          
          resolve();
        };`;
content = content.replace(/        this\.ws\.onopen = \(\) => \{[\s\S]*?resolve\(\);\n        \};/, newOnOpen);

const newOnClose = `        this.ws.onclose = () => {
          console.log('[LightingService] Disconnected from Engine');
          this.stopHeartbeat();
          this.notifyConnection(false);
          this.ws = null;
          this.scheduleReconnect();
        };`;
content = content.replace(/        this\.ws\.onclose = \(\) => \{[\s\S]*?        \};/, newOnClose);

const newHandleMsg = `  private handleMessage(data: any) {
    if (data.version !== 1) return;

    if (data.type === 'pong') {
      if (this.pongTimeout) {
        clearTimeout(this.pongTimeout);
        this.pongTimeout = null;
      }
      return;
    }

    if (data.type === 'lighting_state') {`;
content = content.replace(`  private handleMessage(data: any) {\n    if (data.version !== 1) return;\n\n    if (data.type === 'lighting_state') {`, newHandleMsg);

const newHeartbeat = `  private startHeartbeat() {
    this.stopHeartbeat();
    this.pingTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendCommand('ping', {}, true);
        this.pongTimeout = setTimeout(() => {
          console.warn('[LightingService] Engine missed pong. Forcing reconnect.');
          if (this.ws) this.ws.close();
        }, 5000); // 5 sec to reply
      }
    }, 15000); // Ping every 15s
  }

  private stopHeartbeat() {
    if (this.pingTimer) clearInterval(this.pingTimer);
    if (this.pongTimeout) clearTimeout(this.pongTimeout);
    this.pingTimer = null;
    this.pongTimeout = null;
  }`;

const newSendCommand = `  private sendCommand(type: string, payload: any = {}, ignoreQueue = false): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      if (!ignoreQueue) {
        console.warn(\`[LightingService] Cannot send \${type}, queuing until connected.\`);
        this.commandQueue.set(type, payload);
      }
      return;
    }
    
    const msg = {
      version: 1,
      type,
      payload
    };
    
    this.ws.send(JSON.stringify(msg));
  }`;
content = content.replace(/  private sendCommand\(type: string, payload: any = \{\}\): void \{[\s\S]*?    this\.ws\.send\(JSON\.stringify\(msg\)\);\n  \}/, newSendCommand);

content = content.replace('  async getState(): Promise<LightingState> {', newHeartbeat + '\n\n  async getState(): Promise<LightingState> {');

fs.writeFileSync('/Users/aryandubey/project/personal/Automation/light_sync/desktop_app/src/services/RealLightingService.ts', content);
