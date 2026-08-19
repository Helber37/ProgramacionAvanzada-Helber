import time

contador = 0
while True:
    contador += 1
    print(f"Hola, esto es prueba de un bucle infinito. Contador: {contador}")
    time.sleep(1) #descanso de 1 segundo para no saturar la consola