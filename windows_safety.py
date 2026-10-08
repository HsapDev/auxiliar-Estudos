import ctypes
import sys
from logger import log_info, log_aviso, log_erro

_user32 = None
if sys.platform == "win32":
    try:
        _user32 = ctypes.windll.user32
    except Exception as e:
        log_aviso(f"Não foi possível carregar user32.dll para trava de desligamento: {e}", "WindowsSafety")


def bloquear_desligamento_so(hwnd: int, motivo: str = "Indexação e vetorização de estudos em andamento...") -> bool:
    """Registra trava no Windows API impedindo desligamento involuntário durante I/O."""
    if not _user32 or not hwnd:
        return False
    try:
        sucesso = _user32.ShutdownBlockReasonCreate(hwnd, motivo)
        if sucesso:
            log_info(f"Trava de segurança do Windows ativada: '{motivo}'", "WindowsSafety")
        return bool(sucesso)
    except Exception as e:
        log_erro("Erro ao chamar ShutdownBlockReasonCreate", "WindowsSafety", exc=e)
        return False


def liberar_desligamento_so(hwnd: int) -> bool:
    """Remove a trava de desligamento do Windows."""
    if not _user32 or not hwnd:
        return False
    try:
        sucesso = _user32.ShutdownBlockReasonDestroy(hwnd)
        if sucesso:
            log_info("Trava de segurança do Windows desativada.", "WindowsSafety")
        return bool(sucesso)
    except Exception as e:
        log_erro("Erro ao chamar ShutdownBlockReasonDestroy", "WindowsSafety", exc=e)
        return False
