# Mala práctica: un script sin punto de entrada protegido

## ¿Qué hay aquí?

| Archivo | Rol |
|---------|-----|
| `main.py` | Script del desarrollador "descuidado". Genera un número aleatorio en el ámbito global. |
| `exploit.py` | Script del atacante. Simplemente importa `main` y observa cómo se ejecuta solo. |

> [!CAUTION]
> El "atacante" de este ejemplo no explota ningún bug, no rompe ninguna sandbox, no necesita privilegios. Solo usa Python como Python funciona. **Esa es la gravedad del problema: no es un exploit, es el comportamiento por defecto.**

---

## El código vulnerable

```python
# main.py
import random


def generar_numero():
    return random.randint(0, 100)


# ⚠️ Esto está en el ámbito global: se ejecuta al importar
numero = generar_numero()
print(f"[main.py] Número generado: {numero}")
print("[main.py] Listo para usar.")
```

El desarrollador pensó: *"esto solo correrá cuando yo lo ejecute"*. Es falso.

---

## Cómo reproducir el escenario

1. Guarda `main.py` y `exploit.py` en la misma carpeta.
2. Ejecuta:
   ```bash
   python exploit.py
   ```
3. Observa la salida:
   - Primero aparece la línea de `main.py` (porque se ejecutó al importar).
   - Después aparece el mensaje del "atacante".

> [!TIP]
> Nota algo importante: el atacante **no llamó a `generar_numero()`**. Nunca invocó nada de `main`. El simple `import main` fue suficiente.

---

## ¿Y esto qué tiene de grave? Un número aleatorio no hace daño…

Correcto: en este ejemplo didáctico el impacto es cero. Pero el mecanismo es el mismo sin importar qué haya en el ámbito global. Cambia `generar_numero()` por cualquiera de estos casos reales y la foto cambia:

> [!WARNING]
> **Escenarios equivalentes que sí causan daño real:**
>
> - El código global **abre una conexión a la base de datos de producción** usando credenciales leídas del entorno. El importador queda con esa conexión abierta.
> - El código global **envía un correo** "Aplicación iniciada correctamente" al equipo de soporte. El atacante dispara notificaciones falsas cada vez que importa.
> - El código global **sobrescribe un archivo de configuración** con valores por defecto. Al importarlo, se pierden los ajustes manuales del usuario.
> - El código global **hace `requests.post(...)` a un webhook** de pago. Cada import cuesta dinero.
> - El código global **inicia un scheduler con `APScheduler` o `threading.Timer`**. Nunca se detiene, consume recursos del proceso que importó el módulo.
> - El código global **ejecuta una migración de base de datos** porque "así nos aseguramos de que esté actualizada". El atacante o un test dispara la migración en el momento equivocado.
> - El código global **lee `~/.ssh/id_rsa` y lo carga en una variable**. Cualquiera que importe el módulo tiene la clave en memoria de su proceso.
> - El código global **registra un handler de `SIGTERM`** que escribe en un log específico. Todo el programa importador ahora ignora o altera su comportamiento ante señales.
> - El código global **hace `os.chdir()` a otro directorio**. Todos los paths relativos del importador se rompen.
> - El código global **arranca un servidor Flask/FastAPI con `app.run()`**. El importador se queda bloqueado esperando peticiones.

---

## El vector de ataque en la vida real

> [!CAUTION]
> Este patrón es especialmente peligroso cuando:
>
> - Publicas un paquete en **PyPI** y un typosquatter registra un nombre parecido (`requsts` en vez de `requests`). Al importarlo, ejecuta su payload.
> - Tu proyecto tiene **dependencias transitivas**: una librería que importa otra que importa la tuya. Cualquier punto de esa cadena puede disparar tu código global.
> - Usas **hot-reload** en desarrollo (Flask, Django, Uvicorn, Jupyter). Cada recarga vuelve a ejecutar el código global.
> - Alguien hace `from tu_modulo import *` en una consola interactiva para "ver qué hay dentro".

---

## Conclusión

El código del desarrollador se ejecutó **sin que nadie lo pidiera explícitamente**. No hubo ataque en el sentido técnico: hubo un descuido estructural.

> [!IMPORTANT]
> La lección no es *"ten cuidado con quién importa tu módulo"*. La lección es: **nunca dejes código ejecutable en el ámbito global**. No hay forma de saber quién, cuándo o por qué alguien hará `import` de tu archivo.

Ahora pasa a la carpeta [`../Buena/`](../Buena/README.md) y observa cómo el mismo intento se vuelve inofensivo con un cambio de tres líneas.
