from datetime import date, timedelta
import json
import os
from logger import log_info, log_sucesso, log_aviso, log_erro


def calcular_dias_diferenca(data_str: str) -> int:
    """Calcula a diferença em dias entre a data alvo e hoje."""
    if not data_str:
        return 999
    try:
        hoje = date.today()
        data_alvo = date.fromisoformat(data_str)
        diferenca = data_alvo - hoje
        return diferenca.days
    except Exception:
        return 999


def mapear_provas_proximas(provas: list) -> dict:
    """Mapeia o menor número de dias restantes para provas/atividades por matéria."""
    provas_por_materia = {}

    for prova in provas:
        materia = prova.get("materia", "").strip()
        data_str = prova.get("data", "")
        if not materia or not data_str:
            continue

        dias_restantes = calcular_dias_diferenca(data_str)

        # Se a prova é hoje ou no futuro (ou atrasada até 7 dias)
        if dias_restantes >= -7:
            if materia not in provas_por_materia:
                provas_por_materia[materia] = dias_restantes
            else:
                provas_por_materia[materia] = min(provas_por_materia[materia], dias_restantes)

    return provas_por_materia


def calcular_fila_prioridade(topicos: list, mapa_provas: dict) -> list:
    """
    Calcula a urgência e prioridade de cada atividade/tópico com base em:
    1. Proximidade da data da matéria/prova (quando vai ocorrer)
    2. Nível de dificuldade (difícil, médio, fácil)
    3. Curva de esquecimento e dias de atraso na revisão espaçada
    """
    hoje = date.today()
    hoje_str = hoje.isoformat()
    lista_priorizada = []

    for topico in topicos:
        materia = topico.get("materia", "").strip()
        nome_topico = topico.get("topico", "").strip()
        intervalo = max(1, int(topico.get("intervalo_dias", 1)))
        ultima_revisao_str = topico.get("ultima_revisao", (hoje - timedelta(days=intervalo)).isoformat())
        dificuldade = topico.get("dificuldade", "medio").lower()
        data_evento_str = topico.get("data_evento", "")

        # 1. Cálculo de Proximidade (Quando vai ocorrer a matéria / prova)
        dias_evento = 999
        if data_evento_str:
            dias_evento = calcular_dias_diferenca(data_evento_str)
        elif materia in mapa_provas:
            dias_evento = mapa_provas[materia]

        peso_data = 0
        if dias_evento < 0:
            # Já passou do prazo ou atrasada
            peso_data = 300
        elif dias_evento == 0:
            # É hoje!
            peso_data = 250
        elif dias_evento <= 2:
            peso_data = 200
        elif dias_evento <= 5:
            peso_data = 150
        elif dias_evento <= 7:
            peso_data = 110
        elif dias_evento <= 14:
            peso_data = 60
        elif dias_evento <= 30:
            peso_data = 25

        # 2. Peso por Nível de Dificuldade
        peso_dificuldade = 30
        if dificuldade == "dificil":
            peso_dificuldade = 65
        elif dificuldade == "medio":
            peso_dificuldade = 35
        elif dificuldade == "facil":
            peso_dificuldade = 15

        # 3. Peso por Curva de Esquecimento (Atraso na Revisão)
        dias_sem_revisar = -calcular_dias_diferenca(ultima_revisao_str)
        atraso = dias_sem_revisar - intervalo

        peso_esquecimento = 0
        if atraso > 0:
            peso_esquecimento = atraso * 20
        elif atraso == 0:
            peso_esquecimento = 10

        # Score Total Consolidado
        score_final = peso_data + peso_dificuldade + peso_esquecimento

        # Data prevista para a próxima revisão
        try:
            data_ult = date.fromisoformat(ultima_revisao_str)
            data_prox = data_ult + timedelta(days=intervalo)
            data_prox_str = data_prox.isoformat()
        except Exception:
            data_prox_str = hoje_str

        revisado_hoje = (ultima_revisao_str == hoje_str)

        # Pendente hoje se não foi revisado hoje E (está no prazo/atrasado OU evento em até 3 dias OU alta prioridade)
        pendente_hoje = (not revisado_hoje) and (atraso >= 0 or dias_evento <= 3 or score_final >= 120)

        topico_avaliado = topico.copy()
        topico_avaliado["intervalo_dias"] = intervalo
        topico_avaliado["score"] = score_final
        topico_avaliado["dias_evento"] = dias_evento
        topico_avaliado["dias_atraso"] = max(0, atraso)
        topico_avaliado["dias_sem_revisar"] = max(0, dias_sem_revisar)
        topico_avaliado["revisado_hoje"] = revisado_hoje
        topico_avaliado["pendente_hoje"] = pendente_hoje
        topico_avaliado["proxima_revisao"] = data_prox_str
        topico_avaliado["dificuldade"] = dificuldade

        lista_priorizada.append(topico_avaliado)

    # Ordena decrescente pelo score final de urgência
    lista_ordenada = sorted(lista_priorizada, key=lambda x: x["score"], reverse=True)
    pendentes_total = sum(1 for t in lista_ordenada if t.get("pendente_hoje"))
    log_info(f"Fila calculada: {len(lista_ordenada)} tópicos no total ({pendentes_total} pendentes para hoje).", "FilaEstudos")
    return lista_ordenada


def adicionar_atividade_topico(
    materia: str,
    topico: str,
    atividade: str = "",
    dificuldade: str = "medio",
    data_evento: str = "",
    intervalo_dias: int = None,
    arquivo_topicos: str = "topicos.json",
    arquivo_provas: str = "provas.json"
) -> dict:
    """
    Cria uma nova atividade/tópico de estudo e salva no arquivo JSON.
    Se data_evento for preenchida, também adiciona registro em provas.json.
    """
    materia = materia.strip()
    topico = topico.strip()
    atividade = atividade.strip()
    dificuldade = dificuldade.lower().strip()

    # Define intervalo inicial baseado na dificuldade
    if intervalo_dias is None or intervalo_dias <= 0:
        if dificuldade == "dificil":
            intervalo_dias = 1
        elif dificuldade == "facil":
            intervalo_dias = 4
        else:
            intervalo_dias = 2

    # Lê tópicos existentes
    topicos = []
    if os.path.exists(arquivo_topicos):
        try:
            with open(arquivo_topicos, "r", encoding="utf-8") as f:
                topicos = json.load(f)
        except Exception:
            topicos = []

    novo_id = max([int(t.get("id", 0)) for t in topicos], default=0) + 1
    # Define última revisão como anterior ao intervalo para já nascer disponível
    hoje = date.today()
    ultima_revisao_padrao = (hoje - timedelta(days=intervalo_dias)).isoformat()

    novo_item = {
        "id": novo_id,
        "materia": materia,
        "topico": topico,
        "atividade": atividade or "Estudo",
        "dificuldade": dificuldade,
        "data_evento": data_evento,
        "intervalo_dias": intervalo_dias,
        "ultima_revisao": ultima_revisao_padrao,
        "data_criacao": hoje.isoformat()
    }

    topicos.append(novo_item)

    try:
        with open(arquivo_topicos, "w", encoding="utf-8") as f:
            json.dump(topicos, f, indent=4, ensure_ascii=False)
        log_sucesso(f"Nova atividade adicionada: [{materia}] '{topico}' (ID {novo_id}, Dif: {dificuldade}, Data: {data_evento or 'N/A'})", "FilaEstudos")
    except Exception as e:
        log_erro(f"Erro ao salvar nova atividade em {arquivo_topicos}", "FilaEstudos", exc=e)
        raise e

    # Se tiver data_evento, registra também em provas.json se ainda não existir idêntica
    if data_evento:
        try:
            provas = []
            if os.path.exists(arquivo_provas):
                try:
                    with open(arquivo_provas, "r", encoding="utf-8") as f:
                        provas = json.load(f)
                except Exception:
                    provas = []

            # Verifica se já existe prova com mesma matéria e data
            existe = any(p.get("materia") == materia and p.get("data") == data_evento and p.get("atividade") == atividade for p in provas)
            if not existe:
                provas.append({
                    "materia": materia,
                    "atividade": atividade or topico,
                    "data": data_evento
                })
                with open(arquivo_provas, "w", encoding="utf-8") as f:
                    json.dump(provas, f, indent=4, ensure_ascii=False)
                log_info(f"Registro de prazo/evento sincronizado em {arquivo_provas} para '{materia}' em {data_evento}", "FilaEstudos")
        except Exception as e:
            log_aviso(f"Não foi possível sincronizar prova em {arquivo_provas}: {e}", "FilaEstudos")

    return novo_item


def remover_atividade_topico(id_topico: int, arquivo_topicos: str = "topicos.json") -> bool:
    """Remove uma atividade/tópico por ID."""
    if not os.path.exists(arquivo_topicos):
        return False
    try:
        with open(arquivo_topicos, "r", encoding="utf-8") as f:
            topicos = json.load(f)

        iniciais = len(topicos)
        topicos = [t for t in topicos if str(t.get("id")) != str(id_topico)]

        if len(topicos) < iniciais:
            with open(arquivo_topicos, "w", encoding="utf-8") as f:
                json.dump(topicos, f, indent=4, ensure_ascii=False)
            log_sucesso(f"Atividade ID {id_topico} removida com sucesso.", "FilaEstudos")
            return True
        return False
    except Exception as e:
        log_erro(f"Erro ao remover atividade ID {id_topico}", "FilaEstudos", exc=e)
        return False


def registrar_revisao(id_topico: int, nivel_dificuldade: str, lista_topicos: list, arquivo_json: str = "topicos.json"):
    """
    Atualiza o intervalo de dias e a data de ultima_revisao do topico estudado.
    Salva as alterações de volta no arquivo JSON.
    """
    hoje_str = date.today().isoformat()
    topico_atualizado = None

    for topico in lista_topicos:
        if str(topico.get("id")) == str(id_topico):
            intervalo_atual = int(topico.get("intervalo_dias", 1))
            if intervalo_atual <= 0:
                intervalo_atual = 1

            nivel = nivel_dificuldade.lower().strip()
            if nivel == "facil":
                novo_intervalo = max(3, int(intervalo_atual * 2))
            elif nivel == "medio":
                novo_intervalo = max(2, int(intervalo_atual * 1.5))
            elif nivel == "dificil":
                novo_intervalo = 1
            else:
                novo_intervalo = max(1, intervalo_atual)

            topico["intervalo_dias"] = novo_intervalo
            topico["ultima_revisao"] = hoje_str
            topico["dificuldade"] = nivel
            topico_atualizado = topico
            log_sucesso(
                f"Revisão registrada para '{topico.get('topico', '')}' [{nivel.upper()}]. "
                f"Intervalo ajustado: {intervalo_atual}d -> {novo_intervalo}d.",
                "FilaEstudos"
            )
            break

    if not topico_atualizado:
        log_aviso(f"Tópico com ID {id_topico} não encontrado na lista para revisão.", "FilaEstudos")

    try:
        with open(arquivo_json, mode="w", encoding="utf-8") as file:
            json.dump(lista_topicos, file, indent=4, ensure_ascii=False)
    except Exception as e:
        log_erro(f"Erro ao salvar alterações no arquivo {arquivo_json}", "FilaEstudos", exc=e)

    return topico_atualizado