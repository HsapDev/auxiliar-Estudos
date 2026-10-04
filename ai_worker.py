import os 
import json
import mimetypes
from PyQt6.QtCore import QThread, pyqtSignal
from google import genai
from google.genai import types
from pdf_generator import gerar_pdf_apostila
from logger import log_info, log_sucesso, log_aviso, log_erro


class FabriqueiroWorker(QThread):
    sucesso = pyqtSignal(str)
    erro = pyqtSignal(str)
    progresso = pyqtSignal(str)

    def __init__(self, caminhos_midias: list, api_key: str):
        super().__init__()
        self.caminhos_midias = caminhos_midias
        self.api_key = api_key

    def run(self):
        try:
            total_arqs = len(self.caminhos_midias)
            log_info(f"Iniciando Fabriqueiro para {total_arqs} arquivo(s)...", "Fabriqueiro")
            client = genai.Client(api_key=self.api_key)

            arquivos_uploaded = []

            for idx, caminho in enumerate(self.caminhos_midias, 1):
                caminho_limpo = os.path.abspath(caminho)
                nome_arq = os.path.basename(caminho_limpo)
                self.progresso.emit(f"Enviando arquivo {idx}/{total_arqs}: {nome_arq}...")
                log_info(f"Fazendo upload para API Gemini ({idx}/{total_arqs}): {nome_arq}", "Fabriqueiro")
                
                # Identifica o MIME type
                mime_type, _ = mimetypes.guess_type(caminho_limpo)
                if not mime_type:
                    if caminho_limpo.lower().endswith(".pdf"):
                        mime_type = "application/pdf"
                    else:
                        mime_type = "image/jpeg"

                # No SDK google-genai, ao passar o arquivo aberto em 'rb', evita a injeção
                # de cabeçalhos HTTP com caracteres não-ASCII (que causam o erro 'ascii' codec)
                with open(caminho_limpo, "rb") as f:
                    arq = client.files.upload(
                        file=f,
                        config=types.UploadFileConfig(
                            display_name=os.path.basename(caminho_limpo),
                            mime_type=mime_type
                        )
                    )
                arquivos_uploaded.append(arq)
                log_sucesso(f"Upload concluído com sucesso: {nome_arq}", "Fabriqueiro")

            prompt = """
            Você é um assistente acadêmico especialista. Analise as mídias enviadas (fotos de lousas, resumos ou exercícios) 
            e extraia o conhecimento em formato JSON estrito conforme o esquema:
            {
                "materia": "Nome da matéria",
                "resumo_big_picture": "Visão geral concisa sobre o conceito",
                "formulas": [{"nome": "Nome", "formula": "Expressão"}],
                "alertas_atencao": ["Troca de sinal em álgebra", "Cuidado com simplificação de fração"],
                "exercicios_resolvidos": [
                    {
                        "enunciado": "Descrição do problema",
                        "passos": ["Passo 1...", "Passo 2..."]
                    }
                ]
            }
            Responda SOMENTE o JSON puro, sem blocos markdown adicionais.
            """

            conteudo = arquivos_uploaded + [prompt]

            # Modelos GA disponíveis caso o principal enfrente alta demanda (503)
            modelos_para_tentar = [
                "gemini-3.8-flash",
                "gemini-3.5-flash-lite",
            ]

            response = None
            ultimo_erro = None

            import time
            for mod in modelos_para_tentar:
                self.progresso.emit(f"Analisando conteúdo com {mod}...")
                log_info(f"Enviando requisição de geração para o modelo {mod}...", "Fabriqueiro")
                for tentativa in range(2):
                    try:
                        response = client.models.generate_content(
                            model=mod,
                            contents=conteudo,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json"
                            )
                        )
                        if response and response.text:
                            log_sucesso(f"Conteúdo estruturado retornado com sucesso por {mod}!", "Fabriqueiro")
                            break
                    except Exception as e:
                        ultimo_erro = e
                        msg_erro = str(e).lower()
                        log_aviso(f"Tentativa {tentativa+1} no modelo {mod} falhou: {e}", "Fabriqueiro")
                        if "503" in msg_erro or "unavailable" in msg_erro or "high demand" in msg_erro or "resource_exhausted" in msg_erro:
                            self.progresso.emit(f"Servidor ocupado. Aguardando para tentar novamente...")
                            time.sleep(3)
                            continue
                        raise e

                if response and response.text:
                    break

            if not response or not response.text:
                if ultimo_erro and ("503" in str(ultimo_erro) or "unavailable" in str(ultimo_erro).lower() or "high demand" in str(ultimo_erro).lower()):
                    err_msg = "Os servidores do Gemini estão com alta demanda temporária (Erro 503). Por favor, tente novamente em instantes."
                    log_erro(err_msg, "Fabriqueiro", exc=ultimo_erro)
                    raise RuntimeError(err_msg)
                falha = ultimo_erro or RuntimeError("Falha ao obter resposta dos modelos do Gemini.")
                log_erro("Falha ao obter resposta dos modelos da Gemini", "Fabriqueiro", exc=falha)
                raise falha

            self.progresso.emit("Gerando arquivo PDF da apostila...")

            # Decodifica a resposta com segurança
            texto_resposta = response.text.encode("utf-8", "ignore").decode("utf-8").strip()
            if texto_resposta.startswith("```"):
                texto_resposta = texto_resposta.strip("`")
                if texto_resposta.startswith("json"):
                    texto_resposta = texto_resposta[4:].strip()
            dados_json = json.loads(texto_resposta)

            # Localiza a pasta de estudos configurada em materias.json
            import unicodedata
            import re
            from pathlib import Path
            import shutil
            from organizador_pastas import resolver_caminho

            pasta_destino_base = Path.home() / "Documents" / "estudos"
            materias_cadastradas = []

            caminho_config = "materias.json"
            if os.path.exists(caminho_config):
                try:
                    with open(caminho_config, "r", encoding="utf-8") as f_cfg:
                        cfg = json.load(f_cfg)
                        pasta_destino_str = cfg.get("pasta_destino", "~/Documents/estudos")
                        pasta_destino_base = resolver_caminho(pasta_destino_str, "documents")
                        materias_cadastradas = list(cfg.get("palavras_chave", {}).keys())
                except Exception as e:
                    print(f"Aviso ao ler config: {e}")

            # Encontra ou cria a pasta da matéria correspondente
            materia_ia = dados_json.get("materia", "Geral")
            
            def norm_comp(txt: str) -> str:
                nfd = unicodedata.normalize('NFD', txt)
                sem = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
                return re.sub(r'[^a-zA-Z0-9]', '', sem).lower()

            materia_ia_norm = norm_comp(materia_ia)
            pasta_materia_nome = None

            for cad in materias_cadastradas:
                cad_norm = norm_comp(cad)
                if cad_norm in materia_ia_norm or materia_ia_norm in cad_norm:
                    pasta_materia_nome = cad
                    break

            if not pasta_materia_nome:
                # Cria nome seguro a partir do nome dado pela IA
                nome_limpo = re.sub(r'[\\/*?:"<>|]', '', materia_ia).strip().replace(" ", "_")
                pasta_materia_nome = nome_limpo or "Geral"

            diretorio_materia = pasta_destino_base / pasta_materia_nome
            diretorio_materia.mkdir(parents=True, exist_ok=True)

            caminho_json = str(diretorio_materia / f"conhecimento_{pasta_materia_nome}.json")
            with open(caminho_json, "w", encoding="utf-8") as f:
                json.dump(dados_json, f, indent=4, ensure_ascii=False)

            caminho_pdf = str(diretorio_materia / f"Apostila_{pasta_materia_nome}.pdf")
            gerar_pdf_apostila(caminho_json, caminho_pdf)
            log_sucesso(f"Apostila PDF gerada com sucesso: {caminho_pdf}", "Fabriqueiro")
            log_sucesso(f"Base de conhecimento JSON salva: {caminho_json}", "Fabriqueiro")

            # Cópia local de conveniência
            try:
                shutil.copy(caminho_pdf, "Apostila_consolidada.pdf")
                shutil.copy(caminho_json, "conhecimento_materia.json")
            except Exception:
                pass

            self.sucesso.emit(caminho_pdf)
        except Exception as e:
            log_erro("Falha durante o processo do Fabriqueiro", "Fabriqueiro", exc=e)
            self.erro.emit(str(e))