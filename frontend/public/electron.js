const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const isDev = require('electron-is-dev');

let mainWindow;
let pythonProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    icon: path.join(__dirname, 'favicon.ico')
  });

  const startUrl = process.env.ELECTRON_START_URL || (isDev
    ? 'http://localhost:3000'
    : `file://${path.join(__dirname, '../build/index.html')}`);

  mainWindow.loadURL(startUrl);

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function startPythonBackend() {
  // Python executable is 'python' if in PATH
  let pythonExecutable = 'python';
  let scriptPath;

  if (isDev) {
    // In dev mode, point to the source python file
    scriptPath = path.join(__dirname, '../../backend/server.py');
  } else {
    // In prod mode, find the executable or bundled script
    // E.g., a bundled exe if PyInstaller is used:
    // pythonExecutable = path.join(process.resourcesPath, 'backend', 'backend.exe');
    // For now we'll assume a source deployment or handled via pyinstaller later
    scriptPath = path.join(process.resourcesPath, 'backend', 'server.py');
  }

  console.log(`Starting python backend from: ${scriptPath}`);

  pythonProcess = spawn(pythonExecutable, [scriptPath], {
    cwd: path.dirname(scriptPath)
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python]: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python API]: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
  });
}

app.on('ready', () => {
  startPythonBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  // Gracefully kill python process
  if (pythonProcess) {
    console.log('Killing python process...');
    pythonProcess.kill();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});
