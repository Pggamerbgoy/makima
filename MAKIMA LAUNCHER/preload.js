const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('makima', {
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),
  sendMessage: (text) => ipcRenderer.send('send-to-python', text),
  onMessage: (callback) => ipcRenderer.on('python-message', (_, data) => callback(data)),
  launchVoltEditor: () => ipcRenderer.invoke('launch-volt-editor')
})
