# `if __name__ == "__main__"`: la primera línea de defensa en Python

## ¿Por qué esto no es un detalle menor?

En Python, **importar un módulo ejecuta su código**. No es una lectura pasiva del archivo: cada línea que esté en el ámbito global —fuera de funciones o clases— corre en el instante en que alguien escribe `import tu_modulo`.

Eso significa que, si tu script no protege su punto de entrada, **cualquier persona que importe tu archivo dispara toda la lógica que escribiste pensando en ejecutarlo directamente**. No hace falta malicia: basta con que otro desarrollador, un test automatizado o un linter haga la importación para que tu código se ejecute en un contexto que no previste.

Cuando además hay intención maliciosa, el problema escala: un atacante con acceso a tu `PYTHONPATH` (por ejemplo, dentro del mismo proyecto, un paquete publicado en PyPI con nombre similar, o una dependencia comprometida) puede detonar acciones sin que tú lo sepas.

> [!IMPORTANT]
> `if __name__ == "__main__"` no es una moda estilística ni un adorno de PEP 8. Es un **mecanismo de aislamiento** que separa el rol de "script ejecutable" del rol de "módulo reutilizable". Ignorarlo es mezclar dos responsabilidades que Python trata distinto.

---

## El mecanismo en una frase

Cuando Python carga un archivo:

- Si lo ejecutas con `python main.py` → la variable especial `__name__` vale `"__main__"`.
- Si otro archivo hace `import main` → la variable `__name__` vale `"main"` (el nombre del módulo).

El bloque `if __name__ == "__main__":` usa esa diferencia para decidir qué código corre en cada caso.

---

## Estructura de este ejemplo

| Carpeta | Qué contiene | Qué demuestra |
|---------|--------------|---------------|
| [`Mala/`](Mala/README.md) | `main.py` sin protección + `exploit.py` | Cómo un atacante dispara tu código con solo importarlo |
| [`Buena/`](Buena/README.md) | `main.py` protegido + `intento_ataque.py` | Cómo el mismo intento falla cuando el código está aislado |

> [!TIP]
> Ejecuta primero el ejemplo de `Mala/` y luego el de `Buena/`. La diferencia se siente mucho más cuando ves el "ataque" funcionar y luego rebotar contra la misma estructura corregida.

---

## Escenarios reales donde esto duele

No es un ejemplo de juguete. Estas son situaciones que ocurren en proyectos reales cuando se omite la protección:

> [!WARNING]
> Cualquiera de los siguientes casos puede ejecutarse **sin tu consentimiento** con un simple `import`:
>
> - **Conexiones a bases de datos al importar** → se abren sockets, se consumen conexiones del pool, se dispararán intentos de autenticación.
> - **Lanzamiento de hilos o procesos** → el módulo importado arranca workers que nunca se cierran.
> - **Llamadas HTTP al iniciar** → se envían peticiones a APIs externas (a veces de pago por request).
> - **Escritura o borrado de archivos** → logs, migraciones o scripts de limpieza que corren fuera de contexto.
> - **Lectura de variables de entorno sensibles** → tokens, claves API, credenciales quedan cargadas en memoria del proceso importador.
> - **Modificación de estado global** → `sys.path`, `os.environ`, `logging` reconfigurados sin que el importador lo sepa.
> - **Ejecución de migraciones o seeds de base de datos** → en el peor caso, `DROP TABLE` al importar.
> - **Envío de correos, SMS o notificaciones** → porque "era un script que notifica cuando arranca".
> - **Registro de hooks o señales del sistema** → `signal.signal(...)` global que afecta a todo el intérprete.
> - **Bloqueo del proceso con `input()` o bucles infinitos** → el `import` nunca retorna.

> [!CAUTION]
> El riesgo no se limita a tu código. Si tu módulo es importado por un framework de testing (`pytest`, `unittest`), por un linter que hace análisis estático ejecutando (`importlib`), o por un servidor de desarrollo con hot-reload, **todos esos efectos colaterales se multiplican por cada reimportación**.

---

## El patrón correcto

```python
import random


def generar_numero():
    return random.randint(0, 100)


if __name__ == "__main__":
    numero = generar_numero()
    print(f"Número generado: {numero}")
```

> [!NOTE]
> La regla práctica: **define en el ámbito global, ejecuta dentro del `if`**. Clases, funciones y constantes pueden vivir fuera. Todo lo que "haga cosas" —I/O, red, cálculo pesado, efectos secundarios— va adentro.

---

## Lo que vas a llevarte de este ejercicio

- Entender que un `import` en Python **no es inocuo**.
- Ver con tus ojos cómo un archivo sin protección expone su lógica.
- Adoptar un hábito que cuesta cinco segundos escribir y te ahorra incidentes reales.

> [!IMPORTANT]
> Si vas a desarrollar en Python con seriedad —sea para automatización, backend, ciencia de datos o herramientas internas— este patrón debe ser **reflejo, no decisión**. Escribirlo sin pensarlo es la diferencia entre un script profesional y uno que un día te explota en producción.
