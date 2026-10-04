import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt

from organizador_estudos import (
    mapear_provas_proximas,
    calcular_fila_prioridade,
    registrar_revisao
)
from logger import log_info, log_sucesso, log_aviso, log_erro


class TabHome(QWidget):
    def __init__(self):
        super().__init__()
        self.modo_filtro = "pendentes"  # "pendentes" ou "todos"

        self.layout_principal = QVBoxLayout()

        # Barra de ferramentas no topo
        barra_topo = QHBoxLayout()
        self.lbl_status_fila = QLabel("<b>Fila de Estudos</b>")
        self.lbl_status_fila.setStyleSheet("font-size: 14px;")

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

        self.scroll_area.setWidget(self.container_cards)
        self.layout_principal.addWidget(self.scroll_area)
        self.setLayout(self.layout_principal)

        self.carregar_fila()

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

        try:
            with open("provas.json", "r", encoding="utf-8") as f:
                provas = json.load(f)
            with open("topicos.json", "r", encoding="utf-8") as f:
                topicos = json.load(f)

            mapa_urgencia = mapear_provas_proximas(provas)
            fila = calcular_fila_prioridade(topicos, mapa_urgencia)
        except Exception as e:
            lbl_erro = QLabel(f"Erro ao carregar dados: {e}")
            self.layout_cards.addWidget(lbl_erro)
            return

        total_topicos = len(fila)
        pendentes = [t for t in fila if t.get("pendente_hoje")]

        self.btn_filtro_pendentes.setText(f"🔥 Pendentes Hoje ({len(pendentes)})")
        self.btn_filtro_todos.setText(f"📋 Todos os Tópicos ({total_topicos})")

        lista_exibir = pendentes if self.modo_filtro == "pendentes" else fila

        if not lista_exibir:
            if self.modo_filtro == "pendentes":
                box_vazio = QFrame()
                box_vazio.setStyleSheet("background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 8px; padding: 20px;")
                v_layout = QVBoxLayout(box_vazio)
                lbl_vazio = QLabel("🎉 <b>Parabéns! Nenhum tópico pendente para hoje.</b><br>Todos os seus tópicos programados já foram revisados!")
                lbl_vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_vazio.setStyleSheet("font-size: 14px; color: #2e7d32;")
                
                btn_ver_todos = QPushButton("Ver todos os tópicos cadastrados")
                btn_ver_todos.clicked.connect(self._mostrar_todos)

                v_layout.addWidget(lbl_vazio)
                v_layout.addWidget(btn_ver_todos, alignment=Qt.AlignmentFlag.AlignCenter)
                self.layout_cards.addWidget(box_vazio)
            else:
                lbl_vazio = QLabel("Nenhum tópico cadastrado no sistema.")
                lbl_vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.layout_cards.addWidget(lbl_vazio)
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
                border: 1px solid #d0d7de;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout_card = QHBoxLayout(card)

        info_layout = QVBoxLayout()
        topico_nome = item.get('topico', 'Sem Nome').title()
        materia_nome = item.get('materia', 'Geral')
        atividade_nome = item.get('atividade', '').upper()
        if atividade_nome:
            materia_nome = f"{materia_nome} | {atividade_nome}"

        lbl_titulo = QLabel(f"<span style='font-size: 15px;'><b>{topico_nome}</b></span> <span style='color: #666;'>({materia_nome})</span>")
        
        # Tags de status
        revisado_hoje = item.get('revisado_hoje', False)
        dias_atraso = item.get('dias_atraso', 0)
        intervalo = item.get('intervalo_dias', 1)
        score = item.get('score', 0)
        proxima = item.get('proxima_revisao', '')

        if revisado_hoje:
            tag_status = "<span style='color: #2e7d32; font-weight: bold;'>✅ Revisado hoje</span>"
        elif dias_atraso > 0:
            tag_status = f"<span style='color: #c62828; font-weight: bold;'>⚠️ Atrasado {dias_atraso} dia(s)</span>"
        else:
            tag_status = "<span style='color: #0277bd; font-weight: bold;'>📌 Vence hoje</span>"

        detalhes_html = (
            f"{tag_status} &nbsp;|&nbsp; "
            f"<b>Intervalo:</b> {intervalo} dia(s) &nbsp;|&nbsp; "
            f"<b>Próxima:</b> {proxima} &nbsp;|&nbsp; "
            f"<b>Prioridade:</b> {score} pts"
        )
        lbl_detalhes = QLabel(detalhes_html)

        info_layout.addWidget(lbl_titulo)
        info_layout.addWidget(lbl_detalhes)
        layout_card.addLayout(info_layout)

        # Botões de Nível de Facilidade com cores diferenciadas
        botoes_layout = QHBoxLayout()
        
        btn_facil = QPushButton("🟢 Fácil")
        btn_facil.setToolTip("Aumenta o intervalo para você revisar mais tarde")
        btn_facil.setStyleSheet("background-color: #e8f5e9; color: #2e7d32; font-weight: bold; border: 1px solid #a5d6a7; padding: 6px 12px; border-radius: 4px;")

        btn_medio = QPushButton("🔵 Médio")
        btn_medio.setToolTip("Aumenta o intervalo moderadamente")
        btn_medio.setStyleSheet("background-color: #e1f5fe; color: #0277bd; font-weight: bold; border: 1px solid #81d4fa; padding: 6px 12px; border-radius: 4px;")

        btn_dificil = QPushButton("🔴 Difícil")
        btn_dificil.setToolTip("Reinicia o intervalo para revisar amanhã")
        btn_dificil.setStyleSheet("background-color: #ffebee; color: #c62828; font-weight: bold; border: 1px solid #ef9a9a; padding: 6px 12px; border-radius: 4px;")

        topico_id = item["id"]
        btn_facil.clicked.connect(lambda _, tid=topico_id: self.dar_feedback(tid, "facil"))
        btn_medio.clicked.connect(lambda _, tid=topico_id: self.dar_feedback(tid, "medio"))
        btn_dificil.clicked.connect(lambda _, tid=topico_id: self.dar_feedback(tid, "dificil"))

        botoes_layout.addWidget(btn_facil)
        botoes_layout.addWidget(btn_medio)
        botoes_layout.addWidget(btn_dificil)

        layout_card.addLayout(botoes_layout)
        return card

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
                    f"Tópico: <b>{nome}</b><br>"
                    f"Avaliação: <b>{nivel.capitalize()}</b><br>"
                    f"Novo intervalo de estudo: <b>{novo_intervalo} dia(s)</b>"
                )
            self.carregar_fila()
        except Exception as e:
            log_erro(f"Erro ao salvar feedback do tópico {topico_id}", "FilaEstudos", exc=e)
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar a revisão: {e}")