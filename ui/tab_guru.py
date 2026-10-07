import json
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QScrollArea, QFrame, QMessageBox,
    QTabWidget, QFileDialog, QListWidget, QListWidgetItem, QSplitter,
    QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
import pypdf

import banco_questoes
import resumos_manager
from ollama_client import (
    GuruChatWorker,
    listar_materias_com_conhecimento,
    carregar_conhecimento_materia,
    carregar_erros_recentes
)
from credenciais import carregar_gemini_api_key
from logger import log_info, log_sucesso, log_aviso, log_erro


class TabGuru(QWidget):
    def __init__(self):
        super().__init__()

        self.historico_mensagens = []
        self.worker_chat = None
        self.questao_quiz_em_andamento = None  # Para responder questões dentro do chat!

        # Estado do Visualizador Nativo de PDF (Renderização Gráfica Real)
        self.pdf_doc = QPdfDocument(self)
        self.pdf_view = None
        self.caminho_pdf_atual = None
        self.pagina_atual = 0
        self.total_paginas = 0
        self.comentarios_doc = []  # [{"pagina": int, "comentario": str}]

        layout_externo = QVBoxLayout(self)

        # Abas Internas do Guru
        self.tabs_guru = QTabWidget()
        layout_externo.addWidget(self.tabs_guru)

        # 1. Aba Chat Tutor Interativo
        self.tab_chat = self._criar_aba_chat()
        self.tabs_guru.addTab(self.tab_chat, "💬 Chat Tutor de Estudos (Conversa)")

        # 2. Aba Leitor & Anotador de PDF
        self.tab_pdf = self._criar_aba_pdf()
        self.tabs_guru.addTab(self.tab_pdf, "📄 Anotador de PDF & Gerador de Resumo")

        self.atualizar_materias()
        self._adicionar_mensagem_boas_vindas()

    # =========================================================================
    # ABA 1: CHAT TUTOR INTERATIVO
    # =========================================================================
    def _criar_aba_chat(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Barra Superior de Contexto
        barra_status = QHBoxLayout()
        self.lbl_guru_icone = QLabel("🧙‍♂️ <b>Tutor de Estudos</b>")
        self.lbl_guru_icone.setStyleSheet("font-size: 15px; color: #4a148c;")

        self.cb_modo_local = QCheckBox("Modo Local (100% Offline / Sem Falhas)")
        self.cb_modo_local.setChecked(True)
        self.cb_modo_local.setStyleSheet("font-weight: bold; color: #1b5e20;")
        self.cb_modo_local.setToolTip("Responde instantaneamente usando suas matérias, anotações de PDF e questões sem depender de internet ou IA externa")

        barra_status.addWidget(self.lbl_guru_icone)
        barra_status.addWidget(self.cb_modo_local)
        barra_status.addStretch()

        barra_status.addWidget(QLabel("Matéria Ativa:"))
        self.combo_materia = QComboBox()
        self.combo_materia.setMinimumWidth(180)
        self.combo_materia.currentIndexChanged.connect(self._ao_trocar_materia_chat)
        barra_status.addWidget(self.combo_materia)

        layout.addLayout(barra_status)

        # Botões de Ações Rápidas no Chat (Pills Modernas)
        layout_acoes_rapidas = QHBoxLayout()
        layout_acoes_rapidas.addWidget(QLabel("<b>Ações Rápidas:</b>"))

        btn_chip_style = """
            QPushButton {
                font-size: 12px;
                font-weight: 600;
                padding: 6px 14px;
                border-radius: 14px;
                border: 1.5px solid #e2e8f0;
                background-color: #ffffff;
                color: #334155;
            }
            QPushButton:hover {
                background-color: #eef2ff;
                border-color: #818cf8;
                color: #4338ca;
            }
        """

        btn_acao_questao = QPushButton("🎯 Questão no Chat")
        btn_acao_questao.setStyleSheet(btn_chip_style)
        btn_acao_questao.clicked.connect(lambda: self._disparar_acao_chat("1"))

        btn_acao_resumo = QPushButton("📖 Ver Meu Resumo / PDF")
        btn_acao_resumo.setStyleSheet(btn_chip_style)
        btn_acao_resumo.clicked.connect(lambda: self._disparar_acao_chat("2"))

        btn_acao_erros = QPushButton("❌ Revisar Erros da Arena")
        btn_acao_erros.setStyleSheet(btn_chip_style)
        btn_acao_erros.clicked.connect(lambda: self._disparar_acao_chat("3"))

        btn_acao_formulas = QPushButton("📐 Fórmulas da Matéria")
        btn_acao_formulas.setStyleSheet(btn_chip_style)
        btn_acao_formulas.clicked.connect(lambda: self._disparar_acao_chat("4"))

        layout_acoes_rapidas.addWidget(btn_acao_questao)
        layout_acoes_rapidas.addWidget(btn_acao_resumo)
        layout_acoes_rapidas.addWidget(btn_acao_erros)
        layout_acoes_rapidas.addWidget(btn_acao_formulas)
        layout_acoes_rapidas.addStretch()
        layout.addLayout(layout_acoes_rapidas)

        # Área de Mensagens (Scroll)
        self.scroll_chat = QScrollArea()
        self.scroll_chat.setWidgetResizable(True)
        self.container_mensagens = QWidget()
        self.layout_mensagens = QVBoxLayout(self.container_mensagens)
        self.layout_mensagens.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_mensagens.setSpacing(10)
        self.scroll_chat.setWidget(self.container_mensagens)
        layout.addWidget(self.scroll_chat)

        # Barra de Envio
        barra_envio = QHBoxLayout()
        self.input_pergunta = QLineEdit()
        self.input_pergunta.setPlaceholderText("Converse com o Tutor (digite 1, 2, 3, 4 ou uma dúvida / palavra-chave como 'equivalência', 'hasse')...")
        self.input_pergunta.setStyleSheet("padding: 10px; font-size: 13px; border-radius: 6px; border: 1px solid #ccc;")
        self.input_pergunta.returnPressed.connect(self.enviar_pergunta)

        self.btn_enviar = QPushButton("💬 Enviar")
        self.btn_enviar.setStyleSheet("background-color: #6a1b9a; color: white; font-weight: bold; padding: 10px 18px; border-radius: 6px;")
        self.btn_enviar.clicked.connect(self.enviar_pergunta)

        self.btn_limpar_chat = QPushButton("🧹 Limpar")
        self.btn_limpar_chat.clicked.connect(self.limpar_chat)

        barra_envio.addWidget(self.input_pergunta)
        barra_envio.addWidget(self.btn_enviar)
        barra_envio.addWidget(self.btn_limpar_chat)
        layout.addLayout(barra_envio)

        return widget

    def atualizar_materias(self):
        mat_anterior = self.combo_materia.currentText()
        self.combo_materia.blockSignals(True)
        self.combo_materia.clear()

        materias = banco_questoes.obter_todas_materias()
        if not materias:
            materias = listar_materias_com_conhecimento()
        if not materias:
            materias = ["Matemática Discreta"]

        for m in materias:
            self.combo_materia.addItem(m)

        if mat_anterior:
            self.combo_materia.setCurrentText(mat_anterior)
        self.combo_materia.blockSignals(False)

        # Atualiza também na aba PDF
        if hasattr(self, "combo_pdf_materia"):
            self.combo_pdf_materia.blockSignals(True)
            self.combo_pdf_materia.clear()
            for m in materias:
                self.combo_pdf_materia.addItem(m)
            self.combo_pdf_materia.blockSignals(False)

    def _ao_trocar_materia_chat(self):
        self.questao_quiz_em_andamento = None

    def _adicionar_mensagem_boas_vindas(self):
        msg = (
            "Olá! Sou seu <b>Tutor de Estudos Pessoal</b> 🎓<br><br>"
            "Agora você pode estudar de forma conversacional <b>sem depender de IA</b> ou lentidão!<br>"
            "Eu uso seus próprios dados: anotações dos PDFs, banco de questões e histórico da Arena.<br><br>"
            "<b>O que gostaria de fazer agora?</b><br>"
            "• Digite <b>1</b>: Resolver uma questão rápida aqui mesmo no chat.<br>"
            "• Digite <b>2</b>: Ler meus resumos e comentários de PDF salvos.<br>"
            "• Digite <b>3</b>: Revisar os erros recentes que cometi na Arena.<br>"
            "• Digite <b>4</b>: Consultar fórmulas e conceitos da matéria ativa.<br>"
            "<i>(Ou simplesmente digite o nome de um tópico/termo para pesquisar!)</i>"
        )
        self._renderizar_bolha("assistant", msg)

    def _disparar_acao_chat(self, codigo: str):
        self.input_pergunta.setText(codigo)
        self.enviar_pergunta()

    def enviar_pergunta(self):
        texto = self.input_pergunta.text().strip()
        if not texto:
            return

        self.input_pergunta.clear()
        self._renderizar_bolha("user", texto)

        # 1. Se estiver no Modo Local (Sem IA)
        if self.cb_modo_local.isChecked():
            self._processar_resposta_local(texto)
            return

        # 2. Modo IA (Gemini Cloud)
        chave = carregar_gemini_api_key()
        if not chave:
            self._renderizar_bolha(
                "assistant",
                "⚠️ Para usar o modo Gemini Cloud, você precisa cadastrar sua API Key nas Configurações ou no Fabriqueiro.<br>"
                "Ative o <b>Modo Local (100% Offline)</b> para usar o tutor sem precisar de chave!"
            )
            return

        materia = self.combo_materia.currentText()
        self.historico_mensagens.append({"role": "user", "content": texto})
        self.btn_enviar.setEnabled(False)
        self.input_pergunta.setEnabled(False)

        lbl_espera = self._renderizar_bolha("assistant", "⏳ <i>Consultando Gemini...</i>")

        self.worker_chat = GuruChatWorker(
            historico_mensagens=self.historico_mensagens,
            materia=materia,
            modelo_gemini="gemini-2.5-flash",
            api_key=chave
        )
        self.worker_chat.sucesso.connect(lambda resp: self._ao_receber_resposta_ia(resp, lbl_espera))
        self.worker_chat.erro.connect(lambda err: self._ao_falhar_resposta_ia(err, lbl_espera))
        self.worker_chat.start()

    def _ao_receber_resposta_ia(self, resposta: str, lbl_widget: QLabel):
        self.btn_enviar.setEnabled(True)
        self.input_pergunta.setEnabled(True)
        self.input_pergunta.setFocus()
        lbl_widget.setText(resposta)
        self.historico_mensagens.append({"role": "assistant", "content": resposta})

    def _ao_falhar_resposta_ia(self, erro_str: str, lbl_widget: QLabel):
        self.btn_enviar.setEnabled(True)
        self.input_pergunta.setEnabled(True)
        lbl_widget.setText(
            f"❌ <b>Erro na IA Gemini:</b> {erro_str}<br><br>"
            f"💡 <b>Dica:</b> Marque a opção <b>'Modo Local (100% Offline)'</b> no topo para continuar seus estudos sem travar nem depender do servidor!"
        )

    # ----------------------------------------------------
    # MOTOR DE RESPOSTA LOCAL (SEM IA / ZERO FALHAS)
    # ----------------------------------------------------
    def _processar_resposta_local(self, entrada: str):
        materia_ativa = self.combo_materia.currentText()
        texto_limpo = entrada.strip()
        texto_lower = texto_limpo.lower()

        # Se havia uma questão pendente no chat sendo respondida
        if self.questao_quiz_em_andamento:
            q = self.questao_quiz_em_andamento
            self.questao_quiz_em_andamento = None

            gabarito = str(q.get("resposta_correta", "")).strip().upper()
            tipo = q.get("tipo", "dissertativa")
            passos = q.get("passos", [])
            passos_txt = "<br>• " + "<br>• ".join(passos) if isinstance(passos, list) else str(passos)

            if tipo == "multipla_escolha":
                letra_user = texto_limpo[:1].upper()
                if letra_user == gabarito:
                    resp = (
                        f"🎉 <b>ACERTOU! Muito bem!</b><br>"
                        f"A alternativa correta é exatamente a <b>{gabarito}</b>.<br><br>"
                        f"<b>Resolução explicada:</b>{passos_txt}<br><br>"
                        f"<i>Digite <b>1</b> para outra questão ou digite outra dúvida!</i>"
                    )
                else:
                    resp = (
                        f"❌ <b>Você errou!</b><br>"
                        f"Você respondeu: <i>{texto_limpo}</i>. A alternativa correta era a <b>{gabarito}</b>.<br><br>"
                        f"<b>Resolução passo a passo:</b>{passos_txt}<br><br>"
                        f"<i>Digite <b>1</b> para tentar outra questão!</i>"
                    )
            else:
                resp = (
                    f"📖 <b>Confira a Solução Esperada:</b><br>"
                    f"<b>Sua resposta:</b> <i>{texto_limpo}</i><br><br>"
                    f"<b>Gabarito oficial:</b> {gabarito or '(Ver resolução abaixo)'}<br>"
                    f"<b>Resolução completa:</b>{passos_txt}<br><br>"
                    f"<i>Digite <b>1</b> para tentar outra questão!</i>"
                )
            self._renderizar_bolha("assistant", resp)
            return

        # Opção 1: Questão Rápida no Chat
        if texto_lower in ("1", "1.", "questao", "questão", "quiz", "exercicio", "exercício"):
            questoes = banco_questoes.filtrar_questoes(materia=materia_ativa)
            if not questoes:
                questoes = banco_questoes.carregar_banco_questoes()

            if not questoes:
                self._renderizar_bolha("assistant", "Nenhuma questão encontrada no banco para esta matéria. Cadastre questões na Arena!")
                return

            import random
            q = random.choice(questoes)
            self.questao_quiz_em_andamento = q

            enunciado = q.get("enunciado", "")
            topico = q.get("topico", "Geral")
            tipo = q.get("tipo", "dissertativa")

            if tipo == "multipla_escolha":
                opcoes_txt = "<br>".join([f"&nbsp;&nbsp;<b>{op}</b>" for op in q.get("opcoes", [])])
                msg = (
                    f"🎯 <b>Questão de Treino - {materia_ativa} ({topico}):</b><br><br>"
                    f"{enunciado}<br><br>"
                    f"{opcoes_txt}<br><br>"
                    f"👉 <i>Digite a letra da sua resposta (A, B, C, D ou E):</i>"
                )
            else:
                msg = (
                    f"🎯 <b>Questão Dissertativa - {materia_ativa} ({topico}):</b><br><br>"
                    f"{enunciado}<br><br>"
                    f"👉 <i>Digite sua resposta ou raciocínio para conferir:</i>"
                )
            self._renderizar_bolha("assistant", msg)
            return

        # Opção 2: Resumo e Anotações de PDF
        if texto_lower in ("2", "2.", "resumo", "resumos", "anotacoes", "anotações", "pdf"):
            resumos = resumos_manager.obter_resumos_por_materia(materia_ativa)
            if not resumos:
                self._renderizar_bolha(
                    "assistant",
                    f"Ainda não há anotações ou resumos salvos para <b>{materia_ativa}</b>.<br>"
                    f"Vá até a aba <b>'Anotador de PDF & Gerador de Resumo'</b> ao lado, abra um documento e adicione seus comentários para gerar resumos automáticos!"
                )
                return

            msg_resumo = f"📖 <b>Resumos & Anotações Salvas para {materia_ativa}:</b><br><br>"
            for r in resumos:
                msg_resumo += f"<b>📄 {r.get('arquivo_pdf', 'Documento')}</b> (Tópico: {r.get('topico', 'Geral')})<br>"
                comentarios = r.get("comentarios", [])
                if comentarios:
                    msg_resumo += "<b>Pontos-chave anotados:</b><br>"
                    for c in comentarios:
                        msg_resumo += f"• <i>Pág. {c.get('pagina', 1)}:</i> {c.get('comentario', '')}<br>"
                resumo_texto = r.get("resumo_consolidado", "")
                if resumo_texto:
                    msg_resumo += f"<br><i>Resumo:</i><br>{resumo_texto[:300]}...<br>"
                msg_resumo += "<hr>"

            self._renderizar_bolha("assistant", msg_resumo)
            return

        # Opção 3: Erros Recentes da Arena
        if texto_lower in ("3", "3.", "erros", "erro", "arena"):
            erros = carregar_erros_recentes(materia_ativa, limite=4)
            if not erros:
                self._renderizar_bolha("assistant", f"🎉 Nenhum erro recente registrado para <b>{materia_ativa}</b> na Arena! Parabéns pelo desempenho.")
                return

            msg_erros = f"❌ <b>Seus Erros Recentes na Arena ({materia_ativa}):</b><br><br>"
            for idx, e in enumerate(erros, 1):
                msg_erros += (
                    f"<b>{idx}. Tópico: {e.get('topico', 'Geral')}</b> ({e.get('timestamp', '')})<br>"
                    f"<b>Questão:</b> {e.get('enunciado', '')[:110]}...<br>"
                    f"<b>O que você respondeu:</b> <span style='color: #c62828;'>{e.get('resposta_usuario', '')}</span><br>"
                    f"<b>Solução esperada:</b> <span style='color: #2e7d32;'>{e.get('solucao_esperada', '')[:140]}...</span><br><br>"
                )
            msg_erros += "<i>Fique atento a estes pontos no seu próximo simulado!</i>"
            self._renderizar_bolha("assistant", msg_erros)
            return

        # Opção 4: Fórmulas e Alertas
        if texto_lower in ("4", "4.", "formulas", "fórmulas", "formula", "regras"):
            conhec = carregar_conhecimento_materia(materia_ativa)
            formulas = conhec.get("formulas", [])
            alertas = conhec.get("alertas_atencao", [])

            if not formulas and not alertas:
                self._renderizar_bolha("assistant", f"Nenhuma fórmula específica catalogada ainda para <b>{materia_ativa}</b>.")
                return

            msg_form = f"📐 <b>Fórmulas & Alertas Principais de {materia_ativa}:</b><br><br>"
            if formulas:
                msg_form += "<b>Identidades & Teoremas:</b><br>"
                for f in formulas:
                    if isinstance(f, dict):
                        msg_form += f"• <b>{f.get('nome', '')}:</b> <code>{f.get('formula', '')}</code><br>"
                    else:
                        msg_form += f"• {f}<br>"
            if alertas:
                msg_form += "<br><b>⚠️ Pegadinhas de Prova / Alertas:</b><br>"
                for a in alertas:
                    msg_form += f"• {a}<br>"

            self._renderizar_bolha("assistant", msg_form)
            return

        # Busca Inteligente por Palavra-Chave no Banco e Resumos
        resumos_busca = resumos_manager.buscar_resumos_e_comentarios(texto_limpo, materia_ativa)
        questoes_busca = [
            q for q in banco_questoes.filtrar_questoes(materia_ativa)
            if texto_lower in q.get("enunciado", "").lower() or texto_lower in q.get("topico", "").lower()
        ]

        if resumos_busca or questoes_busca:
            msg_busca = f"🔍 <b>Resultados encontrados para '{texto_limpo}':</b><br><br>"
            if resumos_busca:
                msg_busca += "<b>Anotações do PDF:</b><br>"
                for r in resumos_busca[:2]:
                    for c in r.get("comentarios", [])[:2]:
                        msg_busca += f"• (Pág. {c.get('pagina', 1)}): {c.get('comentario', '')}<br>"
            if questoes_busca:
                msg_busca += f"<br><b>Questões cadastradas ({len(questoes_busca)} encontradas):</b><br>"
                for q in questoes_busca[:2]:
                    msg_busca += f"• [{q.get('topico', '')}] {q.get('enunciado', '')[:90]}... (Gabarito: {q.get('resposta_correta', '')})<br>"

            msg_busca += "<br><i>Digite <b>1</b> para responder uma questão ou <b>2</b> para ver todos os resumos.</i>"
            self._renderizar_bolha("assistant", msg_busca)
        else:
            self._renderizar_bolha(
                "assistant",
                f"Entendido! Para a matéria <b>{materia_ativa}</b>, você pode:<br>"
                f"• Digitar <b>1</b> para resolver uma questão.<br>"
                f"• Digitar <b>2</b> para ver anotações de PDF.<br>"
                f"• Digitar <b>3</b> para revisar erros.<br>"
                f"• Digitar <b>4</b> para consultar fórmulas.<br>"
                f"Ou se preferir respostas abertas com IA, desmarque a opção 'Modo Local' acima!"
            )

    def _renderizar_bolha(self, role: str, texto: str) -> QLabel:
        layout_linha = QHBoxLayout()
        lbl_bolha = QLabel(texto)
        lbl_bolha.setWordWrap(True)
        lbl_bolha.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if role == "user":
            layout_linha.addStretch()
            lbl_bolha.setStyleSheet("""
                background-color: #4f46e5;
                color: #ffffff;
                border-radius: 14px;
                border-bottom-right-radius: 3px;
                padding: 12px 18px;
                font-size: 13px;
                font-weight: 500;
                max-width: 580px;
                line-height: 1.4;
            """)
            layout_linha.addWidget(lbl_bolha)
        else:
            lbl_bolha.setStyleSheet("""
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                border-bottom-left-radius: 3px;
                padding: 14px 20px;
                font-size: 13px;
                max-width: 620px;
                line-height: 1.5;
            """)
            layout_linha.addWidget(lbl_bolha)
            layout_linha.addStretch()

        self.layout_mensagens.addLayout(layout_linha)
        QTimer.singleShot(50, self._rolar_para_fim)
        return lbl_bolha

    def _rolar_para_fim(self):
        barra = self.scroll_chat.verticalScrollBar()
        barra.setValue(barra.maximum())

    def limpar_chat(self):
        while self.layout_mensagens.count():
            item = self.layout_mensagens.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        self.historico_mensagens = []
        self.questao_quiz_em_andamento = None
        self._adicionar_mensagem_boas_vindas()

    # =========================================================================
    # ABA 2: ANOTADOR DE PDF & RESUMOS
    # =========================================================================
    def _criar_aba_pdf(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Barra Superior: Seleção de Arquivo e Metadados
        barra_topo = QHBoxLayout()

        btn_abrir_pdf = QPushButton("📂 Abrir Arquivo PDF")
        btn_abrir_pdf.setStyleSheet("font-weight: bold; padding: 6px 12px; background-color: #007acc; color: white; border-radius: 5px;")
        btn_abrir_pdf.clicked.connect(self._abrir_arquivo_pdf)
        barra_topo.addWidget(btn_abrir_pdf)

        self.lbl_nome_pdf = QLabel("Nenhum arquivo aberto.")
        self.lbl_nome_pdf.setStyleSheet("font-style: italic; color: #555;")
        barra_topo.addWidget(self.lbl_nome_pdf)
        barra_topo.addStretch()

        barra_topo.addWidget(QLabel("Matéria:"))
        self.combo_pdf_materia = QComboBox()
        self.combo_pdf_materia.setEditable(True)
        self.combo_pdf_materia.setMinimumWidth(160)
        barra_topo.addWidget(self.combo_pdf_materia)

        barra_topo.addWidget(QLabel("Tópico:"))
        self.input_pdf_topico = QLineEdit("Geral")
        self.input_pdf_topico.setMinimumWidth(140)
        barra_topo.addWidget(self.input_pdf_topico)

        layout.addLayout(barra_topo)

        # Splitter Central: Esquerda = Visualizador Nativo do PDF (QPdfView), Direita = Anotações & Resumo
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Painel Esquerdo: Visualizador Nativo de PDF
        painel_esquerdo = QWidget()
        layout_esq = QVBoxLayout(painel_esquerdo)
        layout_esq.setContentsMargins(0, 0, 0, 0)

        # Barra de Navegação e Zoom do PDF
        barra_navegacao = QHBoxLayout()

        self.btn_pag_anterior = QPushButton("⬅️ Anterior")
        self.btn_pag_anterior.clicked.connect(self._pag_anterior)
        self.btn_pag_anterior.setEnabled(False)

        self.lbl_num_pagina = QLabel("Página: 0 / 0")
        self.lbl_num_pagina.setStyleSheet("font-weight: bold; min-width: 90px; text-align: center;")

        self.btn_pag_proxima = QPushButton("Próxima ➡️")
        self.btn_pag_proxima.clicked.connect(self._pag_proxima)
        self.btn_pag_proxima.setEnabled(False)

        barra_navegacao.addWidget(self.btn_pag_anterior)
        barra_navegacao.addWidget(self.lbl_num_pagina)
        barra_navegacao.addWidget(self.btn_pag_proxima)
        barra_navegacao.addSpacing(10)

        # Controles de Zoom
        btn_zoom_out = QPushButton("🔍 -")
        btn_zoom_out.setToolTip("Diminuir Zoom")
        btn_zoom_out.setFixedWidth(36)
        btn_zoom_out.clicked.connect(self._zoom_out)

        btn_zoom_in = QPushButton("🔍 +")
        btn_zoom_in.setToolTip("Aumentar Zoom")
        btn_zoom_in.setFixedWidth(36)
        btn_zoom_in.clicked.connect(self._zoom_in)

        btn_fit_width = QPushButton("↔️ Largura")
        btn_fit_width.setToolTip("Ajustar à largura da janela")
        btn_fit_width.clicked.connect(self._ajustar_largura)

        btn_fit_page = QPushButton("📄 Ajustar")
        btn_fit_page.setToolTip("Ajustar página inteira na tela")
        btn_fit_page.clicked.connect(self._ajustar_pagina)

        self.cb_rolagem_continua = QCheckBox("📜 Rolar Contínuo")
        self.cb_rolagem_continua.setToolTip("Permite rolar por todas as páginas continuamente")
        self.cb_rolagem_continua.toggled.connect(self._alternar_modo_rolagem)

        barra_navegacao.addWidget(btn_zoom_out)
        barra_navegacao.addWidget(btn_zoom_in)
        barra_navegacao.addWidget(btn_fit_width)
        barra_navegacao.addWidget(btn_fit_page)
        barra_navegacao.addWidget(self.cb_rolagem_continua)
        barra_navegacao.addStretch()

        layout_esq.addLayout(barra_navegacao)

        # Widget Nativo de PDF (QPdfView) - Renderização 100% Fiel do PDF sem quebrar texto
        self.pdf_view = QPdfView(self)
        self.pdf_view.setDocument(self.pdf_doc)
        self.pdf_view.setPageMode(QPdfView.PageMode.SinglePage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.pdf_view.pageNavigator().currentPageChanged.connect(self._ao_mudar_pagina_pdf)
        self.pdf_view.setStyleSheet("border: 1px solid #ced4da; background-color: #525659;")

        layout_esq.addWidget(self.pdf_view)
        splitter.addWidget(painel_esquerdo)

        # Painel Direito: Anotações da Página & Resumo Consolidado
        painel_direito = QWidget()
        layout_dir = QVBoxLayout(painel_direito)
        layout_dir.setContentsMargins(0, 0, 0, 0)

        # Box Adicionar Anotação
        box_anotacao = QGroupBox("✍️ Anotação para a Página Atual")
        layout_box_anot = QVBoxLayout(box_anotacao)

        self.lbl_anotacao_pagina_info = QLabel("Página ativa: 1")
        self.lbl_anotacao_pagina_info.setStyleSheet("font-weight: bold; color: #1a237e;")
        layout_box_anot.addWidget(self.lbl_anotacao_pagina_info)

        self.txt_novo_comentario = QTextEdit()
        self.txt_novo_comentario.setPlaceholderText("Escreva aqui seu comentário, dúvida ou destaque para a página visível no PDF...")
        self.txt_novo_comentario.setMaximumHeight(70)
        layout_box_anot.addWidget(self.txt_novo_comentario)

        btn_add_coment = QPushButton("➕ Inserir Anotação nesta Página")
        btn_add_coment.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        btn_add_coment.clicked.connect(self._adicionar_comentario_pagina)
        layout_box_anot.addWidget(btn_add_coment)
        layout_dir.addWidget(box_anotacao)

        # Lista de Anotações do Documento (com salto de página ao clicar!)
        layout_dir.addWidget(QLabel("<b>Anotações do Documento (clique para ir à página):</b>"))
        self.lista_comentarios_widget = QListWidget()
        self.lista_comentarios_widget.setMaximumHeight(130)
        self.lista_comentarios_widget.itemClicked.connect(self._ao_clicar_anotacao_lista)
        layout_dir.addWidget(self.lista_comentarios_widget)

        linha_botoes_coment = QHBoxLayout()
        btn_del_coment = QPushButton("🗑️ Remover Anotação Selecionada")
        btn_del_coment.setStyleSheet("font-size: 11px;")
        btn_del_coment.clicked.connect(self._remover_comentario_selecionado)
        linha_botoes_coment.addWidget(btn_del_coment)
        linha_botoes_coment.addStretch()
        layout_dir.addLayout(linha_botoes_coment)

        # Resumo Consolidado
        layout_dir.addWidget(QLabel("<b>📝 Resumo Consolidado das Anotações:</b>"))
        self.txt_resumo_consolidado = QTextEdit()
        self.txt_resumo_consolidado.setPlaceholderText("Clique em 'Gerar Resumo' abaixo para compilar todas as suas anotações...")
        layout_dir.addWidget(self.txt_resumo_consolidado)

        # Botões do Resumo
        linha_acoes_resumo = QHBoxLayout()
        btn_compilar_resumo = QPushButton("⚡ Gerar Resumo")
        btn_compilar_resumo.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 8px; border-radius: 5px;")
        btn_compilar_resumo.clicked.connect(self._gerar_resumo_consolidado)

        btn_salvar_resumo = QPushButton("💾 Salvar no Caderno")
        btn_salvar_resumo.setStyleSheet("background-color: #4a148c; color: white; font-weight: bold; padding: 8px; border-radius: 5px;")
        btn_salvar_resumo.clicked.connect(self._salvar_resumo_no_caderno)

        btn_exportar_txt = QPushButton("📄 Exportar (.txt)")
        btn_exportar_txt.clicked.connect(self._exportar_resumo_txt)

        linha_acoes_resumo.addWidget(btn_compilar_resumo)
        linha_acoes_resumo.addWidget(btn_salvar_resumo)
        linha_acoes_resumo.addWidget(btn_exportar_txt)
        layout_dir.addLayout(linha_acoes_resumo)

        splitter.addWidget(painel_direito)
        splitter.setSizes([550, 390])

        layout.addWidget(splitter)
        return widget

    def _abrir_arquivo_pdf(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Abrir Arquivo PDF", "", "Arquivos PDF (*.pdf)"
        )
        if not caminho:
            return

        try:
            err = self.pdf_doc.load(caminho)
            if err != QPdfDocument.Error.None_:
                raise RuntimeError(f"Erro ao carregar documento PDF (código: {err})")

            self.total_paginas = self.pdf_doc.pageCount()
            self.caminho_pdf_atual = caminho
            self.lbl_nome_pdf.setText(f"📄 {Path(caminho).name} ({self.total_paginas} páginas)")

            # Tenta preencher a matéria a partir do nome do arquivo
            nome = Path(caminho).stem
            for idx in range(self.combo_pdf_materia.count()):
                if self.combo_pdf_materia.itemText(idx).lower() in nome.lower():
                    self.combo_pdf_materia.setCurrentIndex(idx)
                    break

            # Carrega anotações já salvas desse arquivo se existirem
            self.comentarios_doc = []
            resumos_existentes = resumos_manager.carregar_todos_resumos()
            for r in resumos_existentes:
                if r.get("arquivo_pdf") == Path(caminho).name:
                    self.comentarios_doc = r.get("comentarios", [])
                    self.txt_resumo_consolidado.setPlainText(r.get("resumo_consolidado", ""))
                    break

            # Salta para a primeira página
            self.pdf_view.pageNavigator().jump(0, QPointF(), self.pdf_view.pageNavigator().currentZoom())
            self._ao_mudar_pagina_pdf(0)
            self._atualizar_lista_comentarios_ui()
            log_sucesso(f"PDF carregado e renderizado nativamente com sucesso: {caminho}", "GuruPDF")
        except Exception as e:
            log_erro("Falha ao abrir PDF nativamente", "GuruPDF", exc=e)
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir o arquivo PDF: {e}")

    def _ao_mudar_pagina_pdf(self, page_index: int):
        self.pagina_atual = page_index
        total = self.total_paginas
        self.lbl_num_pagina.setText(f"Página: {page_index + 1} / {total}")
        self.lbl_anotacao_pagina_info.setText(f"Página ativa no PDF: {page_index + 1}")
        self.btn_pag_anterior.setEnabled(page_index > 0)
        self.btn_pag_proxima.setEnabled(page_index < total - 1)

    def _pag_anterior(self):
        nav = self.pdf_view.pageNavigator()
        if nav.currentPage() > 0:
            nav.jump(nav.currentPage() - 1, QPointF(), nav.currentZoom())

    def _pag_proxima(self):
        nav = self.pdf_view.pageNavigator()
        if nav.currentPage() < self.total_paginas - 1:
            nav.jump(nav.currentPage() + 1, QPointF(), nav.currentZoom())

    def _zoom_in(self):
        if self.pdf_view:
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.pdf_view.setZoomFactor(self.pdf_view.zoomFactor() * 1.2)

    def _zoom_out(self):
        if self.pdf_view:
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.pdf_view.setZoomFactor(max(0.2, self.pdf_view.zoomFactor() / 1.2))

    def _ajustar_largura(self):
        if self.pdf_view:
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def _ajustar_pagina(self):
        if self.pdf_view:
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

    def _alternar_modo_rolagem(self, rolar_continuo: bool):
        if self.pdf_view:
            modo = QPdfView.PageMode.MultiPage if rolar_continuo else QPdfView.PageMode.SinglePage
            self.pdf_view.setPageMode(modo)

    def _ao_clicar_anotacao_lista(self, item):
        row = self.lista_comentarios_widget.currentRow()
        if 0 <= row < len(self.comentarios_doc):
            pag = self.comentarios_doc[row].get("pagina", 1) - 1
            if 0 <= pag < self.total_paginas:
                self.pdf_view.pageNavigator().jump(pag, QPointF(), self.pdf_view.pageNavigator().currentZoom())

    def _adicionar_comentario_pagina(self):
        texto_coment = self.txt_novo_comentario.toPlainText().strip()
        if not texto_coment:
            QMessageBox.warning(self, "Aviso", "Digite um comentário antes de adicionar.")
            return

        if not self.caminho_pdf_atual:
            QMessageBox.warning(self, "Aviso", "Abra um arquivo PDF antes de adicionar anotações.")
            return

        num_pag = self.pdf_view.pageNavigator().currentPage() + 1
        self.comentarios_doc.append({
            "pagina": num_pag,
            "comentario": texto_coment
        })

        self.txt_novo_comentario.clear()
        self._atualizar_lista_comentarios_ui()
        QMessageBox.information(self, "Anotação Salva", f"Anotação adicionada à Página {num_pag}!")

    def _atualizar_lista_comentarios_ui(self):
        self.lista_comentarios_widget.clear()
        for idx, c in enumerate(self.comentarios_doc):
            item_str = f"📍 Pág. {c.get('pagina', 1)}: {c.get('comentario', '')}"
            self.lista_comentarios_widget.addItem(item_str)

    def _remover_comentario_selecionado(self):
        row = self.lista_comentarios_widget.currentRow()
        if row < 0 or row >= len(self.comentarios_doc):
            QMessageBox.warning(self, "Aviso", "Selecione uma anotação na lista para remover.")
            return
        del self.comentarios_doc[row]
        self._atualizar_lista_comentarios_ui()

    def _gerar_resumo_consolidado(self):
        if not self.comentarios_doc:
            QMessageBox.warning(self, "Aviso", "Adicione pelo menos uma anotação no documento para compilar o resumo.")
            return

        materia = self.combo_pdf_materia.currentText()
        topico = self.input_pdf_topico.text().strip() or "Geral"
        nome_doc = Path(self.caminho_pdf_atual).name if self.caminho_pdf_atual else "Documento"

        linhas = [
            f"# RESUMO CONSOLIDADO DE ESTUDOS",
            f"**Matéria:** {materia} | **Tópico:** {topico}",
            f"**Documento de Origem:** {nome_doc}",
            f"---",
            f"## PONTOS-CHAVE & ANOTAÇÕES POR PÁGINA:\n"
        ]

        # Agrupa comentários por página
        por_pagina = {}
        for c in self.comentarios_doc:
            p = c.get("pagina", 1)
            por_pagina.setdefault(p, []).append(c.get("comentario", ""))

        for p in sorted(por_pagina.keys()):
            linhas.append(f"### Página {p}:")
            for coment in por_pagina[p]:
                linhas.append(f"- {coment}")
            linhas.append("")

        linhas.append("## SÍNTESE DO ESTUDANTE:")
        linhas.append(f"Material revisado com foco em {topico}. Conteúdo integrado ao Chat Tutor de Estudos.")

        resumo_final = "\n".join(linhas)
        self.txt_resumo_consolidado.setPlainText(resumo_final)
        QMessageBox.information(self, "Resumo Gerado", "🎉 Resumo compilado com sucesso a partir das suas anotações!")

    def _salvar_resumo_no_caderno(self):
        resumo_texto = self.txt_resumo_consolidado.toPlainText().strip()
        if not resumo_texto:
            QMessageBox.warning(self, "Aviso", "Gere o resumo antes de salvar.")
            return

        materia = self.combo_pdf_materia.currentText()
        topico = self.input_pdf_topico.text().strip() or "Geral"

        resumos_manager.salvar_resumo_documento(
            materia=materia,
            topico=topico,
            arquivo_pdf=self.caminho_pdf_atual,
            comentarios=self.comentarios_doc,
            resumo_consolidado=resumo_texto
        )

        QMessageBox.information(
            self, "Resumo Gravado",
            f"🎉 Resumo salvo no seu caderno de <b>{materia}</b>!<br><br>"
            f"Ele já está disponível no <b>Chat Tutor</b> (basta digitar <b>2</b> ou 'resumo')!"
        )

    def _exportar_resumo_txt(self):
        texto = self.txt_resumo_consolidado.toPlainText().strip()
        if not texto:
            QMessageBox.warning(self, "Aviso", "Não há resumo para exportar.")
            return

        caminho_save, _ = QFileDialog.getSaveFileName(
            self, "Exportar Resumo", "Resumo_Estudos.txt", "Texto (*.txt)"
        )
        if caminho_save:
            try:
                with open(caminho_save, "w", encoding="utf-8") as f:
                    f.write(texto)
                QMessageBox.information(self, "Exportado", "Arquivo de resumo exportado com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao exportar arquivo: {e}")
