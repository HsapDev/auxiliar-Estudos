import json
import os
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from organizador_pastas import resolver_caminho
from logger import log_info, log_sucesso, log_aviso, log_erro
from credenciais import carregar_gemini_api_key


def carregar_conhecimento_materia(materia: str) -> dict:
    """
    Localiza o arquivo de conhecimento compilado da matéria.
    Procura tanto na pasta de estudos quanto na raiz.
    """
    candidatos = [
        Path(f"conhecimento_{materia}.json"),
        Path("conhecimento_materia.json")
    ]

    try:
        pasta_destino = Path.home() / "Documents" / "estudos"
        if os.path.exists("materias.json"):
            with open("materias.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                pasta_destino = resolver_caminho(cfg.get("pasta_destino", "~/Documents/estudos"), "documents")

        candidatos.insert(0, pasta_destino / materia / f"conhecimento_{materia}.json")
        candidatos.insert(1, pasta_destino / materia / "conhecimento_materia.json")

        # Busca por aproximação de nome de pasta
        if pasta_destino.exists():
            for sub in pasta_destino.iterdir():
                if sub.is_dir() and (materia.lower() in sub.name.lower() or sub.name.lower() in materia.lower()):
                    candidatos.insert(0, sub / f"conhecimento_{sub.name}.json")
                    candidatos.insert(1, sub / "conhecimento_materia.json")
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


def carregar_todas_questoes_arena(materias_filtro: list[str] = None) -> list[dict]:
    """
    Varre a pasta de estudos e a raiz em busca de todos os arquivos de conhecimento
    e consolida os exercícios de todas as matérias encontradas.
    """
    questoes = []
    arquivos_vistos = set()

    pasta_destino = Path.home() / "Documents" / "estudos"
    if os.path.exists("materias.json"):
        try:
            with open("materias.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                pasta_destino = resolver_caminho(cfg.get("pasta_destino", "~/Documents/estudos"), "documents")
        except Exception:
            pass

    candidatos = []
    if pasta_destino.exists():
        for arq in pasta_destino.glob("**/conhecimento*.json"):
            candidatos.append(arq)

    for arq in Path(".").glob("conhecimento*.json"):
        candidatos.append(arq.resolve())

    for arq in candidatos:
        caminho_real = arq.resolve()
        if caminho_real in arquivos_vistos or not caminho_real.exists():
            continue
        arquivos_vistos.add(caminho_real)

        try:
            with open(caminho_real, "r", encoding="utf-8") as f:
                dados = json.load(f)
                materia_nome = dados.get("materia", "").strip() or arq.parent.name
                exercicios = dados.get("exercicios_resolvidos", [])

                if materias_filtro:
                    # Se tiver filtro, verifica se a matéria bate com alguma selecionada
                    match = any(
                        m.lower() in materia_nome.lower() or materia_nome.lower() in m.lower()
                        for m in materias_filtro
                    )
                    if not match:
                        continue

                for ex in exercicios:
                    item = dict(ex)
                    item["materia"] = materia_nome
                    questoes.append(item)
        except Exception as e:
            log_aviso(f"Não foi possível ler {caminho_real}: {e}", "Arena")

    return questoes


def listar_materias_com_conhecimento() -> list[str]:
    """Retorna a lista de todas as matérias cadastradas ou que possuem apostila/conhecimento."""
    materias = set()

    if os.path.exists("materias.json"):
        try:
            with open("materias.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                for k in cfg.get("palavras_chave", {}).keys():
                    if k.strip():
                        materias.add(k.strip())
        except Exception:
            pass

    pasta_destino = Path.home() / "Documents" / "estudos"
    if pasta_destino.exists():
        for sub in pasta_destino.iterdir():
            if sub.is_dir() and not sub.name.startswith("."):
                materias.add(sub.name)

    return sorted(list(materias))


def carregar_erros_recentes(materia: str = None, limite: int = 5) -> list[dict]:
    """Carrega os erros mais recentes cometidos na Arena."""
    caminho = Path("erros_arena.json")
    if not caminho.exists():
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            todos_erros = json.load(f)
        if materia:
            todos_erros = [
                e for e in todos_erros 
                if e.get("materia", "").lower() in materia.lower() or materia.lower() in e.get("materia", "").lower()
            ]
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
- Se envolver contas ou raciocínio lógico, mostre o passo a passo alertando sobre pegadinhas e trocas de sinal.
"""
    return system_prompt


class GuruChatWorker(QThread):
    """Worker que comunica com a API Google Gemini com suporte a streaming contínuo."""
    resposta_parcial = pyqtSignal(str)
    resposta_completa = pyqtSignal(str)
    erro = pyqtSignal(str)

    def __init__(self, modelo: str, materia: str, historico: list, pergunta: str, api_key_gemini: str = ""):
        super().__init__()
        self.modelo = modelo or "gemini-2.5-flash"
        self.materia = materia
        self.historico = historico  # Lista de {"role": "user"|"assistant", "content": "..."}
        self.pergunta = pergunta
        self.api_key_gemini = api_key_gemini or carregar_gemini_api_key()

    def run(self):
        if not self.api_key_gemini:
            self.erro.emit("Chave da API Gemini não configurada. Configure sua chave na aba Configurações.")
            return

        system_prompt = construir_system_prompt_guru(self.materia)
        log_info(f"Guru ativado para matéria '{self.materia}' via Gemini Cloud (Modelo: {self.modelo})", "Guru")

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key_gemini)

            # Constrói o histórico de mensagens formatado
            mensagens_prompt = f"{system_prompt}\n\n--- HISTÓRICO DA CONVERSA RECENTE ---"
            for msg in self.historico[-6:]:
                papel = "Aluno" if msg.get("role") == "user" else "Guru"
                mensagens_prompt += f"\n{papel}: {msg.get('content', '')}"

            mensagens_prompt += f"\n\n--- NOVA DÚVIDA DO ESTUDANTE ---\n{self.pergunta}"

            # Modelos para tentar caso o selecionado sofra instabilidade temporária (503)
            modelos_para_tentar = [
                self.modelo,
                "gemini-2.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.5-flash"
            ]
            # Remove duplicatas preservando ordem
            modelos_unicos = []
            for m in modelos_para_tentar:
                if m not in modelos_unicos:
                    modelos_unicos.append(m)

            sucesso = False
            texto_acumulado = ""

            for mod in modelos_unicos:
                try:
                    log_info(f"Enviando consulta do Guru para o modelo {mod}...", "Guru")
                    response = client.models.generate_content_stream(
                        model=mod,
                        contents=mensagens_prompt
                    )

                    for chunk in response:
                        if chunk and chunk.text:
                            texto_acumulado += chunk.text
                            self.resposta_parcial.emit(chunk.text)

                    if texto_acumulado.strip():
                        log_sucesso(f"Resposta concluída com sucesso via {mod}!", "Guru")
                        self.resposta_completa.emit(texto_acumulado)
                        sucesso = True
                        break

                except Exception as e:
                    msg_erro = str(e).lower()
                    log_aviso(f"Modelo {mod} retornou erro no Guru: {e}", "Guru")
                    if "503" in msg_erro or "unavailable" in msg_erro or "high demand" in msg_erro:
                        # Tenta o próximo modelo
                        continue
                    else:
                        raise e

            if not sucesso and not texto_acumulado.strip():
                raise RuntimeError("Não foi possível obter resposta dos modelos Gemini no momento. Verifique sua conexão ou chave de API.")

        except Exception as e:
            log_erro("Erro ao consultar o Guru de Estudos via Gemini", "Guru", exc=e)
            self.erro.emit(f"Erro no Guru de Estudos: {e}")


# Stubs para retrocompatibilidade sem Ollama
def verificar_ollama_online(timeout: float = 1.0) -> bool:
    return False

def listar_modelos_locais(timeout: float = 1.0) -> list[str]:
    return []

def iniciar_servico_ollama() -> bool:
    return False

class OllamaPullWorker(QThread):
    progresso = pyqtSignal(str)
    concluido = pyqtSignal(str)
    erro = pyqtSignal(str)
    def __init__(self, modelo: str):
        super().__init__()
    def run(self):
        self.erro.emit("Ollama foi desativado em favor do Gemini Cloud.")
