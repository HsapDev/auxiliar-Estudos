import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QSystemTrayIcon, QMenu, QStyle
)
from PyQt6.QtGui import QIcon, QAction

# Logger Central
from logger import log_info, log_sucesso, log_aviso, log_erro
from ui.theme import aplicar_estilo_app

# Importa as abas criadas
from ui.tab_home import TabHome
from ui.tab_arena import TabArena
from ui.tab_guru import TabGuru
from ui.tab_fabriqueiro import TabFabriqueiro
from ui.tab_config import TabConfig
from ui.tab_logs import TabLogs

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎓 Auxiliar de Estudos & Simulados")
        self.resize(1120, 780)
        self.setMinimumSize(960, 680)
        log_info("Inicializando interface gráfica principal...", "App")

        # Configura as Abas Principais
        self.tabs = QTabWidget()
        self.tab_home = TabHome()
        self.tab_arena = TabArena()
        self.tab_guru = TabGuru()
        self.tab_fabriqueiro = TabFabriqueiro()
        self.tab_config = TabConfig()
        self.tab_logs = TabLogs()

        self.tabs.addTab(self.tab_home, "Fila de Estudos")
        self.tabs.addTab(self.tab_arena, "⚔️ Arena (Simulados)")
        self.tabs.addTab(self.tab_guru, "🧙‍♂️ Guru de Estudos")
        self.tabs.addTab(self.tab_fabriqueiro, "🏭 O Fabriqueiro (Prompts)")
        self.tabs.addTab(self.tab_config, "Configurações")
        self.tabs.addTab(self.tab_logs, "📋 Central de Logs")

        self.setCentralWidget(self.tabs)

        # Configura o Tray Icon
        self._configurar_tray_icon()
        log_sucesso("Aplicação iniciada e pronta para uso!", "App")

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
        action_sair.triggered.connect(self._sair_aplicacao)
        tray_menu.addAction(action_sair)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def _sair_aplicacao(self):
        log_info("Encerrando aplicação definitivamente a pedido do usuário...", "App")
        QApplication.instance().quit()

    def enviar_notificacao_diaria(self):
        """Dispara um pop-up de notificação nativo do sistema operacional."""
        log_info("Disparando notificação de lembrete diário.", "App")
        self.tray_icon.showMessage(
            "Plano de Estudos do Dia",
            "Você tem tópicos pendentes para revisar hoje! Clique para abrir.",
            QSystemTrayIcon.MessageIcon.Information,
            3000  # Duração em milissegundos
        )

    def closeEvent(self, event):
        """Minimiza para o Tray Icon ao clicar no 'X' em vez de fechar o app."""
        if self.tray_icon.isVisible():
            log_info("Janela fechada pelo usuário: minimizando para a bandeja do sistema (Tray).", "App")
            self.hide()
            self.enviar_notificacao_diaria()
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Aplica o tema visual moderno em toda a aplicação
    aplicar_estilo_app(app)

    # Garante que o app não encerre se a janela for fechada (apenas se chamar quit)
    app.setQuitOnLastWindowClosed(False)

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        log_erro("Erro não tratado na execução principal do app", "App", exc=e)
        raise e