import json
import os
from pathlib import Path
from datetime import datetime
from logger import log_info, log_sucesso, log_aviso, log_erro

CAMINHO_RESUMOS = Path("resumos_estudos.json")


def carregar_todos_resumos() -> list[dict]:
    """Carrega todos os resumos e anotações de PDFs salvos."""
    if not CAMINHO_RESUMOS.exists():
        return []
    try:
        with open(CAMINHO_RESUMOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados if isinstance(dados, list) else []
    except Exception as e:
        log_erro("Falha ao ler resumos_estudos.json", "ResumosManager", exc=e)
        return []


def salvar_resumo_documento(
    materia: str,
    topico: str,
    arquivo_pdf: str,
    comentarios: list[dict],
    resumo_consolidado: str
) -> dict:
    """Salva ou atualiza um resumo consolidado de um PDF com seus comentários."""
    resumos = carregar_todos_resumos()

    # Procura se já existe resumo deste arquivo para atualizar
    item_existente = None
    nome_arquivo = Path(arquivo_pdf).name if arquivo_pdf else "Documento"

    for r in resumos:
        if r.get("arquivo_pdf") == nome_arquivo and r.get("materia") == materia:
            item_existente = r
            break

    if item_existente:
        item_existente["topico"] = topico
        item_existente["data_atualizacao"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        item_existente["comentarios"] = comentarios
        item_existente["resumo_consolidado"] = resumo_consolidado
        novo_registro = item_existente
    else:
        novo_registro = {
            "id": f"RES_{int(datetime.now().timestamp())}",
            "materia": materia,
            "topico": topico,
            "arquivo_pdf": nome_arquivo,
            "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "data_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "comentarios": comentarios,
            "resumo_consolidado": resumo_consolidado
        }
        resumos.append(novo_registro)

    try:
        with open(CAMINHO_RESUMOS, "w", encoding="utf-8") as f:
            json.dump(resumos, f, indent=4, ensure_ascii=False)
        log_sucesso(f"Resumo do documento '{nome_arquivo}' salvo com sucesso!", "ResumosManager")
        return novo_registro
    except Exception as e:
        log_erro("Erro ao salvar resumo", "ResumosManager", exc=e)
        return None


def obter_resumos_por_materia(materia: str = None) -> list[dict]:
    resumos = carregar_todos_resumos()
    if not materia or "todas" in materia.lower() or "geral" in materia.lower():
        return resumos
    return [
        r for r in resumos
        if r.get("materia", "").lower() == materia.lower() or materia.lower() in r.get("materia", "").lower()
    ]


def buscar_resumos_e_comentarios(termo: str, materia: str = None) -> list[dict]:
    """Busca em todos os resumos e comentários por uma palavra-chave."""
    resumos = obter_resumos_por_materia(materia)
    termo_norm = termo.lower().strip()
    resultados = []

    for r in resumos:
        texto_resumo = r.get("resumo_consolidado", "").lower()
        if termo_norm in texto_resumo or termo_norm in r.get("topico", "").lower():
            resultados.append(r)
            continue

        # Busca nos comentários individuais
        for c in r.get("comentarios", []):
            if termo_norm in c.get("comentario", "").lower() or termo_norm in c.get("texto_destaque", "").lower():
                resultados.append(r)
                break

    return resultados
