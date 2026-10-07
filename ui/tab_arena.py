import json
import os
import random
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QFrame, QMessageBox, QScrollArea, QProgressBar,
    QDialog, QCheckBox, QDialogButtonBox, QRadioButton, QButtonGroup, QGroupBox
)
from PyQt6.QtCore import Qt

from organizador_estudos import registrar_revisao
from ollama_client import registrar_erro_arena
import banco_questoes
from ui.dialog_gerenciar_questoes import DialogGerenciarQuestoes
from logger import log_info, log_sucesso, log_aviso, log_erro


class DialogSelecaoMaterias(QDialog):
    """Diálogo para selecionar múltiplas matérias para o simulado."""
    def __init__(self, materias_disponiveis: list[str], selecionadas: list[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar Matérias para o Simulado")
        self.setMinimumWidth(360)
        self.selecionadas = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Escolha quais matérias deseja incluir no simulado:</b>"))

        self.checkboxes = {}
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout_checks = QVBoxLayout(container)

        selecionadas_set = set(selecionadas or [])

        for mat in materias_disponiveis:
            cb = QCheckBox(mat)
            if not selecionadas_set or mat in selecionadas_set:
                cb.setChecked(True)
            layout_checks.addWidget(cb)
            self.checkboxes[mat] = cb

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Botões Todos / Nenhum
        layout_acoes = QHBoxLayout()
        btn_todos = QPushButton("Marcar Todas")
        btn_todos.clicked.connect(self._marcar_todas)
        btn_nenhum = QPushButton("Desmarcar Todas")
        btn_nenhum.clicked.connect(self._desmarcar_todas)
        layout_acoes.addWidget(btn_todos)
        layout_acoes.addWidget(btn_nenhum)
        layout.addLayout(layout_acoes)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._ao_confirmar)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _marcar_todas(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def _desmarcar_todas(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def _ao_confirmar(self):
        self.selecionadas = [mat for mat, cb in self.checkboxes.items() if cb.isChecked()]
        if not self.selecionadas:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos uma matéria!")
            return
        self.accept()


class TabArena(QWidget):
    def __init__(self):
        super().__init__()

        self.questoes = []
        self.indice_atual = 0
        self.acertos = 0
        self.erros = 0
        self.materias_selecionadas_custom = []
        self.desempenho_por_materia = {}

        layout_externo = QVBoxLayout(self)

        # 1. Barra Superior (Seleção de Matéria, Tópico e Ações)
        barra_topo = QHBoxLayout()
        lbl_titulo = QLabel("⚔️ <b>Arena de Estudos & Simulados</b>")
        lbl_titulo.setStyleSheet("font-size: 15px; color: #1a237e;")

        self.combo_materia = QComboBox()
        self.combo_materia.setMinimumWidth(180)
        self.combo_materia.currentIndexChanged.connect(self._ao_mudar_materia)

        self.combo_topico = QComboBox()
        self.combo_topico.setMinimumWidth(180)
        self.combo_topico.setToolTip("Filtrar questões por tópico específico da matéria")

        self.btn_multi_materias = QPushButton("☑️ Múltiplas")
        self.btn_multi_materias.setToolTip("Selecionar várias matérias para simulado misto")
        self.btn_multi_materias.clicked.connect(self._abrir_seletor_multiplas)

        self.btn_gerenciar = QPushButton("📝 Cadastrar / Importar Questões")
        self.btn_gerenciar.setStyleSheet("background-color: #475569; color: white; font-weight: bold; padding: 7px 12px; border-radius: 7px;")
        self.btn_gerenciar.clicked.connect(self._abrir_gerenciador_questoes)

        self.btn_iniciar = QPushButton("🚀 Iniciar Simulado")
        self.btn_iniciar.setStyleSheet("background-color: #4f46e5; color: white; font-weight: bold; padding: 7px 16px; border-radius: 7px;")
        self.btn_iniciar.clicked.connect(self.iniciar_simulado)

        self.badge_acertos = QLabel("0 Acertos")
        self.badge_acertos.setStyleSheet("background-color: #ecfdf5; color: #047857; font-weight: bold; padding: 4px 10px; border-radius: 6px; border: 1px solid #a7f3d0;")

        self.badge_erros = QLabel("0 Erros")
        self.badge_erros.setStyleSheet("background-color: #fef2f2; color: #b91c1c; font-weight: bold; padding: 4px 10px; border-radius: 6px; border: 1px solid #fecaca;")

        barra_topo.addWidget(lbl_titulo)
        barra_topo.addSpacing(10)
        barra_topo.addWidget(QLabel("Matéria:"))
        barra_topo.addWidget(self.combo_materia)
        barra_topo.addWidget(QLabel("Tópico:"))
        barra_topo.addWidget(self.combo_topico)
        barra_topo.addWidget(self.btn_multi_materias)
        barra_topo.addWidget(self.btn_gerenciar)
        barra_topo.addWidget(self.btn_iniciar)
        barra_topo.addStretch()
        barra_topo.addWidget(self.badge_acertos)
        barra_topo.addWidget(self.badge_erros)
        layout_externo.addLayout(barra_topo)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout_externo.addWidget(self.progress_bar)

        # 2. Área Central com Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container_questao = QWidget()
        self.layout_conteudo = QVBoxLayout(self.container_questao)
        self.layout_conteudo.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.container_questao)
        layout_externo.addWidget(scroll)

        self.atualizar_materias_e_topicos()
        self._exibir_tela_inicial()

    def atualizar_materias_e_topicos(self):
        """Atualiza os menus de matérias e tópicos a partir do banco de questões."""
        mat_anterior = self.combo_materia.currentText()
        self.combo_materia.blockSignals(True)
        self.combo_materia.clear()
        self.combo_materia.addItem("🎯 Todas as Matérias (Misto)")

        materias = banco_questoes.obter_todas_materias()
        for m in materias:
            self.combo_materia.addItem(f"📚 {m}")

        if mat_anterior:
            self.combo_materia.setCurrentText(mat_anterior)
        self.combo_materia.blockSignals(False)

        self._atualizar_topicos()

    def _ao_mudar_materia(self):
        self.materias_selecionadas_custom = []
        self._atualizar_topicos()

    def _atualizar_topicos(self):
        mat_texto = self.combo_materia.currentText()
        m_limpa = None
        if "Todas as Matérias" not in mat_texto and not self.materias_selecionadas_custom:
            m_limpa = mat_texto.replace("📚", "").strip()

        self.combo_topico.blockSignals(True)
        self.combo_topico.clear()
        self.combo_topico.addItem("📌 Todos os Tópicos")

        topicos = banco_questoes.obter_topicos_por_materia(m_limpa)
        for t in topicos:
            self.combo_topico.addItem(t)
        self.combo_topico.blockSignals(False)

    def _abrir_seletor_multiplas(self):
        materias = banco_questoes.obter_todas_materias()
        if not materias:
            QMessageBox.information(self, "Sem matérias", "Nenhuma matéria cadastrada com questões ainda.")
            return

        diag = DialogSelecaoMaterias(materias, self.materias_selecionadas_custom, self)
        if diag.exec() == QDialog.DialogCode.Accepted:
            self.materias_selecionadas_custom = diag.selecionadas
            qtd = len(self.materias_selecionadas_custom)
            self.combo_materia.blockSignals(True)
            self.combo_materia.setEditText(f"Customizado: {qtd} matérias")
            self.combo_materia.blockSignals(False)
            self._atualizar_topicos()
            QMessageBox.information(self, "Matérias Selecionadas", f"{qtd} matéria(s) selecionada(s) para o simulado!\nClique em 'Iniciar Simulado'.")

    def _abrir_gerenciador_questoes(self):
        diag = DialogGerenciarQuestoes(self)
        diag.exec()
        self.atualizar_materias_e_topicos()

    def _limpar_layout_conteudo(self):
        while self.layout_conteudo.count():
            item = self.layout_conteudo.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _exibir_tela_inicial(self):
        self._limpar_layout_conteudo()
        self.progress_bar.setVisible(False)

        box = QFrame()
        box.setStyleSheet("background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 22px;")
        v = QVBoxLayout(box)

        lbl = QLabel(
            "<h3>Bem-vindo à Arena de Questões e Simulados! 🎯</h3>"
            "<p>Pratique com questões organizadas por matéria e tópico específico, com correção imediata para múltipla escolha e gabarito passo a passo para dissertativas.</p>"
            "<ul>"
            "<li><b>Filtro por Matéria & Tópico:</b> Escolha exatamente o assunto que precisa treinar (ex: Matemática Discreta -> Relações de Equivalência).</li>"
            "<li><b>Múltipla Escolha com Correção Imediata:</b> Se você errar a alternativa, o sistema acusa o erro na hora, destaca a alternativa correta e registra para revisão.</li>"
            "<li><b>Cadastre ou Cole 100 Questões de Uma Vez:</b> Clique no botão <i>'📝 Cadastrar / Importar 100 Questões'</i> acima para adicionar questões manualmente ou colar dezenas de questões em massa!</li>"
            "<li><b>Repetição Espaçada:</b> Seus acertos e erros atualizam automaticamente a sua fila de estudos.</li>"
            "</ul>"
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 13px; line-height: 1.5;")
        v.addWidget(lbl)
        self.layout_conteudo.addWidget(box)

    def _atualizar_placar(self):
        self.badge_acertos.setText(f"✅ {self.acertos} Acerto(s)")
        self.badge_erros.setText(f"❌ {self.erros} Erro(s)")

    def iniciar_simulado(self):
        mat_texto = self.combo_materia.currentText()
        top_texto = self.combo_topico.currentText()

        materia_filtro = None
        if self.materias_selecionadas_custom:
            materias_busca = self.materias_selecionadas_custom
        elif "Todas as Matérias" in mat_texto:
            materias_busca = None
        else:
            materias_busca = [mat_texto.replace("📚", "").strip()]

        topico_filtro = None if "Todos os Tópicos" in top_texto else top_texto.strip()

        # Busca no banco de questões
        questoes_encontradas = []
        if materias_busca:
            for m in materias_busca:
                questoes_encontradas.extend(banco_questoes.filtrar_questoes(materia=m, topico=topico_filtro))
        else:
            questoes_encontradas = banco_questoes.filtrar_questoes(materia=None, topico=topico_filtro)

        if not questoes_encontradas:
            QMessageBox.information(
                self, "Nenhuma Questão Encontrada",
                f"Nenhuma questão encontrada para a matéria e tópico selecionados.<br><br>"
                f"💡 Clique no botão <b>'📝 Cadastrar / Importar Questões'</b> para adicionar questões individualmente ou colar em massa!"
            )
            return

        random.shuffle(questoes_encontradas)
        self.questoes = questoes_encontradas
        self.indice_atual = 0
        self.acertos = 0
        self.erros = 0
        self.desempenho_por_materia = {}

        for q in self.questoes:
            m = q.get("materia", "Geral")
            if m not in self.desempenho_por_materia:
                self.desempenho_por_materia[m] = {"acertos": 0, "erros": 0, "total": 0}
            self.desempenho_por_materia[m]["total"] += 1

        self.progress_bar.setMaximum(len(self.questoes))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self._atualizar_placar()

        nome_exib = topico_filtro if topico_filtro else (mat_texto.replace("📚", "").strip())
        log_info(f"Simulado iniciado com {len(self.questoes)} questões ({nome_exib}).", "Arena")
        self.exibir_questao_atual()

    def exibir_questao_atual(self):
        self._limpar_layout_conteudo()

        if self.indice_atual >= len(self.questoes):
            self.exibir_tela_final()
            return

        self.progress_bar.setValue(self.indice_atual)
        questao = self.questoes[self.indice_atual]
        num_q = self.indice_atual + 1
        total_q = len(self.questoes)

        materia_q = questao.get("materia", "Geral")
        topico_q = questao.get("topico", "Geral")
        tipo_q = questao.get("tipo", "dissertativa")

        card_q = QFrame()
        card_q.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 22px;")
        layout_q = QVBoxLayout(card_q)
        layout_q.setSpacing(14)

        # Cabeçalho da Questão
        badge_tipo = "Múltipla Escolha" if tipo_q == "multipla_escolha" else "Dissertativa"
        lbl_header = QLabel(
            f"<b>Questão {num_q} de {total_q}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<span style='background-color: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 6px; font-weight: 600;'>📚 {materia_q}</span> &nbsp;"
            f"<span style='background-color: #f3e8ff; color: #6b21a8; padding: 4px 10px; border-radius: 6px; font-weight: 600;'>📌 {topico_q}</span> &nbsp;"
            f"<span style='background-color: #ecfdf5; color: #047857; padding: 4px 10px; border-radius: 6px; font-weight: 600;'>{badge_tipo}</span>"
        )
        lbl_header.setStyleSheet("font-size: 13px;")
        layout_q.addWidget(lbl_header)

        # Enunciado
        enunciado = questao.get("enunciado", "")
        lbl_enunciado = QLabel(enunciado)
        lbl_enunciado.setWordWrap(True)
        lbl_enunciado.setStyleSheet("font-size: 14px; font-weight: 500; line-height: 1.6; color: #0f172a; margin: 4px 0; padding: 16px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;")
        layout_q.addWidget(lbl_enunciado)

        # Se for Múltipla Escolha
        if tipo_q == "multipla_escolha":
            self.grupo_radios = QButtonGroup(self)
            self.radios_opcoes = {}

            box_opcoes = QWidget()
            layout_opcoes = QVBoxLayout(box_opcoes)
            layout_opcoes.setSpacing(10)

            opcoes = questao.get("opcoes", [])
            for idx, opc_str in enumerate(opcoes):
                rb = QRadioButton(opc_str)
                rb.setCursor(Qt.CursorShape.PointingHandCursor)
                rb.setStyleSheet("""
                    QRadioButton {
                        background-color: #ffffff;
                        border: 1.5px solid #e2e8f0;
                        border-radius: 9px;
                        padding: 12px 16px;
                        font-size: 13px;
                        color: #1e293b;
                    }
                    QRadioButton:hover {
                        border-color: #818cf8;
                        background-color: #f8fafc;
                    }
                    QRadioButton:checked {
                        border: 2px solid #4f46e5;
                        background-color: #eef2ff;
                        font-weight: 600;
                        color: #312e81;
                    }
                """)
                letra_match = re.match(r"^([A-Ea-e])[\)\.\-\]]", opc_str)
                letra = letra_match.group(1).upper() if letra_match else chr(65 + idx)
                self.grupo_radios.addButton(rb, idx)
                self.radios_opcoes[letra] = rb
                layout_opcoes.addWidget(rb)

            layout_q.addWidget(box_opcoes)

            self.btn_confirmar_mc = QPushButton("✔️ Confirmar Resposta")
            self.btn_confirmar_mc.setStyleSheet("background-color: #4f46e5; color: white; font-weight: bold; padding: 11px; border-radius: 8px; font-size: 13px;")
            self.btn_confirmar_mc.clicked.connect(self._avaliar_multipla_escolha)
            layout_q.addWidget(self.btn_confirmar_mc)

        # Se for Dissertativa
        else:
            lbl_instrucao = QLabel("<b>Sua Resolução / Resposta:</b>")
            self.txt_resposta_diss = QTextEdit()
            self.txt_resposta_diss.setPlaceholderText("Digite aqui sua resposta, raciocínio ou resultado...")
            self.txt_resposta_diss.setMinimumHeight(90)

            self.btn_verificar_diss = QPushButton("🔍 Conferir Gabarito e Solução Passo a Passo")
            self.btn_verificar_diss.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 8px; border-radius: 6px;")
            self.btn_verificar_diss.clicked.connect(self._verificar_dissertativa)

            layout_q.addWidget(lbl_instrucao)
            layout_q.addWidget(self.txt_resposta_diss)
            layout_q.addWidget(self.btn_verificar_diss)

        # Frame de Gabarito e Explicação
        self.frame_gabarito = QFrame()
        self.frame_gabarito.setStyleSheet("background-color: #fdfdfd; border: 1px solid #c3e6cb; border-radius: 6px; padding: 12px; margin-top: 10px;")
        layout_gab = QVBoxLayout(self.frame_gabarito)

        self.lbl_feedback_resultado = QLabel("")
        self.lbl_feedback_resultado.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 6px;")
        layout_gab.addWidget(self.lbl_feedback_resultado)

        lbl_titulo_gab = QLabel("<b>📖 Resolução Passo a Passo / Comentários:</b>")
        lbl_titulo_gab.setStyleSheet("color: #155724; font-size: 13px;")
        layout_gab.addWidget(lbl_titulo_gab)

        passos = questao.get("passos", [])
        passos_txt = "\n".join([f"• {p}" for p in passos]) if isinstance(passos, list) else str(passos)
        lbl_passos = QLabel(passos_txt)
        lbl_passos.setWordWrap(True)
        lbl_passos.setStyleSheet("font-size: 13px; color: #212529; line-height: 1.4; padding: 6px;")
        layout_gab.addWidget(lbl_passos)

        # Botões de Ação Final da Questão
        if tipo_q == "multipla_escolha":
            self.btn_proxima_mc = QPushButton("Próxima Questão ➡️")
            self.btn_proxima_mc.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
            self.btn_proxima_mc.clicked.connect(self._avancar_proxima)
            layout_gab.addWidget(self.btn_proxima_mc, alignment=Qt.AlignmentFlag.AlignRight)
        else:
            # Auto-avaliação para dissertativa
            lbl_autoaval = QLabel("<b>Como foi seu desempenho nesta questão?</b>")
            lbl_autoaval.setStyleSheet("margin-top: 8px; font-weight: bold;")
            layout_gab.addWidget(lbl_autoaval)

            layout_botoes_aval = QHBoxLayout()
            btn_facil = QPushButton("🟢 Acertei com Facilidade")
            btn_facil.setStyleSheet("background-color: #e8f5e9; color: #2e7d32; font-weight: bold; padding: 6px; border-radius: 4px;")
            btn_facil.clicked.connect(lambda: self._avaliar_dissertativa_final("facil"))

            btn_medio = QPushButton("🔵 Acertei com Esforço")
            btn_medio.setStyleSheet("background-color: #e1f5fe; color: #0277bd; font-weight: bold; padding: 6px; border-radius: 4px;")
            btn_medio.clicked.connect(lambda: self._avaliar_dissertativa_final("medio"))

            btn_erro = QPushButton("🔴 Errei / Não Soube")
            btn_erro.setStyleSheet("background-color: #ffebee; color: #c62828; font-weight: bold; padding: 6px; border-radius: 4px;")
            btn_erro.clicked.connect(lambda: self._avaliar_dissertativa_final("dificil"))

            layout_botoes_aval.addWidget(btn_facil)
            layout_botoes_aval.addWidget(btn_medio)
            layout_botoes_aval.addWidget(btn_erro)
            layout_gab.addLayout(layout_botoes_aval)

        self.frame_gabarito.setVisible(False)
        layout_q.addWidget(self.frame_gabarito)

        self.layout_conteudo.addWidget(card_q)

    # Avaliação Múltipla Escolha
    def _avaliar_multipla_escolha(self):
        questao = self.questoes[self.indice_atual]
        correta = str(questao.get("resposta_correta", "")).strip().upper()

        letra_escolhida = None
        for letra, rb in self.radios_opcoes.items():
            if rb.isChecked():
                letra_escolhida = letra
                break

        if not letra_escolhida:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione uma das alternativas antes de confirmar!")
            return

        self.btn_confirmar_mc.setEnabled(False)
        materia_q = questao.get("materia", "Geral")
        topico_q = questao.get("topico", "Geral")

        if letra_escolhida == correta:
            self.acertos += 1
            self.desempenho_por_materia[materia_q]["acertos"] += 1
            self.lbl_feedback_resultado.setText(f"🎉 <span style='color: #2e7d32;'>PARABÉNS! Você acertou a questão (Alternativa {correta}).</span>")
            log_sucesso(f"Questão {self.indice_atual+1} [{materia_q}] ACERTO! Escolhida: {letra_escolhida}", "Arena")
            self._atualizar_topicos_repeticao(materia_q, topico_q, "facil")
        else:
            self.erros += 1
            self.desempenho_por_materia[materia_q]["erros"] += 1
            self.lbl_feedback_resultado.setText(
                f"❌ <span style='color: #c62828;'>RESPOSTA INCORRETA! Você marcou {letra_escolhida}, mas a correta era a <b>{correta}</b>.</span>"
            )
            log_aviso(f"Questão {self.indice_atual+1} [{materia_q}] ERRO! Escolhida: {letra_escolhida}, Correta: {correta}", "Arena")

            # Registra o erro no histórico
            passos = questao.get("passos", [])
            solucao = "\n".join(passos) if isinstance(passos, list) else str(passos)
            registrar_erro_arena(
                materia=materia_q,
                topico=topico_q,
                enunciado=questao.get("enunciado", ""),
                resposta_usuario=f"Marcou Alternativa {letra_escolhida}",
                solucao_esperada=f"Alternativa Correta {correta}\n{solucao}"
            )
            self._atualizar_topicos_repeticao(materia_q, topico_q, "dificil")

            # Destaca cores nos rádios com estilo moderno
            if correta in self.radios_opcoes:
                self.radios_opcoes[correta].setStyleSheet("background-color: #ecfdf5; border: 2px solid #10b981; color: #065f46; font-weight: bold; border-radius: 9px; padding: 12px 16px;")
            if letra_escolhida in self.radios_opcoes and letra_escolhida != correta:
                self.radios_opcoes[letra_escolhida].setStyleSheet("background-color: #fef2f2; border: 2px solid #ef4444; color: #991b1b; font-weight: bold; border-radius: 9px; padding: 12px 16px;")

        self._atualizar_placar()
        self.frame_gabarito.setVisible(True)

    # Avaliação Dissertativa
    def _verificar_dissertativa(self):
        resposta_usuario = self.txt_resposta_diss.toPlainText().strip()
        if not resposta_usuario:
            resp = QMessageBox.question(
                self, "Resposta em branco",
                "Você não digitou nenhuma resposta. Deseja ver o gabarito mesmo assim?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                return

        self.btn_verificar_diss.setEnabled(False)
        self.lbl_feedback_resultado.setText("<b>Confira o gabarito oficial e avalie sua resposta:</b>")
        self.frame_gabarito.setVisible(True)

    def _avaliar_dissertativa_final(self, nivel: str):
        questao = self.questoes[self.indice_atual]
        materia_q = questao.get("materia", "Geral")
        topico_q = questao.get("topico", "Geral")
        resposta_usuario = self.txt_resposta_diss.toPlainText().strip()

        if nivel in ("facil", "medio"):
            self.acertos += 1
            self.desempenho_por_materia[materia_q]["acertos"] += 1
            self._atualizar_topicos_repeticao(materia_q, topico_q, nivel)
        else:
            self.erros += 1
            self.desempenho_por_materia[materia_q]["erros"] += 1
            passos = questao.get("passos", [])
            solucao = "\n".join(passos) if isinstance(passos, list) else str(passos)
            registrar_erro_arena(
                materia=materia_q,
                topico=topico_q,
                enunciado=questao.get("enunciado", ""),
                resposta_usuario=resposta_usuario or "(Em branco)",
                solucao_esperada=solucao
            )
            self._atualizar_topicos_repeticao(materia_q, topico_q, "dificil")

        self._atualizar_placar()
        self._avancar_proxima()

    def _avancar_proxima(self):
        self.indice_atual += 1
        self.exibir_questao_atual()

    def _atualizar_topicos_repeticao(self, materia: str, topico_nome: str, nivel: str):
        """Sincroniza o desempenho com a Fila de Repetição Espaçada em topicos.json."""
        if not os.path.exists("topicos.json"):
            return
        try:
            with open("topicos.json", "r", encoding="utf-8") as f:
                topicos = json.load(f)

            id_encontrado = None
            for t in topicos:
                if t.get("materia", "").lower() in materia.lower() or materia.lower() in t.get("materia", "").lower():
                    if topico_nome.lower() in t.get("topico", "").lower() or t.get("topico", "").lower() in topico_nome.lower():
                        id_encontrado = t.get("id")
                        break

            if id_encontrado:
                registrar_revisao(id_encontrado, nivel, topicos)
        except Exception as e:
            log_erro("Falha ao registrar revisão espaçada", "Arena", exc=e)

    def exibir_tela_final(self):
        self._limpar_layout_conteudo()
        self.progress_bar.setValue(len(self.questoes))

        box = QFrame()
        box.setStyleSheet("background-color: #f8f9fa; border: 1px solid #ced4da; border-radius: 8px; padding: 25px;")
        v = QVBoxLayout(box)

        total = len(self.questoes)
        pct = int((self.acertos / total) * 100) if total > 0 else 0
        cor_pct = "#2e7d32" if pct >= 70 else ("#f57c00" if pct >= 50 else "#c62828")

        linhas_materias = ""
        for mat, st in self.desempenho_por_materia.items():
            tot_m = st["total"]
            ac_m = st["acertos"]
            pct_m = int((ac_m / tot_m) * 100) if tot_m > 0 else 0
            cor_m = "#2e7d32" if pct_m >= 70 else ("#f57c00" if pct_m >= 50 else "#c62828")
            linhas_materias += f"<li><b>{mat}:</b> {ac_m}/{tot_m} acertos (<span style='color: {cor_m}; font-weight: bold;'>{pct_m}%</span>)</li>"

        lbl_resultado = QLabel(
            f"<h2>Simulado Finalizado! 🏁</h2>"
            f"<p style='font-size: 15px;'>Você concluiu todas as <b>{total}</b> questões do simulado.</p>"
            f"<h1 style='color: {cor_pct}; margin: 5px 0;'>{pct}% de Aproveitamento Geral</h1>"
            f"<p style='font-size: 14px;'>✅ <b>Acertos:</b> {self.acertos} &nbsp;&nbsp;|&nbsp;&nbsp; ❌ <b>Erros:</b> {self.erros}</p>"
            f"<hr>"
            f"<h4>📊 Desempenho por Matéria:</h4>"
            f"<ul style='font-size: 13px; line-height: 1.6;'>"
            f"{linhas_materias}"
            f"</ul>"
            f"<hr>"
            f"<p><i>Sua <b>Fila de Estudos</b> foi sincronizada com base nas suas respostas.</i><br>"
            f"<i>Os erros foram anotados e já estão disponíveis no <b>Guru de Estudos</b> para revisão!</i></p>"
        )
        lbl_resultado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl_resultado)

        layout_btns = QHBoxLayout()
        btn_refazer = QPushButton("🔄 Fazer Novamente")
        btn_refazer.setStyleSheet("padding: 8px 16px; font-weight: bold; background-color: #007acc; color: white; border-radius: 6px;")
        btn_refazer.clicked.connect(self.iniciar_simulado)

        btn_gerenciar_mais = QPushButton("📝 Adicionar / Importar Mais Questões")
        btn_gerenciar_mais.setStyleSheet("padding: 8px 16px; font-weight: bold; background-color: #455a64; color: white; border-radius: 6px;")
        btn_gerenciar_mais.clicked.connect(self._abrir_gerenciador_questoes)

        layout_btns.addStretch()
        layout_btns.addWidget(btn_refazer)
        layout_btns.addWidget(btn_gerenciar_mais)
        layout_btns.addStretch()
        v.addLayout(layout_btns)

        self.layout_conteudo.addWidget(box)
