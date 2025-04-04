const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  startSSHTunnel: (target) => ipcRenderer.invoke('start-ssh-tunnel', target)
});
