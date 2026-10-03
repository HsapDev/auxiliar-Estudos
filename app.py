import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QSystemTrayIcon, QMenu, QStyle
)
from PyQt6.QtGui import QIcon, QAction

# Importa as abas criadas
from ui.tab_home import TabHome
from ui.tab_dropzone import TabDropZone


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador de Estudos & Arquivos")
        self.resize(800, 600)

        # Configura as Abas Principais
        self.tabs = QTabWidget()
        self.tab_home = TabHome()
        self.tab_dropzone = TabDropZone()

        self.tabs.addTab(self.tab_home, "Fila de Estudos")
        self.tabs.addTab(self.tab_dropzone, "Organizador (Drag & Drop)")

        self.setCentralWidget(self.tabs)

        # Configura o Tray Icon
        self._configurar_tray_icon()

    def _configurar_tray_icon(self):
        """Cria o ícone no relógio do Windows e o menu de contexto."""
        # Usa um ícone padrão do sistema para testes
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Gerenciador de Estudos")

        # Menu do Tray Icon
        tray_menu = QMenu()
        
        action_abrir = QAction("Abrir Aplicação", self)
        action_abrir.triggered.connect(self.showNormal)
        tray_menu.addAction(action_abrir)

        action_notificacao = QAction("Testar Notificação", self)
        action_notificacao.triggered.connect(self.enviar_notificacao_diaria)
        tray_menu.addAction(action_notificacao)

        tray_menu.addSeparator()

        action_sair = QAction("Sair Definitivamente", self)
        action_sair.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(action_sair)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def enviar_notificacao_diaria(self):
        """Dispara um pop-up de notificação nativo do sistema operacional."""
        self.tray_icon.showMessage(
            "Plano de Estudos do Dia",
            "Você tem tópicos pendentes para revisar hoje! Clique para abrir.",
            QSystemTrayIcon.MessageIcon.Information,
            3000  # Duração em milissegundos
        )

    def closeEvent(self, event):
        """Minimiza para o Tray Icon ao clicar no 'X' em vez de fechar o app."""
        if self.tray_icon.isVisible():
            self.hide()
            self.enviar_notificacao_diaria()
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Garante que o app não encerre se a janela for fechada (apenas se chamar quit)
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())