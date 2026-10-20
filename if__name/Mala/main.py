import random


def generar_numero():
    return random.randint(0, 100)


# Código suelto en el ámbito global: se ejecutará al importar
numero = generar_numero()
print(f"[main.py] Número generado: {numero}")
print("[main.py] Listo para usar.")
