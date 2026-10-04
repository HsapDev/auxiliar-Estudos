from datetime import date
import json
from logger import log_info, log_sucesso, log_aviso, log_erro

def calcular_dias_diferenca(data_str: str) -> int:

    hoje = date.today()
    data_alvo = date.fromisoformat(data_str)

    diferenca = data_alvo - hoje
    return diferenca.days

def mapear_provas_proximas(provas:list)->dict:

    provas_por_materia={}

    for prova in provas:
        materia = prova["materia"]
        data_str= prova["data"]

        dias_restantes = calcular_dias_diferenca(data_str)

        if dias_restantes>=0:
            #senao tiver no dicionario , adiciona
            if materia not in provas_por_materia:
                provas_por_materia[materia]= dias_restantes
                #se ja existe, manetemos o menor valor
            else:
                provas_por_materia[materia]= min(provas_por_materia[materia],dias_restantes)
    return provas_por_materia


def calcular_fila_prioridade(topicos: list, mapa_provas: dict) -> list:
    from datetime import timedelta
    hoje = date.today()
    hoje_str = hoje.isoformat()
    lista_priorizada = []

    for topico in topicos:
        materia = topico.get("materia", "")
        intervalo = max(1, int(topico.get("intervalo_dias", 1)))
        ultima_revisao_str = topico.get("ultima_revisao", hoje_str)

        # 1. Peso Prova
        peso_prova = 0
        if materia in mapa_provas:
            dias_prova = mapa_provas[materia]
            if dias_prova <= 14:
                peso_prova = (15 - dias_prova) * 10

        # 2. Peso Curva de Esquecimento (Atraso)
        dias_sem_revisar = -calcular_dias_diferenca(ultima_revisao_str)
        atraso = dias_sem_revisar - intervalo

        peso_esquecimento = 0
        if atraso > 0:
            peso_esquecimento = atraso * 15

        # Score final
        score_final = peso_prova + peso_esquecimento

        # Data prevista para a próxima revisão
        try:
            data_ult = date.fromisoformat(ultima_revisao_str)
            data_prox = data_ult + timedelta(days=intervalo)
            data_prox_str = data_prox.isoformat()
        except Exception:
            data_prox_str = hoje_str

        revisado_hoje = (ultima_revisao_str == hoje_str)
        # Pendente se: não foi revisado hoje E (está vencido/atrasado ou a prova está a menos de 4 dias)
        dias_prova_materia = mapa_provas.get(materia, 999)
        pendente_hoje = (not revisado_hoje) and (atraso >= 0 or dias_prova_materia <= 3)

        topico_avaliado = topico.copy()
        topico_avaliado["intervalo_dias"] = intervalo
        topico_avaliado["score"] = score_final
        topico_avaliado["dias_atraso"] = max(0, atraso)
        topico_avaliado["dias_sem_revisar"] = max(0, dias_sem_revisar)
        topico_avaliado["revisado_hoje"] = revisado_hoje
        topico_avaliado["pendente_hoje"] = pendente_hoje
        topico_avaliado["proxima_revisao"] = data_prox_str

        lista_priorizada.append(topico_avaliado)

    lista_ordenada = sorted(lista_priorizada, key=lambda x: x["score"], reverse=True)
    pendentes_total = sum(1 for t in lista_ordenada if t.get("pendente_hoje"))
    log_info(f"Fila calculada: {len(lista_ordenada)} tópicos no total ({pendentes_total} pendentes para hoje).", "FilaEstudos")
    return lista_ordenada


def registrar_revisao(id_topico: int, nivel_dificuldade: str, lista_topicos: list, arquivo_json: str = "topicos.json"):
    """
    Atualiza o intervalo de dias e a data de ultima_revisao do topico estudado.
    Salva as alteracoes de volta no arquivo JSON.
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
            topico_atualizado = topico
            log_sucesso(
                f"Revisão registrada para '{topico['topico']}' [{nivel.upper()}]. "
                f"Intervalo ajustado: {intervalo_atual}d -> {novo_intervalo}d.",
                "FilaEstudos"
            )
            break

    if not topico_atualizado:
        log_aviso(f"Tópico com ID {id_topico} não encontrado na lista para revisão.", "FilaEstudos")

    try:
        # Salva o arquivo JSON atualizado
        with open(arquivo_json, mode="w", encoding="utf-8") as file:
            json.dump(lista_topicos, file, indent=4, ensure_ascii=False)
    except Exception as e:
        log_erro(f"Erro ao salvar alterações no arquivo {arquivo_json}", "FilaEstudos", exc=e)

    return topico_atualizado


if __name__ == "__main__":
    with open("provas.json", mode="r", encoding="utf-8") as file:
        provas = json.load(file)

    with open("topicos.json", mode="r", encoding="utf-8") as file:
        topicos = json.load(file)

    mapa_urgencia = mapear_provas_proximas(provas)
    fila_estudos = calcular_fila_prioridade(topicos, mapa_urgencia)

    print("--- PLANO DE ESTUDOS DO DIA (ORDEM DE PRIORIDADE) ---")
    for item in fila_estudos:
        print(f"[{item['score']}pts] {item['materia']} ->{item['topico']} (Atraso: {item['dias_atraso']} dias)")