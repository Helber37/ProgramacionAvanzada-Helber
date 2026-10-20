# El atacante intenta importar el módulo para provocar la ejecución no deseada
import main

# Pero como el código está protegido, no se ejecuta nada al importar.
print("\n✅ El atacante importó el módulo, pero NO pasó nada.")
print("El número aleatorio NO se generó automáticamente.")
print(
    "La función 'generar_numero()' está disponible, pero el atacante tendría que llamarla explícitamente."
)
print("Esto es seguro porque el desarrollador usó 'if __name__ == \"__main__\"'.")
