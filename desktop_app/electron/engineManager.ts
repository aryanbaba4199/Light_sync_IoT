import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import { BrowserWindow } from 'electron';

export class EngineManager {
  private engineProcess: ChildProcess | null = null;
  private isShuttingDown = false;
  private restartCount = 0;
  private maxRestarts = 5;

  constructor(private mainWindow: BrowserWindow | null) {}

  public start() {
    if (this.engineProcess) return;

    if (this.restartCount >= this.maxRestarts) {
      console.error('[EngineManager] Max restarts reached. Giving up.');
      return;
    }

    const pythonExecutable = 'python3';
    // When running in dev, __dirname is .../desktop_app/dist-electron
    const hostDir = path.join(__dirname, '../../host');
    const scriptPath = path.join(hostDir, 'app_headless.py');

    console.log(`[EngineManager] Starting Engine (Attempt ${this.restartCount + 1}): ${pythonExecutable} -u ${scriptPath}`);

    try {
      this.engineProcess = spawn(pythonExecutable, ['-u', scriptPath], {
        cwd: hostDir,
        stdio: 'pipe',
      });

      this.engineProcess.stdout?.on('data', (data) => {
        const str = data.toString().trim();
        if (str) console.log(`[Engine] ${str}`);
      });

      this.engineProcess.stderr?.on('data', (data) => {
        const str = data.toString().trim();
        if (str) console.error(`[Engine Error] ${str}`);
      });

      this.engineProcess.on('close', (code) => {
        console.log(`[EngineManager] Process exited with code ${code}`);
        this.engineProcess = null;

        if (!this.isShuttingDown) {
          this.restartCount++;
          setTimeout(() => this.start(), 2000); // Backoff before restart
        }
      });
    } catch (e) {
      console.error('[EngineManager] Failed to spawn python process', e);
    }
  }

  public stop() {
    this.isShuttingDown = true;
    if (this.engineProcess) {
      console.log('[EngineManager] Stopping Engine...');
      this.engineProcess.kill();
      this.engineProcess = null;
    }
  }
}
