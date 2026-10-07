import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QMessageBox, QLineEdit, QComboBox, QTextEdit, QGroupBox, QListWidget,
    QSplitter, QApplication
)
from PyQt6.QtCore import Qt

import banco_questoes
from ai_worker import FabriqueiroWorker
from logger import log_info, log_sucesso, log_aviso, log_erro
from credenciais import carregar_gemini_api_key, salvar_gemini_api_key


class TabFabriqueiro(QWidget):
    def __init__(self):
        super().__init__()

        self.caminhos_arquivos = []
        self.worker_ia = None

        layout_externo = QVBoxLayout(self)
        layout_externo.setSpacing(8)

        # Cabeçalho
        lbl_titulo = QLabel("🏭 <b>O Fabriqueiro</b>: Central de Prompts Padronizados & Customizados")
        lbl_titulo.setStyleSheet("font-size: 15px; color: #1a237e;")
        lbl_desc = QLabel(
            "Junte seus arquivos (PDFs, fotos de lousa, listas) e suas matérias para criar <b>prompts profissionais e padronizados</b>.<br>"
            "<small style='color: #555;'>Copie o prompt perfeito para colar no ChatGPT, Claude ou Gemini Web, ou execute diretamente se desejar!</small>"
        )
        layout_externo.addWidget(lbl_titulo)
        layout_externo.addWidget(lbl_desc)

        # Splitter Principal: Esquerda = Configuração e Arquivos, Direita = Prompt Gerado
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # -----------------------------------------------------------------
        # PAINEL ESQUERDO: CONFIGURAÇÃO, MATÉRIAS E ARQUIVOS
        # -----------------------------------------------------------------
        painel_esq = QWidget()
        layout_esq = QVBoxLayout(painel_esq)
        layout_esq.setSpacing(8)

        # 1. Matéria e Tópico
        box_materia = QGroupBox("1. Selecione a Matéria e o Tópico")
        layout_box_mat = QVBoxLayout(box_materia)

        linha_mat = QHBoxLayout()
        linha_mat.addWidget(QLabel("Matéria:"))
        self.combo_materia = QComboBox()
        self.combo_materia.setEditable(True)
        self.combo_materia.setMinimumWidth(180)
        self.combo_materia.currentTextChanged.connect(self._ao_mudar_materia)
        linha_mat.addWidget(self.combo_materia)
        layout_box_mat.addLayout(linha_mat)

        linha_top = QHBoxLayout()
        linha_top.addWidget(QLabel("Tópico:"))
        self.combo_topico = QComboBox()
        self.combo_topico.setEditable(True)
        self.combo_topico.setMinimumWidth(180)
        linha_top.addWidget(self.combo_topico)
        layout_box_mat.addLayout(linha_top)

        layout_esq.addWidget(box_materia)

        # 2. Seleção de Arquivos
        box_arqs = QGroupBox("2. Arquivos Associados (PDFs, Fotos da Lousa, Listas)")
        layout_box_arqs = QVBoxLayout(box_arqs)

        linha_btn_arqs = QHBoxLayout()
        btn_add_arq = QPushButton("📁 Adicionar Arquivos...")
        btn_add_arq.setStyleSheet("font-weight: bold; padding: 5px;")
        btn_add_arq.clicked.connect(self._selecionar_arquivos)

        btn_limpar_arqs = QPushButton("🧹 Limpar Lista")
        btn_limpar_arqs.clicked.connect(self._limpar_arquivos)

        linha_btn_arqs.addWidget(btn_add_arq)
        linha_btn_arqs.addWidget(btn_limpar_arqs)
        layout_box_arqs.addLayout(linha_btn_arqs)

        self.lista_arqs_widget = QListWidget()
        self.lista_arqs_widget.setMaximumHeight(85)
        layout_box_arqs.addWidget(self.lista_arqs_widget)

        layout_esq.addWidget(box_arqs)

        # 3. Modelo Padronizado de Prompt
        box_modelo = QGroupBox("3. Tipo de Material / Modelo Padronizado")
        layout_box_mod = QVBoxLayout(box_modelo)

        self.combo_modelo = QComboBox()
        self.combo_modelo.addItem("🎯 50 a 100 Questões para Importar na Arena (Múltipla Escolha + Gabarito)", "questoes_arena")
        self.combo_modelo.addItem("📋 Resolução Completa Passo a Passo de Exercícios", "resolucao_lista")
        self.combo_modelo.addItem("📖 Resumo Teórico Aprofundado & Tabela de Fórmulas", "teoria_formulas")
        self.combo_modelo.addItem("⚠️ Simulado de Prova & Alerta de Pegadinhas Clássicas", "simulado_pegadinhas")
        self.combo_modelo.addItem("🃏 Flashcards & Perguntas Rápidas de Fixação", "flashcards")
        self.combo_modelo.currentIndexChanged.connect(self._ao_trocar_modelo)
        layout_box_mod.addWidget(self.combo_modelo)

        layout_esq.addWidget(box_modelo)

        # 4. Customizações Específicas do Aluno
        box_custom = QGroupBox("4. Instruções Customizadas (Opcional)")
        layout_box_cust = QVBoxLayout(box_custom)

        self.txt_custom = QTextEdit()
        self.txt_custom.setPlaceholderText(
            "Ex: 'Focar em relações de equivalência e diagramas de Hasse', 'Nível de dificuldade alto', 'Não pular contas'."
        )
        self.txt_custom.setMaximumHeight(65)
        layout_box_cust.addWidget(self.txt_custom)

        # Chips de sugestão rápida
        linha_chips = QHBoxLayout()
        chip1 = QPushButton("+ Nível Difícil")
        chip1.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        chip1.clicked.connect(lambda: self._inserir_chip("Exigir nível de dificuldade alto, com pegadinhas comuns em provas."))

        chip2 = QPushButton("+ Cálculos Detalhados")
        chip2.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        chip2.clicked.connect(lambda: self._inserir_chip("Mostrar todos os passos algébricos e justificativas formais."))

        chip3 = QPushButton("+ Formato Compacto")
        chip3.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        chip3.clicked.connect(lambda: self._inserir_chip("Ser direto ao ponto e objetivo, sem enrolação."))

        linha_chips.addWidget(chip1)
        linha_chips.addWidget(chip2)
        linha_chips.addWidget(chip3)
        linha_chips.addStretch()
        layout_box_cust.addLayout(linha_chips)

        layout_esq.addWidget(box_custom)

        # Botão Gerador de Prompt
        btn_gerar_prompt = QPushButton("⚡ Montar Prompt Padronizado & Customizado")
        btn_gerar_prompt.setStyleSheet("background-color: #4f46e5; color: white; font-weight: bold; font-size: 13px; padding: 11px; border-radius: 8px;")
        btn_gerar_prompt.clicked.connect(self.montar_prompt)
        layout_esq.addWidget(btn_gerar_prompt)

        splitter.addWidget(painel_esq)

        # -----------------------------------------------------------------
        # PAINEL DIREITO: PROMPT MONTADO & AÇÕES DE CÓPIA / EXECUÇÃO
        # -----------------------------------------------------------------
        painel_dir = QWidget()
        layout_dir = QVBoxLayout(painel_dir)
        layout_dir.setSpacing(10)

        lbl_tit_saida = QLabel("<b>📋 Prompt Gerado (Pronto para Copiar ou Executar):</b>")
        lbl_tit_saida.setStyleSheet("color: #0f172a; font-size: 13px;")
        layout_dir.addWidget(lbl_tit_saida)

        self.txt_prompt_gerado = QTextEdit()
        self.txt_prompt_gerado.setPlaceholderText("Clique em 'Montar Prompt' para gerar a estrutura completa...")
        self.txt_prompt_gerado.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Fira Code', 'Cascadia Code', monospace;
                font-size: 12.5px;
                background-color: #0f172a;
                color: #f8fafc;
                border: 1.5px solid #334155;
                border-radius: 10px;
                padding: 14px;
                line-height: 1.5;
                selection-background-color: #4f46e5;
                selection-color: #ffffff;
            }
        """)
        layout_dir.addWidget(self.txt_prompt_gerado)

        # Barra de Ações do Prompt
        linha_acoes = QHBoxLayout()

        btn_copiar = QPushButton("📋 Copiar Prompt")
        btn_copiar.setStyleSheet("background-color: #10b981; color: white; font-weight: bold; padding: 9px 18px; border-radius: 8px; font-size: 13px;")
        btn_copiar.clicked.connect(self._copiar_prompt)

        btn_salvar_txt = QPushButton("💾 Salvar em .txt")
        btn_salvar_txt.setStyleSheet("background-color: #ffffff; color: #334155; border: 1.5px solid #cbd5e1; font-weight: bold; padding: 9px 14px; border-radius: 8px;")
        btn_salvar_txt.clicked.connect(self._salvar_prompt_txt)

        linha_acoes.addWidget(btn_copiar)
        linha_acoes.addWidget(btn_salvar_txt)
        linha_acoes.addStretch()
        layout_dir.addLayout(linha_acoes)

        # Opção de Execução via API
        box_api = QGroupBox("Execução Direta via API Gemini (Opcional)")
        layout_box_api = QHBoxLayout(box_api)

        self.btn_executar_api = QPushButton("✨ Executar via Gemini API")
        self.btn_executar_api.setStyleSheet("background-color: #6366f1; color: white; font-weight: bold; padding: 7px 14px; border-radius: 7px;")
        self.btn_executar_api.clicked.connect(self._executar_via_api)

        self.lbl_status_api = QLabel("Pronto.")
        self.lbl_status_api.setStyleSheet("color: #666; font-size: 11px;")

        layout_box_api.addWidget(self.btn_executar_api)
        layout_box_api.addWidget(self.lbl_status_api)
        layout_box_api.addStretch()
        layout_dir.addWidget(box_api)

        splitter.addWidget(painel_dir)
        splitter.setSizes([450, 470])
        layout_externo.addWidget(splitter)

        self._carregar_materias()

    def _carregar_materias(self):
        self.combo_materia.blockSignals(True)
        self.combo_materia.clear()
        materias = banco_questoes.obter_todas_materias()
        if not materias:
            materias = ["Matemática Discreta"]
        for m in materias:
            self.combo_materia.addItem(m)
        self.combo_materia.blockSignals(False)

        self._ao_mudar_materia(self.combo_materia.currentText())

    def _ao_mudar_materia(self, mat: str):
        self.combo_topico.blockSignals(True)
        self.combo_topico.clear()
        topicos = banco_questoes.obter_topicos_por_materia(mat)
        if not topicos:
            topicos = ["Geral"]
        for t in topicos:
            self.combo_topico.addItem(t)
        self.combo_topico.blockSignals(False)

    def _selecionar_arquivos(self):
        caminhos, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar Arquivos ou Fotos de Estudo", "",
            "Arquivos Suportados (*.pdf *.png *.jpg *.jpeg *.txt);;Todos (*.*)"
        )
        if caminhos:
            for c in caminhos:
                if c not in self.caminhos_arquivos:
                    self.caminhos_arquivos.append(c)
                    self.lista_arqs_widget.addItem(f"📄 {Path(c).name}")
            log_info(f"{len(caminhos)} arquivos adicionados ao Fabriqueiro.", "Fabriqueiro")

    def _limpar_arquivos(self):
        self.caminhos_arquivos = []
        self.lista_arqs_widget.clear()

    def _ao_trocar_modelo(self):
        pass

    def _inserir_chip(self, texto: str):
        atual = self.txt_custom.toPlainText().strip()
        if atual:
            self.txt_custom.setPlainText(f"{atual}\n{texto}")
        else:
            self.txt_custom.setPlainText(texto)

    def montar_prompt(self):
        materia = self.combo_materia.currentText().strip() or "Matemática Discreta"
        topico = self.combo_topico.currentText().strip() or "Geral"
        modelo = self.combo_modelo.currentData()
        custom = self.txt_custom.toPlainText().strip()

        nomes_arqs = [Path(c).name for c in self.caminhos_arquivos]
        bloco_arqs = f"ARQUIVOS ANEXADOS / DE REFERÊNCIA: {', '.join(nomes_arqs)}" if nomes_arqs else "REFERÊNCIA: Material conceitual da matéria."

        # Estrutura padronizada por modelo
        if modelo == "questoes_arena":
            prompt = f"""Você é um professor universitário e especialista na disciplina de {materia}.
Com base no tópico "{topico}" e nos materiais anexados, elabore um banco de 50 a 100 questões inéditas e desafiadoras.

{bloco_arqs}

DIRETRIZES DO FORMATO DE SAÍDA (PADRONIZADO PARA IMPORTAÇÃO AUTOMÁTICA):
Para cada questão gerada, utilize rigorosamente o seguinte formato de bloco separado por '---':

MATERIA: {materia}
TOPICO: {topico}
TIPO: multipla_escolha
ENUNCIADO: [Digite aqui o enunciado exato e completo da questão]
A) [Alternativa A]
B) [Alternativa B]
C) [Alternativa C]
D) [Alternativa D]
GABARITO: [Letra da alternativa correta: A, B, C ou D]
RESOLUCAO: [Explicação passo a passo detalhada demonstrando o porquê da alternativa correta e refutando pegadinhas]
---

INSTRUÇÕES ADICIONAIS DO ESTUDANTE:
{custom if custom else "Garanta questões de múltiplos níveis (fácil, médio e difícil) que cubram todos os subconceitos."}
"""

        elif modelo == "resolucao_lista":
            prompt = f"""Você é um tutor acadêmico especialista em {materia}.
Analise as questões presentes na lista de exercícios anexada ({', '.join(nomes_arqs) if nomes_arqs else 'anexa'}) para o tópico "{topico}".

DIRETRIZES DE RESOLUÇÃO:
1. Resolva TODAS as questões passo a passo, sem pular nenhuma passagem matemática ou lógica.
2. Identifique os teoremas, propriedades ou fórmulas aplicadas em cada etapa.
3. Destaque claramente o resultado final ou conclusão.

INSTRUÇÕES CUSTOMIZADAS:
{custom if custom else "Explique a intuição por trás de cada passo da resolução para fins de estudo."}
"""

        elif modelo == "teoria_formulas":
            prompt = f"""Você é um autor de livros didáticos renomado na área de {materia}.
Crie um resumo teórico aprofundado e completo sobre o tópico "{topico}".

{bloco_arqs}

ESTRUTURA NECESSÁRIA:
1. INTRODUÇÃO E BIG PICTURE: Por que este assunto é estudado e qual sua aplicação real.
2. DEFINIÇÕES FORMAIS: Notação matemática rigorosa e propriedades axiomáticas.
3. TABELA DE IDENTIDADES E FÓRMULAS: Liste cada fórmula, nomeando as variáveis e restrições.
4. ALERTAS E PEGADINHAS DE PROVA: Principais erros cometidos por estudantes em avaliações.

INSTRUÇÕES DO ALUNO:
{custom if custom else "Seja rigoroso com a fundamentação matemática e forneça exemplos práticos."}
"""

        elif modelo == "simulado_pegadinhas":
            prompt = f"""Você é uma banca examinadora de alto nível da disciplina {materia}.
Crie um simulado de preparação pesada para prova focado no tópico "{topico}".

{bloco_arqs}

REQUISITOS:
- Foque especificamente nas armadilhas clássicas, contraexemplos e casos de borda que costumam derrubar candidatos.
- Para cada questão, explique detalhadamente a pegadinha e como não cair nela.

INSTRUÇÕES DO ALUNO:
{custom if custom else "Exija raciocínio crítico em vez de mera memorização."}
"""

        else:  # flashcards
            prompt = f"""Crie uma coleção de Flashcards (Perguntas e Respostas Rápidas) para fixação ativa na matéria de {materia}, tópico "{topico}".

{bloco_arqs}

FORMATO:
Pergunta: [Conceito direto e instigante]
Resposta: [Explicação concisa e memorável]

INSTRUÇÕES DO ALUNO:
{custom if custom else "Foque nas definições essenciais e fórmulas mais cobradas."}
"""

        self.txt_prompt_gerado.setPlainText(prompt.strip())
        log_sucesso("Prompt montado com sucesso no Fabriqueiro!", "Fabriqueiro")

    def _copiar_prompt(self):
        texto = self.txt_prompt_gerado.toPlainText().strip()
        if not texto:
            QMessageBox.warning(self, "Aviso", "Monte o prompt antes de copiar.")
            return

        QApplication.clipboard().setText(texto)
        QMessageBox.information(
            self, "Copiado! 📋",
            "🎉 O prompt foi copiado para a área de transferência com sucesso!<br><br>"
            "Agora você pode colar diretamente no <b>ChatGPT</b>, <b>Claude</b> ou <b>Gemini Web</b> para gerar seu material sem limites!"
        )

    def _salvar_prompt_txt(self):
        texto = self.txt_prompt_gerado.toPlainText().strip()
        if not texto:
            QMessageBox.warning(self, "Aviso", "Monte o prompt antes de salvar.")
            return

        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar Prompt", "Prompt_Estudos.txt", "Texto (*.txt)")
        if caminho:
            try:
                with open(caminho, "w", encoding="utf-8") as f:
                    f.write(texto)
                QMessageBox.information(self, "Salvo", "Prompt gravado com sucesso em arquivo!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao salvar: {e}")

    def _executar_via_api(self):
        chave = carregar_gemini_api_key()
        if not chave:
            QMessageBox.warning(self, "Chave Não Configurada", "Cadastre sua chave Gemini na aba Configurações para executar direto no app.")
            return

        if not self.caminhos_arquivos:
            QMessageBox.warning(self, "Aviso", "Selecione ao menos um arquivo ou imagem para enviar à API.")
            return

        foco = self.combo_modelo.currentData()
        custom = self.txt_custom.toPlainText().strip()

        self.btn_executar_api.setEnabled(False)
        self.lbl_status_api.setText("Executando na API Gemini...")

        self.worker_ia = FabriqueiroWorker(
            caminhos_midias=self.caminhos_arquivos,
            api_key=chave,
            tipo_foco=foco,
            instrucoes_customizadas=custom
        )
        self.worker_ia.progresso.connect(lambda msg: self.lbl_status_api.setText(msg))
        self.worker_ia.sucesso.connect(self._ao_sucesso_api)
        self.worker_ia.erro.connect(self._ao_erro_api)
        self.worker_ia.start()

    def _ao_sucesso_api(self, pdf_gerado: str):
        self.btn_executar_api.setEnabled(True)
        self.lbl_status_api.setText("Sucesso!")
        QMessageBox.information(
            self, "Sucesso na Geração",
            f"🎉 Material gerado e salvo em PDF!<br>Arquivo: {pdf_gerado}"
        )

    def _ao_erro_api(self, erro_str: str):
        self.btn_executar_api.setEnabled(True)
        self.lbl_status_api.setText("Falha na API.")
        QMessageBox.warning(
            self, "Aviso da API Gemini",
            f"A API retornou uma falha temporária ou lentidão: {erro_str}<br><br>"
            f"💡 <b>Solução Recomendada:</b> Use o botão <b>'📋 Copiar Prompt'</b> e cole diretamente na versão web do Gemini ou ChatGPT!"
        )