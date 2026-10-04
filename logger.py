import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Garante que sys.stdout e sys.stderr não quebrem com caracteres unicode no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Arquivo padrão de log no diretório raiz do projeto
LOG_FILE = Path(__file__).parent / "app.log"

# Níveis customizados / representação visual
SUCESSO_LEVEL = 25  # Entre INFO (20) e WARNING (30)
logging.addLevelName(SUCESSO_LEVEL, "SUCESSO")

class SafeFileFormatter(logging.Formatter):
    """Formatador para arquivo com ícones UTF-8."""
    FORMATOS = {
        logging.DEBUG: "🔍 [DEBUG]",
        logging.INFO: "ℹ️ [INFO]",
        SUCESSO_LEVEL: "✅ [SUCESSO]",
        logging.WARNING: "⚠️ [AVISO]",
        logging.ERROR: "❌ [ERRO]",
        logging.CRITICAL: "🚨 [CRÍTICO]"
    }

    def format(self, record):
        prefixo = self.FORMATOS.get(record.levelno, "[LOG]")
        dt_str = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        modulo = record.name if record.name and record.name != "root" else "App"
        
        msg = record.getMessage()
        texto_formatado = f"[{dt_str}] {prefixo} [{modulo}] {msg}"
        
        if record.exc_info:
            texto_formatado += "\n" + "".join(traceback.format_exception(*record.exc_info))
        return texto_formatado


class SafeConsoleFormatter(logging.Formatter):
    """Formatador robusto para console que evita erros de encoding em qualquer terminal."""
    FORMATOS = {
        logging.DEBUG: "[DEBUG]",
        logging.INFO: "[INFO]",
        SUCESSO_LEVEL: "[SUCESSO]",
        logging.WARNING: "[AVISO]",
        logging.ERROR: "[ERRO]",
        logging.CRITICAL: "[CRITICO]"
    }

    def format(self, record):
        prefixo = self.FORMATOS.get(record.levelno, "[LOG]")
        dt_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        modulo = record.name if record.name and record.name != "root" else "App"
        
        msg = record.getMessage()
        texto_formatado = f"[{dt_str}] {prefixo} [{modulo}] {msg}"
        
        if record.exc_info:
            texto_formatado += "\n" + "".join(traceback.format_exception(*record.exc_info))
        return texto_formatado


# Configuração do Logger Central
_logger = logging.getLogger("AuxiliarEstudos")
_logger.setLevel(logging.DEBUG)

# Evita duplicar handlers se o módulo for recarregado
if not _logger.handlers:
    # 1. Handler para Arquivo (UTF-8, persistente)
    try:
        file_handler = logging.FileHandler(str(LOG_FILE), mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(SafeFileFormatter())
        _logger.addHandler(file_handler)
    except Exception as e:
        print(f"Aviso: Não foi possível abrir {LOG_FILE} para gravação: {e}")

    # 2. Handler para o Console (Terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(SafeConsoleFormatter())
    _logger.addHandler(console_handler)


# Listener / Signal para a Interface Gráfica PyQt (se estiver rodando com interface)
_qt_listener = None

def registrar_qt_listener(callback_fn):
    """Permite que a interface gráfica receba logs em tempo real."""
    global _qt_listener
    _qt_listener = callback_fn

def _notificar_qt(nivel: str, msg: str, modulo: str):
    if _qt_listener:
        try:
            dt_str = datetime.now().strftime("%H:%M:%S")
            _qt_listener(dt_str, nivel, modulo, msg)
        except Exception:
            pass


# Métodos de Conveniência
def log_info(mensagem: str, modulo: str = "Geral"):
    """Registra uma mensagem informativa de rotina."""
    logger_mod = logging.getLogger(modulo)
    logger_mod.parent = _logger
    logger_mod.info(mensagem)
    _notificar_qt("INFO", mensagem, modulo)

def log_sucesso(mensagem: str, modulo: str = "Geral"):
    """Registra uma operação concluída com êxito (✅)."""
    logger_mod = logging.getLogger(modulo)
    logger_mod.parent = _logger
    logger_mod.log(SUCESSO_LEVEL, mensagem)
    _notificar_qt("SUCESSO", mensagem, modulo)

def log_aviso(mensagem: str, modulo: str = "Geral"):
    """Registra um aviso ou situação não ideal (⚠️)."""
    logger_mod = logging.getLogger(modulo)
    logger_mod.parent = _logger
    logger_mod.warning(mensagem)
    _notificar_qt("AVISO", mensagem, modulo)

def log_erro(mensagem: str, modulo: str = "Geral", exc: Exception = None):
    """Registra um erro ou falha com detalhes da exceção (❌)."""
    logger_mod = logging.getLogger(modulo)
    logger_mod.parent = _logger
    if exc:
        logger_mod.error(mensagem, exc_info=exc)
    else:
        logger_mod.error(mensagem)
    _notificar_qt("ERRO", f"{mensagem} ({exc})" if exc else mensagem, modulo)

def obter_ultimos_logs(max_linhas: int = 200) -> str:
    """Lê as últimas linhas do arquivo app.log."""
    if not LOG_FILE.exists():
        return "Nenhum log registrado ainda."
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            linhas = f.readlines()
            return "".join(linhas[-max_linhas:])
    except Exception as e:
        return f"Erro ao ler arquivo de log: {e}"

def limpar_logs() -> bool:
    """Limpa o conteúdo do arquivo app.log."""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ℹ️ [INFO] [Logger] Arquivo de log reiniciado pelo usuário.\n")
        log_sucesso("Arquivo de logs limpo com sucesso!", "Logger")
        return True
    except Exception as e:
        log_erro(f"Falha ao limpar arquivo de log: {e}", "Logger")
        return False

def caminho_arquivo_log() -> str:
    """Retorna o caminho absoluto do arquivo app.log."""
    return str(LOG_FILE.resolve())
