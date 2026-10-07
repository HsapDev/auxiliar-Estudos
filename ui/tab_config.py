import json
import os
from datetime import date, timedelta
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDateEdit, QMessageBox, QGroupBox, QFormLayout, QScrollArea, QFileDialog
)
from PyQt6.QtCore import QDate
from organizador_pastas import resolver_caminho
from logger import log_info, log_sucesso, log_aviso, log_erro
from credenciais import carregar_gemini_api_key, salvar_gemini_api_key


class TabConfig(QWidget):
    def __init__(self):
        super().__init__()
        layout_externo = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout_principal = QVBoxLayout(container)

        # 0. Box Pastas do Sistema de Estudos
        box_pastas = QGroupBox("📁 Pastas do Sistema de Estudos")
        form_pastas = QFormLayout()

        # Entrada
        layout_in = QHBoxLayout()
        self.input_pasta_entrada = QLineEdit()
        self.input_pasta_entrada.setPlaceholderText("~/Downloads/estudos")
        btn_browse_in = QPushButton("Procurar...")
        btn_browse_in.clicked.connect(self._selecionar_pasta_entrada)
        layout_in.addWidget(self.input_pasta_entrada)
        layout_in.addWidget(btn_browse_in)

        # Destino
        layout_out = QHBoxLayout()
        self.input_pasta_destino = QLineEdit()
        self.input_pasta_destino.setPlaceholderText("~/Documents/estudos")
        btn_browse_out = QPushButton("Procurar...")
        btn_browse_out.clicked.connect(self._selecionar_pasta_destino)
        layout_out.addWidget(self.input_pasta_destino)
        layout_out.addWidget(btn_browse_out)

        btn_salvar_pastas = QPushButton("Salvar Pastas de Estudo")
        btn_salvar_pastas.setStyleSheet("font-weight: bold;")
        btn_salvar_pastas.clicked.connect(self.salvar_pastas)

        form_pastas.addRow("Pasta de Entrada (downloads/arquivos brutos):", layout_in)
        form_pastas.addRow("Pasta de Destino (onde ficam as matérias e apostilas):", layout_out)
        form_pastas.addRow(btn_salvar_pastas)
        box_pastas.setLayout(form_pastas)

        # 0.5 Box Chave API Gemini
        box_api = QGroupBox("🔑 Chave API do Google Gemini (IA)")
        form_api = QFormLayout()

        layout_chave_cfg = QHBoxLayout()
        self.input_gemini_key = QLineEdit()
        self.input_gemini_key.setPlaceholderText("Cole sua GEMINI_API_KEY para salvar permanentemente")
        self.input_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        chave_salva = carregar_gemini_api_key()
        if chave_salva:
            self.input_gemini_key.setText(chave_salva)

        self.btn_toggle_cfg_key = QPushButton("👁️")
        self.btn_toggle_cfg_key.setFixedWidth(36)
        self.btn_toggle_cfg_key.clicked.connect(self._alternar_visibilidade_chave_cfg)

        btn_salvar_api = QPushButton("Salvar Chave API")
        btn_salvar_api.setStyleSheet("font-weight: bold;")
        btn_salvar_api.clicked.connect(self.salvar_chave_api)

        layout_chave_cfg.addWidget(self.input_gemini_key)
        layout_chave_cfg.addWidget(self.btn_toggle_cfg_key)
        layout_chave_cfg.addWidget(btn_salvar_api)

        lbl_info_api = QLabel("<small>Obtenha sua chave gratuita em: <b>aistudio.google.com/app/apikey</b>. A chave é usada no Fabriqueiro e no Guru de Estudos (Nuvem).</small>")
        lbl_info_api.setStyleSheet("color: #555;")

        form_api.addRow("Chave API:", layout_chave_cfg)
        form_api.addRow(lbl_info_api)
        box_api.setLayout(form_api)

        # 1. Box Matéria
        box_materia = QGroupBox("Cadastrar Nova Materia / Palavras-chave")
        form_materia = QFormLayout()

        self.input_nome_materia = QLineEdit()
        self.input_nome_materia.setPlaceholderText("Ex: Programacao")

        self.input_palavras = QLineEdit()
        self.input_palavras.setPlaceholderText("Ex: python, java, algoritmos (separado por virgula)")

        btn_salvar_materia = QPushButton("Salvar Materia")
        btn_salvar_materia.clicked.connect(self.salvar_materia)

        form_materia.addRow("Nome da materia:", self.input_nome_materia)
        form_materia.addRow("Palavras-chave:", self.input_palavras)
        form_materia.addRow(btn_salvar_materia)
        box_materia.setLayout(form_materia)

        # 2. Box Prova
        box_prova = QGroupBox("Cadastrar Nova Prova")
        form_prova = QFormLayout()

        self.input_prova_materia = QLineEdit()
        self.input_prova_materia.setPlaceholderText("Ex: Matematica_discreta")

        self.input_prova_atividade = QLineEdit()
        self.input_prova_atividade.setPlaceholderText("Ex: P1, P2, listas")

        self.input_prova_data = QDateEdit()
        self.input_prova_data.setDate(QDate.currentDate())
        self.input_prova_data.setDisplayFormat("yyyy-MM-dd")
        self.input_prova_data.setCalendarPopup(True)

        btn_salvar_prova = QPushButton("Salvar Prova")
        btn_salvar_prova.clicked.connect(self.salvar_prova)

        form_prova.addRow("Materia:", self.input_prova_materia)
        form_prova.addRow("Atividade/Prova:", self.input_prova_atividade)
        form_prova.addRow("Data da prova:", self.input_prova_data)
        form_prova.addRow(btn_salvar_prova)
        box_prova.setLayout(form_prova)

        # 3. Box Tópico de Estudo
        box_topico = QGroupBox("Cadastrar Novo Tópico de Estudo")
        form_topico = QFormLayout()

        self.input_topico_materia = QLineEdit()
        self.input_topico_materia.setPlaceholderText("Ex: Matematica_discreta")

        self.input_topico_nome = QLineEdit()
        self.input_topico_nome.setPlaceholderText("Ex: Inducao Matematica")

        self.input_topico_atividade = QLineEdit()
        self.input_topico_atividade.setPlaceholderText("Ex: P1")

        self.input_topico_intervalo = QLineEdit("1")
        self.input_topico_intervalo.setPlaceholderText("Dias para primeira revisão (padrão: 1)")

        btn_salvar_topico = QPushButton("Salvar Tópico de Estudo")
        btn_salvar_topico.clicked.connect(self.salvar_topico)

        form_topico.addRow("Matéria:", self.input_topico_materia)
        form_topico.addRow("Nome do Tópico:", self.input_topico_nome)
        form_topico.addRow("Atividade/Prova:", self.input_topico_atividade)
        form_topico.addRow("Intervalo Inicial (dias):", self.input_topico_intervalo)
        form_topico.addRow(btn_salvar_topico)
        box_topico.setLayout(form_topico)

        layout_principal.addWidget(box_pastas)
        layout_principal.addWidget(box_api)
        layout_principal.addWidget(box_materia)
        layout_principal.addWidget(box_prova)
        layout_principal.addWidget(box_topico)
        layout_principal.addStretch()

        scroll.setWidget(container)
        layout_externo.addWidget(scroll)

        self._carregar_pastas_existentes()

    def _alternar_visibilidade_chave_cfg(self):
        if self.input_gemini_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_gemini_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_cfg_key.setText("🔒")
        else:
            self.input_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_cfg_key.setText("👁️")

    def salvar_chave_api(self):
        chave = self.input_gemini_key.text().strip()
        if not chave:
            QMessageBox.warning(self, "Aviso", "Digite a chave antes de salvar!")
            return
        salvar_gemini_api_key(chave)
        QMessageBox.information(
            self, "Sucesso",
            "Chave API do Gemini salva com sucesso!<br>Ela foi configurada de forma permanente para o Fabriqueiro e o Guru."
        )

    def _carregar_pastas_existentes(self):
        try:
            if os.path.exists("materias.json"):
                with open("materias.json", "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    self.input_pasta_entrada.setText(dados.get("pasta_entrada", "~/Downloads/estudos"))
                    self.input_pasta_destino.setText(dados.get("pasta_destino", "~/Documents/estudos"))
        except Exception:
            pass

    def _selecionar_pasta_entrada(self):
        caminho = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Entrada")
        if caminho:
            self.input_pasta_entrada.setText(caminho)

    def _selecionar_pasta_destino(self):
        caminho = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Destino dos Estudos")
        if caminho:
            self.input_pasta_destino.setText(caminho)

    def salvar_pastas(self):
        p_in = self.input_pasta_entrada.text().strip()
        p_out = self.input_pasta_destino.text().strip()

        if not p_in or not p_out:
            QMessageBox.warning(self, "Aviso", "Preencha ambas as pastas!")
            return

        try:
            if os.path.exists("materias.json"):
                with open("materias.json", "r+", encoding="utf-8") as f:
                    dados = json.load(f)
                    dados["pasta_entrada"] = p_in
                    dados["pasta_destino"] = p_out
                    f.seek(0)
                    json.dump(dados, f, indent=4, ensure_ascii=False)
                    f.truncate()
            else:
                dados = {
                    "pasta_entrada": p_in,
                    "pasta_destino": p_out,
                    "palavras_chave": {}
                }
                with open("materias.json", "w", encoding="utf-8") as f:
                    json.dump(dados, f, indent=4, ensure_ascii=False)

            # Garante que as pastas sejam criadas no disco
            dir_in = resolver_caminho(p_in, "downloads")
            dir_out = resolver_caminho(p_out, "documents")
            dir_in.mkdir(parents=True, exist_ok=True)
            dir_out.mkdir(parents=True, exist_ok=True)
            log_sucesso(f"Pastas de estudo atualizadas: Entrada='{dir_in}', Destino='{dir_out}'", "Config")

            QMessageBox.information(
                self, "Sucesso",
                f"Pastas de estudo salvas com sucesso!<br><br>"
                f"<b>Entrada:</b> {dir_in}<br>"
                f"<b>Destino:</b> {dir_out}"
            )
        except Exception as e:
            log_erro("Erro ao salvar pastas de estudo", "Config", exc=e)
            QMessageBox.critical(self, "Erro", f"Erro ao salvar pastas: {e}")

    def salvar_materia(self):
        nome = self.input_nome_materia.text().strip()
        palavras_raw = self.input_palavras.text().strip()

        if not nome or not palavras_raw:
            QMessageBox.warning(self, "Aviso", "Preencha o nome da materia e pelo menos uma palavra-chave!")
            return
        palavras_lista = [p.strip().lower() for p in palavras_raw.split(",") if p.strip()]

        try:
            with open("materias.json", "r+", encoding="utf-8") as f:
                dados = json.load(f)
                if "palavras_chave" not in dados:
                    dados["palavras_chave"] = {}
                dados["palavras_chave"][nome] = palavras_lista
                f.seek(0)
                json.dump(dados, f, indent=4, ensure_ascii=False)
                f.truncate()

            log_sucesso(f"Matéria '{nome}' cadastrada/atualizada com palavras: {palavras_lista}", "Config")
            QMessageBox.information(self, "Sucesso", f"Materia '{nome}' salva com sucesso!")
            self.input_nome_materia.clear()
            self.input_palavras.clear()
        except Exception as e:
            log_erro(f"Erro ao salvar matéria '{nome}'", "Config", exc=e)
            QMessageBox.critical(self, "Erro", f"Erro ao salvar materias: {e}")

    def salvar_prova(self):
        materia = self.input_prova_materia.text().strip()
        atividade = self.input_prova_atividade.text().strip()
        data_str = self.input_prova_data.date().toString("yyyy-MM-dd")

        if not materia or not atividade:
            QMessageBox.warning(self, "Aviso", "Preencha a materia e a atividade!")
            return

        nova_prova = {
            "materia": materia,
            "atividade": atividade,
            "data": data_str
        }

        try:
            try:
                with open("provas.json", "r", encoding="utf-8") as f:
                    provas = json.load(f)
            except Exception:
                provas = []

            provas.append(nova_prova)
            with open("provas.json", "w", encoding="utf-8") as f:
                json.dump(provas, f, indent=4, ensure_ascii=False)

            log_sucesso(f"Nova prova cadastrada: [{materia}] {atividade} na data {data_str}.", "Config")
            QMessageBox.information(self, "Sucesso", "Prova cadastrada com sucesso!")
            self.input_prova_materia.clear()
            self.input_prova_atividade.clear()
        except Exception as e:
            log_erro(f"Erro ao cadastrar prova [{materia}] {atividade}", "Config", exc=e)
            QMessageBox.critical(self, "ERRO", f"Erro ao salvar prova: {e}")

    def salvar_topico(self):
        materia = self.input_topico_materia.text().strip()
        topico = self.input_topico_nome.text().strip()
        atividade = self.input_topico_atividade.text().strip()
        intervalo_str = self.input_topico_intervalo.text().strip()

        if not materia or not topico:
            QMessageBox.warning(self, "Aviso", "Preencha a matéria e o nome do tópico!")
            return

        try:
            intervalo = max(1, int(intervalo_str))
        except ValueError:
            intervalo = 1

        try:
            try:
                with open("topicos.json", "r", encoding="utf-8") as f:
                    topicos = json.load(f)
            except Exception:
                topicos = []

            # Gera novo ID
            proximo_id = max([t.get("id", 0) for t in topicos], default=0) + 1
            # Define última revisão como ontem para que já fique pendente para estudo hoje
            ontem_str = (date.today() - timedelta(days=intervalo)).isoformat()

            novo_topico = {
                "id": proximo_id,
                "materia": materia,
                "intervalo_dias": intervalo,
                "topico": topico,
                "atividade": atividade,
                "dificuldade": "medio",
                "data_evento": "",
                "ultima_revisao": ontem_str
            }

            topicos.append(novo_topico)

            with open("topicos.json", "w", encoding="utf-8") as f:
                json.dump(topicos, f, indent=4, ensure_ascii=False)

            log_sucesso(f"Novo tópico cadastrado: [{materia}] '{topico}' (Intervalo: {intervalo}d, ID: {proximo_id}).", "Config")
            QMessageBox.information(self, "Sucesso", f"Tópico '{topico}' cadastrado com sucesso e já adicionado à fila!")
            self.input_topico_nome.clear()
            self.input_topico_atividade.clear()
        except Exception as e:
            log_erro(f"Erro ao salvar tópico '{topico}'", "Config", exc=e)
            QMessageBox.critical(self, "ERRO", f"Erro ao salvar tópico: {e}")