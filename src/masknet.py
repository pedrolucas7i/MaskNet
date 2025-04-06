import sys
import os
import subprocess
import signal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QLineEdit, QLabel, QInputDialog, QHBoxLayout
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer, Qt


class MaskNetApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MaskNet - SSH SOCKS5 Browser")
        self.setGeometry(100, 100, 1080, 720)

        self.setStyleSheet("background-color: #f4f7fa;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(10, 20, 10, 10)
        self.layout.setSpacing(5)
        self.logo = QLabel("🛡️ MaskNet", self)
        self.logo.setStyleSheet("font-size: 40px;")
        self.logo.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.logo)
        # Layout superior com os controles (barra de URL, SSH)
        self.top_layout = QHBoxLayout()
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(5)

        # Barra de URL
        # self.url_label = QLabel("URL", self)
        # self.url_label.setStyleSheet("color: black;")
        # self.top_layout.addWidget(self.url_label)

        self.undo_button = QPushButton("◀", self)
        self.undo_button.setStyleSheet("border: none; font-weight: bold; background-color: #5c6bc0; color: white; padding: 0px 5px 2.5px 2.5px")
        self.undo_button.clicked.connect(self.undo_page)
        self.top_layout.addWidget(self.undo_button)

        self.url_bar = QLineEdit(self)
        self.url_bar.setPlaceholderText("Digite a URL e pressione Enter")
        self.url_bar.setStyleSheet("border: 2px solid #5c6bc0; border-radius: 10px;")
        self.url_bar.returnPressed.connect(self.load_url)
        self.top_layout.addWidget(self.url_bar)

        self.forward_button = QPushButton("▶", self)
        self.forward_button.setStyleSheet("border: none; border font-weight: bold; background-color: #5c6bc0; color: white; padding: 0px 2.5px 2.5px 5px;")
        self.forward_button.clicked.connect(self.forward_page)
        self.top_layout.addWidget(self.forward_button)

        # Entrada de SSH
        # self.ssh_label = QLabel("USER@HOST", self)
        # self.ssh_label.setStyleSheet("color: rgb(50, 50, 50)")
        # self.top_layout.addWidget(self.ssh_label)

        self.ssh_target_entry = QLineEdit(self)
        self.ssh_target_entry.setPlaceholderText("user@host")
        self.ssh_target_entry.setStyleSheet("border: 2px solid #5c6bc0; border-radius: 10px;")
        self.top_layout.addWidget(self.ssh_target_entry)

        # Botão de Conectar
        self.connect_button = QPushButton("   Connect   ", self)
        self.connect_button.setStyleSheet("border: none; font-weight: bold;")
        self.connect_button.clicked.connect(self.connect)
        self.top_layout.addWidget(self.connect_button)

        # Adiciona o layout superior com stretch 0 (tamanho mínimo)
        self.layout.addLayout(self.top_layout, 0)

        # Status (opcional, também com tamanho mínimo)
        self.status_label = QLabel("", self)
        self.status_label.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.status_label, 0)

        # Browser ocupa o restante do espaço disponível (stretch 1)
        self.browser = QWebEngineView()
        self.browser.urlChanged.connect(self.update_url_bar)
        self.layout.addWidget(self.browser, 1)

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
            self.browser.setUrl(QUrl(self.url_bar.text().strip()))
            self.url_bar.setText(self.url_bar.text().strip())
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

    def undo_page(self):
        if self.browser.history().canGoBack():
            self.browser.back()

    def forward_page(self):
        if self.browser.history().canGoForward():
            self.browser.forward()


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
    window.showMaximized()  # Maximiza a janela ao iniciar
    sys.exit(app.exec_())
