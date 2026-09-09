import { app, BrowserWindow } from 'electron';
import * as path from 'path';
import { EngineManager } from './engineManager';

let mainWindow: BrowserWindow | null = null;
let engineManager: EngineManager | null = null;

const isDev = process.env.NODE_ENV === 'development';

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 750,
    minWidth: 900,
    minHeight: 600,
    titleBarStyle: 'hiddenInset', // Mac-like premium window
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false, // For simplicity in this dev phase, usually use preload
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    // mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();
  
  engineManager = new EngineManager(mainWindow);
  engineManager.start();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  if (engineManager) {
    engineManager.stop();
  }
});
