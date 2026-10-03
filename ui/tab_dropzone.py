from pathlib import Path
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from organizador_pastas import executar_organizacao

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
            
        print(f"Arquivos/pastas recebidos via Drag & Drop: {caminhos_recebidos}")

        try:
            executar_organizacao("materias.json")
            QMessageBox.information(self, "Sucesso", "Arquivos Processados e organizados com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "ERRO", f"Erro ao processar arquivos: {e}")

class TabDropZone(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.drop_zone = DropZoneWidget()

        layout.addWidget(self.drop_zone)
        self.setLayout(layout)