import json
import os
import re
import unicodedata
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QFrame, QMessageBox, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt

from organizador_estudos import registrar_revisao
from organizador_pastas import resolver_caminho
from ollama_client import registrar_erro_arena, carregar_conhecimento_materia
from logger import log_info, log_sucesso, log_aviso, log_erro


class TabArena(QWidget):
    def __init__(self):
        super().__init__()

        self.questoes = []
        self.indice_atual = 0
        self.acertos = 0
        self.erros = 0
        self.materia_atual = ""

        layout_externo = QVBoxLayout(self)

        # 1. Barra Superior (Seleção de Matéria e Status)
        barra_topo = QHBoxLayout()
        lbl_titulo = QLabel("⚔️ <b>Arena de Estudos</b>")
        lbl_titulo.setStyleSheet("font-size: 16px; color: #1a237e;")

        self.combo_materia = QComboBox()
        self.combo_materia.setMinimumWidth(200)
        self.combo_materia.currentIndexChanged.connect(self._ao_mudar_materia)

        self.btn_iniciar = QPushButton("🚀 Iniciar Simulado")
        self.btn_iniciar.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_iniciar.clicked.connect(self.iniciar_simulado)

        self.lbl_score = QLabel("Acertos: 0 | Erros: 0")
        self.lbl_score.setStyleSheet("font-weight: bold; color: #333;")

        barra_topo.addWidget(lbl_titulo)
        barra_topo.addSpacing(15)
        barra_topo.addWidget(QLabel("Matéria:"))
        barra_topo.addWidget(self.combo_materia)
        barra_topo.addWidget(self.btn_iniciar)
        barra_topo.addStretch()
        barra_topo.addWidget(self.lbl_score)
        layout_externo.addLayout(barra_topo)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout_externo.addWidget(self.progress_bar)

        # 2. Área Central de Conteúdo com Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container_questao = QWidget()
        self.layout_conteudo = QVBoxLayout(self.container_questao)
        self.layout_conteudo.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.container_questao)
        layout_externo.addWidget(scroll)

        # Carrega as matérias disponíveis
        self.atualizar_materias_disponiveis()
        self._exibir_tela_inicial()

    def atualizar_materias_disponiveis(self):
        """Preenche o combo com matérias cadastradas e que possuem conhecimento."""
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

    def _ao_mudar_materia(self):
        pass

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
        box.setStyleSheet("background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 25px;")
        v = QVBoxLayout(box)

        lbl = QLabel(
            "<h3>Bem-vindo à Arena de Questões e Simulados! 🎯</h3>"
            "<p>Aqui você testa seus conhecimentos com as questões reais extraídas e compiladas pela IA.</p>"
            "<ul>"
            "<li>Selecione a matéria acima e clique em <b>Iniciar Simulado</b>.</li>"
            "<li>Resolva a questão no campo de resposta.</li>"
            "<li>Ao conferir a resposta, sua curva de repetição espaçada é <b>atualizada automaticamente</b>!</li>"
            "<li>Os erros cometidos aqui são enviados para o <b>Guru de Estudos</b>, que focará exatamente nas suas dificuldades.</li>"
            "</ul>"
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 13px; line-height: 1.5;")
        v.addWidget(lbl)
        self.layout_conteudo.addWidget(box)

    def iniciar_simulado(self):
        materia = self.combo_materia.currentText()
        if not materia:
            QMessageBox.warning(self, "Aviso", "Selecione uma matéria!")
            return

        self.materia_atual = materia
        dados = carregar_conhecimento_materia(materia)
        exercicios = dados.get("exercicios_resolvidos", [])

        if not exercicios:
            QMessageBox.information(
                self, "Sem Questões",
                f"Nenhuma questão encontrada para a matéria '{materia}'.\n"
                f"Gere primeiro uma apostila no Fabriqueiro para extrair as questões!"
            )
            return

        self.questoes = exercicios
        self.indice_atual = 0
        self.acertos = 0
        self.erros = 0
        self.progress_bar.setMaximum(len(self.questoes))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.lbl_score.setText(f"Acertos: 0 | Erros: 0")
        log_info(f"Iniciando simulado da matéria '{materia}' com {len(exercicios)} questões.", "Arena")

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

        # Card Principal da Questão
        card_q = QFrame()
        card_q.setStyleSheet("background-color: #ffffff; border: 1px solid #ced4da; border-radius: 8px; padding: 16px;")
        layout_q = QVBoxLayout(card_q)

        lbl_header = QLabel(f"<b>Questão {num_q} de {total_q}</b> — <span style='color: #007acc;'>{self.materia_atual}</span>")
        lbl_header.setStyleSheet("font-size: 14px;")

        enunciado = questao.get("enunciado", "")
        lbl_enunciado = QLabel(enunciado)
        lbl_enunciado.setWordWrap(True)
        lbl_enunciado.setStyleSheet("font-size: 14px; margin: 10px 0; padding: 10px; background-color: #f1f8ff; border-radius: 6px;")

        lbl_instrucao = QLabel("<b>Sua Resolução / Resposta:</b>")
        self.txt_resposta = QTextEdit()
        self.txt_resposta.setPlaceholderText("Digite aqui sua resposta, raciocínio ou resultado...")
        self.txt_resposta.setMinimumHeight(100)

        # Botão de verificar
        self.btn_verificar = QPushButton("🔍 Conferir Gabarito e Solução Passo a Passo")
        self.btn_verificar.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 8px;")
        self.btn_verificar.clicked.connect(self.verificar_resposta)

        layout_q.addWidget(lbl_header)
        layout_q.addWidget(lbl_enunciado)
        layout_q.addWidget(lbl_instrucao)
        layout_q.addWidget(self.txt_resposta)
        layout_q.addWidget(self.btn_verificar)

        # Área de gabarito (inicialmente oculta)
        self.frame_gabarito = QFrame()
        self.frame_gabarito.setStyleSheet("background-color: #fdfdfd; border: 1px solid #c3e6cb; border-radius: 6px; padding: 12px;")
        layout_gab = QVBoxLayout(self.frame_gabarito)

        lbl_titulo_gab = QLabel("<b>📖 Resolução Passo a Passo:</b>")
        lbl_titulo_gab.setStyleSheet("color: #155724; font-size: 14px;")
        layout_gab.addWidget(lbl_titulo_gab)

        passos = questao.get("passos", [])
        passos_txt = "\n".join([f"• {p}" for p in passos]) if isinstance(passos, list) else str(passos)
        lbl_passos = QLabel(passos_txt)
        lbl_passos.setWordWrap(True)
        lbl_passos.setStyleSheet("font-size: 13px; color: #212529; line-height: 1.4; padding: 8px;")
        layout_gab.addWidget(lbl_passos)

        # Botões de Auto-Avaliação para atualizar curva de repetição espaçada
        lbl_autoaval = QLabel("<b>Como foi seu desempenho nesta questão?</b> (Atualizará sua fila de estudos)")
        lbl_autoaval.setStyleSheet("margin-top: 10px;")
        layout_gab.addWidget(lbl_autoaval)

        layout_botoes_aval = QHBoxLayout()
        btn_acerto_facil = QPushButton("🟢 Acertei com Facilidade (+ Intervalo)")
        btn_acerto_facil.setStyleSheet("background-color: #e8f5e9; color: #2e7d32; font-weight: bold; padding: 8px;")
        btn_acerto_facil.clicked.connect(lambda: self.avaliar_questao("facil"))

        btn_acerto_medio = QPushButton("🔵 Acertei com Esforço (~ Intervalo)")
        btn_acerto_medio.setStyleSheet("background-color: #e1f5fe; color: #0277bd; font-weight: bold; padding: 8px;")
        btn_acerto_medio.clicked.connect(lambda: self.avaliar_questao("medio"))

        btn_erro = QPushButton("🔴 Errei / Não Soube (Revisar Amanhã)")
        btn_erro.setStyleSheet("background-color: #ffebee; color: #c62828; font-weight: bold; padding: 8px;")
        btn_erro.clicked.connect(lambda: self.avaliar_questao("dificil"))

        layout_botoes_aval.addWidget(btn_acerto_facil)
        layout_botoes_aval.addWidget(btn_acerto_medio)
        layout_botoes_aval.addWidget(btn_erro)
        layout_gab.addLayout(layout_botoes_aval)

        self.frame_gabarito.setVisible(False)
        layout_q.addWidget(self.frame_gabarito)

        self.layout_conteudo.addWidget(card_q)

    def verificar_resposta(self):
        resposta_usuario = self.txt_resposta.toPlainText().strip()
        if not resposta_usuario:
            resp = QMessageBox.question(
                self, "Resposta em branco",
                "Você não digitou nenhuma resposta. Deseja ver o gabarito mesmo assim?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                return

        self.btn_verificar.setEnabled(False)
        self.frame_gabarito.setVisible(True)

    def avaliar_questao(self, nivel: str):
        questao = self.questoes[self.indice_atual]
        enunciado = questao.get("enunciado", "")
        passos = questao.get("passos", [])
        solucao_str = "\n".join(passos) if isinstance(passos, list) else str(passos)
        resposta_usuario = self.txt_resposta.toPlainText().strip()

        # Encontra se existe um tópico correspondente em topicos.json para atualizar
        topico_id = self._encontrar_topico_id_para_questao(enunciado)

        if nivel in ("facil", "medio"):
            self.acertos += 1
            log_sucesso(f"Questão {self.indice_atual+1} avaliada como '{nivel.upper()}'. Acertos: {self.acertos}, Erros: {self.erros}.", "Arena")
            if topico_id:
                try:
                    with open("topicos.json", "r", encoding="utf-8") as f:
                        topicos = json.load(f)
                    registrar_revisao(topico_id, nivel, topicos)
                except Exception as e:
                    log_erro(f"Erro ao registrar revisão do tópico {topico_id}", "Arena", exc=e)
        else:
            self.erros += 1
            nome_topico_err = self._extrair_nome_topico_questao(enunciado)
            log_aviso(f"Questão {self.indice_atual+1} marcada como ERRO no tópico '{nome_topico_err}'.", "Arena")
            # Registra o erro no histórico da Arena para o Guru saber
            registrar_erro_arena(
                materia=self.materia_atual,
                topico=nome_topico_err,
                enunciado=enunciado,
                resposta_usuario=resposta_usuario or "(Em branco)",
                solucao_esperada=solucao_str
            )
            # Atualiza a curva de esquecimento para voltar rápido (dificil -> intervalo 1)
            if topico_id:
                try:
                    with open("topicos.json", "r", encoding="utf-8") as f:
                        topicos = json.load(f)
                    registrar_revisao(topico_id, "dificil", topicos)
                except Exception as e:
                    log_erro(f"Erro ao registrar rebaixamento do tópico {topico_id}", "Arena", exc=e)

        self.lbl_score.setText(f"Acertos: {self.acertos} | Erros: {self.erros}")
        self.indice_atual += 1
        self.exibir_questao_atual()

    def _encontrar_topico_id_para_questao(self, enunciado: str) -> int:
        """Tenta associar a questão a um tópico de topicos.json por palavra-chave."""
        if not os.path.exists("topicos.json"):
            return None
        try:
            with open("topicos.json", "r", encoding="utf-8") as f:
                topicos = json.load(f)

            enunciado_norm = enunciado.lower()
            for t in topicos:
                nome_topico = t.get("topico", "").lower()
                if nome_topico and nome_topico in enunciado_norm:
                    return t.get("id")

            # Se não achou por correspondência exata, associa ao primeiro da mesma matéria
            for t in topicos:
                if t.get("materia", "").lower() in self.materia_atual.lower():
                    return t.get("id")

            return topicos[0].get("id") if topicos else None
        except Exception:
            return None

    def _extrair_nome_topico_questao(self, enunciado: str) -> str:
        """Extrai um resumo curto do tópico da questão."""
        match = re.search(r"Exerc[íi]cio\s+[\d\.]+", enunciado, re.IGNORECASE)
        if match:
            return match.group(0)
        return enunciado[:40] + "..."

    def exibir_tela_final(self):
        self._limpar_layout_conteudo()
        self.progress_bar.setValue(len(self.questoes))

        box = QFrame()
        box.setStyleSheet("background-color: #f8f9fa; border: 1px solid #ced4da; border-radius: 8px; padding: 25px;")
        v = QVBoxLayout(box)

        total = len(self.questoes)
        pct = int((self.acertos / total) * 100) if total > 0 else 0

        cor_pct = "#2e7d32" if pct >= 70 else ("#f57c00" if pct >= 50 else "#c62828")
        log_sucesso(f"Simulado finalizado para '{self.materia_atual}': {self.acertos} acertos, {self.erros} erros ({pct}% de aproveitamento).", "Arena")

        lbl_resultado = QLabel(
            f"<h2>Simulado Finalizado! 🏁</h2>"
            f"<p style='font-size: 16px;'>Você concluiu todas as <b>{total}</b> questões de <b>{self.materia_atual}</b>.</p>"
            f"<h1 style='color: {cor_pct};'>{pct}% de Aproveitamento</h1>"
            f"<p style='font-size: 14px;'>✅ <b>Acertos:</b> {self.acertos} &nbsp;&nbsp;|&nbsp;&nbsp; ❌ <b>Erros:</b> {self.erros}</p>"
            f"<hr>"
            f"<p><i>Sua <b>Fila de Estudos</b> foi sincronizada com base nas suas respostas.</i><br>"
            f"<i>Os erros foram anotados e já estão disponíveis no <b>Guru de Estudos</b> para tirar dúvidas!</i></p>"
        )
        lbl_resultado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl_resultado)

        layout_btns = QHBoxLayout()
        btn_refazer = QPushButton("🔄 Fazer Novamente")
        btn_refazer.clicked.connect(self.iniciar_simulado)

        layout_btns.addStretch()
        layout_btns.addWidget(btn_refazer)
        layout_btns.addStretch()
        v.addLayout(layout_btns)

        self.layout_conteudo.addWidget(box)
