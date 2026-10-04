import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from organizador_pastas import resolver_caminho
from logger import log_info, log_sucesso, log_aviso, log_erro


OLLAMA_BASE_URL = "http://localhost:11434"


def verificar_ollama_online(timeout: float = 2.0) -> bool:
    """Verifica se o servidor do Ollama está rodando localmente."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def listar_modelos_locais(timeout: float = 3.0) -> list[str]:
    """Retorna a lista de modelos baixados no Ollama."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
            modelos = [m.get("name") for m in dados.get("models", [])]
            return modelos
    except Exception:
        return []


def carregar_conhecimento_materia(materia: str) -> dict:
    """
    Localiza o arquivo de conhecimento compilado da matéria.
    Procura tanto na raiz quanto na pasta de estudos configurada.
    """
    candidatos = [
        Path(f"conhecimento_{materia}.json"),
        Path("conhecimento_materia.json")
    ]

    try:
        if os.path.exists("materias.json"):
            with open("materias.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                pasta_destino = resolver_caminho(cfg.get("pasta_destino", "~/Documents/estudos"), "documents")
                candidatos.insert(0, pasta_destino / materia / f"conhecimento_{materia}.json")
                candidatos.insert(1, pasta_destino / materia / "conhecimento_materia.json")
    except Exception:
        pass

    for p in candidatos:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    return {}


def carregar_erros_recentes(materia: str = None, limite: int = 5) -> list[dict]:
    """Carrega os erros mais recentes cometidos na Arena."""
    caminho = Path("erros_arena.json")
    if not caminho.exists():
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            todos_erros = json.load(f)
        if materia:
            todos_erros = [e for e in todos_erros if e.get("materia", "").lower() == materia.lower()]
        return todos_erros[-limite:]
    except Exception:
        return []


def registrar_erro_arena(materia: str, topico: str, enunciado: str, resposta_usuario: str, solucao_esperada: str):
    """Registra um erro cometido na Arena para ser lembrado pelo Guru."""
    from datetime import datetime
    caminho = Path("erros_arena.json")
    erros = []
    if caminho.exists():
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                erros = json.load(f)
        except Exception:
            erros = []

    novo_erro = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "materia": materia,
        "topico": topico,
        "enunciado": enunciado,
        "resposta_usuario": resposta_usuario,
        "solucao_esperada": solucao_esperada
    }
    erros.append(novo_erro)

    # Mantém os últimos 50 erros
    if len(erros) > 50:
        erros = erros[-50:]

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(erros, f, indent=4, ensure_ascii=False)
    log_aviso(f"Erro registrado na Arena para revisão posterior: [{materia}] {topico}", "Arena")


def construir_system_prompt_guru(materia: str) -> str:
    """
    Realiza a INJEÇÃO DE CONTEXTO compilando:
    1. Preferências do estudante (preferencias.json)
    2. Base de conhecimento da matéria (conhecimento_materia.json)
    3. Histórico de erros recentes da Arena (erros_arena.json)
    """
    # 1. Preferências
    prefs_str = "Responda de forma direta ao ponto, didática, prática e focada em evitar erros de conta e pegadinhas."
    if os.path.exists("preferencias.json"):
        try:
            with open("preferencias.json", "r", encoding="utf-8") as f:
                p = json.load(f)
                prefs_str = (
                    f"Estilo: {p.get('estilo_resposta', 'direto ao ponto')}. "
                    f"Didática: {p.get('didatica', 'objetiva')}. "
                    f"Foco: {p.get('foco', 'evitar armadilhas e erros de cálculo')}. "
                    f"Instruções extras: {p.get('detalhes_adicionais', '')}"
                )
        except Exception:
            pass

    # 2. Conhecimento da Matéria
    dados_conhecimento = carregar_conhecimento_materia(materia)
    conhecimento_bloco = ""
    if dados_conhecimento:
        resumo = dados_conhecimento.get("resumo_big_picture", "")
        alertas = dados_conhecimento.get("alertas_atencao", [])
        formulas = dados_conhecimento.get("formulas", [])

        conhecimento_bloco += f"\nVISÃO GERAL DA MATÉRIA:\n{resumo}\n"

        if alertas:
            conhecimento_bloco += "\nALERTAS CRÍTICOS & ERROS FREQUENTES CONHECIDOS:\n"
            for a in alertas:
                conhecimento_bloco += f"- {a}\n"

        if formulas:
            conhecimento_bloco += "\nFÓRMULAS E IDENTIDADES PRINCIPAIS:\n"
            for item in formulas:
                if isinstance(item, dict):
                    conhecimento_bloco += f"- {item.get('nome', '')}: {item.get('formula', '')}\n"
                else:
                    conhecimento_bloco += f"- {item}\n"
    else:
        conhecimento_bloco = "Conhecimento geral da disciplina (apostila ainda não compilada para esta matéria)."

    # 3. Erros Recentes na Arena
    erros = carregar_erros_recentes(materia, limite=4)
    erros_bloco = ""
    if erros:
        erros_bloco = "\nHISTÓRICO DE ERROS RECENTES DO ESTUDANTE NA ARENA (DÊ ATENÇÃO ESPECIAL A ESTES PONTOS):\n"
        for idx, e in enumerate(erros, 1):
            erros_bloco += (
                f"{idx}. No tópico '{e.get('topico', 'Geral')}':\n"
                f"   Pergunta: {e.get('enunciado', '')[:120]}...\n"
                f"   O que o aluno respondeu: {e.get('resposta_usuario', '')}\n"
                f"   Solução correta: {e.get('solucao_esperada', '')[:120]}...\n"
            )
    else:
        erros_bloco = "Nenhum erro recente registrado na Arena até o momento."

    # Prompt Consolidado
    system_prompt = f"""Você é o 'Guru de Estudos', o mentor e tutor acadêmico pessoal do estudante para a matéria '{materia}'.

DIRETRIZES E PREFERÊNCIAS DO ESTUDANTE:
{prefs_str}

BASE DE CONHECIMENTO COMPILADA DA MATÉRIA:
{conhecimento_bloco}

HISTÓRICO DO ALUNO:
{erros_bloco}

INSTRUÇÕES DO GURU:
- Responda em português claro, direto ao ponto e incentivador.
- Quando o aluno fizer uma pergunta ou demonstrar dúvida, use a base de conhecimento compilada e dê ênfase nas áreas em que ele costuma tropeçar (erros recentes).
- Se envolver contas, mostre o passo a passo alertando sobre pegadinhas e trocas de sinal.
"""
    return system_prompt


class GuruChatWorker(QThread):
    resposta_parcial = pyqtSignal(str)
    resposta_completa = pyqtSignal(str)
    erro = pyqtSignal(str)

    def __init__(self, modelo: str, materia: str, historico: list, pergunta: str, api_key_gemini: str = ""):
        super().__init__()
        self.modelo = modelo
        self.materia = materia
        self.historico = historico  # Lista de {"role": "user"|"assistant", "content": "..."}
        self.pergunta = pergunta
        self.api_key_gemini = api_key_gemini

    def run(self):
        system_prompt = construir_system_prompt_guru(self.materia)

        # Se o modelo selecionado for Gemini ou se o Ollama estiver offline e tiver chave configurada
        is_gemini = "gemini" in self.modelo.lower()
        ollama_online = verificar_ollama_online(timeout=1.0)
        log_info(f"Guru ativado para matéria '{self.materia}' (Ollama online: {ollama_online}, Modelo: {self.modelo})", "Guru")

        if is_gemini or (not ollama_online and self.api_key_gemini):
            try:
                log_info("Utilizando modelo Gemini Flash em nuvem para responder à dúvida...", "Guru")
                from google import genai
                client = genai.Client(api_key=self.api_key_gemini)
                prompt_completo = f"{system_prompt}\n\nDÚVIDA DO ESTUDANTE: {self.pergunta}"
                
                # Tenta modelo leve
                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=prompt_completo
                )
                log_sucesso("Resposta gerada com sucesso via Gemini Flash Nuvem!", "Guru")
                self.resposta_completa.emit(response.text)
                return
            except Exception as e:
                log_erro("Falha na geração via Gemini Nuvem", "Guru", exc=e)
                if not ollama_online:
                    self.erro.emit(f"Ollama local está offline e houve erro no fallback da Gemini: {e}")
                    return

        try:
            log_info(f"Enviando consulta ao Ollama local ({self.modelo})...", "Guru")
            mensagens = [{"role": "system", "content": system_prompt}]
            # Adiciona histórico recente da conversa
            for msg in self.historico[-10:]:
                mensagens.append(msg)

            # Adiciona a pergunta atual
            mensagens.append({"role": "user", "content": self.pergunta})

            payload = {
                "model": self.modelo,
                "messages": mensagens,
                "stream": True,
                "options": {
                    "num_gpu": 0,    # Força execução na CPU, evitando crash do driver da Intel Iris Xe (que só tem 1GB)
                    "num_ctx": 2048,  # Reduz a alocação de memória RAM para KV cache de 8k para 2k
                    "num_thread": 4   # Limita uso de CPU para manter o Windows 100% responsivo
                }
            }

            req = urllib.request.Request(
                f"{OLLAMA_BASE_URL}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            texto_acumulado = ""
            with urllib.request.urlopen(req, timeout=120) as response:
                for line in response:
                    if line:
                        chunk_json = json.loads(line.decode("utf-8"))
                        msg_chunk = chunk_json.get("message", {}).get("content", "")
                        texto_acumulado += msg_chunk
                        self.resposta_parcial.emit(msg_chunk)

            log_sucesso(f"Resposta concluída com sucesso via Ollama ({self.modelo}).", "Guru")
            self.resposta_completa.emit(texto_acumulado)

        except urllib.error.HTTPError as e:
            corpo_erro = ""
            try:
                corpo_erro = e.read().decode("utf-8", "ignore")
            except Exception:
                pass
            msg_completa = f"{e} - {corpo_erro}"
            if "bad_alloc" in msg_completa or "exit status 1" in msg_completa:
                diag = (
                    "⚠️ Erro de Memória RAM (std::bad_alloc):\n\n"
                    "O modelo escolhido é muito pesado para a memória RAM livre do seu notebook no momento.\n\n"
                    "💡 Soluções recomendadas:\n"
                    "1. Use o modelo 'llama3.2:1b' ou 'qwen2.5:1.5b' (muito mais leves e rápidos).\n"
                    "2. Ou mude o Modelo para 'Gemini Flash (Nuvem)' no topo da tela (é gratuito e não usa a memória RAM do PC).\n"
                    "3. Feche outros aplicativos ou abas do navegador abertos."
                )
                log_erro("Falha de alocação de memória no Ollama (std::bad_alloc)", "Guru", exc=e)
                self.erro.emit(diag)
            else:
                log_erro(f"Erro HTTP do Ollama: {msg_completa}", "Guru", exc=e)
                self.erro.emit(f"Erro no Ollama: {corpo_erro or e}")

        except urllib.error.URLError as e:
            msg_erro = f"Não foi possível conectar ao Ollama local em {OLLAMA_BASE_URL}."
            log_erro(msg_erro, "Guru", exc=e)
            self.erro.emit(f"{msg_erro}\nVerifique se o serviço 'ollama' está rodando.\nDetalhes: {e}")
        except Exception as e:
            log_erro(f"Erro ao consultar o Guru de Estudos", "Guru", exc=e)
            self.erro.emit(f"Erro ao consultar o Guru de Estudos: {e}")


class OllamaPullWorker(QThread):
    progresso = pyqtSignal(str)
    concluido = pyqtSignal(str)
    erro = pyqtSignal(str)

    def __init__(self, modelo: str):
        super().__init__()
        self.modelo = modelo

    def run(self):
        try:
            log_info(f"Iniciando download do modelo '{self.modelo}' no Ollama...", "Ollama")
            self.progresso.emit(f"Iniciando download do modelo {self.modelo} no Ollama...")
            payload = {"name": self.modelo, "stream": True}
            req = urllib.request.Request(
                f"{OLLAMA_BASE_URL}/api/pull",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=600) as response:
                for line in response:
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        status = chunk.get("status", "")
                        completed = chunk.get("completed", 0)
                        total = chunk.get("total", 0)
                        if total > 0:
                            pct = int((completed / total) * 100)
                            self.progresso.emit(f"{status}: {pct}%")
                        else:
                            self.progresso.emit(status)

            log_sucesso(f"Download do modelo '{self.modelo}' concluído no Ollama!", "Ollama")
            self.concluido.emit(self.modelo)
        except Exception as e:
            log_erro(f"Erro ao baixar modelo '{self.modelo}'", "Ollama", exc=e)
            self.erro.emit(str(e))
