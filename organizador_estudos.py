from datetime import date
import json
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


def calcular_fila_prioridade(topicos:list,mapa_provas:dict)->list:
    lista_priorizada=[]

    for topico in topicos:
        materia=topico["materia"]

        #1 peso prova
        peso_prova=0
        if materia in mapa_provas:
            dias_prova= mapa_provas[materia]

            if dias_prova<=14:
                peso_prova = (15-dias_prova)*10

        # 2. PESO CURVA DE ESQUECIMENTO (ATRASO)
        # Como a última revisão foi no passado, calcular_dias_diferenca dá negativo.
        # Invertemos o sinal para ter o número positivo de dias decorridos:
        dias_sem_revisar = -calcular_dias_diferenca(topico["ultima_revisao"])

        atraso=dias_sem_revisar -topico["intervalo_dias"]

        peso_esquecimento=0

        if atraso>0:
            peso_esquecimento=atraso *15

        # SCore final
        score_final = peso_prova+peso_esquecimento

        topico_avaliado=topico.copy()
        topico_avaliado["score"]=score_final
        topico_avaliado["dias_atraso"] = max(0,atraso)

        lista_priorizada.append(topico_avaliado)

    lista_ordenada = sorted(lista_priorizada,key=lambda x: x["score"],reverse=True)
    return lista_priorizada

with open("provas.json",mode="r",encoding="utf-8") as file:
    provas= json.load(file)

with open("topicos.json",mode="r",encoding="utf-8") as file:
    topicos= json.load(file)



mapa_urgencia = mapear_provas_proximas(provas)
fila_estudos = calcular_fila_prioridade(topicos,mapa_urgencia)

print("--- PLANO DE ESTUDOS DO DIA (ORDEM DE PRIORIDADE) ---")
for item in fila_estudos:
    print(f"[{item['score']}pts] {item['materia']} ->{item['topico']} (Atraso: {item['dias_atraso']} dias)")

def registrar_revisao(id_topico: int, nivel_dificuldade: str, lista_topicos: list, arquivo_json: str = "topicos.json"):
    """
    Atualiza o intervalo de dias e a data de ultima_revisao do topico estudado.
    Salva as alteracoes de volta no arquivo JSON.
    """
    hoje_str = date.today().isoformat()

    for topico in lista_topicos:
        if topico["id"] == id_topico:
            intervalo_atual = topico["intervalo_dias"]

            # Reajuste do intervalo com base no feedback
            if nivel_dificuldade.lower() == "facil":
                topico["intervalo_dias"] = int(intervalo_atual * 2)
            elif nivel_dificuldade.lower() == "medio":
                topico["intervalo_dias"] = max(1, int(intervalo_atual * 1.5))
            elif nivel_dificuldade.lower() == "dificil":
                topico["intervalo_dias"] = 1

            # Atualiza a data da ultima revisao para hoje
            topico["ultima_revisao"] = hoje_str
            print(f"\nTópico '{topico['topico']}' atualizado com sucesso!")
            print(f" -> Novo intervalo: {topico['intervalo_dias']} dias.")
            break

    # Salva o arquivo JSON atualizado
    with open(arquivo_json, mode="w", encoding="utf-8") as file:
        json.dump(lista_topicos, file, indent=4, ensure_ascii=False)

registrar_revisao(id_topico=1, nivel_dificuldade="facil", lista_topicos=topicos)