import html
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor

from bilau_chat import BilauWorker
import database
from logger import log_info, log_sucesso, log_aviso, log_erro


class TabBilauTerminal(QWidget):
    """Interface do Chat Terminal ('Campo Bilau') com visual terminal e streaming."""

    def __init__(self):
        super().__init__()
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Barra Superior de Status
        barra_status = QHBoxLayout()
        lbl_titulo = QLabel("⚡ <b>Terminal Bilau</b> | <i>Ollama (Qwen 2.5 3B) + PostgreSQL pgvector</i>")
        lbl_titulo.setStyleSheet("font-size: 14px; color: #0284c7;")
        barra_status.addWidget(lbl_titulo)
        barra_status.addStretch()

        btn_status_db = QPushButton("📊 Status Banco")
        btn_status_db.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        btn_status_db.clicked.connect(self._verificar_status_banco)
        barra_status.addWidget(btn_status_db)

        btn_limpar = QPushButton("🧹 Limpar")
        btn_limpar.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        btn_limpar.clicked.connect(self._limpar_terminal)
        barra_status.addWidget(btn_limpar)

        layout.addLayout(barra_status)

        # Área de Exibição estilo Terminal (Fundo escuro, fonte mono)
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        fonte_mono = QFont("Consolas", 11)
        fonte_mono.setStyleHint(QFont.StyleHint.Monospace)
        self.terminal_output.setFont(fonte_mono)
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 12px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.terminal_output)

        # Linha de Entrada ("Campo Bilau")
        frame_input = QFrame()
        frame_input.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px 8px;
            }
        """)
        layout_input = QHBoxLayout(frame_input)
        layout_input.setContentsMargins(4, 2, 4, 2)

        lbl_prompt = QLabel("bilau:~$")
        lbl_prompt.setFont(fonte_mono)
        lbl_prompt.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        layout_input.addWidget(lbl_prompt)

        self.input_campo = QLineEdit()
        self.input_campo.setFont(fonte_mono)
        self.input_campo.setPlaceholderText("como eu resolvo essa questão da lista daquela cachorra...")
        self.input_campo.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #f8fafc;
                font-size: 13px;
                padding: 6px;
            }
        """)
        self.input_campo.returnPressed.connect(self._enviar_pergunta)
        layout_input.addWidget(self.input_campo)

        self.btn_enviar = QPushButton("Enviar (Enter)")
        self.btn_enviar.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_enviar.clicked.connect(self._enviar_pergunta)
        layout_input.addWidget(self.btn_enviar)

        layout.addWidget(frame_input)

        # Mensagem inicial de boas-vindas no terminal
        self._imprimir_sistema(
            "=== BILAU STUDY AGENT [Terminal Ativo] ===\n"
            "Conectado à esteira de ingestão local (data/entrada/ -> data/processados/).\n"
            "Mapeamento de gírias e apelidos ativo via tabela 'contextos_professores'.\n"
            "Digite sua dúvida abaixo ou arraste arquivos para a pasta de entrada."
        )

    def _imprimir_sistema(self, texto: str):
        self.terminal_output.append(f"<span style='color: #64748b;'>{html.escape(texto)}</span><br>")
        self._scroll_para_fim()

    def _imprimir_usuario(self, texto: str):
        self.terminal_output.append(f"<b style='color: #38bdf8;'>aluno:~$</b> <span style='color: #f8fafc;'>{html.escape(texto)}</span><br>")
        self._scroll_para_fim()

    def _scroll_para_fim(self):
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.terminal_output.setTextCursor(cursor)

    def _limpar_terminal(self):
        self.terminal_output.clear()
        self._imprimir_sistema("Terminal limpo.")

    def _verificar_status_banco(self):
        self._imprimir_sistema("--- Verificando PostgreSQL & pgvector ---")
        try:
            conn = database.obter_conexao()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM conteudos_rag;")
                total_chunks = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM materias;")
                total_materias = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM contextos_professores;")
                total_apelidos = cur.fetchone()[0]
            conn.close()
            self._imprimir_sistema(
                f"✅ PostgreSQL Conectado com sucesso!\n"
                f"• Matérias cadastradas: {total_materias}\n"
                f"• Chunks RAG vetorizados: {total_chunks}\n"
                f"• Apelidos de professores: {total_apelidos}"
            )
        except Exception as e:
            self._imprimir_sistema(f"❌ Banco offline ou não configurado: {e}\n(Verifique as instruções em pendencias.txt)")

    def _enviar_pergunta(self):
        texto = self.input_campo.text().strip()
        if not texto:
            return

        self.input_campo.clear()
        self._imprimir_usuario(texto)

        # Inicia resposta do Bilau
        self.terminal_output.append("<b style='color: #4ade80;'>bilau:~$ </b>")
        self._scroll_para_fim()

        self.input_campo.setEnabled(False)
        self.btn_enviar.setEnabled(False)

        self.worker = BilauWorker(pergunta=texto)
        self.worker.token_recebido.connect(self._ao_receber_token)
        self.worker.finalizado.connect(self._ao_finalizar)
        self.worker.erro.connect(self._ao_erro)
        self.worker.start()

    def _ao_receber_token(self, token: str):
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self.terminal_output.setTextCursor(cursor)

    def _ao_finalizar(self, resposta_completa: str):
        self.terminal_output.append("<br>")
        self._scroll_para_fim()
        self.input_campo.setEnabled(True)
        self.btn_enviar.setEnabled(True)
        self.input_campo.setFocus()

    def _ao_erro(self, msg_erro: str):
        self.terminal_output.append(f"<br><span style='color: #ef4444;'>[ERRO]: {html.escape(msg_erro)}</span><br>")
        self._scroll_para_fim()
        self.input_campo.setEnabled(True)
        self.btn_enviar.setEnabled(True)
        self.input_campo.setFocus()
