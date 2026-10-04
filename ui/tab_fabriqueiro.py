import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt
from ai_worker import FabriqueiroWorker
from logger import log_info, log_sucesso, log_aviso, log_erro
from credenciais import carregar_gemini_api_key, salvar_gemini_api_key


class TabFabriqueiro(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.lbl_instrucoes = QLabel("✨ <b>O Fabriqueiro</b>: Transforme fotos de lousas e PDFs em Apostilas de Estudo")
        self.lbl_instrucoes.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Campo da chave com botão de salvar e alternar visibilidade
        layout_chave = QHBoxLayout()
        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("Cole sua chave API do Google AI Studio (GEMINI_API_KEY)")
        self.input_key.setEchoMode(QLineEdit.EchoMode.Password)

        # Carrega a chave salva
        chave_salva = carregar_gemini_api_key()
        if chave_salva:
            self.input_key.setText(chave_salva)

        self.btn_toggle_key = QPushButton("👁️")
        self.btn_toggle_key.setFixedWidth(36)
        self.btn_toggle_key.setToolTip("Mostrar/Ocultar chave")
        self.btn_toggle_key.clicked.connect(self._alternar_visibilidade_chave)

        self.btn_salvar_key = QPushButton("💾 Salvar Chave")
        self.btn_salvar_key.setToolTip("Salva sua chave permanentemente para não precisar digitar de novo")
        self.btn_salvar_key.clicked.connect(self._ao_clicar_salvar_chave)

        layout_chave.addWidget(self.input_key)
        layout_chave.addWidget(self.btn_toggle_key)
        layout_chave.addWidget(self.btn_salvar_key)

        self.btn_selecionar = QPushButton("📁 Selecionar Fotos da Lousa ou PDFs de Exercícios")
        self.btn_selecionar.clicked.connect(self.selecionar_arquivo)

        self.lbl_arquivo_selecionado = QLabel("Nenhum arquivo selecionado.")
        self.lbl_arquivo_selecionado.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_gerar = QPushButton("✨ Gerar Apostila da Matéria")
        self.btn_gerar.setStyleSheet("font-weight: bold; padding: 10px; background-color: #007acc; color: white;")
        self.btn_gerar.clicked.connect(self.iniciar_geracao)
        self.btn_gerar.setEnabled(False)

        self.caminhos_midias = []

        layout.addWidget(self.lbl_instrucoes)
        layout.addLayout(layout_chave)
        layout.addWidget(self.btn_selecionar)
        layout.addWidget(self.lbl_arquivo_selecionado)
        layout.addWidget(self.btn_gerar)
        layout.addStretch()

        self.setLayout(layout)

    def _alternar_visibilidade_chave(self):
        if self.input_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🔒")
        else:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁️")

    def _ao_clicar_salvar_chave(self):
        chave = self.input_key.text().strip()
        if not chave:
            QMessageBox.warning(self, "Aviso", "Digite uma chave antes de salvar!")
            return
        salvar_gemini_api_key(chave)
        QMessageBox.information(self, "Chave Salva", "🎉 Sua chave Gemini foi gravada com sucesso! Você não precisará digitá-la novamente.")


    def selecionar_arquivo(self):
        # Permite selecionar múltiplos arquivos (getOpenFileNames no plural)
        caminhos, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar Mídias", "", "Imagens e PDFs (*.png *.jpg *.jpeg *.pdf)"
        )
        if caminhos:
            self.caminhos_midias = caminhos
            qtd = len(caminhos)
            if qtd == 1:
                self.lbl_arquivo_selecionado.setText(f"Arquivo: {os.path.basename(caminhos[0])}")
            else:
                self.lbl_arquivo_selecionado.setText(f"{qtd} arquivos selecionados.")
            self.btn_gerar.setEnabled(True)
            log_info(f"{qtd} arquivo(s) selecionado(s) para o Fabriqueiro.", "Fabriqueiro")

    def iniciar_geracao(self):
        api_key = self.input_key.text().strip()
        if not api_key:
            log_aviso("Tentativa de gerar apostila sem preencher chave API do Gemini.", "Fabriqueiro")
            QMessageBox.warning(self, "Aviso", "Insira a chave API do Gemini!")
            return

        # Salva a chave automaticamente no sistema
        salvar_gemini_api_key(api_key)

        self.btn_gerar.setEnabled(False)
        self.btn_gerar.setText("⏳ Processando IA e Gerando PDF...")

        self.worker = FabriqueiroWorker(self.caminhos_midias, api_key)
        self.worker.progresso.connect(self.ao_atualizar_progresso)
        self.worker.sucesso.connect(self.ao_concluir_sucesso)
        self.worker.erro.connect(self.ao_ocorrer_erro)
        self.worker.start()

    def ao_atualizar_progresso(self, mensagem: str):
        self.btn_gerar.setText(f"⏳ {mensagem}")

    def ao_concluir_sucesso(self, caminho_pdf: str):
        self.btn_gerar.setEnabled(True)
        self.btn_gerar.setText("✨ Gerar Apostila da Matéria")
        
        caminho_abs = os.path.abspath(caminho_pdf)
        pasta_destino = os.path.dirname(caminho_abs)

        msg = QMessageBox(self)
        msg.setWindowTitle("Sucesso")
        msg.setText(f"🎉 <b>Apostila gerada com sucesso na pasta da matéria!</b><br><br>"
                    f"<b>Arquivo:</b> {os.path.basename(caminho_abs)}<br>"
                    f"<b>Local:</b> {pasta_destino}")
        btn_abrir = msg.addButton("📁 Abrir Pasta da Matéria", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        msg.exec()

        if msg.clickedButton() == btn_abrir and os.path.exists(pasta_destino):
            import subprocess
            try:
                os.startfile(pasta_destino)
            except Exception:
                subprocess.Popen(["explorer", pasta_destino])

    def ao_ocorrer_erro(self, mensagem_erro: str):
        self.btn_gerar.setEnabled(True)
        self.btn_gerar.setText("✨ Gerar Apostila da Matéria")
        QMessageBox.critical(self, "Erro no Fabriqueiro", f"Falha ao gerar apostila:\n{mensagem_erro}")