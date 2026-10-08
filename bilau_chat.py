import os
import json
import requests
from typing import Optional, Generator
from PyQt6.QtCore import QThread, pyqtSignal
from dotenv import load_dotenv

from logger import log_info, log_sucesso, log_aviso, log_erro
import database
from watcher import obter_modelo_embedding

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


def construir_prompt_bilau(
    pergunta: str,
    apelido_info: Optional[dict] = None,
    trechos_rag: list = None,
    perfil: dict = None,
    desempenho: list = None
) -> str:
    """Consolida as 4 etapas da arquitetura em um System Prompt cirúrgico para o Qwen 2.5 3B."""
    
    # 1. Informações de Matéria/Professor mapeados
    contexto_materia = ""
    if apelido_info:
        contexto_materia = (
            f"- Matéria detectada via apelido/gíria: {apelido_info.get('materia_nome')}\n"
            f"- Professor(a) / Referência: {apelido_info.get('nome_professor')} (Termo: '{apelido_info.get('apelido_ou_termo')}')"
        )
    else:
        contexto_materia = "- Matéria: Não especificada explicitamente (usar conhecimento geral e base RAG)."

    # 2. Trechos RAG recuperados
    bloco_rag = "Nenhum material indexado diretamente para esta dúvida."
    if trechos_rag:
        trechos_formatados = []
        for t in trechos_rag:
            origem = t.get("arquivo_origem", "Arquivo")
            trechos_formatados.append(f"[{origem}]:\n{t.get('texto', '')}")
        bloco_rag = "\n\n---\n\n".join(trechos_formatados)

    # 3. Perfil do Aluno (Ficha Freud)
    estilo = perfil.get("estilo_explicacao", "Direto ao ponto, com exemplos de código e passos práticos") if perfil else "Direto ao ponto"
    tom = perfil.get("tom_conversa", "Informal, brother de estudos, sem enrolação") if perfil else "Informal"

    # 4. Histórico de Erros / Desempenho
    bloco_erros = ""
    if desempenho:
        top_erros = [f"- {d['topico']}: {d['erros']} erro(s) registrados" for d in desempenho[:3]]
        bloco_erros = f"\nATENÇÃO AO HISTÓRICO DO ALUNO (Tópicos em que ele costuma errar):\n" + "\n".join(top_erros)

    prompt = f"""Você é o "Bilau", o auxiliar de estudos do usuário.
Você é um parceiro de estudos inteligente, direto ao ponto, informal e extremamente didático.
Proibido formalidades corporativas ou enrolação vazia.

PERFIL DO ESTUDANTE (FREUD):
- Estilo: {estilo}
- Tom: {tom}
{bloco_erros}

CONTEXTO DETECTADO:
{contexto_materia}

CONTEÚDO DAS APOSTILAS / LISTAS DE EXERCÍCIOS (RAG LOCAL):
{bloco_rag}

PERGUNTA DO USUÁRIO:
{pergunta}

INSTRUÇÕES DE RESPOSTA:
1. Vá direto na solução ou explicação do que foi pedido.
2. Se a pergunta for sobre lista ou professor citado por apelido, use o contexto acima para resolver a questão exata.
3. Se envolver cálculos ou código, mostre o raciocínio claro e objetivo sem pular etapas cruciais.
"""
    return prompt


def consultar_ollama_stream(prompt: str) -> Generator[str, None, None]:
    """Chama a API local do Ollama com streaming ativo."""
    endpoint = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.4
        }
    }

    try:
        response = requests.post(endpoint, json=payload, stream=True, timeout=60)
        if response.status_code != 200:
            yield f"\n[Erro Ollama]: Status {response.status_code} - {response.text}"
            return

        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    dado = json.loads(line)
                    texto = dado.get("response", "")
                    if texto:
                        yield texto
                    if dado.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
    except requests.exceptions.ConnectionError:
        yield (
            f"\n⚠️ **Bilau Offline**: O Ollama não está respondendo em `{OLLAMA_URL}`.\n"
            f"Para ativar o cérebro local, abra um terminal e rode:\n"
            f"```powershell\nollama run {OLLAMA_MODEL}\n```"
        )
    except Exception as e:
        log_erro("Falha na chamada ao Ollama", "BilauChat", exc=e)
        yield f"\n[Erro ao consultar Ollama]: {e}"


class BilauWorker(QThread):
    """Worker QThread para integração fluida no PySide6 sem travar a interface."""
    token_recebido = pyqtSignal(str)
    finalizado = pyqtSignal(str)
    erro = pyqtSignal(str)

    def __init__(self, pergunta: str):
        super().__init__()
        self.pergunta = pergunta

    def run(self):
        try:
            log_info(f"Processando pergunta no Campo Bilau: '{self.pergunta}'", "BilauChat")

            # 1. Mapeamento de Apelidos
            apelido_info = None
            materia_id = None
            try:
                apelido_info = database.mapear_apelido(self.pergunta)
                if apelido_info:
                    materia_id = apelido_info.get("materia_id")
                    log_sucesso(f"Apelido identificado: {apelido_info}", "BilauChat")
            except Exception as e:
                log_aviso(f"Consulta de apelido ignorada: {e}", "BilauChat")

            # 2. Busca Vetorial (pgvector)
            trechos_rag = []
            try:
                modelo = obter_modelo_embedding()
                emb = modelo.encode(self.pergunta, convert_to_numpy=True).tolist()
                trechos_rag = database.buscar_contexto_rag(emb, limite=4, materia_id=materia_id)
                log_info(f"RAG: {len(trechos_rag)} trecho(s) semântico(s) resgatado(s).", "BilauChat")
            except Exception as e:
                log_aviso(f"Busca RAG ignorada: {e}", "BilauChat")

            # 3. Filtro de Perfil (Ficha Freud)
            perfil = {}
            desempenho = []
            try:
                perfil = database.obter_perfil_estudante()
                if materia_id:
                    desempenho = database.obter_desempenho_materia(materia_id)
            except Exception as e:
                log_aviso(f"Perfil/Desempenho ignorado: {e}", "BilauChat")

            # 4. Chamada ao LLM Local (Ollama)
            prompt_completo = construir_prompt_bilau(
                pergunta=self.pergunta,
                apelido_info=apelido_info,
                trechos_rag=trechos_rag,
                perfil=perfil,
                desempenho=desempenho
            )

            texto_acumulado = ""
            for pedaco in consultar_ollama_stream(prompt_completo):
                texto_acumulado += pedaco
                self.token_recebido.emit(pedaco)

            self.finalizado.emit(texto_acumulado)

        except Exception as e:
            log_erro("Erro geral no worker do Bilau", "BilauChat", exc=e)
            self.erro.emit(str(e))
