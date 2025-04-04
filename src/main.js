const { app, BrowserWindow, ipcMain, session } = require('electron');
const { spawn } = require('child_process');
let sshProcess;

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: __dirname + '/preload.js',
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  win.loadFile('renderer.html');

  win.on('closed', () => {
    if (sshProcess) sshProcess.kill();
  });
}

app.whenReady().then(createWindow);

// Handle the SSH connection
ipcMain.handle('start-ssh-tunnel', async (_, sshTarget) => {
  if (sshProcess) sshProcess.kill();

  return new Promise((resolve, reject) => {
    // Adicionando a opção '-T' para evitar a alocação de pseudo-terminal
    sshProcess = spawn('ssh', ['-T', '-D', '1080', sshTarget]);

    sshProcess.stderr.on('data', async (data) => {
      const output = data.toString().toLowerCase();
      console.log('SSH stderr:', output);

      // Detect password prompt
      if (output.includes('password')) {
        const win = BrowserWindow.getAllWindows()[0];
        const password = await win.webContents.executeJavaScript(
          `showPasswordModal("${sshTarget}")`
        );

        if (password) {
          sshProcess.stdin.write(password + '\n');
        } else {
          sshProcess.kill();
          reject('SSH connection cancelled by user');
        }
      }
    });

    sshProcess.on('error', (err) => {
      reject('SSH Error: ' + err.message);
    });

    sshProcess.on('close', (code) => {
      if (code !== 0) {
        reject(`SSH process exited with code ${code}`);
      }
    });

    // Aguardar até o túnel ser estabelecido
    setTimeout(() => {
      // Configurar proxy SOCKS5 para 127.0.0.1:1080
      session.defaultSession.setProxy({ proxyRules: 'socks5://127.0.0.1:1080' }).then(() => {
        // Carregar o DuckDuckGo ou Google após estabelecer o proxy
        const win = BrowserWindow.getAllWindows()[0];
        win.webContents.executeJavaScript(`
          document.getElementById('browser').src = "https://duckduckgo.com"; // Ou mude para "https://www.google.com"
        `);
      });

      resolve('Connected successfully!');
    }, 3000);
  });
});
