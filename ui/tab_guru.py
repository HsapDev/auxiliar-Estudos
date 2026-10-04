import json
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QScrollArea, QFrame, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer

from ollama_client import (
    verificar_ollama_online,
    listar_modelos_locais,
    GuruChatWorker,
    OllamaPullWorker
)
from credenciais import carregar_gemini_api_key, salvar_gemini_api_key


class TabGuru(QWidget):
    def __init__(self):
        super().__init__()

        self.historico_mensagens = []  # [{"role": "user"|"assistant", "content": "..."}]
        self.worker_chat = None
        self.worker_pull = None
        self.msg_guru_atual_widget = None

        layout_externo = QVBoxLayout(self)

        # 1. Barra de Conexão e Seleção de Contexto
        barra_status = QHBoxLayout()

        self.lbl_guru_icone = QLabel("🧙‍♂️ <b>Guru de Estudos</b>")
        self.lbl_guru_icone.setStyleSheet("font-size: 16px; color: #4a148c;")

        # Status do Ollama
        self.lbl_status_ollama = QLabel("🔴 Verificando Ollama...")
        self.lbl_status_ollama.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px;")

        self.btn_reconectar = QPushButton("🔄 Checar Ollama")
        self.btn_reconectar.clicked.connect(self.verificar_servico_ollama)

        barra_status.addWidget(self.lbl_guru_icone)
        barra_status.addSpacing(10)
        barra_status.addWidget(self.lbl_status_ollama)
        barra_status.addWidget(self.btn_reconectar)
        barra_status.addStretch()

        # Seletores
        barra_status.addWidget(QLabel("Matéria Ativa:"))
        self.combo_materia = QComboBox()
        self.combo_materia.setMinimumWidth(160)
        barra_status.addWidget(self.combo_materia)

        barra_status.addWidget(QLabel("Modelo Local:"))
        self.combo_modelo = QComboBox()
        self.combo_modelo.setMinimumWidth(160)
        barra_status.addWidget(self.combo_modelo)

        self.btn_baixar_modelo = QPushButton("📥 Baixar Modelo Leve")
        self.btn_baixar_modelo.setToolTip("Baixa modelos leves otimizados para evitar erros de memória RAM (std::bad_alloc)")
        self.btn_baixar_modelo.clicked.connect(self.solicitar_download_modelo)
        barra_status.addWidget(self.btn_baixar_modelo)

        layout_externo.addLayout(barra_status)

        # 2. Área de Histórico de Conversa (Chat)
        self.scroll_chat = QScrollArea()
        self.scroll_chat.setWidgetResizable(True)
        self.container_mensagens = QWidget()
        self.layout_mensagens = QVBoxLayout(self.container_mensagens)
        self.layout_mensagens.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_mensagens.setSpacing(12)

        self.scroll_chat.setWidget(self.container_mensagens)
        layout_externo.addWidget(self.scroll_chat)

        # 3. Barra de Digitação
        barra_envio = QHBoxLayout()

        self.input_pergunta = QLineEdit()
        self.input_pergunta.setPlaceholderText("Tire uma dúvida com o Guru (ex: 'Não entendi por que o inverso modular deu 15')...")
        self.input_pergunta.setStyleSheet("padding: 10px; font-size: 14px; border-radius: 6px; border: 1px solid #ccc;")
        self.input_pergunta.returnPressed.connect(self.enviar_pergunta)

        self.btn_enviar = QPushButton("💬 Enviar")
        self.btn_enviar.setStyleSheet("background-color: #6a1b9a; color: white; font-weight: bold; padding: 10px 18px; border-radius: 6px;")
        self.btn_enviar.clicked.connect(self.enviar_pergunta)

        self.btn_limpar_chat = QPushButton("🧹 Limpar")
        self.btn_limpar_chat.setToolTip("Limpar histórico da conversa")
        self.btn_limpar_chat.clicked.connect(self.limpar_chat)

        barra_envio.addWidget(self.input_pergunta)
        barra_envio.addWidget(self.btn_enviar)
        barra_envio.addWidget(self.btn_limpar_chat)
        layout_externo.addLayout(barra_envio)

        self.carregar_materias()
        self.verificar_servico_ollama()
        self._adicionar_mensagem_boas_vindas()

    def carregar_materias(self):
        self.combo_materia.clear()
        materias = set()

        if os.path.exists("materias.json"):
            try:
                with open("materias.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    for k in cfg.get("palavras_chave", {}).keys():
                        materias.add(k)
            except Exception:
                pass

        if os.path.exists("conhecimento_materia.json"):
            try:
                with open("conhecimento_materia.json", "r", encoding="utf-8") as f:
                    d = json.load(f)
                    mat = d.get("materia")
                    if mat:
                        materias.add(mat)
            except Exception:
                pass

        if not materias:
            materias.add("Matematica_Discreta")

        for m in sorted(materias):
            self.combo_materia.addItem(m)

    def verificar_servico_ollama(self):
        """Verifica se o Ollama está rodando e atualiza a lista de modelos."""
        online = verificar_ollama_online(timeout=1.5)
        modelo_anterior = self.combo_modelo.currentText()
        self.combo_modelo.clear()

        # Sempre disponibiliza o fallback da nuvem (ótimo para computadores com pouca RAM)
        self.combo_modelo.addItem("Gemini Flash (Nuvem - 0 MB RAM)")

        if online:
            self.lbl_status_ollama.setText("🟢 Ollama Online")
            self.lbl_status_ollama.setStyleSheet("background-color: #e8f5e9; color: #2e7d32; font-weight: bold; padding: 4px 8px; border-radius: 4px;")
            self.btn_enviar.setEnabled(True)
            self.btn_baixar_modelo.setEnabled(True)

            modelos = listar_modelos_locais()
            if modelos:
                for mod in modelos:
                    self.combo_modelo.addItem(mod)

                itens = [self.combo_modelo.itemText(i) for i in range(self.combo_modelo.count())]
                if modelo_anterior in itens:
                    self.combo_modelo.setCurrentText(modelo_anterior)
                elif "llama3.2:1b" in modelos:
                    self.combo_modelo.setCurrentText("llama3.2:1b")
                elif "llama3.2:latest" in modelos or "llama3.2" in modelos:
                    self.combo_modelo.setCurrentText("llama3.2:latest" if "llama3.2:latest" in modelos else "llama3.2")
        else:
            self.lbl_status_ollama.setText("🔴 Ollama Offline")
            self.lbl_status_ollama.setStyleSheet("background-color: #ffebee; color: #c62828; font-weight: bold; padding: 4px 8px; border-radius: 4px;")
            self.combo_modelo.addItem("llama3.2:1b")
            self.combo_modelo.addItem("qwen2.5:1.5b")

    def _adicionar_mensagem_boas_vindas(self):
        msg = (
            "Olá! Sou seu <b>Guru de Estudos</b> pessoal. 🧠<br><br>"
            "Quando você me faz uma pergunta, eu analiso automaticamente:<br>"
            "• As fórmulas e alertas da sua matéria selecionada.<br>"
            "• Os erros que você cometeu na <b>Arena de Questões</b> para te ajudar a não cair nas mesmas pegadinhas.<br>"
            "• Suas preferências de estudo (direto ao ponto e sem enrolação).<br><br>"
            "<i>Como posso te ajudar hoje?</i>"
        )
        self._renderizar_bolha("assistant", msg)

    def _renderizar_bolha(self, role: str, texto: str) -> QLabel:
        """Cria e adiciona uma bolha estilizada ao chat."""
        layout_linha = QHBoxLayout()

        lbl_bolha = QLabel(texto)
        lbl_bolha.setWordWrap(True)
        lbl_bolha.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if role == "user":
            layout_linha.addStretch()
            lbl_bolha.setStyleSheet("""
                background-color: #e3f2fd;
                color: #0d47a1;
                border: 1px solid #bbdefb;
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 13px;
                max-width: 550px;
            """)
            layout_linha.addWidget(lbl_bolha)
        else:
            lbl_bolha.setStyleSheet("""
                background-color: #f3e5f5;
                color: #4a148c;
                border: 1px solid #e1bee7;
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 13px;
                max-width: 580px;
            """)
            layout_linha.addWidget(lbl_bolha)
            layout_linha.addStretch()

        self.layout_mensagens.addLayout(layout_linha)
        QTimer.singleShot(50, self._rolar_para_fim)
        return lbl_bolha

    def _rolar_para_fim(self):
        barra = self.scroll_chat.verticalScrollBar()
        barra.setValue(barra.maximum())

    def enviar_pergunta(self):
        texto = self.input_pergunta.text().strip()
        if not texto:
            return

        gemini_key = carregar_gemini_api_key()
        ollama_online = verificar_ollama_online(timeout=1.0)
        modelo_selecionado = self.combo_modelo.currentText()
        is_nuvem = "gemini" in modelo_selecionado.lower() or "nuvem" in modelo_selecionado.lower()

        if is_nuvem:
            if not gemini_key:
                chave, ok = QInputDialog.getText(
                    self, "Chave API do Gemini",
                    "Para usar o modelo em nuvem (0 MB de RAM), insira sua chave gratuita do Google AI Studio:\n(Ela será salva permanentemente)",
                    QLineEdit.EchoMode.Password
                )
                if ok and chave.strip():
                    gemini_key = chave.strip()
                    salvar_gemini_api_key(gemini_key)
                else:
                    QMessageBox.warning(self, "Chave necessária", "A chave API do Gemini é necessária para usar o modelo em nuvem.")
                    return
            modelo = "gemini-3.5-flash-lite"
        else:
            if not ollama_online and not gemini_key:
                QMessageBox.warning(
                    self, "Ollama Offline",
                    "O servidor do Ollama não está ativo no momento.\n\n"
                    "Para usar o modelo local:\n"
                    "1. Inicie o Ollama no Windows (menu Iniciar ou comando: ollama serve)\n"
                    "2. Em seguida clique em 'Checar Ollama'.\n\n"
                    "(Dica: Você também pode selecionar 'Gemini Flash (Nuvem - 0 MB RAM)' no seletor de modelos acima!)."
                )
                return
            modelo = modelo_selecionado or "llama3.2:1b"

        materia = self.combo_materia.currentText() or "Geral"

        # Adiciona mensagem do usuário na tela e no histórico
        self._renderizar_bolha("user", f"<b>Você:</b><br>{texto}")
        self.historico_mensagens.append({"role": "user", "content": texto})
        self.input_pergunta.clear()

        # Prepara a bolha de resposta do Guru
        self.msg_guru_atual_widget = self._renderizar_bolha("assistant", "<b>Guru:</b><br><i>Pensando e consultando seu histórico...</i>")
        self.texto_parcial_guru = ""

        self.btn_enviar.setEnabled(False)
        self.input_pergunta.setEnabled(False)

        # Inicia a thread de comunicação com o Ollama / fallback
        self.worker_chat = GuruChatWorker(
            modelo=modelo,
            materia=materia,
            historico=self.historico_mensagens[:-1],
            pergunta=texto,
            api_key_gemini=gemini_key
        )
        self.worker_chat.resposta_parcial.connect(self._ao_receber_chunk)
        self.worker_chat.resposta_completa.connect(self._ao_concluir_resposta)
        self.worker_chat.erro.connect(self._ao_ocorrer_erro)
        self.worker_chat.start()

    def _ao_receber_chunk(self, chunk: str):
        self.texto_parcial_guru += chunk
        # Formata quebras de linha simples
        texto_formatado = self.texto_parcial_guru.replace("\n", "<br>")
        if self.msg_guru_atual_widget:
            self.msg_guru_atual_widget.setText(f"<b>Guru:</b><br>{texto_formatado}")
        self._rolar_para_fim()

    def _ao_concluir_resposta(self, resposta_completa: str):
        self.historico_mensagens.append({"role": "assistant", "content": resposta_completa})
        self.btn_enviar.setEnabled(True)
        self.input_pergunta.setEnabled(True)
        self.input_pergunta.setFocus()
        self._rolar_para_fim()

    def _ao_ocorrer_erro(self, msg_erro: str):
        if self.msg_guru_atual_widget:
            self.msg_guru_atual_widget.setText(f"<b>Guru:</b><br><span style='color: #c62828;'>⚠️ {msg_erro}</span>")
        self.btn_enviar.setEnabled(True)
        self.input_pergunta.setEnabled(True)
        self.input_pergunta.setFocus()

    def solicitar_download_modelo(self):
        """Baixa modelos leves otimizados para evitar erros de memória RAM (std::bad_alloc)."""
        if not verificar_ollama_online(timeout=1.0):
            QMessageBox.warning(self, "Ollama Offline", "O Ollama precisa estar em execução para baixar modelos!")
            return

        opcoes = [
            "llama3.2:1b (1.3 GB - Ultraleve Meta, ideal para notebooks)",
            "qwen2.5:1.5b (986 MB - Rápido, leve e excelente em exatas)",
            "qwen2.5:0.5b (398 MB - Micro, roda em qualquer computador)",
            "llama3.2:latest (2.0 GB - Requer mais de 3GB de RAM livre)"
        ]

        item, ok = QInputDialog.getItem(
            self, "Baixar Modelo no Ollama",
            "Escolha um modelo leve compatível com a memória do seu computador:\n(Modelos 1B / 1.5B evitam erro de memória std::bad_alloc)",
            opcoes, 0, False
        )
        if not ok or not item:
            return

        modelo = item.split(" ")[0].strip()
        self.btn_baixar_modelo.setEnabled(False)
        self.btn_baixar_modelo.setText(f"⏳ Baixando {modelo}...")

        self.worker_pull = OllamaPullWorker(modelo)
        self.worker_pull.progresso.connect(self._ao_progresso_pull)
        self.worker_pull.concluido.connect(self._ao_concluir_pull)
        self.worker_pull.erro.connect(self._ao_erro_pull)
        self.worker_pull.start()

    def _ao_progresso_pull(self, status: str):
        self.btn_baixar_modelo.setText(f"⏳ {status}")

    def _ao_concluir_pull(self, modelo: str):
        self.btn_baixar_modelo.setEnabled(True)
        self.btn_baixar_modelo.setText(f"✅ {modelo} Instalado")
        self.verificar_servico_ollama()
        QMessageBox.information(self, "Sucesso", f"O modelo '{modelo}' foi instalado no Ollama local com sucesso!")

    def _ao_erro_pull(self, erro_msg: str):
        self.btn_baixar_modelo.setEnabled(True)
        self.btn_baixar_modelo.setText("📥 Baixar Modelo Leve")
        QMessageBox.critical(self, "Erro ao Baixar", f"Falha ao baixar modelo no Ollama:\n{erro_msg}")

    def limpar_chat(self):
        self.historico_mensagens = []
        while self.layout_mensagens.count():
            item = self.layout_mensagens.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._adicionar_mensagem_boas_vindas()
