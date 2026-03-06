const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('node:path')
const { spawn } = require('child_process')

let mainWindow
let pythonProcess

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 780,
    minWidth: 1000,
    minHeight: 600,
    frame: false,          // removes default Windows title bar
    transparent: false,
    backgroundColor: '#0d0d1a',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  })

  mainWindow.loadFile('index.html')

  // Start Python backend
  startPython()
}

function startPython() {
  // Adjust path to your makima main file
  const pythonPath = 'python'
  const scriptPath = path.join(__dirname, '..', 'makima_assistant.py')

  pythonProcess = spawn(pythonPath, [scriptPath, '--ipc'], {
    stdio: ['pipe', 'pipe', 'pipe'],
  })

  pythonProcess.stdout.on('data', (data) => {
    const lines = data.toString().split('\n')
    for (const line of lines) {
      if (line.startsWith('MSG:::')) {
        const msg = line.substring(6).trim()
        if (mainWindow) {
          mainWindow.webContents.send('python-message', msg)
        }
      } else if (line.trim()) {
        console.log('[Python]', line.trim())
      }
    }
  })

  pythonProcess.stderr.on('data', (data) => {
    console.error('[Python Error]', data.toString())
  })

  pythonProcess.on('close', (code) => {
    console.log('[Python] exited with code', code)
  })
}

// Window controls (since we removed the frame)
ipcMain.on('window-minimize', () => mainWindow.minimize())
ipcMain.on('window-maximize', () => {
  if (mainWindow.isMaximized()) mainWindow.unmaximize()
  else mainWindow.maximize()
})
ipcMain.on('window-close', () => {
  if (pythonProcess) pythonProcess.kill()
  app.quit()
})

// Send message to Python
ipcMain.on('send-to-python', (event, message) => {
  if (pythonProcess && pythonProcess.stdin.writable) {
    pythonProcess.stdin.write(message + '\n')
  }
})

// Handle Python connection test
ipcMain.handle('test-python-connection', () => {
  return true;
});

// Launch Volt Code Editor
ipcMain.handle('launch-volt-editor', () => {
  const voltPath = path.join(__dirname, '..', 'code editor', 'main.py');
  const voltProcess = spawn('python', [voltPath], {
    detached: true,
    stdio: 'ignore'
  });
  voltProcess.unref(); // Allow Makima to close while Volt stays open
  return true;
});

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
