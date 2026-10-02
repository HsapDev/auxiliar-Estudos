import json
from pathlib import Path
import shutil


def executar_organizacao(caminho_config:str="materias.json"):
    # Abre o json e pega as infos
    with open("materias.json", mode="r", encoding="utf-8") as file:
        configuracoes = json.load(file)

    pasta_entrada = configuracoes["pasta_entrada"]
    pasta_destino = configuracoes["pasta_destino"]
    palavras_chave = configuracoes["palavras_chave"]

    # Verifica se o diretorio de entrada existe
    diretorio_entrada = Path(pasta_entrada)

    if not diretorio_entrada.exists():
        print(f"ERRO: A pasta {pasta_entrada} nao foi encontrada!")
    else:
        arquivos_encontrados = []
        for item in diretorio_entrada.iterdir():
            if item.is_file():
                arquivos_encontrados.append(item)

        print(f"Total de arquivos encontrados: {len(arquivos_encontrados)}")
        for arq in arquivos_encontrados:
            print(f"-> encontrado: {arq.name}")

        # Le o conteudo dos arquivos
        conteudo_arquivo = {}

        for arquivo in arquivos_encontrados:
            try:
                texto = arquivo.read_text(encoding='utf-8').lower()
                # Unimos o NOME com o CONTEUDO para ajudar na busca por palavras-chave
                texto_completo = f"{arquivo.name.lower()} {texto}"
                conteudo_arquivo[arquivo] = texto_completo
                print(f"Lido com sucesso: {arquivo.name}")

            except UnicodeDecodeError:
                print(f"Aviso: nao foi possivel ler {arquivo.name} como texto (formato incompativel)")
            except Exception as e:
                print(f"ERRO ao ler {arquivo.name}: {e}")

        print(f"\nTotal de arquivos lidos com sucesso: {len(conteudo_arquivo)}")

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
            print(f"Arquivo {arquivo.name} -> classificado como: {materia_vencedora} (Matches: {maior_pontuacao})")

        # Movel os arquivos para as pastas finais
        diretorio_destino_base = Path(pasta_destino)

        print("\n--- Iniciando Movimentacao ---")

        for arquivo, materia in classificacao_arquivos.items():
            pasta_destino_materia = diretorio_destino_base / materia
            pasta_destino_materia.mkdir(parents=True, exist_ok=True)

            caminho_final = pasta_destino_materia / arquivo.name

            shutil.move(arquivo, caminho_final)
            print(f"Movido: {arquivo.name} -> {materia}/")

        print("\nOrganizacao concluida com sucesso!")