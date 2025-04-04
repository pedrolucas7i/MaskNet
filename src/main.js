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
    // Starting SSH process with '-T' to avoid pseudo-terminal allocation
    sshProcess = spawn('ssh', ['-T', '-D', '1080', sshTarget]);

    let sshConnected = false;

    sshProcess.stdout.on('data', async (data) => {
      const output = data.toString().toLowerCase();
      console.log('SSH stdout:', output);

      // If we detect the connection is established, we know it's ready
      if (output.includes('remote port forwarding') || output.includes('channel open')) {
        sshConnected = true;
      }
    });

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

      // Detect the authenticity prompt of the host
      if (output.includes('are you sure you want to continue connecting')) {
        const win = BrowserWindow.getAllWindows()[0];
        const confirmation = await win.webContents.executeJavaScript(
          `showHostAuthenticityModal("${sshTarget}")`
        );

        if (confirmation === 'yes') {
          sshProcess.stdin.write('yes\n'); // Confirm the authenticity of the host
        } else {
          sshProcess.kill(); // Cancel connection if the user selects "no"
          reject('SSH connection cancelled by user');
        }
      }
    });

    sshProcess.on('error', (err) => {
      console.error("Error with SSH process:", err);
      reject('SSH Error: ' + err.message);
    });

    sshProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`SSH process exited with code ${code}`);
        reject(`SSH process exited with code ${code}`);
      }
    });

    // Wait for SSH to be fully connected before setting up the proxy and loading the browser
    const checkInterval = setInterval(() => {
      if (sshConnected) {
        clearInterval(checkInterval);
        session.defaultSession.setProxy({ proxyRules: 'socks5://127.0.0.1:1080' }).then(() => {
          // Once the SSH connection is ready, load DuckDuckGo
          const win = BrowserWindow.getAllWindows()[0];
          win.webContents.executeJavaScript(`
            document.getElementById('browser').src = "https://duckduckgo.com"; // Or use Google
          `);
        });
        resolve('Connected successfully!');
      }
    }, 500); // Check every 500ms

    // Timeout if SSH doesn't connect within a reasonable time (e.g., 60 seconds)
    setTimeout(() => {
      if (!sshConnected) {
        reject('SSH connection timeout');
      }
    }, 60000); // Timeout after 1 minute
  }).catch((errorMessage) => {
    // If an error occurs, show the error in the UI
    const win = BrowserWindow.getAllWindows()[0];
    win.webContents.send('show-error-modal', errorMessage); // Emit event for error modal
  });
});
