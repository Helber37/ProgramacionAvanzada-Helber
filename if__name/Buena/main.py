import random


def generar_numero():
    return random.randint(0, 100)


# El código que debe ejecutarse solo cuando el script se corre directamente
# queda protegido dentro de este bloque.
if __name__ == "__main__":
    numero = generar_numero()
    print(f"[main.py] Número generado: {numero}")
    print("[main.py] Listo para usar.")
