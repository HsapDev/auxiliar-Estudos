from pathlib import Path
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from organizador_pastas import executar_organizacao
from logger import log_info, log_sucesso, log_aviso, log_erro

class DropZoneWidget(QLabel):
    def __init__(self):
        super().__init__()

        self.setText("Arraste e solte seus arquivos ou pastas aqui")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 40px;
                background-color: #f9f9f9;
                color: #555;
                font-size: 16px;
                font-weight: bold;
            }        
            QLabel:hover {
                background-color: #f0f0f0;
                border-color: #007acc;
            }
        """)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        caminhos_recebidos = []

        for url in urls:
            caminho_local = url.toLocalFile()
            caminhos_recebidos.append(caminho_local)
            
        log_info(f"Arquivos/pastas soltos na DropZone: {len(caminhos_recebidos)} item(ns).", "DropZone")

        try:
            resultado = executar_organizacao("materias.json", arquivos_extras=caminhos_recebidos)
            destino = resultado.get("pasta_destino", "") if isinstance(resultado, dict) else ""
            total = resultado.get("total_movidos", len(caminhos_recebidos)) if isinstance(resultado, dict) else len(caminhos_recebidos)
            log_sucesso(f"Organização finalizada via DropZone: {total} arquivo(s) movidos para '{destino}'.", "DropZone")

            msg = QMessageBox(self)
            msg.setWindowTitle("Sucesso")
            msg.setText(f"🎉 <b>{total} arquivo(s) organizados com sucesso nas pastas das matérias!</b><br><br>"
                        f"<b>Salvos em:</b> {destino}")
            btn_abrir = msg.addButton("📁 Abrir Pasta de Estudos", QMessageBox.ButtonRole.ActionRole)
            msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            msg.exec()

            if msg.clickedButton() == btn_abrir and destino:
                import os, subprocess
                try:
                    os.startfile(destino)
                except Exception:
                    subprocess.Popen(["explorer", destino])
        except Exception as e:
            log_erro("Falha ao processar arquivos recebidos via Drag & Drop", "DropZone", exc=e)
            QMessageBox.critical(self, "ERRO", f"Erro ao processar arquivos: {e}")

class TabDropZone(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.drop_zone = DropZoneWidget()

        layout.addWidget(self.drop_zone)
        self.setLayout(layout)