import re

def ler_versao():
    with open("VERSION", "r") as f:
        return f.read().strip()

def atualizar_versao(nova_versao):
    with open("VERSION", "w") as f:
        f.write(nova_versao + "\n")

def incrementar_versao(tipo="patch"):
    versao_atual = ler_versao()
    major, minor, patch = map(int, versao_atual.split("."))

    if tipo == "major":
        major += 1
        minor = 0
        patch = 0
    elif tipo == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    nova_versao = f"{major}.{minor}.{patch}"
    atualizar_versao(nova_versao)
    print(f"Versão atualizada para: {nova_versao}")
    return nova_versao

if __name__ == "__main__":
    tipo = input("Digite o tipo de incremento (major, minor, patch): ").strip().lower()
    incrementar_versao(tipo)