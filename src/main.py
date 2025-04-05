import sys
import os
import subprocess
import signal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QLineEdit, QLabel, QInputDialog, QHBoxLayout
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer


class MaskNetApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MaskNet - SSH SOCKS5 Browser")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.logo = QLabel("🛡️ MaskNet", self)
        self.layout.addWidget(self.logo)

        self.ssh_target_entry = QLineEdit(self)
        self.ssh_target_entry.setPlaceholderText("user@host")
        self.layout.addWidget(self.ssh_target_entry)

        self.connect_button = QPushButton("Connect", self)
        self.connect_button.clicked.connect(self.connect)
        self.layout.addWidget(self.connect_button)

        self.status_label = QLabel("", self)
        self.layout.addWidget(self.status_label)

        # Barra de URL
        self.url_bar = QLineEdit(self)
        self.url_bar.setPlaceholderText("Enter URL and press Enter")
        self.url_bar.returnPressed.connect(self.load_url)
        self.layout.addWidget(self.url_bar)

        self.browser = QWebEngineView()
        self.browser.urlChanged.connect(self.update_url_bar)
        self.layout.addWidget(self.browser)

        self.ssh_process = None
        self.proxy_port = 1080
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_connection)

    def connect(self):
        target = self.ssh_target_entry.text().strip()
        if not target or "@" not in target:
            self.status_label.setText("Enter SSH target like user@host")
            return

        password, ok = QInputDialog.getText(self, 'Password', 'SSH Password:', QLineEdit.Password)
        if not ok or not password:
            self.status_label.setText("Password canceled")
            return

        self.status_label.setText("Connecting...")
        self.start_ssh_socks_proxy(target, password)

    def start_ssh_socks_proxy(self, target, password):
        try:
            user, host = target.split("@")

            self.ssh_process = subprocess.Popen(
                ['sshpass', '-p', password, 'ssh', '-o', 'StrictHostKeyChecking=no', '-D', str(self.proxy_port), '-N', f'{user}@{host}'],
                preexec_fn=os.setsid
            )

            self.status_label.setText("SSH SOCKS5 tunnel started.")
            self.browser.setUrl(QUrl("https://www.google.com"))
            self.url_bar.setText("https://www.google.com")
            self.timer.start(5000)

        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")

    def load_url(self):
        url_text = self.url_bar.text()
        if not url_text.startswith("http"):
            url_text = "http://" + url_text
        self.browser.setUrl(QUrl(url_text))

    def update_url_bar(self, url):
        self.url_bar.setText(url.toString())

    def check_connection(self):
        import socket
        try:
            socket.create_connection(("www.google.com", 80), timeout=5)
            self.status_label.setText("Internet OK through SSH tunnel")
        except Exception as e:
            self.status_label.setText(f"No Internet via proxy: {str(e)}")

    def closeEvent(self, event):
        if self.ssh_process:
            os.killpg(os.getpgid(self.ssh_process.pid), signal.SIGTERM)
        event.accept()


if __name__ == "__main__":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--proxy-server=socks5://127.0.0.1:1080"
    app = QApplication(sys.argv)
    window = MaskNetApp()
    window.show()
    sys.exit(app.exec_())
