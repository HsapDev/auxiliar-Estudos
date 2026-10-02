import json 
from pathlib import Path 


from organizador_pastas import (executar_organizacao)

from organizador_estudos import(
    mapear_provas_proximas,calcular_fila_prioridade,registrar_revisao)


def carregar_json(caminho_arquivo:str):
    path = Path(caminho_arquivo)
    if not path.exists():
        print(f"AVISO: O arquivo {caminho_arquivo}nao foi encontrado")
        return []

    with open(path, mode="r",encoding="utf-8") as file:
        return json.load(file)

def exibir_menu():
    """Exibe no terminal as opções disponíveis para o usuário."""
    print("\n" + "=" * 40)
    print("      SISTEMA GERENCIADOR DE ESTUDOS")
    print("=" * 40)
    print("1 - Organizar Arquivos da Pasta de Entrada")
    print("2 - Ver o Plano de Estudos de Hoje")
    print("3 - Registrar Estudo Realizado (Repetição Espaçada)")
    print("4 - Sair")
    print("=" * 40)

def main():
    while True:
        exibir_menu()
        opcao =input("Digite a opcao desejada (1-4):").strip()
        if opcao == "1":
            print("\n[Ação] Executando organizador de arquivos...")
            executar_organizacao("materias.json")

        elif opcao == "2":
            print("\n[Ação] Carregando plano de estudos...")
            provas = carregar_json("provas.json")
            topicos = carregar_json("topicos.json")
            
            mapa_urgencia = mapear_provas_proximas(provas)
            fila = calcular_fila_prioridade(topicos, mapa_urgencia)

            print("\n--- TÓPICOS PRIORITÁRIOS PARA HOJE ---")
            for item in fila:
                print(f"ID {item['id']} | [{item['score']} pts] {item['materia']} -> {item['topico']} (Atraso: {item['dias_atraso']} dias)")

        elif opcao == "3":
            print("\n[Ação] Registrar Estudo")
            topicos = carregar_json("topicos.json")
            
            try:
                id_topico = int(input("Digite o ID do tópico que você estudou: "))
                dificuldade = input("Qual foi o nível de facilidade? (facil / medio / dificil): ").strip()
                
                registrar_revisao(id_topico, dificuldade, topicos)
            except ValueError:
                print("Erro: O ID precisa ser um número inteiro válido.")

        elif opcao == "4":
            print("\nSaindo do sistema... Até a próxima!")
            break

        else:
            print("\nOpção inválida! Por favor, escolha um número entre 1 e 4.")


if __name__ == "__main__":
    main()
    
