
# ============================================================
# ANÁLISIS ESTADÍSTICO - STUDENTS PERFORMANCE
# Comparación de calificaciones de matemáticas por género
# ============================================================

import pandas as pd               # Manejo de datos y archivos CSV
from scipy import stats           # Pruebas estadísticas
import matplotlib.pyplot as plt   # Creación de gráficas
import seaborn as sns             # Visualización estadística


# ============================================================
# 1. CARGAR EL DATASET
# ============================================================

# Leer el archivo CSV ubicado en la carpeta del proyecto
df = pd.read_csv("StudentsPerformance.csv")

# Mostrar los primeros cinco registros
print("\nPRIMEROS CINCO REGISTROS")
print(df.head())

# Mostrar cantidad de filas y columnas
print("\nDIMENSIONES")
print(df.shape)


# ============================================================
# 2. SEPARAR LOS GRUPOS
# ============================================================

# Obtener las calificaciones de matemáticas de los hombres
hombres = df[df["gender"] == "male"]["math score"]

# Obtener las calificaciones de matemáticas de las mujeres
mujeres = df[df["gender"] == "female"]["math score"]


# ============================================================
# 3. PRUEBA DE NORMALIDAD SHAPIRO-WILK
# ============================================================

# Evaluar normalidad de cada grupo
shapiro_hombres = stats.shapiro(hombres)
shapiro_mujeres = stats.shapiro(mujeres)

# Mostrar los p-valores
print("\nNORMALIDAD SHAPIRO-WILK")
print("Hombres:", shapiro_hombres.pvalue)
print("Mujeres:", shapiro_mujeres.pvalue)

# Evaluar normalidad utilizando un nivel de significancia del 5 %
if shapiro_hombres.pvalue > 0.05 and shapiro_mujeres.pvalue > 0.05:
    print("No se rechaza la normalidad en ninguno de los grupos.")
else:
    print("Se rechaza la normalidad en al menos un grupo.")


# ============================================================
# 4. PRUEBA MANN-WHITNEY U
# ============================================================

# Comparar las distribuciones de dos grupos independientes
resultado = stats.mannwhitneyu(
    hombres,                   # Primer grupo
    mujeres,                   # Segundo grupo
    alternative="two-sided"    # Prueba bilateral
)

# Mostrar resultados
print("\nPRUEBA MANN-WHITNEY U")
print("Estadístico U:", resultado.statistic)
print("p-valor:", resultado.pvalue)

# Interpretar el p-valor con significancia del 5 %
if resultado.pvalue < 0.05:
    print("Se rechaza H0: hay diferencias estadísticamente significativas.")
else:
    print("No se rechaza H0: no hay evidencia suficiente de diferencias.")


# ============================================================
# 5. ESTADÍSTICAS DESCRIPTIVAS
# ============================================================

# Calcular cantidad, media, mediana y desviación estándar
resumen = df.groupby("gender")["math score"].agg(
    ["count", "mean", "median", "std"]
)

# Mostrar resultados
print("\nESTADÍSTICAS POR GÉNERO")
print(resumen)


# ============================================================
# 6. GRÁFICA DE CAJAS (BOXPLOT)
# ============================================================

# Crear la figura
plt.figure(figsize=(8, 5))

# Representar las calificaciones agrupadas por género
sns.boxplot(
    data=df,
    x="gender",
    y="math score"
)

# Configurar títulos y etiquetas
plt.title("Calificaciones de matemáticas por género")
plt.xlabel("Género")
plt.ylabel("Calificación de matemáticas")

# Ajustar los elementos de la gráfica
plt.tight_layout()

# Guardar las gráficas en la carpeta imagenes
plt.savefig("imagenes/grafica_matematicas.png", dpi=300)
plt.savefig("imagenes/grafica_cinco_grupos.png", dpi=300)
plt.savefig("imagenes/grafica_correlacion.png", dpi=300)
plt.savefig("imagenes/grafica_chi_cuadrado.png", dpi=300)

# Mostrar mensaje de confirmación
print("\nGráfica guardada: grafica_matematicas.png")

# Mostrar la gráfica en una ventana si el entorno lo permite
plt.show()


# ============================================================
# 7. COMPARACIÓN DE CINCO GRUPOS
# ============================================================

# Agrupar las calificaciones según race/ethnicity
grupos = [
    grupo["math score"].to_numpy()
    for _, grupo in df.groupby("race/ethnicity")
]

# Obtener los nombres de los grupos
nombres = sorted(df["race/ethnicity"].unique())

# Mostrar los grupos y sus resultados de normalidad
print("\nNORMALIDAD POR GRUPO")

# Guardar los resultados de normalidad de cada grupo
normalidades = []

for nombre, datos in zip(nombres, grupos):

    # Aplicar Shapiro-Wilk a cada grupo
    p = stats.shapiro(datos).pvalue

    # Guardar el p-valor
    normalidades.append(p)

    # Mostrar resultado
    print(nombre, "p-valor:", p)

# ============================================================
# 8. HOMOGENEIDAD DE VARIANZAS
# ============================================================

# Aplicar prueba de Levene
levene = stats.levene(*grupos)

print("\nPRUEBA DE LEVENE")
print("p-valor:", levene.pvalue)

# ============================================================
# 9. SELECCIONAR LA PRUEBA ESTADÍSTICA
# ============================================================

# Comprobar si todos los grupos superan el umbral de normalidad
normal = all(p > 0.05 for p in normalidades)

# Elegir la prueba según los supuestos
if normal and levene.pvalue > 0.05:

    # ANOVA clásico para grupos normales y varianzas homogéneas
    prueba = "ANOVA de una vía"
    resultado_grupos = stats.f_oneway(*grupos)

elif normal:

    # ANOVA de Welch para varianzas diferentes
    prueba = "ANOVA de Welch"
    resultado_grupos = stats.f_oneway(
        *grupos, equal_var=False
    )

else:

    # Kruskal-Wallis cuando se elige una alternativa no paramétrica
    prueba = "Kruskal-Wallis"
    resultado_grupos = stats.kruskal(*grupos)

# Mostrar resultados
print("\nCOMPARACIÓN DE CINCO GRUPOS")
print("Prueba seleccionada:", prueba)
print("Estadístico:", resultado_grupos.statistic)
print("p-valor:", resultado_grupos.pvalue)

# Interpretar el resultado
if resultado_grupos.pvalue < 0.05:
    print("Se rechaza H0: existen diferencias entre grupos.")
else:
    print("No se rechaza H0: evidencia insuficiente de diferencias.")

# ============================================================
# 10. PRUEBA POST HOC DE DUNN
# ============================================================

import scikit_posthocs as sp  # Pruebas posteriores no paramétricas

# Comparar todos los pares de grupos
# La corrección Bonferroni controla las comparaciones múltiples
resultado_dunn = sp.posthoc_dunn(
    df,
    val_col="math score",       # Variable numérica
    group_col="race/ethnicity", # Variable de agrupación
    p_adjust="bonferroni"       # Corrección de p-valores
)

# Mostrar la matriz de comparaciones
print("\nPRUEBA POST HOC DE DUNN")
print(resultado_dunn.round(5))

# ============================================================
# 11. GRÁFICA COMPARATIVA DE LOS CINCO GRUPOS
# ============================================================

# Crear una figura de 10 por 6 pulgadas
plt.figure(figsize=(10, 6))

# Representar la distribución de las notas por grupo
sns.boxplot(
    data=df,
    x="race/ethnicity",
    y="math score",
    order=sorted(df["race/ethnicity"].unique())
)

# Configurar el título y los ejes
plt.title("Calificaciones de matemáticas por grupo")
plt.xlabel("Grupo")
plt.ylabel("Calificación de matemáticas")

# Ajustar la distribución de los elementos
plt.tight_layout()

# Guardar la imagen en la carpeta del proyecto
plt.savefig("grafica_cinco_grupos.png", dpi=300)

# Mostrar la gráfica si el entorno lo permite
plt.show()

# ============================================================
# 12. COMPARACIÓN DE DOS MUESTRAS PAREADAS
# ============================================================

# Obtener las calificaciones de matemáticas
matematicas = df["math score"]

# Obtener las calificaciones de lectura
lectura = df["reading score"]

# Calcular las diferencias de cada estudiante
diferencias = matematicas - lectura

# Mostrar estadísticas descriptivas
print("\nCOMPARACIÓN DE MATEMÁTICAS Y LECTURA")
print("Promedio matemáticas:", matematicas.mean())
print("Promedio lectura:", lectura.mean())
print("Promedio de diferencias:", diferencias.mean())

# ============================================================
# 13. NORMALIDAD DE LAS DIFERENCIAS
# ============================================================

# Aplicar Shapiro-Wilk a las diferencias pareadas
normalidad_diferencias = stats.shapiro(diferencias)

# Mostrar el p-valor
print("\nNORMALIDAD DE LAS DIFERENCIAS")
print("p-valor:", normalidad_diferencias.pvalue)

# ============================================================
# 14. SELECCIÓN DE LA PRUEBA PAREADA
# ============================================================

# Seleccionar la prueba según la normalidad
if normalidad_diferencias.pvalue > 0.05:

    # Prueba t para muestras relacionadas
    prueba_pareada = "t de Student pareada"
    resultado_pareado = stats.ttest_rel(
        matematicas,
        lectura
    )

else:

    # Prueba no paramétrica para muestras relacionadas
    prueba_pareada = "Wilcoxon"
    resultado_pareado = stats.wilcoxon(
        matematicas,
        lectura
    )

# Mostrar los resultados
print("\nRESULTADO DE LA PRUEBA PAREADA")
print("Prueba seleccionada:", prueba_pareada)
print("Estadístico:", resultado_pareado.statistic)
print("p-valor:", resultado_pareado.pvalue)

# Interpretar el resultado con significancia del 5 %
if resultado_pareado.pvalue < 0.05:
    print("Se rechaza H0: existen diferencias significativas.")
else:
    print("No se rechaza H0: evidencia insuficiente de diferencias.")

# ============================================================
# 15. CORRELACIÓN ENTRE MATEMÁTICAS Y LECTURA
# ============================================================

# Obtener las dos variables numéricas
matematicas = df["math score"]
lectura = df["reading score"]

# Calcular la correlación de Spearman
correlacion = stats.spearmanr(
    matematicas,  # Primera variable
    lectura       # Segunda variable
)

# Mostrar los resultados estadísticos
print("\nCORRELACIÓN DE SPEARMAN")
print("Coeficiente:", correlacion.statistic)
print("p-valor:", correlacion.pvalue)

# Evaluar si existe una asociación significativa
if correlacion.pvalue < 0.05:
    print("Se rechaza H0: existe una asociación significativa.")
else:
    print("No se rechaza H0: evidencia insuficiente de asociación.")

# Interpretar la dirección de la correlación
if correlacion.statistic > 0:
    print("La correlación es positiva.")
elif correlacion.statistic < 0:
    print("La correlación es negativa.")
else:
    print("No existe correlación monotónica observada.")


# ============================================================
# 16. GRÁFICA DE DISPERSIÓN
# ============================================================

# Crear una figura de 8 por 6 pulgadas
plt.figure(figsize=(8, 6))

# Representar cada estudiante mediante un punto
sns.scatterplot(
    data=df,
    x="math score",
    y="reading score",
    alpha=0.5
)

# Configurar título y etiquetas
plt.title("Relación entre matemáticas y lectura")
plt.xlabel("Calificación de matemáticas")
plt.ylabel("Calificación de lectura")

# Ajustar la presentación de la gráfica
plt.tight_layout()

# Guardar la imagen en la carpeta del proyecto
plt.savefig("grafica_correlacion.png", dpi=300)

# Mostrar la gráfica si el entorno lo permite
plt.show()

# ============================================================
# 17. PRUEBA CHI-CUADRADO DE INDEPENDENCIA
# ============================================================

# Crear una tabla de frecuencias entre las dos variables
tabla = pd.crosstab(
    df["gender"],                  # Filas: género
    df["test preparation course"]  # Columnas: preparación
)

# Mostrar la tabla de contingencia
print("\nTABLA DE CONTINGENCIA")
print(tabla)

# Aplicar la prueba chi-cuadrado de independencia
chi2, p_valor, grados_libertad, esperados = stats.chi2_contingency(
    tabla
)

# Mostrar los resultados estadísticos
print("\nPRUEBA CHI-CUADRADO")
print("Estadístico chi-cuadrado:", chi2)
print("Grados de libertad:", grados_libertad)
print("p-valor:", p_valor)

# Comprobar las frecuencias esperadas
print("Frecuencia esperada mínima:", esperados.min())

# Interpretar el resultado con significancia del 5 %
if p_valor < 0.05:
    print("Se rechaza H0: existe asociación entre las variables.")
else:
    print("No se rechaza H0: no hay evidencia suficiente de asociación.")


# ============================================================
# 18. GRÁFICA DE FRECUENCIAS
# ============================================================

# Crear una figura de 8 por 5 pulgadas
plt.figure(figsize=(8, 5))

# Comparar las frecuencias de preparación por género
sns.countplot(
    data=df,
    x="gender",
    hue="test preparation course"
)

# Configurar título y etiquetas
plt.title("Curso de preparación según género")
plt.xlabel("Género")
plt.ylabel("Cantidad de estudiantes")
plt.legend(title="Curso de preparación")

# Ajustar y guardar la gráfica
plt.tight_layout()
plt.savefig("grafica_chi_cuadrado.png", dpi=300)

# Mostrar la gráfica si el entorno lo permite
plt.show()
