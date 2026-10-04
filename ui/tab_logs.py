import os
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCursor

from logger import (
    log_info, log_sucesso, log_aviso, log_erro,
    obter_ultimos_logs, limpar_logs, caminho_arquivo_log,
    registrar_qt_listener
)


class TabLogs(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 1. Barra Superior com Título e Status
        barra_topo = QHBoxLayout()
        lbl_titulo = QLabel("📋 <b>Central de Logs & Diagnóstico</b>")
        lbl_titulo.setStyleSheet("font-size: 16px; color: #0d47a1;")

        lbl_caminho = QLabel(f"Arquivo: <code>{os.path.basename(caminho_arquivo_log())}</code>")
        lbl_caminho.setStyleSheet("color: #666; font-size: 11px;")

        barra_topo.addWidget(lbl_titulo)
        barra_topo.addSpacing(10)
        barra_topo.addWidget(lbl_caminho)
        barra_topo.addStretch()

        layout.addLayout(barra_topo)

        # 2. Barra de Ferramentas / Filtros
        barra_acoes = QHBoxLayout()

        self.filtro_combo = QComboBox()
        self.filtro_combo.addItems([
            "🔍 Todos os Níveis",
            "❌ Apenas Erros",
            "✅ Apenas Sucessos",
            "⚠️ Apenas Avisos",
            "ℹ️ Apenas Informações"
        ])
        self.filtro_combo.currentIndexChanged.connect(self.carregar_logs)

        btn_atualizar = QPushButton("🔄 Atualizar")
        btn_atualizar.setToolTip("Recarregar logs do arquivo")
        btn_atualizar.clicked.connect(self.carregar_logs)

        btn_abrir_log = QPushButton("📝 Abrir no Bloco de Notas")
        btn_abrir_log.setToolTip("Abrir o arquivo app.log no editor padrão")
        btn_abrir_log.clicked.connect(self.abrir_arquivo_externo)

        btn_abrir_pasta = QPushButton("📁 Abrir Pasta")
        btn_abrir_pasta.setToolTip("Abrir a pasta onde o log está salvo")
        btn_abrir_pasta.clicked.connect(self.abrir_pasta)

        btn_limpar = QPushButton("🧹 Limpar Logs")
        btn_limpar.setToolTip("Zerar o arquivo de log atual")
        btn_limpar.clicked.connect(self.ao_limpar_logs)

        btn_teste = QPushButton("🧪 Testar Logger")
        btn_teste.setToolTip("Gera logs de teste (sucesso, aviso e erro) para conferência")
        btn_teste.clicked.connect(self.gerar_log_teste)

        barra_acoes.addWidget(QLabel("Filtrar:"))
        barra_acoes.addWidget(self.filtro_combo)
        barra_acoes.addWidget(btn_atualizar)
        barra_acoes.addWidget(btn_teste)
        barra_acoes.addStretch()
        barra_acoes.addWidget(btn_abrir_log)
        barra_acoes.addWidget(btn_abrir_pasta)
        barra_acoes.addWidget(btn_limpar)

        layout.addLayout(barra_acoes)

        # 3. Área de Texto dos Logs (Console Visual)
        self.texto_logs = QTextEdit()
        self.texto_logs.setReadOnly(True)
        self.texto_logs.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.texto_logs)

        # 4. Rodapé Informativo
        self.lbl_status = QLabel("Pronto para monitorar o sistema.")
        self.lbl_status.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # Registra o listener para receber logs em tempo real
        registrar_qt_listener(self.ao_receber_novo_log)

        # Carrega o histórico de logs ao abrir
        self.carregar_logs()

    def _colorir_linha(self, linha: str) -> str:
        """Formata uma linha de texto de log com tags HTML coloridas."""
        linha_escapada = (
            linha.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
        )

        if "❌ [ERRO]" in linha_escapada or "🚨 [CRÍTICO]" in linha_escapada:
            return f'<span style="color: #ff5252; font-weight: bold;">{linha_escapada}</span>'
        elif "✅ [SUCESSO]" in linha_escapada:
            return f'<span style="color: #4caf50; font-weight: bold;">{linha_escapada}</span>'
        elif "⚠️ [AVISO]" in linha_escapada:
            return f'<span style="color: #ffb74d;">{linha_escapada}</span>'
        elif "ℹ️ [INFO]" in linha_escapada:
            return f'<span style="color: #64b5f6;">{linha_escapada}</span>'
        elif "🔍 [DEBUG]" in linha_escapada:
            return f'<span style="color: #9e9e9e;">{linha_escapada}</span>'
        else:
            return f'<span style="color: #cfd8dc;">{linha_escapada}</span>'

    def carregar_logs(self):
        """Recarrega os logs do arquivo app.log aplicando o filtro selecionado."""
        texto_bruto = obter_ultimos_logs(max_linhas=300)
        linhas = texto_bruto.splitlines()

        filtro = self.filtro_combo.currentText()
        linhas_filtradas = []

        for linha in linhas:
            if "Apenas Erros" in filtro:
                if "❌ [ERRO]" not in linha and "🚨 [CRÍTICO]" not in linha:
                    continue
            elif "Apenas Sucessos" in filtro:
                if "✅ [SUCESSO]" not in linha:
                    continue
            elif "Apenas Avisos" in filtro:
                if "⚠️ [AVISO]" not in linha:
                    continue
            elif "Apenas Informações" in filtro:
                if "ℹ️ [INFO]" not in linha:
                    continue
            linhas_filtradas.append(linha)

        if not linhas_filtradas:
            html = '<span style="color: #888;">Nenhum registro encontrado para este filtro.</span>'
        else:
            html = "<br>".join(self._colorir_linha(l) for l in linhas_filtradas)

        self.texto_logs.setHtml(html)
        self.texto_logs.moveCursor(QTextCursor.MoveOperation.End)
        self.lbl_status.setText(f"Exibindo {len(linhas_filtradas)} registro(s) de log.")

    def ao_receber_novo_log(self, hora: str, nivel: str, modulo: str, mensagem: str):
        """Callback acionado sempre que um novo log é emitido no sistema."""
        # Se estivermos com o filtro geral ou compatível, adiciona dinamicamente
        filtro = self.filtro_combo.currentText()
        if (
            "Todos" in filtro or
            ("Erros" in filtro and nivel == "ERRO") or
            ("Sucessos" in filtro and nivel == "SUCESSO") or
            ("Avisos" in filtro and nivel == "AVISO") or
            ("Informações" in filtro and nivel == "INFO")
        ):
            icones = {
                "ERRO": "❌ [ERRO]",
                "SUCESSO": "✅ [SUCESSO]",
                "AVISO": "⚠️ [AVISO]",
                "INFO": "ℹ️ [INFO]"
            }
            tag = icones.get(nivel, f"[{nivel}]")
            linha = f"[{hora}] {tag} [{modulo}] {mensagem}"
            linha_html = self._colorir_linha(linha)
            self.texto_logs.append(linha_html)
            self.texto_logs.moveCursor(QTextCursor.MoveOperation.End)
            self.lbl_status.setText(f"Última atividade: [{hora}] {tag} {mensagem[:60]}...")

    def abrir_arquivo_externo(self):
        caminho = caminho_arquivo_log()
        if os.path.exists(caminho):
            try:
                os.startfile(caminho)
            except Exception:
                subprocess.Popen(["notepad.exe", caminho])
        else:
            QMessageBox.warning(self, "Aviso", "O arquivo app.log ainda não foi gerado.")

    def abrir_pasta(self):
        pasta = os.path.dirname(caminho_arquivo_log())
        if os.path.exists(pasta):
            try:
                os.startfile(pasta)
            except Exception:
                subprocess.Popen(["explorer", pasta])

    def ao_limpar_logs(self):
        resp = QMessageBox.question(
            self, "Limpar Logs",
            "Deseja realmente limpar o histórico do arquivo app.log?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            limpar_logs()
            self.carregar_logs()

    def gerar_log_teste(self):
        """Dispara mensagens de teste de diferentes níveis para testar o funcionamento."""
        log_info("Teste de rotina do sistema executado com sucesso.", "TesteLogger")
        log_sucesso("Teste de operação bem-sucedida: todos os módulos estão online!", "TesteLogger")
        log_aviso("Teste de aviso: o modelo local está em modo econômico.", "TesteLogger")
        try:
            # Simula um erro proposital para demonstrar o registro de erro
            1 / 0
        except ZeroDivisionError as e:
            log_erro("Teste de captura de erro: divisão por zero simulada com sucesso.", "TesteLogger", exc=e)
        self.carregar_logs()
