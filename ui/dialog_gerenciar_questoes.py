import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QComboBox, QTabWidget, QWidget, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt

import banco_questoes
from logger import log_info, log_sucesso, log_aviso, log_erro


class DialogGerenciarQuestoes(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📚 Gerenciador de Questões (Cadastro & Importação em Massa)")
        self.resize(880, 640)

        layout_principal = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout_principal.addWidget(self.tabs)

        # 1. Aba Cadastro Individual
        self.tab_individual = self._criar_aba_individual()
        self.tabs.addTab(self.tab_individual, "➕ Adicionar Questão")

        # 2. Aba Importação em Massa
        self.tab_massa = self._criar_aba_massa()
        self.tabs.addTab(self.tab_massa, "🚀 Importação em Massa (10 a 100 Questões)")

        # 3. Aba Ver / Gerenciar Questões
        self.tab_listar = self._criar_aba_listar()
        self.tabs.addTab(self.tab_listar, "📋 Banco Atual de Questões")

        self.tabs.currentChanged.connect(self._ao_trocar_aba)

        # Botão Fechar
        btn_fechar = QPushButton("Concluir e Voltar para a Arena")
        btn_fechar.setStyleSheet("padding: 8px 16px; font-weight: bold; background-color: #007acc; color: white; border-radius: 6px;")
        btn_fechar.clicked.connect(self.accept)
        layout_principal.addWidget(btn_fechar, alignment=Qt.AlignmentFlag.AlignRight)

    def _ao_trocar_aba(self, index: int):
        if index == 0:
            self._atualizar_combos_individual()
        elif index == 2:
            self._carregar_tabela_questoes()

    # ----------------------------------------------------
    # ABA 1: CADASTRO INDIVIDUAL
    # ----------------------------------------------------
    def _criar_aba_individual(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Linha 1: Matéria, Tópico e Tipo
        linha1 = QHBoxLayout()

        linha1.addWidget(QLabel("<b>Matéria:</b>"))
        self.combo_ind_materia = QComboBox()
        self.combo_ind_materia.setEditable(True)
        self.combo_ind_materia.setMinimumWidth(180)
        self.combo_ind_materia.currentTextChanged.connect(self._ao_mudar_materia_ind)
        linha1.addWidget(self.combo_ind_materia)

        linha1.addWidget(QLabel("<b>Tópico:</b>"))
        self.combo_ind_topico = QComboBox()
        self.combo_ind_topico.setEditable(True)
        self.combo_ind_topico.setMinimumWidth(180)
        linha1.addWidget(self.combo_ind_topico)

        linha1.addWidget(QLabel("<b>Tipo:</b>"))
        self.combo_ind_tipo = QComboBox()
        self.combo_ind_tipo.addItem("Múltipla Escolha", "multipla_escolha")
        self.combo_ind_tipo.addItem("Dissertativa", "dissertativa")
        self.combo_ind_tipo.currentIndexChanged.connect(self._ao_mudar_tipo_ind)
        linha1.addWidget(self.combo_ind_tipo)

        layout.addLayout(linha1)

        # Enunciado
        layout.addWidget(QLabel("<b>Enunciado da Questão:</b>"))
        self.txt_ind_enunciado = QTextEdit()
        self.txt_ind_enunciado.setPlaceholderText("Digite aqui o enunciado completo da questão...")
        self.txt_ind_enunciado.setMaximumHeight(90)
        layout.addWidget(self.txt_ind_enunciado)

        # Container Múltipla Escolha
        self.box_multipla = QGroupBox("Alternativas da Questão (Múltipla Escolha)")
        layout_box_m = QVBoxLayout(self.box_multipla)

        self.inputs_opcoes = {}
        for letra in ["A", "B", "C", "D", "E"]:
            h = QHBoxLayout()
            h.addWidget(QLabel(f"<b>{letra})</b>"))
            inp = QLineEdit()
            inp.setPlaceholderText(f"Texto da alternativa {letra}...")
            h.addWidget(inp)
            layout_box_m.addLayout(h)
            self.inputs_opcoes[letra] = inp

        linha_gab_m = QHBoxLayout()
        linha_gab_m.addWidget(QLabel("<b>Alternativa Correta (Gabarito):</b>"))
        self.combo_ind_gabarito = QComboBox()
        for letra in ["A", "B", "C", "D", "E"]:
            self.combo_ind_gabarito.addItem(f"Alternativa {letra}", letra)
        linha_gab_m.addWidget(self.combo_ind_gabarito)
        linha_gab_m.addStretch()
        layout_box_m.addLayout(linha_gab_m)

        layout.addWidget(self.box_multipla)

        # Container Dissertativa
        self.box_dissertativa = QGroupBox("Gabarito Dissertativo")
        layout_box_d = QVBoxLayout(self.box_dissertativa)
        layout_box_d.addWidget(QLabel("Resposta / Conceito Esperado:"))
        self.txt_ind_resposta_dissertativa = QLineEdit()
        self.txt_ind_resposta_dissertativa.setPlaceholderText("Ex: Relação reflexiva, simétrica e transitiva.")
        layout_box_d.addWidget(self.txt_ind_resposta_dissertativa)
        layout.addWidget(self.box_dissertativa)
        self.box_dissertativa.setVisible(False)

        # Resolução Passo a Passo
        layout.addWidget(QLabel("<b>Resolução Passo a Passo / Comentários da Resolução:</b>"))
        self.txt_ind_passos = QTextEdit()
        self.txt_ind_passos.setPlaceholderText("Explique os passos da resolução ou digite a demonstração completa...")
        self.txt_ind_passos.setMaximumHeight(85)
        layout.addWidget(self.txt_ind_passos)

        # Botão Salvar
        btn_salvar = QPushButton("💾 Salvar Esta Questão no Banco")
        btn_salvar.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 9px; border-radius: 6px;")
        btn_salvar.clicked.connect(self._salvar_questao_individual)
        layout.addWidget(btn_salvar)

        self._atualizar_combos_individual()
        return widget

    def _ao_mudar_tipo_ind(self):
        tipo = self.combo_ind_tipo.currentData()
        if tipo == "multipla_escolha":
            self.box_multipla.setVisible(True)
            self.box_dissertativa.setVisible(False)
        else:
            self.box_multipla.setVisible(False)
            self.box_dissertativa.setVisible(True)

    def _atualizar_combos_individual(self):
        materia_atual = self.combo_ind_materia.currentText()
        self.combo_ind_materia.blockSignals(True)
        self.combo_ind_materia.clear()
        materias = banco_questoes.obter_todas_materias()
        if not materias:
            materias = ["Matemática Discreta"]
        for m in materias:
            self.combo_ind_materia.addItem(m)
        if materia_atual:
            self.combo_ind_materia.setEditText(materia_atual)
        self.combo_ind_materia.blockSignals(False)

        self._ao_mudar_materia_ind(self.combo_ind_materia.currentText())

    def _ao_mudar_materia_ind(self, mat: str):
        self.combo_ind_topico.clear()
        topicos = banco_questoes.obter_topicos_por_materia(mat)
        if not topicos:
            topicos = ["Geral"]
        for t in topicos:
            self.combo_ind_topico.addItem(t)

    def _salvar_questao_individual(self):
        materia = self.combo_ind_materia.currentText().strip()
        topico = self.combo_ind_topico.currentText().strip()
        tipo = self.combo_ind_tipo.currentData()
        enunciado = self.txt_ind_enunciado.toPlainText().strip()

        if not materia:
            QMessageBox.warning(self, "Aviso", "Por favor, informe a matéria da questão.")
            return
        if not topico:
            topico = "Geral"
        if not enunciado:
            QMessageBox.warning(self, "Aviso", "O enunciado da questão não pode ficar em branco.")
            return

        opcoes = []
        resposta_correta = ""

        if tipo == "multipla_escolha":
            for letra in ["A", "B", "C", "D", "E"]:
                txt_op = self.inputs_opcoes[letra].text().strip()
                if txt_op:
                    opcoes.append(f"{letra}) {txt_op}")
            if len(opcoes) < 2:
                QMessageBox.warning(self, "Aviso", "Preencha pelo menos duas alternativas (ex: A e B).")
                return
            resposta_correta = self.combo_ind_gabarito.currentData()
        else:
            resposta_correta = self.txt_ind_resposta_dissertativa.text().strip()

        passos_txt = self.txt_ind_passos.toPlainText().strip()
        passos = [p.strip() for p in passos_txt.splitlines() if p.strip()] if passos_txt else [f"Gabarito: {resposta_correta}"]

        nova_q = {
            "materia": materia,
            "topico": topico,
            "tipo": tipo,
            "enunciado": enunciado,
            "opcoes": opcoes,
            "resposta_correta": resposta_correta,
            "passos": passos
        }

        banco_questoes.adicionar_questao_individual(nova_q)
        QMessageBox.information(self, "Sucesso", "🎉 Questão cadastrada com sucesso no banco!")

        # Limpa campos
        self.txt_ind_enunciado.clear()
        for inp in self.inputs_opcoes.values():
            inp.clear()
        self.txt_ind_resposta_dissertativa.clear()
        self.txt_ind_passos.clear()

    # ----------------------------------------------------
    # ABA 2: IMPORTAÇÃO EM MASSA (BULK IMPORT)
    # ----------------------------------------------------
    def _criar_aba_massa(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lbl_desc = QLabel(
            "<b>Cole abaixo de 10 a 100 questões de uma só vez!</b><br>"
            "<small style='color: #555;'>Você pode colar questões geradas no ChatGPT, DeepSeek, Claude ou extraídas de provas. O sistema identifica enunciados, alternativas e gabarito automaticamente!</small>"
        )
        layout.addWidget(lbl_desc)

        # Linha de matéria e tópico padrão
        linha_padrao = QHBoxLayout()
        linha_padrao.addWidget(QLabel("Matéria Padrão (se não especificada no texto):"))
        self.input_massa_materia = QLineEdit("Matemática Discreta")
        linha_padrao.addWidget(self.input_massa_materia)

        linha_padrao.addWidget(QLabel("Tópico Padrão:"))
        self.input_massa_topico = QLineEdit("Geral")
        linha_padrao.addWidget(self.input_massa_topico)
        layout.addLayout(linha_padrao)

        # Botões de Modelos Prontos
        linha_modelos = QHBoxLayout()
        linha_modelos.addWidget(QLabel("<b>Modelos de Exemplo:</b>"))

        btn_mod_mc = QPushButton("📄 Exemplo Múltipla Escolha")
        btn_mod_mc.setStyleSheet("font-size: 11px; padding: 4px;")
        btn_mod_mc.clicked.connect(self._carregar_modelo_multipla)
        linha_modelos.addWidget(btn_mod_mc)

        btn_mod_diss = QPushButton("📄 Exemplo Dissertativa")
        btn_mod_diss.setStyleSheet("font-size: 11px; padding: 4px;")
        btn_mod_diss.clicked.connect(self._carregar_modelo_dissertativa)
        linha_modelos.addWidget(btn_mod_diss)

        btn_mod_json = QPushButton("📄 Exemplo JSON")
        btn_mod_json.setStyleSheet("font-size: 11px; padding: 4px;")
        btn_mod_json.clicked.connect(self._carregar_modelo_json)
        linha_modelos.addWidget(btn_mod_json)

        linha_modelos.addStretch()
        layout.addLayout(linha_modelos)

        # Caixa de Texto
        self.txt_massa = QTextEdit()
        self.txt_massa.setPlaceholderText("Cole aqui suas dezenas de questões...")
        self.txt_massa.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        layout.addWidget(self.txt_massa)

        # Botão Importar
        self.btn_importar_massa = QPushButton("⚡ Processar e Importar Questões para o Banco")
        self.btn_importar_massa.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 12px; border-radius: 6px; font-size: 14px;")
        self.btn_importar_massa.clicked.connect(self._processar_importacao_massa)
        layout.addWidget(self.btn_importar_massa)

        return widget

    def _carregar_modelo_multipla(self):
        modelo = (
            "MATERIA: Matemática Discreta\n"
            "TOPICO: Relações Binárias\n"
            "ENUNCIADO: Seja R uma relação sobre um conjunto A. Se (a, a) pertence a R para todo a em A, R é:\n"
            "A) Simétrica\n"
            "B) Reflexiva\n"
            "C) Transitiva\n"
            "D) Antissimétrica\n"
            "GABARITO: B\n"
            "RESOLUCAO: Por definição formal, reflexividade exige que cada elemento esteja relacionado a si próprio.\n"
            "---\n"
            "MATERIA: Matemática Discreta\n"
            "TOPICO: Teoria dos Grafos\n"
            "ENUNCIADO: Qual o número mínimo de cores necessárias para colorir um grafo planar, segundo o Teorema das Quatro Cores?\n"
            "A) 2\n"
            "B) 3\n"
            "C) 4\n"
            "D) 5\n"
            "GABARITO: C\n"
            "RESOLUCAO: O célebre Teorema das Quatro Cores garante que todo grafo planar pode ser colorido com no máximo 4 cores.\n"
        )
        self.txt_massa.setPlainText(modelo)

    def _carregar_modelo_dissertativa(self):
        modelo = (
            "MATERIA: Matemática Discreta\n"
            "TOPICO: Diagramas de Hasse\n"
            "TIPO: dissertativa\n"
            "ENUNCIADO: Explique por que no Diagrama de Hasse as arestas de transitividade e reflexividade não são desenhadas.\n"
            "GABARITO: Porque são redundantes e estão implícitas na ordem vertical.\n"
            "RESOLUCAO: O diagrama de Hasse omite loops de reflexividade e arestas transitivas para deixar a representação limpa e sem poluição visual.\n"
        )
        self.txt_massa.setPlainText(modelo)

    def _carregar_modelo_json(self):
        modelo = json.dumps([
            {
                "materia": "Matemática Discreta",
                "topico": "Relações",
                "tipo": "multipla_escolha",
                "enunciado": "Quantas relações binárias existem em um conjunto de 3 elementos?",
                "opcoes": ["A) 9", "B) 27", "C) 512", "D) 1024"],
                "resposta_correta": "C",
                "passos": ["Um conjunto com n elementos tem 2^(n^2) relações. Para n=3, 2^(3^2) = 2^9 = 512."]
            }
        ], indent=4, ensure_ascii=False)
        self.txt_massa.setPlainText(modelo)

    def _processar_importacao_massa(self):
        texto = self.txt_massa.toPlainText().strip()
        if not texto:
            QMessageBox.warning(self, "Aviso", "Por favor, cole o texto das questões antes de importar.")
            return

        mat_padrao = self.input_massa_materia.text().strip() or "Matemática Discreta"
        top_padrao = self.input_massa_topico.text().strip() or "Geral"

        questoes = banco_questoes.parser_importacao_em_massa(
            texto=texto,
            materia_padrao=mat_padrao,
            topico_padrao=top_padrao
        )

        if not questoes:
            QMessageBox.warning(
                self, "Erro na leitura",
                "Não foi possível extrair nenhuma questão do texto colado.<br>"
                "Verifique os modelos de exemplo acima para o formato esperado."
            )
            return

        # Adiciona ao banco
        total_adicionadas = 0
        for q in questoes:
            if banco_questoes.adicionar_questao_individual(q):
                total_adicionadas += 1

        QMessageBox.information(
            self, "Importação Concluída com Sucesso! 🚀",
            f"🎉 <b>{total_adicionadas} questão(ões)</b> foram processadas e salvas com sucesso no banco de questões!<br><br>"
            f"Elas já estão disponíveis para você praticar na <b>Arena</b> por matéria e tópico!"
        )
        self.txt_massa.clear()
        self._carregar_tabela_questoes()
        self.tabs.setCurrentIndex(2)

    # ----------------------------------------------------
    # ABA 3: LISTAGEM E GERENCIAMENTO
    # ----------------------------------------------------
    def _criar_aba_listar(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Filtros
        linha_filtros = QHBoxLayout()
        linha_filtros.addWidget(QLabel("Filtrar por Matéria:"))
        self.combo_filtro_materia = QComboBox()
        self.combo_filtro_materia.currentIndexChanged.connect(self._carregar_tabela_questoes)
        linha_filtros.addWidget(self.combo_filtro_materia)

        linha_filtros.addWidget(QLabel("Tópico:"))
        self.combo_filtro_topico = QComboBox()
        self.combo_filtro_topico.currentIndexChanged.connect(self._carregar_tabela_questoes)
        linha_filtros.addWidget(self.combo_filtro_topico)

        self.lbl_total_banco = QLabel("Total: 0 questões")
        self.lbl_total_banco.setStyleSheet("font-weight: bold; color: #1a237e;")
        linha_filtros.addStretch()
        linha_filtros.addWidget(self.lbl_total_banco)
        layout.addLayout(linha_filtros)

        # Tabela
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6)
        self.tabela.setHorizontalHeaderLabels(["ID", "Matéria", "Tópico", "Tipo", "Gabarito", "Enunciado"])
        self.tabela.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabela)

        # Botões de Ação
        linha_acoes = QHBoxLayout()
        btn_recarregar = QPushButton("🔄 Atualizar Lista")
        btn_recarregar.clicked.connect(self._carregar_tabela_questoes)
        linha_acoes.addWidget(btn_recarregar)

        btn_excluir = QPushButton("🗑️ Excluir Questão Selecionada")
        btn_excluir.setStyleSheet("color: #c62828; font-weight: bold;")
        btn_excluir.clicked.connect(self._excluir_selecionada)
        linha_acoes.addWidget(btn_excluir)

        linha_acoes.addStretch()
        layout.addLayout(linha_acoes)

        return widget

    def _carregar_tabela_questoes(self):
        # Atualiza combos de filtro se necessário
        mat_sel = self.combo_filtro_materia.currentText()
        self.combo_filtro_materia.blockSignals(True)
        self.combo_filtro_materia.clear()
        self.combo_filtro_materia.addItem("🎯 Todas as Matérias")
        for m in banco_questoes.obter_todas_materias():
            self.combo_filtro_materia.addItem(m)
        if mat_sel:
            self.combo_filtro_materia.setCurrentText(mat_sel)
        self.combo_filtro_materia.blockSignals(False)

        mat_atual = self.combo_filtro_materia.currentText()
        m_filtro = None if "todas" in mat_atual.lower() else mat_atual

        top_sel = self.combo_filtro_topico.currentText()
        self.combo_filtro_topico.blockSignals(True)
        self.combo_filtro_topico.clear()
        self.combo_filtro_topico.addItem("📌 Todos os Tópicos")
        for t in banco_questoes.obter_topicos_por_materia(m_filtro):
            self.combo_filtro_topico.addItem(t)
        if top_sel:
            self.combo_filtro_topico.setCurrentText(top_sel)
        self.combo_filtro_topico.blockSignals(False)

        top_atual = self.combo_filtro_topico.currentText()
        t_filtro = None if "todos" in top_atual.lower() else top_atual

        questoes = banco_questoes.filtrar_questoes(materia=m_filtro, topico=t_filtro)
        self.lbl_total_banco.setText(f"Exibindo: {len(questoes)} questão(ões)")

        self.tabela.setRowCount(len(questoes))
        for row, q in enumerate(questoes):
            self.tabela.setItem(row, 0, QTableWidgetItem(str(q.get("id", ""))))
            self.tabela.setItem(row, 1, QTableWidgetItem(str(q.get("materia", ""))))
            self.tabela.setItem(row, 2, QTableWidgetItem(str(q.get("topico", ""))))
            self.tabela.setItem(row, 3, QTableWidgetItem("Múlt. Escolha" if q.get("tipo") == "multipla_escolha" else "Dissertativa"))
            self.tabela.setItem(row, 4, QTableWidgetItem(str(q.get("resposta_correta", ""))))
            enunc = q.get("enunciado", "").replace("\n", " ")
            self.tabela.setItem(row, 5, QTableWidgetItem(enunc[:120] + ("..." if len(enunc) > 120 else "")))

    def _excluir_selecionada(self):
        row = self.tabela.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Aviso", "Selecione uma linha na tabela para excluir.")
            return

        id_q = self.tabela.item(row, 0).text()
        confirma = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Tem certeza que deseja excluir a questão {id_q}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirma == QMessageBox.StandardButton.Yes:
            if banco_questoes.excluir_questao(id_q):
                QMessageBox.information(self, "Sucesso", "Questão removida do banco.")
                self._carregar_tabela_questoes()
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível remover a questão.")
