import json
import os
from pathlib import Path
import shutil

from logger import log_info, log_sucesso, log_aviso, log_erro


def resolver_caminho(caminho_str: str, tipo_padrao: str = "downloads") -> Path:
    """
    Resolve caminhos relativos ao usuário (~/Downloads, ~/Documents),
    variáveis de ambiente (%USERPROFILE%) e caminhos legados de outras máquinas.
    """
    home = Path.home()
    if not caminho_str or "ap44" in caminho_str:
        if tipo_padrao == "downloads":
            return home / "Downloads" / "estudos"
        else:
            docs = home / "Documents"
            if not docs.exists() and (home / "Documentos").exists():
                docs = home / "Documentos"
            return docs / "estudos"

    caminho_expandido = os.path.expandvars(os.path.expanduser(caminho_str))
    p = Path(caminho_expandido)
    if "Documents" in p.parts and not p.exists():
        p_alt = Path(str(p).replace("Documents", "Documentos"))
        if p_alt.parent.exists():
            return p_alt
    return p


def executar_organizacao(caminho_config: str = "materias.json", arquivos_extras: list = None):
    # Abre o json e pega as infos
    with open(caminho_config, mode="r", encoding="utf-8") as file:
        configuracoes = json.load(file)

    pasta_entrada = configuracoes.get("pasta_entrada", "~/Downloads/estudos")
    pasta_destino = configuracoes.get("pasta_destino", "~/Documents/estudos")
    palavras_chave = configuracoes.get("palavras_chave", {})

    # Resolve os caminhos universais no computador atual
    diretorio_entrada = resolver_caminho(pasta_entrada, "downloads")
    diretorio_destino_base = resolver_caminho(pasta_destino, "documents")

    # Garante que os diretórios existam
    diretorio_entrada.mkdir(parents=True, exist_ok=True)
    diretorio_destino_base.mkdir(parents=True, exist_ok=True)

    arquivos_encontrados = []
    if diretorio_entrada.exists():
        for item in diretorio_entrada.iterdir():
            if item.is_file():
                arquivos_encontrados.append(item)

    # Adiciona arquivos recebidos diretamente (ex: via Drag & Drop)
    if arquivos_extras:
        for extra in arquivos_extras:
            p_extra = Path(extra)
            if p_extra.is_file() and p_extra not in arquivos_encontrados:
                arquivos_encontrados.append(p_extra)
            elif p_extra.is_dir():
                for sub in p_extra.iterdir():
                    if sub.is_file() and sub not in arquivos_encontrados:
                        arquivos_encontrados.append(sub)

    log_info(f"Escaneando arquivos... Encontrados: {len(arquivos_encontrados)}", "Organizador")
    for arq in arquivos_encontrados:
        log_info(f"Arquivo identificado: {arq.name}", "Organizador")

    if not arquivos_encontrados:
        log_aviso("Nenhum arquivo encontrado para organizar na pasta de entrada.", "Organizador")
        return {
            "pasta_destino": str(diretorio_destino_base),
            "total_movidos": 0,
            "classificacao": {}
        }

    # Le o conteudo dos arquivos
    conteudo_arquivo = {}

    for arquivo in arquivos_encontrados:
        try:
            texto = arquivo.read_text(encoding='utf-8').lower()
            # Unimos o NOME com o CONTEUDO para ajudar na busca por palavras-chave
            texto_completo = f"{arquivo.name.lower()} {texto}"
            conteudo_arquivo[arquivo] = texto_completo
            log_info(f"Texto lido com sucesso: {arquivo.name}", "Organizador")

        except UnicodeDecodeError:
            # Se for PDF, imagem ou binário, usa o próprio nome do arquivo para classificação
            texto_completo = arquivo.name.lower()
            conteudo_arquivo[arquivo] = texto_completo
            log_info(f"Arquivo binário/mídia: usando nome do arquivo para classificação: {arquivo.name}", "Organizador")
        except Exception as e:
            log_erro(f"Erro ao ler arquivo {arquivo.name}", "Organizador", exc=e)

    # Classifica por palavras-chave
    classificacao_arquivos = {}     

    for arquivo, texto in conteudo_arquivo.items():
        materia_vencedora = "Sem_Categoria"
        maior_pontuacao = 0

        for materia, palavras in palavras_chave.items():
            pontos_materia = 0

            for palavra in palavras:
                pontos_materia += texto.count(palavra.lower())

            if pontos_materia > maior_pontuacao:
                maior_pontuacao = pontos_materia
                materia_vencedora = materia

        classificacao_arquivos[arquivo] = materia_vencedora
        if materia_vencedora == "Sem_Categoria":
            log_aviso(f"'{arquivo.name}' não correspondeu a nenhuma matéria. Movendo para 'Sem_Categoria'.", "Organizador")
        else:
            log_sucesso(f"'{arquivo.name}' classificado em '{materia_vencedora}' ({maior_pontuacao} pontos).", "Organizador")

    # Mover os arquivos para as pastas finais
    log_info("Iniciando movimentação de arquivos para pastas de destino...", "Organizador")

    for arquivo, materia in classificacao_arquivos.items():
        try:
            pasta_destino_materia = diretorio_destino_base / materia
            pasta_destino_materia.mkdir(parents=True, exist_ok=True)

            caminho_final = pasta_destino_materia / arquivo.name
            shutil.move(arquivo, caminho_final)
            log_sucesso(f"Movido com sucesso: {arquivo.name} -> {materia}/", "Organizador")
        except Exception as e:
            log_erro(f"Falha ao mover {arquivo.name} para {materia}/", "Organizador", exc=e)

    log_sucesso(f"Organização finalizada! Total de arquivos organizados: {len(classificacao_arquivos)}", "Organizador")
    return {
        "pasta_destino": str(diretorio_destino_base),
        "total_movidos": len(classificacao_arquivos),
        "classificacao": {str(arq.name): mat for arq, mat in classificacao_arquivos.items()}
    }