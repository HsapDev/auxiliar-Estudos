import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QSystemTrayIcon, QMenu, QStyle
)
from PyQt6.QtGui import QIcon, QAction

# Logger Central
from logger import log_info, log_sucesso, log_aviso, log_erro
from ui.theme import aplicar_estilo_app

# Importa as abas criadas
from ui.tab_bilau_terminal import TabBilauTerminal
from ui.tab_home import TabHome
from ui.tab_arena import TabArena
from ui.tab_guru import TabGuru
from ui.tab_fabriqueiro import TabFabriqueiro
from ui.tab_config import TabConfig
from ui.tab_logs import TabLogs

import database
from windows_safety import bloquear_desligamento_so, liberar_desligamento_so
from watcher import IngestaoWatcherHandler, Observer
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎓 Auxiliar de Estudos & Simulados (Bilau)")
        self.resize(1120, 780)
        self.setMinimumSize(960, 680)
        log_info("Inicializando interface gráfica principal...", "App")

        self.indexando_ativo = False

        # Inicializa banco de dados se disponível
        try:
            database.inicializar_banco()
        except Exception as e:
            log_aviso(f"Banco de dados não conectado na inicialização: {e}", "App")

        # Configura as Abas Principais
        self.tabs = QTabWidget()
        self.tab_bilau = TabBilauTerminal()
        self.tab_home = TabHome()
        self.tab_arena = TabArena()
        self.tab_guru = TabGuru()
        self.tab_fabriqueiro = TabFabriqueiro()
        self.tab_config = TabConfig()
        self.tab_logs = TabLogs()

        self.tabs.addTab(self.tab_bilau, "⚡ Campo Bilau (Terminal)")
        self.tabs.addTab(self.tab_home, "Fila de Estudos")
        self.tabs.addTab(self.tab_arena, "⚔️ Arena (Simulados)")
        self.tabs.addTab(self.tab_guru, "🧙‍♂️ Guru de Estudos")
        self.tabs.addTab(self.tab_fabriqueiro, "🏭 O Fabriqueiro (Prompts)")
        self.tabs.addTab(self.tab_config, "Configurações")
        self.tabs.addTab(self.tab_logs, "📋 Central de Logs")

        self.setCentralWidget(self.tabs)

        # Inicia Watcher em segundo plano
        self._iniciar_watcher_background()

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

    def _iniciar_watcher_background(self):
        """Inicia o watchdog monitorando a pasta data/entrada em thread background."""
        try:
            pasta_in = Path("data/entrada")
            pasta_proc = Path("data/processados")
            pasta_in.mkdir(parents=True, exist_ok=True)
            pasta_proc.mkdir(parents=True, exist_ok=True)

            handler = IngestaoWatcherHandler(
                pasta_in,
                pasta_proc,
                callback_iniciar=self._ao_iniciar_indexacao,
                callback_concluir=self._ao_concluir_indexacao
            )
            self.observer = Observer()
            self.observer.schedule(handler, str(pasta_in), recursive=False)
            self.observer.start()
            log_sucesso("Watcher de arquivos ativado na pasta 'data/entrada'.", "App")
        except Exception as e:
            log_aviso(f"Não foi possível inicializar o Watcher: {e}", "App")
            self.observer = None

    def _ao_iniciar_indexacao(self):
        """Ativa trava de segurança do Windows API durante vetorização."""
        self.indexando_ativo = True
        bloquear_desligamento_so(int(self.winId()), "Indexando e vetorizando novos arquivos no Auxiliar de Estudos...")

    def _ao_concluir_indexacao(self):
        """Libera trava do Windows após conclusão do processamento."""
        self.indexando_ativo = False
        liberar_desligamento_so(int(self.winId()))

    def _sair_aplicacao(self):
        log_info("Encerrando aplicação definitivamente a pedido do usuário...", "App")
        if hasattr(self, "observer") and self.observer:
            self.observer.stop()
            self.observer.join(timeout=2)
        liberar_desligamento_so(int(self.winId()))
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
        """Trava de segurança: avisa se houver indexação e minimiza para bandeja."""
        if self.indexando_ativo:
            from PyQt6.QtWidgets import QMessageBox
            resp = QMessageBox.question(
                self,
                "Processamento em Andamento",
                "Arquivos ainda estão sendo vetorizados na esteira. O app continuará em segundo plano na bandeja do sistema para não corromper os dados. Deseja minimizar agora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if resp == QMessageBox.StandardButton.No:
                event.ignore()
                return

        if self.tray_icon.isVisible():
            log_info("Janela minimizada para a bandeja do sistema (Tray).", "App")
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