# Buena práctica: punto de entrada protegido

## ¿Qué hay aquí?

| Archivo | Rol |
|---------|-----|
| `main.py` | El mismo script que en `Mala/`, pero con la lógica de ejecución protegida por `if __name__ == "__main__":`. |
| `intento_ataque.py` | El mismo intento de importación. Ahora no consigue nada. |

> [!NOTE]
> La diferencia entre la versión vulnerable y la versión segura son **tres líneas**. No hay librerías nuevas, no hay frameworks, no hay sandbox. Solo una estructura correcta.

---

## El código corregido

```python
# main.py
import random


def generar_numero():
    return random.randint(0, 100)


# ✅ Este bloque solo corre cuando el script se ejecuta directamente.
if __name__ == "__main__":
    numero = generar_numero()
    print(f"[main.py] Número generado: {numero}")
    print("[main.py] Listo para usar.")
```

La función `generar_numero()` sigue **disponible** para quien quiera usarla como módulo. Lo que cambia es que ya no se **ejecuta sola**.

---

## Cómo probarlo

1. Guarda `main.py` e `intento_ataque.py` en la misma carpeta.
2. Ejecuta el intento de ataque:
   ```bash
   python intento_ataque.py
   ```
   → No se imprime ningún número. El import no disparó nada.
3. Ejecuta el script directamente:
   ```bash
   python main.py
   ```
   → Ahora sí funciona normalmente, como script principal.

> [!TIP]
> Si quieres probar que la función sigue accesible como módulo, modifica `intento_ataque.py` para hacer `import main; print(main.generar_numero())`. Verás que la función existe y se puede llamar **explícitamente** —que es justo lo que queremos: el importador decide, no el script.

---

## Comparación directa: antes vs. después

| Aspecto | Sin `if __name__` (carpeta `Mala/`) | Con `if __name__` (carpeta `Buena/`) |
|---------|-------------------------------------|--------------------------------------|
| Ejecución al importar | Todo el código global corre | Solo se definen funciones y clases |
| Control del importador | Ninguno: el módulo decide | Total: el importador decide qué llamar |
| Efectos colaterales | Impredecibles | Ninguno por defecto |
| Riesgo ante dependencias comprometidas | Alto | Contenido |
| Compatibilidad con tests automáticos | Rompe fixtures y estado | Se integra sin sorpresas |
| Compatibilidad con hot-reload | Ejecuta efectos en cada recarga | Silencioso en recargas |
| Reutilización como librería | Inviable en la práctica | Diseño estándar |
| Esfuerzo de implementación | — | 3 líneas |

---

## Qué gana el proyecto al adoptarlo siempre

> [!TIP]
> Más allá de "seguridad" en sentido estricto, proteger el punto de entrada te da:
>
> - **Archivos que funcionan como script y como módulo** sin duplicar código.
> - **Tests unitarios** que pueden importar el archivo para probar sus funciones sin disparar el `main()`.
> - **Documentación automática** (Sphinx, pdoc) que puede analizar el módulo sin ejecutarlo.
> - **Linters y herramientas de análisis** (`mypy`, `ruff`, `pylint`) que inspeccionan sin efectos colaterales.
> - **Depuración más limpia**: sabes exactamente desde dónde arranca la ejecución.
> - **Multiprocessing en Windows**: `multiprocessing` en Windows **exige** este patrón. Sin él, los procesos hijo re-importan el script y entran en bucle infinito de spawning.

---

## Errores comunes al adoptar el patrón

> [!WARNING]
> Cuidado con estos antipatrones que anulan el beneficio:
>
> - **Poner lógica dentro del `if` y también fuera**: si mezclas, el código de fuera sigue siendo vulnerable.
> - **Llamar a una función pesada directamente en el global** (por ejemplo `config = cargar_config_desde_red()` fuera del `if`). El efecto es el mismo que no tener el `if`.
> - **Poner `import` condicionales caros dentro del `if`** que otros módulos esperan encontrar al importar. Rompes la API pública.
> - **Usar variables definidas dentro del `if` desde otros módulos** (`from main import numero`). Esas variables no existen cuando se importa: obtendrás `ImportError`.

---

## Regla para recordar

> [!IMPORTANT]
> **Define fuera. Ejecuta dentro.**
>
> Todo lo que sea declaración (funciones, clases, constantes, tipos) puede vivir en el ámbito global. Todo lo que sea acción (I/O, red, cálculo, efectos) va dentro de `if __name__ == "__main__":`.
>
> No es opcional si pretendes que tu código sea serio, reutilizable y mantenible. Es la barrera más barata que Python te ofrece: úsala siempre.
