import json
import os
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QMessageBox, QDialog, QLineEdit, QComboBox, QDateEdit, QFormLayout
)
from PyQt6.QtCore import Qt, QDate

from organizador_estudos import (
    mapear_provas_proximas,
    calcular_fila_prioridade,
    registrar_revisao,
    adicionar_atividade_topico,
    remover_atividade_topico
)
from logger import log_info, log_sucesso, log_aviso, log_erro


class DialogNovaAtividade(QDialog):
    """Diálogo interativo para criar novas atividades e matérias na Fila de Estudos."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nova Atividade / Matéria de Estudo")
        self.setMinimumWidth(450)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { font-size: 13px; font-weight: bold; color: #333; }
            QLineEdit, QComboBox, QDateEdit {
                padding: 8px;
                font-size: 13px;
                border: 1px solid #ccc;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl_header = QLabel("<h3>📝 Cadastrar Atividade de Estudo</h3>")
        lbl_header.setStyleSheet("color: #1a237e; margin-bottom: 5px;")
        layout.addWidget(lbl_header)

        form = QFormLayout()
        form.setSpacing(10)

        # 1. Matéria Relacionada
        self.combo_materia = QComboBox()
        self.combo_materia.setEditable(True)
        self.combo_materia.setPlaceholderText("Selecione ou digite a matéria...")
        self._carregar_materias_sugestao()

        # 2. Nome da Atividade / Tópico
        self.input_topico = QLineEdit()
        self.input_topico.setPlaceholderText("Ex: Lista 3 de Exercícios, Portas Lógicas, P1")

        # 3. Tipo de Atividade
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Lista de Exercícios", "Prova / Avaliação", "Trabalho / Projeto", "Revisão Teórica", "Aula / Conteúdo Novo"])

        # 4. Nível de Dificuldade
        self.combo_dificuldade = QComboBox()
        self.combo_dificuldade.addItem("🔴 Difícil (Revisar diariamente)", "dificil")
        self.combo_dificuldade.addItem("🔵 Médio (Revisar a cada 2 dias)", "medio")
        self.combo_dificuldade.addItem("🟢 Fácil (Revisar a cada 4 dias)", "facil")
        self.combo_dificuldade.setCurrentIndex(1)  # Médio padrão

        # 5. Quando vai ocorrer a matéria / prazo
        self.date_evento = QDateEdit()
        self.date_evento.setDate(QDate.currentDate().addDays(7))
        self.date_evento.setCalendarPopup(True)
        self.date_evento.setDisplayFormat("dd/MM/yyyy")

        form.addRow("Matéria Relacionada:*", self.combo_materia)
        form.addRow("Nome da Atividade / Tópico:*", self.input_topico)
        form.addRow("Tipo de Atividade:", self.combo_tipo)
        form.addRow("Nível de Dificuldade:", self.combo_dificuldade)
        form.addRow("Quando vai ocorrer (Prazo/Data):", self.date_evento)

        layout.addLayout(form)

        # Botões de Ação
        botoes = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("padding: 8px 16px; background-color: #f1f1f1; border-radius: 6px;")
        btn_cancelar.clicked.connect(self.reject)

        btn_salvar = QPushButton("💾 Salvar Atividade")
        btn_salvar.setStyleSheet("padding: 8px 18px; background-color: #2e7d32; color: white; font-weight: bold; border-radius: 6px;")
        btn_salvar.clicked.connect(self._salvar)

        botoes.addStretch()
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)
        layout.addLayout(botoes)

    def _carregar_materias_sugestao(self):
        materias = set()
        if os.path.exists("materias.json"):
            try:
                with open("materias.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    for k in cfg.get("palavras_chave", {}).keys():
                        materias.add(k)
            except Exception:
                pass

        if os.path.exists("topicos.json"):
            try:
                with open("topicos.json", "r", encoding="utf-8") as f:
                    tops = json.load(f)
                    for t in tops:
                        m = t.get("materia")
                        if m:
                            materias.add(m)
            except Exception:
                pass

        for m in sorted(materias):
            self.combo_materia.addItem(m)

    def _salvar(self):
        materia = self.combo_materia.currentText().strip()
        topico = self.input_topico.text().strip()
        tipo = self.combo_tipo.currentText().strip()
        dificuldade = self.combo_dificuldade.currentData()
        data_evento = self.date_evento.date().toString("yyyy-MM-dd")

        if not materia:
            QMessageBox.warning(self, "Aviso", "Por favor, informe a matéria relacionada.")
            self.combo_materia.setFocus()
            return

        if not topico:
            QMessageBox.warning(self, "Aviso", "Por favor, dê um nome à atividade ou tópico.")
            self.input_topico.setFocus()
            return

        try:
            adicionar_atividade_topico(
                materia=materia,
                topico=topico,
                atividade=tipo,
                dificuldade=dificuldade,
                data_evento=data_evento
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar a atividade: {e}")


class TabHome(QWidget):
    def __init__(self):
        super().__init__()
        self.modo_filtro = "pendentes"  # "pendentes" ou "todos"

        self.layout_principal = QVBoxLayout(self)

        # Barra de ferramentas no topo
        barra_topo = QHBoxLayout()
        self.lbl_status_fila = QLabel("<b>Fila de Estudos & Urgência</b>")
        self.lbl_status_fila.setStyleSheet("font-size: 15px; color: #1a237e;")

        self.btn_nova_atividade = QPushButton("➕ Nova Atividade")
        self.btn_nova_atividade.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #1b5e20; }
        """)
        self.btn_nova_atividade.clicked.connect(self._abrir_dialogo_nova_atividade)

        self.btn_filtro_pendentes = QPushButton("🔥 Pendentes Hoje")
        self.btn_filtro_pendentes.setCheckable(True)
        self.btn_filtro_pendentes.setChecked(True)
        self.btn_filtro_pendentes.clicked.connect(self._mostrar_pendentes)

        self.btn_filtro_todos = QPushButton("📋 Todos os Tópicos")
        self.btn_filtro_todos.setCheckable(True)
        self.btn_filtro_todos.setChecked(False)
        self.btn_filtro_todos.clicked.connect(self._mostrar_todos)

        self.btn_atualizar = QPushButton("🔄 Atualizar")
        self.btn_atualizar.clicked.connect(self.carregar_fila)

        barra_topo.addWidget(self.lbl_status_fila)
        barra_topo.addSpacing(10)
        barra_topo.addWidget(self.btn_nova_atividade)
        barra_topo.addStretch()
        barra_topo.addWidget(self.btn_filtro_pendentes)
        barra_topo.addWidget(self.btn_filtro_todos)
        barra_topo.addWidget(self.btn_atualizar)

        self.layout_principal.addLayout(barra_topo)

        # Área de rolagem para os cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.container_cards = QWidget()
        self.layout_cards = QVBoxLayout(self.container_cards)
        self.layout_cards.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_cards.setSpacing(10)

        self.scroll_area.setWidget(self.container_cards)
        self.layout_principal.addWidget(self.scroll_area)

        self.carregar_fila()

    def _abrir_dialogo_nova_atividade(self):
        diag = DialogNovaAtividade(self)
        if diag.exec() == QDialog.DialogCode.Accepted:
            self.carregar_fila()
            QMessageBox.information(self, "Sucesso", "Atividade adicionada com sucesso e fila recalculada!")

    def _mostrar_pendentes(self):
        self.modo_filtro = "pendentes"
        self.btn_filtro_pendentes.setChecked(True)
        self.btn_filtro_todos.setChecked(False)
        self.carregar_fila()

    def _mostrar_todos(self):
        self.modo_filtro = "todos"
        self.btn_filtro_pendentes.setChecked(False)
        self.btn_filtro_todos.setChecked(True)
        self.carregar_fila()

    def carregar_fila(self):
        """Limpa e recarrega os cards na tela."""
        while self.layout_cards.count():
            item = self.layout_cards.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        provas = []
        topicos = []

        if os.path.exists("provas.json"):
            try:
                with open("provas.json", "r", encoding="utf-8") as f:
                    provas = json.load(f)
            except Exception:
                provas = []

        if os.path.exists("topicos.json"):
            try:
                with open("topicos.json", "r", encoding="utf-8") as f:
                    topicos = json.load(f)
            except Exception:
                topicos = []

        try:
            mapa_urgencia = mapear_provas_proximas(provas)
            fila = calcular_fila_prioridade(topicos, mapa_urgencia)
        except Exception as e:
            lbl_erro = QLabel(f"Erro ao carregar fila de estudos: {e}")
            self.layout_cards.addWidget(lbl_erro)
            return

        total_topicos = len(fila)
        pendentes = [t for t in fila if t.get("pendente_hoje")]

        self.btn_filtro_pendentes.setText(f"🔥 Pendentes Hoje ({len(pendentes)})")
        self.btn_filtro_todos.setText(f"📋 Todas as Atividades ({total_topicos})")

        lista_exibir = pendentes if self.modo_filtro == "pendentes" else fila

        if not lista_exibir:
            box_vazio = QFrame()
            box_vazio.setStyleSheet("background-color: #f8f9fa; border: 1px dashed #b0bec5; border-radius: 8px; padding: 30px;")
            v_layout = QVBoxLayout(box_vazio)
            v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if total_topicos == 0:
                lbl_vazio = QLabel(
                    "<h3>Sua Fila de Estudos está vazia! 📚</h3>"
                    "<p style='color: #555;'>Clique no botão abaixo para adicionar sua primeira atividade, matéria ou prova.</p>"
                )
                lbl_vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
                btn_criar = QPushButton("➕ Criar Primeira Atividade")
                btn_criar.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
                btn_criar.clicked.connect(self._abrir_dialogo_nova_atividade)
                v_layout.addWidget(lbl_vazio)
                v_layout.addWidget(btn_criar, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                lbl_vazio = QLabel("🎉 <b>Parabéns! Todas as atividades de hoje foram revisadas!</b><br>Nenhum item pendente para hoje.")
                lbl_vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_vazio.setStyleSheet("font-size: 14px; color: #2e7d32;")
                btn_ver_todos = QPushButton("Ver todas as atividades cadastradas")
                btn_ver_todos.clicked.connect(self._mostrar_todos)
                v_layout.addWidget(lbl_vazio)
                v_layout.addWidget(btn_ver_todos, alignment=Qt.AlignmentFlag.AlignCenter)

            self.layout_cards.addWidget(box_vazio)
            return

        for item in lista_exibir:
            card = self._criar_card_topico(item)
            self.layout_cards.addWidget(card)

    def _criar_card_topico(self, item: dict) -> QFrame:
        """Cria o card individual do tópico com visual e feedback claro."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 14px;
            }
            QFrame:hover {
                border-color: #cbd5e1;
            }
        """)
        layout_card = QHBoxLayout(card)

        info_layout = QVBoxLayout()
        topico_nome = item.get('topico', 'Sem Nome').title()
        materia_nome = item.get('materia', 'Geral')
        atividade_tipo = item.get('atividade', 'Estudo')
        dificuldade = item.get('dificuldade', 'medio').lower()
        score = item.get('score', 0)
        data_evento = item.get('data_evento', '')
        dias_evento = item.get('dias_evento', 999)

        # Tags de dificuldade
        if dificuldade == "dificil":
            tag_dif = "<span style='background-color: #ffebee; color: #c62828; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🔴 DIFÍCIL</span>"
        elif dificuldade == "facil":
            tag_dif = "<span style='background-color: #e8f5e9; color: #2e7d32; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🟢 FÁCIL</span>"
        else:
            tag_dif = "<span style='background-color: #e1f5fe; color: #0277bd; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🔵 MÉDIO</span>"

        # Tag de prazo/data
        if data_evento:
            if dias_evento < 0:
                tag_prazo = f"<span style='color: #c62828; font-weight: bold;'>⚠️ Venceu há {-dias_evento}d ({data_evento})</span>"
            elif dias_evento == 0:
                tag_prazo = f"<span style='color: #d84315; font-weight: bold;'>🚨 Ocorre HOJE ({data_evento})</span>"
            elif dias_evento <= 3:
                tag_prazo = f"<span style='color: #ef6c00; font-weight: bold;'>⏰ Ocorre em {dias_evento}d ({data_evento})</span>"
            else:
                tag_prazo = f"<span style='color: #555;'>📅 Ocorre em {dias_evento}d ({data_evento})</span>"
        else:
            tag_prazo = "<span style='color: #777;'>📅 Sem data fixada</span>"

        lbl_titulo = QLabel(
            f"<span style='font-size: 15px;'><b>{topico_nome}</b></span> &nbsp; "
            f"<span style='background-color: #ede7f6; color: #4a148c; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 12px;'>📚 {materia_nome}</span> &nbsp; "
            f"<span style='color: #666; font-size: 12px;'>[{atividade_tipo}]</span> &nbsp; "
            f"{tag_dif}"
        )

        # Status de Urgência
        revisado_hoje = item.get('revisado_hoje', False)
        dias_atraso = item.get('dias_atraso', 0)
        intervalo = item.get('intervalo_dias', 1)
        proxima = item.get('proxima_revisao', '')

        if revisado_hoje:
            tag_status = "<span style='color: #2e7d32; font-weight: bold;'>✅ Revisado hoje</span>"
        elif dias_atraso > 0:
            tag_status = f"<span style='color: #c62828; font-weight: bold;'>⚠️ Atrasado {dias_atraso}d</span>"
        else:
            tag_status = "<span style='color: #0277bd; font-weight: bold;'>📌 Revisar hoje</span>"

        cor_score = "#c62828" if score >= 150 else ("#e65100" if score >= 80 else "#1565c0")
        tag_urgencia = f"<span style='color: {cor_score}; font-weight: bold;'>🔥 Urgência: {score} pts</span>"

        detalhes_html = (
            f"{tag_status} &nbsp;|&nbsp; "
            f"{tag_prazo} &nbsp;|&nbsp; "
            f"<b>Intervalo:</b> {intervalo}d &nbsp;|&nbsp; "
            f"<b>Próxima:</b> {proxima} &nbsp;|&nbsp; "
            f"{tag_urgencia}"
        )
        lbl_detalhes = QLabel(detalhes_html)

        info_layout.addWidget(lbl_titulo)
        info_layout.addWidget(lbl_detalhes)
        layout_card.addLayout(info_layout)

        # Botões de Ação
        botoes_layout = QHBoxLayout()
        topico_id = item.get("id")

        btn_facil = QPushButton("🟢 Fácil")
        btn_facil.setToolTip("Aumenta o intervalo de revisão")
        btn_facil.setStyleSheet("background-color: #e8f5e9; color: #2e7d32; font-weight: bold; border: 1px solid #a5d6a7; padding: 6px 10px; border-radius: 4px;")

        btn_medio = QPushButton("🔵 Médio")
        btn_medio.setToolTip("Aumenta o intervalo moderadamente")
        btn_medio.setStyleSheet("background-color: #e1f5fe; color: #0277bd; font-weight: bold; border: 1px solid #81d4fa; padding: 6px 10px; border-radius: 4px;")

        btn_dificil = QPushButton("🔴 Difícil")
        btn_dificil.setToolTip("Reinicia o intervalo para revisar amanhã")
        btn_dificil.setStyleSheet("background-color: #ffebee; color: #c62828; font-weight: bold; border: 1px solid #ef9a9a; padding: 6px 10px; border-radius: 4px;")

        btn_excluir = QPushButton("🗑️")
        btn_excluir.setToolTip("Excluir esta atividade")
        btn_excluir.setStyleSheet("background-color: #f5f5f5; color: #757575; border: 1px solid #ccc; padding: 6px 8px; border-radius: 4px;")

        btn_facil.clicked.connect(lambda _, tid=topico_id: self.dar_feedback(tid, "facil"))
        btn_medio.clicked.connect(lambda _, tid=topico_id: self.dar_feedback(tid, "medio"))
        btn_dificil.clicked.connect(lambda _, tid=topico_id: self.dar_feedback(tid, "dificil"))
        btn_excluir.clicked.connect(lambda _, tid=topico_id, nome=topico_nome: self._excluir_topico(tid, nome))

        botoes_layout.addWidget(btn_facil)
        botoes_layout.addWidget(btn_medio)
        botoes_layout.addWidget(btn_dificil)
        botoes_layout.addWidget(btn_excluir)

        layout_card.addLayout(botoes_layout)
        return card

    def _excluir_topico(self, topico_id: int, nome: str):
        resp = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Deseja realmente remover a atividade '<b>{nome}</b>'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            remover_atividade_topico(topico_id)
            self.carregar_fila()

    def dar_feedback(self, topico_id: int, nivel: str):
        """Salva o nível de facilidade e recarrega a lista com feedback imediato."""
        try:
            with open("topicos.json", "r", encoding="utf-8") as f:
                topicos = json.load(f)

            topico_atualizado = registrar_revisao(topico_id, nivel, topicos)
            if topico_atualizado:
                novo_intervalo = topico_atualizado.get("intervalo_dias", 1)
                nome = topico_atualizado.get("topico", "").title()
                QMessageBox.information(
                    self,
                    "Revisão Registrada!",
                    f"Atividade: <b>{nome}</b><br>"
                    f"Avaliação: <b>{nivel.capitalize()}</b><br>"
                    f"Novo intervalo de estudo: <b>{novo_intervalo} dia(s)</b>"
                )
            self.carregar_fila()
        except Exception as e:
            log_erro(f"Erro ao salvar feedback do tópico {topico_id}", "FilaEstudos", exc=e)
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar a revisão: {e}")