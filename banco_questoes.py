import json
import os
import re
from pathlib import Path
from datetime import datetime
from logger import log_info, log_sucesso, log_aviso, log_erro

CAMINHO_BANCO_QUESTOES = Path("banco_questoes.json")


def carregar_banco_questoes() -> list[dict]:
    """Carrega todas as questões salvas no banco_questoes.json.
    Se o arquivo não existir, importa as questões do conhecimento_materia.json como semente inicial.
    """
    if CAMINHO_BANCO_QUESTOES.exists():
        try:
            with open(CAMINHO_BANCO_QUESTOES, "r", encoding="utf-8") as f:
                questoes = json.load(f)
                if isinstance(questoes, list):
                    return questoes
        except Exception as e:
            log_erro("Falha ao carregar banco_questoes.json", "BancoQuestoes", exc=e)

    # Se não existe banco_questoes.json, inicializa importando de conhecimento_materia.json
    questoes_iniciais = _importar_questoes_iniciais_de_conhecimento()
    salvar_banco_questoes(questoes_iniciais)
    return questoes_iniciais


def salvar_banco_questoes(questoes: list[dict]) -> bool:
    """Salva a lista completa de questões no arquivo banco_questoes.json."""
    try:
        with open(CAMINHO_BANCO_QUESTOES, "w", encoding="utf-8") as f:
            json.dump(questoes, f, indent=4, ensure_ascii=False)
        log_sucesso(f"Banco de questões salvo com {len(questoes)} questão(ões).", "BancoQuestoes")
        return True
    except Exception as e:
        log_erro("Falha ao salvar banco_questoes.json", "BancoQuestoes", exc=e)
        return False


def _importar_questoes_iniciais_de_conhecimento() -> list[dict]:
    """Importa questões existentes em conhecimento_materia.json e arquivos semelhantes."""
    questoes = []
    candidatos = [
        Path("conhecimento_materia.json"),
        Path("conhecimento_Matemática Discreta II.json")
    ]

    for p in candidatos:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    materia = dados.get("materia", "Matemática Discreta").strip()
                    exercicios = dados.get("exercicios_resolvidos", [])
                    for i, ex in enumerate(exercicios, 1):
                        enunciado = ex.get("enunciado", "").strip()
                        passos = ex.get("passos", [])

                        # Tenta extrair tópico do enunciado
                        topico = "Relações e Ordem Parcial"
                        if "hasse" in enunciado.lower():
                            topico = "Diagramas de Hasse"
                        elif "equivalência" in enunciado.lower() or "equivalencia" in enunciado.lower():
                            topico = "Relações de Equivalência"
                        elif "ordem parcial" in enunciado.lower() or "ordem total" in enunciado.lower():
                            topico = "Ordens Parciais e Totais"

                        questoes.append({
                            "id": f"MD_{i}",
                            "materia": materia,
                            "topico": topico,
                            "tipo": "dissertativa",
                            "enunciado": enunciado,
                            "opcoes": [],
                            "resposta_correta": "",
                            "passos": passos if isinstance(passos, list) else [str(passos)],
                            "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
            except Exception as e:
                log_aviso(f"Não foi possível carregar {p} para inicialização: {e}", "BancoQuestoes")

    return questoes


def obter_todas_materias() -> list[str]:
    """Retorna a lista ordenada de matérias únicas presentes no banco de questões."""
    questoes = carregar_banco_questoes()
    materias = set(q.get("materia", "Geral").strip() for q in questoes if q.get("materia"))
    return sorted(list(materias))


def obter_topicos_por_materia(materia: str = None) -> list[str]:
    """Retorna os tópicos associados a uma matéria específica (ou todos se matéria for None)."""
    questoes = carregar_banco_questoes()
    topicos = set()
    for q in questoes:
        m = q.get("materia", "Geral").strip()
        t = q.get("topico", "Geral").strip()
        if not materia or m.lower() == materia.lower():
            if t:
                topicos.add(t)
    return sorted(list(topicos))


def filtrar_questoes(materia: str = None, topico: str = None) -> list[dict]:
    """Filtra questões por matéria e tópico. Se 'Todas', ignora o filtro."""
    questoes = carregar_banco_questoes()
    resultado = []
    for q in questoes:
        m = q.get("materia", "Geral").strip()
        t = q.get("topico", "Geral").strip()

        match_materia = True
        if materia and "todas" not in materia.lower():
            match_materia = (m.lower() == materia.lower())

        match_topico = True
        if topico and "todos" not in topico.lower():
            match_topico = (t.lower() == topico.lower())

        if match_materia and match_topico:
            resultado.append(q)

    return resultado


def adicionar_questao_individual(questao: dict) -> bool:
    """Adiciona uma nova questão ao banco e salva."""
    questoes = carregar_banco_questoes()
    if not questao.get("id"):
        questao["id"] = f"Q_{int(datetime.now().timestamp() * 1000)}"
    if not questao.get("data_cadastro"):
        questao["data_cadastro"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    questoes.append(questao)
    return salvar_banco_questoes(questoes)


def excluir_questao(id_questao: str) -> bool:
    """Remove uma questão pelo ID."""
    questoes = carregar_banco_questoes()
    novas = [q for q in questoes if str(q.get("id")) != str(id_questao)]
    if len(novas) < len(questoes):
        return salvar_banco_questoes(novas)
    return False


def parser_importacao_em_massa(
    texto: str,
    materia_padrao: str = "Matemática Discreta",
    topico_padrao: str = "Geral"
) -> list[dict]:
    """
    Parser ultrarrobusto para importação de 10, 50, 100 questões coladas de uma só vez.
    Aceita:
    1. Formato JSON (array de questões ou objeto com array)
    2. Formato Chave-Valor estruturado (MATERIA:, TOPICO:, ENUNCIADO:, A), B)..., GABARITO:)
    3. Formato Numérico de Prova / Apostila (1. Enunciado... a) ... b) ... Gabarito: b)
    """
    texto = texto.strip()
    if not texto:
        return []

    # 1. Tenta interpretar como JSON
    if (texto.startswith("[") and texto.endswith("]")) or (texto.startswith("{") and texto.endswith("}")):
        try:
            dados = json.loads(texto)
            if isinstance(dados, dict):
                # Se for dict com lista de exercicios ou questoes
                for chave in ["questoes", "exercicios", "exercicios_resolvidos", "items"]:
                    if chave in dados and isinstance(dados[chave], list):
                        dados = dados[chave]
                        break
            if isinstance(dados, list):
                questoes_processadas = []
                for idx, item in enumerate(dados, 1):
                    if isinstance(item, dict):
                        q = {
                            "id": str(item.get("id", f"IMP_{int(datetime.now().timestamp())}_{idx}")),
                            "materia": item.get("materia", materia_padrao).strip(),
                            "topico": item.get("topico", topico_padrao).strip(),
                            "tipo": item.get("tipo", "multipla_escolha" if item.get("opcoes") else "dissertativa"),
                            "enunciado": item.get("enunciado", "").strip(),
                            "opcoes": item.get("opcoes", []),
                            "resposta_correta": str(item.get("resposta_correta", item.get("gabarito", ""))).strip().upper(),
                            "passos": item.get("passos", item.get("explicacao", item.get("resolucao", []))),
                            "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        if isinstance(q["passos"], str):
                            q["passos"] = [q["passos"]]
                        if q["enunciado"]:
                            questoes_processadas.append(q)
                if questoes_processadas:
                    return questoes_processadas
        except Exception:
            pass  # Segue para parser de texto

    # 2. Divide em blocos por delimitador explícito "---" ou "====" ou por numeração de questão
    if "---" in texto:
        blocos = [b.strip() for b in re.split(r"\n\s*---\s*\n", texto) if b.strip()]
    elif re.search(r"\n\s*Questão\s+\d+", texto, re.IGNORECASE):
        blocos = [b.strip() for b in re.split(r"(?=\n\s*Questão\s+\d+)", texto, flags=re.IGNORECASE) if b.strip()]
    elif re.search(r"\n\s*\d+[\.\)]\s+", texto):
        blocos = [b.strip() for b in re.split(r"(?=\n\s*\d+[\.\)]\s+)", texto) if b.strip()]
    else:
        # Se for um único bloco
        blocos = [texto]

    questoes_extraidas = []

    for idx, bloco in enumerate(blocos, 1):
        if not bloco.strip():
            continue

        q = _parse_bloco_individual(bloco, materia_padrao, topico_padrao, idx)
        if q and q.get("enunciado"):
            questoes_extraidas.append(q)

    return questoes_extraidas


def _parse_bloco_individual(bloco: str, materia_padrao: str, topico_padrao: str, index: int) -> dict:
    """Extrai uma única questão a partir de um bloco de texto."""
    linhas = [l.strip() for l in bloco.splitlines() if l.strip()]
    if not linhas:
        return None

    materia = materia_padrao
    topico = topico_padrao
    tipo = "dissertativa"
    enunciado_linhas = []
    opcoes = []
    gabarito = ""
    passos_linhas = []

    estado = "enunciado"

    for linha in linhas:
        # Verifica tags chave-valor
        m_mat = re.match(r"^(?:MATERIA|DISCIPLINA)\s*:\s*(.+)$", linha, re.IGNORECASE)
        if m_mat:
            materia = m_mat.group(1).strip()
            continue

        m_top = re.match(r"^(?:TOPICO|TEMA|ASSUNTO)\s*:\s*(.+)$", linha, re.IGNORECASE)
        if m_top:
            topico = m_top.group(1).strip()
            continue

        m_tipo = re.match(r"^(?:TIPO)\s*:\s*(.+)$", linha, re.IGNORECASE)
        if m_tipo:
            t_val = m_tipo.group(1).strip().lower()
            tipo = "multipla_escolha" if "multipla" in t_val or "escolha" in t_val else "dissertativa"
            continue

        m_gab = re.match(r"^(?:GABARITO|RESPOSTA|CORRETA|RESPOSTA_CORRETA)\s*:\s*(.+)$", linha, re.IGNORECASE)
        if m_gab:
            gabarito = m_gab.group(1).strip()
            # Se for apenas letra como "A)" ou "B", limpa
            match_letra = re.match(r"^([A-E])\b", gabarito, re.IGNORECASE)
            if match_letra:
                gabarito = match_letra.group(1).upper()
            estado = "gabarito"
            continue

        m_res = re.match(r"^(?:RESOLUCAO|RESOLUÇÃO|PASSOS|EXPLICAÇÃO|EXPLICACAO)\s*:\s*(.*)$", linha, re.IGNORECASE)
        if m_res:
            resto = m_res.group(1).strip()
            if resto:
                passos_linhas.append(resto)
            estado = "resolucao"
            continue

        # Verifica alternativa de múltipla escolha (ex: A) texto, [A] texto, A. texto, (A) texto)
        m_opcao = re.match(r"^([A-Ea-e])[\)\.\-\]]\s*(.+)$", linha)
        if m_opcao:
            letra = m_opcao.group(1).upper()
            conteudo = m_opcao.group(2).strip()
            opcoes.append(f"{letra}) {conteudo}")
            tipo = "multipla_escolha"
            estado = "opcoes"
            continue

        # Distribuição de conteúdo conforme o estado atual
        if estado == "resolucao":
            passos_linhas.append(linha)
        elif estado == "opcoes":
            # Se a linha seguinte à opção não tem letra, junta com a última opção
            if opcoes:
                opcoes[-1] = opcoes[-1] + " " + linha
            else:
                enunciado_linhas.append(linha)
        else:
            # É parte do enunciado
            # Remove marcação "Enunciado:" ou "1." se estiver no começo
            linha_limpa = re.sub(r"^(?:ENUNCIADO\s*:\s*|Questão\s+\d+[\.\:\-]?\s*|\d+[\.\)]\s*)", "", linha, flags=re.IGNORECASE)
            enunciado_linhas.append(linha_limpa.strip() if linha_limpa.strip() else linha)

    enunciado_final = "\n".join(enunciado_linhas).strip()
    if not enunciado_final:
        return None

    # Se detectou opções mas não tinha tipo setado
    if opcoes and tipo != "multipla_escolha":
        tipo = "multipla_escolha"

    # Se é múltipla escolha e o gabarito é algo como "b) alguma coisa", pega só a letra
    if tipo == "multipla_escolha" and gabarito:
        m_letra = re.search(r"\b([A-E])\b", gabarito, re.IGNORECASE)
        if m_letra:
            gabarito = m_letra.group(1).upper()

    return {
        "id": f"IMP_{int(datetime.now().timestamp())}_{index}",
        "materia": materia,
        "topico": topico,
        "tipo": tipo,
        "enunciado": enunciado_final,
        "opcoes": opcoes,
        "resposta_correta": gabarito,
        "passos": passos_linhas if passos_linhas else [f"Gabarito: {gabarito}" if gabarito else "Sem resolução cadastrada."],
        "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
