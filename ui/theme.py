"""
Sistema de Design e Estilo Visual Moderno (Tema UI Premium)
Define cores, fontes, estilos de botões, abas, inputs, scrollbars e cartões.
"""

TEMA_MODERNO_QSS = """
/* =========================================================================
   CONFIGURAÇÃO GLOBAL & TIPOGRAFIA
   ========================================================================= */
* {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', 'Arial', sans-serif;
    outline: none;
}

QMainWindow, QDialog {
    background-color: #f8fafc;
    color: #1e293b;
}

QWidget {
    color: #1e293b;
    font-size: 13px;
}

/* =========================================================================
   ABAS PRINCIPAIS (QTABWIDGET & QTABBAR)
   ========================================================================= */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background-color: #ffffff;
    top: -1px;
    padding: 8px;
}

QTabBar::tab {
    background: #f1f5f9;
    color: #475569;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 13px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid transparent;
    margin-right: 4px;
    margin-bottom: 2px;
}

QTabBar::tab:hover {
    background: #e2e8f0;
    color: #1e293b;
}

QTabBar::tab:selected {
    background: #ffffff;
    color: #4f46e5;
    border: 1px solid #e2e8f0;
    border-bottom: 2px solid #4f46e5;
}

/* =========================================================================
   BOTÕES (QPUSHBUTTON)
   ========================================================================= */
QPushButton {
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
    color: #0f172a;
}

QPushButton:pressed {
    background-color: #e2e8f0;
    border-color: #64748b;
}

QPushButton:disabled {
    background-color: #f8fafc;
    border-color: #e2e8f0;
    color: #94a3b8;
}

/* Botões de Ação Primária (Destaque Azul / Roxo Moderno) */
QPushButton#btn-primary, QPushButton[accent="primary"] {
    background-color: #4f46e5;
    color: #ffffff;
    border: 1px solid #4338ca;
}
QPushButton#btn-primary:hover, QPushButton[accent="primary"]:hover {
    background-color: #4338ca;
}
QPushButton#btn-primary:pressed, QPushButton[accent="primary"]:pressed {
    background-color: #3730a3;
}

/* Botões de Sucesso (Verde) */
QPushButton#btn-success, QPushButton[accent="success"] {
    background-color: #10b981;
    color: #ffffff;
    border: 1px solid #059669;
}
QPushButton#btn-success:hover, QPushButton[accent="success"]:hover {
    background-color: #059669;
}

/* Botões de Alerta / Perigo (Vermelho) */
QPushButton#btn-danger, QPushButton[accent="danger"] {
    background-color: #ef4444;
    color: #ffffff;
    border: 1px solid #dc2626;
}
QPushButton#btn-danger:hover, QPushButton[accent="danger"]:hover {
    background-color: #dc2626;
}

/* =========================================================================
   CAMPOS DE TEXTO & ENTRADA (QLINEEDIT, QTEXTEDIT)
   ========================================================================= */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 12px;
    color: #0f172a;
    font-size: 13px;
    selection-background-color: #c7d2fe;
    selection-color: #1e1b4b;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1.5px solid #4f46e5;
    background-color: #ffffff;
}

QLineEdit:hover, QTextEdit:hover {
    border-color: #94a3b8;
}

/* =========================================================================
   COMBOS (QCOMBOBOX)
   ========================================================================= */
QComboBox {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 8px;
    padding: 7px 12px;
    color: #0f172a;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #94a3b8;
}

QComboBox:focus {
    border: 1.5px solid #4f46e5;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid #e2e8f0;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #e0e7ff;
    selection-color: #3730a3;
    outline: none;
}

/* =========================================================================
   CARTÕES & CAIXAS (QGROUPBOX, QFRAME)
   ========================================================================= */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: 700;
    color: #334155;
    font-size: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 2px;
    padding: 0 6px;
    background-color: #ffffff;
    color: #4f46e5;
}

/* =========================================================================
   BARRAS DE PROGRESSO (QPROGRESSBAR)
   ========================================================================= */
QProgressBar {
    background-color: #e2e8f0;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    font-size: 10px;
    font-weight: bold;
    color: #334155;
    border: none;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #4f46e5);
    border-radius: 6px;
}

/* =========================================================================
   BARRA DE ROLAGEM SLIM MODERNA (QSCROLLBAR)
   ========================================================================= */
QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    border-radius: 4px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 25px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #f1f5f9;
    height: 8px;
    border-radius: 4px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #cbd5e1;
    min-width: 25px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* =========================================================================
   DIVISORES (QSPLITTER)
   ========================================================================= */
QSplitter::handle {
    background-color: #e2e8f0;
    width: 3px;
    height: 3px;
    border-radius: 1px;
}

QSplitter::handle:hover {
    background-color: #6366f1;
}

/* =========================================================================
   TABELAS & LISTAS (QTABLEWIDGET, QLISTWIDGET)
   ========================================================================= */
QTableWidget, QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #e0e7ff;
    selection-color: #3730a3;
    alternate-background-color: #f8fafc;
}

QHeaderView::section {
    background-color: #f1f5f9;
    color: #475569;
    font-weight: 700;
    font-size: 12px;
    padding: 6px 8px;
    border: none;
    border-bottom: 1.5px solid #cbd5e1;
}

QListWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #f1f5f9;
    border-radius: 6px;
    margin: 2px 4px;
}

QListWidget::item:hover {
    background-color: #f8fafc;
}

QListWidget::item:selected {
    background-color: #e0e7ff;
    color: #3730a3;
    font-weight: 600;
}

/* =========================================================================
   RADIO BUTTONS (QRADIOBUTTON)
   ========================================================================= */
QRadioButton {
    spacing: 10px;
    font-size: 13px;
    color: #1e293b;
    padding: 6px 8px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}

QRadioButton::indicator:hover {
    border-color: #6366f1;
}

QRadioButton::indicator:checked {
    border-color: #4f46e5;
    background-color: #4f46e5;
}

/* =========================================================================
   CHECKBOX (QCHECKBOX)
   ========================================================================= */
QCheckBox {
    spacing: 8px;
    font-size: 13px;
    color: #334155;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid #cbd5e1;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #6366f1;
}

QCheckBox::indicator:checked {
    border-color: #4f46e5;
    background-color: #4f46e5;
}
"""


def aplicar_estilo_app(app):
    """Aplica o tema moderno universal à aplicação."""
    app.setStyleSheet(TEMA_MODERNO_QSS)
