# SONAR — recomendación musical basada en contenido

Proyecto para demostrar y explicar un sistema de recomendación **exclusivamente basado en contenido** con tu Spotify Tracks Dataset. Busca una canción, obtiene sus vecinas por similitud coseno y explica el resultado mediante gráficos y aportes por atributo.

## Ejecutar

Necesitas Python 3.11 o posterior. Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 app.py
```

Abre [SONAR en localhost:8000](http://localhost:8000). El primer arranque prepara el catálogo; espera el mensaje «canciones listas». Para detenerlo, pulsa **Ctrl+C** en la terminal.

Si las dependencias ya están instaladas, ejecuta directamente `python3 app.py`. La interfaz funciona sin conexión después de instalar las dependencias; no requiere cuenta, claves, API de Spotify ni servicios externos.

Para cambiar el puerto o usar otro CSV con las mismas columnas:

```bash
python3 app.py --port 8001 --dataset archive/dataset.csv
```

## Demostración

1. Observa el ejemplo inicial: **Blinding Lights**, de **The Weeknd**.
2. Busca una canción por título o artista y selecciona una coincidencia.
3. Pulsa **Encontrar canciones**.
4. Selecciona un resultado para ver el radar, las barras y el cálculo exacto.
5. Abre **Ajustar características**, cambia los pesos y vuelve a recomendar.
6. Abre **Cómo funciona** para presentar las etapas del algoritmo.

La puntuación está entre −1 y 1. **No es un porcentaje de acierto ni una probabilidad de gusto.** El radar usa siete características con escala original de 0 a 1; el algoritmo y la tabla usan los nueve atributos.

## Datos y modelo

El archivo original permanece en `archive/dataset.csv`.

| Operación | Resultado en este CSV |
| --- | ---: |
| Filas originales | 114 000 |
| Filas descartadas por identidad/título/artista faltante | 1 |
| Repeticiones de ID eliminadas después de ese descarte | 24 259 |
| Canciones únicas disponibles | 89 740 |
| Géneros distintos | 114 |
| Valores numéricos imputados | 0 |

Para cada ID se conserva la primera fila y se agrupan sus etiquetas de género. Los valores numéricos faltantes o no finitos se imputan con la mediana cuando existen; una característica enteramente ausente genera un error.

El vector contiene `danceability`, `energy`, `valence`, `acousticness`, `instrumentalness`, `speechiness`, `liveness`, `tempo` y `loudness`. Se ajusta **StandardScaler** sobre el catálogo limpio, se multiplica cada componente por la raíz del peso y se calcula coseno contra la canción base. El ranking ordena de mayor a menor coseno; los empates conservan el orden del CSV.

Se excluye la referencia y se evita repetir la combinación exacta de título y artista normalizados, incluso con IDs distintos. La normalización ignora mayúsculas, acentos y espacios en los extremos; no identifica todas las versiones, remixes o grabaciones equivalentes. Los vectores nulos no participan en el ranking.

El modelo no usa popularidad, géneros, títulos, artistas, ratings, historial ni datos de usuarios como características de similitud. Los títulos y artistas permiten buscar, presentar y quitar duplicados. Los géneros son etiquetas descriptivas. Los pesos cambian la importancia del contenido; no convierten el modelo en colaborativo ni híbrido.

## Archivos

| Archivo | Función |
| --- | --- |
| `recommender.py` | Limpieza, vectores, búsqueda, ranking y explicación |
| `app.py` | Servidor HTTP local y API |
| `static/index.html` | Interfaz y explicación del método |
| `static/app.js` | Búsqueda, controles y gráficos SVG |
| `static/styles.css` | Diseño adaptable a distintos anchos |
| `docs/EXPOSICION.md` | Guion, fórmulas, ejemplo y preguntas frecuentes |
| `tests/test_recommender.py` | Verificación matemática y casos límite |

## Verificar el motor

Ejecuta las pruebas desde la carpeta del proyecto:

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas comparan el cálculo con `sklearn.metrics.pairwise.cosine_similarity`, comprueban los pesos y la suma de aportes, evitan autorrecomendaciones y verifican limpieza, imputación y manejo de entradas inválidas. Son pruebas de implementación; no miden satisfacción de usuarios.

## Límites

Los atributos están precalculados en el CSV: el sistema no escucha audio ni reproduce canciones. La similitud es relativa al catálogo y a los atributos elegidos. No existen etiquetas de relevancia que permitan afirmar precisión o satisfacción. El escalado es sensible a valores extremos y varios atributos pueden estar correlacionados. Los resultados pueden pertenecer a otros idiomas y géneros.

El cálculo por consulta usa una matriz de N × 9 y un vector de N puntuaciones; no construye una matriz N × N. El servidor sirve únicamente la carpeta `static/` y escucha en `127.0.0.1` para demostraciones locales.

## Referencias

Consulta la definición de estandarización en [StandardScaler, documentación oficial](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html) y la de producto escalar normalizado en [cosine_similarity, documentación oficial](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html).
