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


class TabHome(QWidget):
    def __init__(self):
        super().__init__()
        self.layout_principal = QVBoxLayout()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.container_cards = QWidget()
        self.layout_cards = QVBoxLayout(self.container_cards)
        self.layout_cards.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.container_cards)
        self.layout_principal.addWidget(self.scroll_area)
        self.setLayout(self.layout_principal)

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

        if not fila:
            lbl_vazio = QLabel("Parabéns! Nenhum tópico pendente para hoje.")
            lbl_vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout_cards.addWidget(lbl_vazio)
            return

        for item in fila:
            card = self._criar_card_topico(item)
            self.layout_cards.addWidget(card)

    def _criar_card_topico(self, item: dict) -> QFrame:
        """Cria o card individual do tópico."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout_card = QHBoxLayout(card)

        info_layout = QVBoxLayout()
        lbl_titulo = QLabel(f"<b>{item['topico'].title()}</b> ({item['materia']})")
        lbl_detalhes = QLabel(f"Prioridade: {item['score']} pts | Atraso: {item['dias_atraso']} dia(s)")
        info_layout.addWidget(lbl_titulo)
        info_layout.addWidget(lbl_detalhes)

        layout_card.addLayout(info_layout)

        btn_facil = QPushButton("Fácil")
        btn_medio = QPushButton("Médio")
        btn_dificil = QPushButton("Difícil")

        topico_id = item["id"]
        btn_facil.clicked.connect(lambda: self.dar_feedback(topico_id, "facil"))
        btn_medio.clicked.connect(lambda: self.dar_feedback(topico_id, "medio"))
        btn_dificil.clicked.connect(lambda: self.dar_feedback(topico_id, "dificil"))

        layout_card.addWidget(btn_facil)
        layout_card.addWidget(btn_medio)
        layout_card.addWidget(btn_dificil)

        return card

    def dar_feedback(self, topico_id: int, nivel: str):
        """Salva o nível de facilidade e recarrega a lista."""
        try:
            with open("topicos.json", "r", encoding="utf-8") as f:
                topicos = json.load(f)

            registrar_revisao(topico_id, nivel, topicos)
            self.carregar_fila()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar a revisão: {e}")