import os
import json
from pathlib import Path
from logger import log_info, log_sucesso, log_erro

CAMINHO_PREFERENCIAS = Path("preferencias.json")
CAMINHO_ENV = Path(".env")


def carregar_gemini_api_key() -> str:
    """
    Retorna a chave da API Gemini buscando em:
    1. os.environ['GEMINI_API_KEY']
    2. Arquivo .env
    3. preferencias.json
    """
    # 1. Variável de ambiente do processo
    chave = os.getenv("GEMINI_API_KEY", "").strip()
    if chave:
        return chave

    # 2. Arquivo .env
    if CAMINHO_ENV.exists():
        try:
            with open(CAMINHO_ENV, "r", encoding="utf-8") as f:
                for line in f:
                    linha = line.strip()
                    if linha.startswith("GEMINI_API_KEY="):
                        chave = linha.split("=", 1)[1].strip().strip('"').strip("'")
                        if chave:
                            os.environ["GEMINI_API_KEY"] = chave
                            return chave
        except Exception as e:
            log_erro("Falha ao ler .env", "Credenciais", exc=e)

    # 3. Arquivo preferencias.json
    if CAMINHO_PREFERENCIAS.exists():
        try:
            with open(CAMINHO_PREFERENCIAS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                chave = dados.get("gemini_api_key", "").strip()
                if chave:
                    os.environ["GEMINI_API_KEY"] = chave
                    return chave
        except Exception as e:
            log_erro("Falha ao ler preferencias.json", "Credenciais", exc=e)

    return ""


def salvar_gemini_api_key(chave: str) -> bool:
    """
    Salva a chave no preferencias.json, no .env e na variável de ambiente do processo.
    """
    chave_limpa = chave.strip()
    if not chave_limpa:
        return False

    os.environ["GEMINI_API_KEY"] = chave_limpa

    # 1. Se existir a chave legada em preferencias.json, remove para evitar commit acidental
    try:
        if CAMINHO_PREFERENCIAS.exists():
            with open(CAMINHO_PREFERENCIAS, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if "gemini_api_key" in dados:
                del dados["gemini_api_key"]
                with open(CAMINHO_PREFERENCIAS, "w", encoding="utf-8") as f:
                    json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log_erro("Erro ao limpar chave em preferencias.json", "Credenciais", exc=e)

    # 2. Salva no .env
    try:
        linhas = []
        if CAMINHO_ENV.exists():
            with open(CAMINHO_ENV, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip().startswith("GEMINI_API_KEY="):
                        linhas.append(line)
        linhas.append(f"GEMINI_API_KEY={chave_limpa}\n")
        with open(CAMINHO_ENV, "w", encoding="utf-8") as f:
            f.writelines(linhas)
    except Exception as e:
        log_erro("Erro ao salvar chave em .env", "Credenciais", exc=e)

    log_sucesso("Chave API do Gemini salva com sucesso e persistida no sistema!", "Credenciais")
    return True
