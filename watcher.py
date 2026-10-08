import os
import time
import shutil
from pathlib import Path
from typing import Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pypdf

from logger import log_info, log_sucesso, log_aviso, log_erro
import database

_modelo_embedding = None

def obter_modelo_embedding():
    """Carrega o modelo de embeddings na CPU sob demanda (Singleton)."""
    global _modelo_embedding
    if _modelo_embedding is None:
        log_info("Carregando modelo local de embeddings (all-MiniLM-L6-v2) na CPU...", "Watcher")
        from sentence_transformers import SentenceTransformer
        _modelo_embedding = SentenceTransformer("all-MiniLM-L6-v2")
        log_sucesso("Modelo de embeddings carregado na CPU!", "Watcher")
    return _modelo_embedding


def esperar_arquivo_estabilizar(caminho: Path, timeout: float = 30.0, intervalo: float = 1.0) -> bool:
    """Aguarda o término do download/escrita no disco verificando tamanho e lock."""
    tempo_inicial = time.time()
    tamanho_anterior = -1

    while time.time() - tempo_inicial < timeout:
        if not caminho.exists():
            return False

        try:
            # Tenta abrir o arquivo em modo append exclusivo para checar locks de escrita
            with open(caminho, "ab"):
                pass
            tamanho_atual = caminho.stat().st_size
            if tamanho_atual > 0 and tamanho_atual == tamanho_anterior:
                return True
            tamanho_anterior = tamanho_atual
        except (PermissionError, IOError):
            # Arquivo ainda sendo gravado por outro processo (ex: navegador)
            pass

        time.sleep(intervalo)
    return False


def extrair_texto_arquivo(caminho: Path) -> str:
    """Extrai texto de arquivos PDF ou arquivos de texto puro."""
    extensao = caminho.suffix.lower()
    if extensao == ".pdf":
        try:
            leitor = pypdf.PdfReader(str(caminho))
            texto_completo = []
            for num, pag in enumerate(leitor.pages):
                conteudo_pag = pag.extract_text() or ""
                if conteudo_pag.strip():
                    texto_completo.append(conteudo_pag)
            return "\n\n".join(texto_completo)
        except Exception as e:
            log_erro(f"Falha ao ler PDF {caminho.name}", "Watcher", exc=e)
            return ""
    else:
        try:
            return caminho.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            log_erro(f"Falha ao ler arquivo de texto {caminho.name}", "Watcher", exc=e)
            return ""


def fatiar_texto(texto: str, tamanho_chunk: int = 600, sobreposicao: int = 100) -> list[str]:
    """Divide o texto em pedaços com sobreposição para preservar contexto semântico."""
    if not texto:
        return []
    pedacos = []
    inicio = 0
    tamanho_total = len(texto)

    while inicio < tamanho_total:
        fim = min(inicio + tamanho_chunk, tamanho_total)
        trecho = texto[inicio:fim].strip()
        if trecho:
            pedacos.append(trecho)
        if fim >= tamanho_total:
            break
        inicio += (tamanho_chunk - sobreposicao)

    return pedacos


def processar_arquivo_entrada(
    caminho: Path,
    pasta_processados: Path,
    ao_iniciar: Optional[Callable] = None,
    ao_concluir: Optional[Callable] = None
) -> bool:
    """Executa a pipeline de ingestão: extração -> chunking -> embedding -> pgvector -> limpeza."""
    ignorar_extensoes = {".tmp", ".crdownload", ".part", ".downloading"}
    if caminho.suffix.lower() in ignorar_extensoes or caminho.name.startswith("~"):
        return False

    log_info(f"Novo arquivo detectado na esteira: {caminho.name}. Verificando estabilidade de gravação...", "Watcher")
    if not esperar_arquivo_estabilizar(caminho):
        log_aviso(f"Arquivo {caminho.name} não estabilizou a gravação a tempo. Pulando.", "Watcher")
        return False

    if ao_iniciar:
        ao_iniciar()

    try:
        texto = extrair_texto_arquivo(caminho)
        if not texto.strip():
            log_aviso(f"Nenhum texto extraível encontrado em {caminho.name}", "Watcher")
            # Move mesmo assim para não ficar em loop
            destino = pasta_processados / caminho.name
            shutil.move(str(caminho), str(destino))
            return False

        chunks = fatiar_texto(texto)
        log_info(f"Arquivo fatiado em {len(chunks)} chunks semânticos. Gerando embeddings...", "Watcher")

        # Determina matéria e tópico padrão a partir do nome do arquivo
        nome_base = caminho.stem
        materia_nome = "Geral"
        if "_" in nome_base:
            partes = nome_base.split("_", 1)
            materia_nome = partes[0].capitalize()
            topico_nome = partes[1].replace("_", " ").capitalize()
        else:
            topico_nome = nome_base.replace("-", " ").capitalize()

        # Tenta persistir no PostgreSQL se o banco estiver online
        try:
            materia_id = database.obter_ou_criar_materia(materia_nome)
            topico_id = database.obter_ou_criar_topico(materia_id, topico_nome)

            modelo = obter_modelo_embedding()
            embeddings = modelo.encode(chunks, convert_to_numpy=True)

            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                database.salvar_chunk_rag(
                    materia_id=materia_id,
                    topico_id=topico_id,
                    arquivo=caminho.name,
                    indice=i,
                    texto=chunk,
                    embedding=emb.tolist()
                )
            log_sucesso(f"Indexação concluída: {len(chunks)} vetores inseridos em 'conteudos_rag' para '{materia_nome}'.", "Watcher")
        except Exception as e_db:
            log_aviso(f"Banco PostgreSQL indisponível durante vetorização ({e_db}). O arquivo será arquivado.", "Watcher")

        # 5. Limpeza automática: move para data/processados
        pasta_processados.mkdir(parents=True, exist_ok=True)
        destino_final = pasta_processados / caminho.name
        # Evita sobrescrever com mesmo nome
        if destino_final.exists():
            destino_final = pasta_processados / f"{caminho.stem}_{int(time.time())}{caminho.suffix}"

        shutil.move(str(caminho), str(destino_final))
        log_sucesso(f"Arquivo movido para {destino_final.name}.", "Watcher")
        return True

    except Exception as e:
        log_erro(f"Erro no processamento do arquivo {caminho.name}", "Watcher", exc=e)
        return False
    finally:
        if ao_concluir:
            ao_concluir()


class IngestaoWatcherHandler(FileSystemEventHandler):
    def __init__(self, pasta_entrada: Path, pasta_processados: Path, callback_iniciar=None, callback_concluir=None):
        self.pasta_entrada = pasta_entrada
        self.pasta_processados = pasta_processados
        self.callback_iniciar = callback_iniciar
        self.callback_concluir = callback_concluir

    def on_created(self, event):
        if not event.is_directory:
            processar_arquivo_entrada(
                Path(event.src_path),
                self.pasta_processados,
                self.callback_iniciar,
                self.callback_concluir
            )


def iniciar_servico_watcher(pasta_entrada: str = "data/entrada", pasta_processados: str = "data/processados"):
    """Inicia o observador de arquivos em modo daemon / standalone."""
    p_in = Path(pasta_entrada)
    p_proc = Path(pasta_processados)
    p_in.mkdir(parents=True, exist_ok=True)
    p_proc.mkdir(parents=True, exist_ok=True)

    handler = IngestaoWatcherHandler(p_in, p_proc)
    observer = Observer()
    observer.schedule(handler, str(p_in), recursive=False)
    observer.start()
    log_sucesso(f"Watcher ativo e monitorando a pasta: {p_in.resolve()}", "Watcher")
    return observer


if __name__ == "__main__":
    obs = iniciar_servico_watcher()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()
