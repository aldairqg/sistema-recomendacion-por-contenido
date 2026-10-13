# Exposición: sistema de recomendación musical basado en contenido

Usa este guion para presentar en aproximadamente cinco minutos un recomendador musical basado únicamente en contenido. Abre la aplicación con `python3 app.py` y entra en `http://localhost:8000` antes de comenzar.

## Objetivo del proyecto

Desarrollar un sistema que, a partir de una canción seleccionada, recomiende otras con características de audio similares y permita explicar visualmente cómo se obtiene cada resultado.

Los objetivos específicos son:

- Preparar el Spotify Tracks Dataset y eliminar registros repetidos por identificador.
- Representar cada canción mediante nueve características numéricas de audio.
- Estandarizar las características y calcular similitud coseno.
- Presentar las canciones más similares y el aporte de cada característica.
- Permitir cambios de importancia mediante pesos definidos por quien realiza la demostración.

## Concepto central: recomendación basada en contenido

Un sistema de recomendación basado en contenido compara las características de los elementos que recomienda. En este proyecto, los elementos son canciones y su contenido se representa con descriptores de audio incluidos en el dataset.

La entrada es una canción de referencia y la salida es una lista ordenada de canciones similares. Se implementa una comparación **ítem a ítem**: canción contra canción. No se construye un perfil histórico de gustos ni se emplean preferencias de otros usuarios.

El flujo completo es:

```text
Dataset CSV
    ↓
Limpieza y eliminación de IDs repetidos
    ↓
Selección de nueve características de audio
    ↓
Estandarización de cada característica
    ↓
Selección de canción de referencia y pesos
    ↓
Cálculo de similitud coseno con el catálogo
    ↓
Exclusión de la referencia y resultados repetidos
    ↓
Ordenamiento y selección de las K mejores canciones
    ↓
Visualización y explicación
```

## 1. Problema y propuesta — 30 segundos

“Quiero encontrar canciones que se parezcan musicalmente a una canción elegida. Para eso uso características del audio del Spotify Tracks Dataset. El sistema compara canciones por contenido; no necesita valoraciones ni historiales de personas.”

La canción elegida actúa como referencia. No hay un perfil de usuario aprendido.

## 2. Preparación — 45 segundos

“Parto de 114 000 filas. Descarto una fila sin los metadatos necesarios y quito 24 259 repeticiones de identificador. Quedan 89 740 canciones distintas. Un ID puede tener varias etiquetas de género; las conservo para mostrarlas.”

El archivo original no se modifica. Si aparecen valores numéricos faltantes, se usa la mediana del atributo. En este archivo no hizo falta imputar valores numéricos.

## La base de datos utilizada

### Qué contiene y cómo está organizada

El proyecto utiliza el archivo local **`archive/dataset.csv`**, identificado en el trabajo como Spotify Tracks Dataset. Es un conjunto de datos tabular en formato CSV: cada fila contiene un registro de una canción y cada columna representa un atributo. No es una base relacional con varias tablas ni necesita un gestor como MySQL para esta demostración.

El archivo ocupa **20 145 433 bytes, aproximadamente 20.15 MB**, y contiene **114 000 filas y 21 columnas**. Una de las columnas, `Unnamed: 0`, es un índice de exportación; las otras 20 contienen identificadores, metadatos o descriptores musicales.

Los datos son una copia local: no se actualizan automáticamente con Spotify. El CSV por sí solo no permite verificar autor, enlace de descarga, licencia, fecha de extracción ni procedimiento de muestreo. Si necesitas citar su procedencia académica, agrega la ficha original desde la que lo descargaste; no debe suponerse que los valores describen el catálogo actual de Spotify.

### Unidad de observación e identificador

La unidad de cada fila original es un **registro de canción asociado a una etiqueta de género**. Sin embargo, varias filas pueden compartir `track_id`: el número de filas no equivale al número de canciones diferentes.

`track_id` identifica la pista y es la clave empleada para agrupar registros. El archivo original contiene **89 741 identificadores distintos**. Después de descartar la fila sin título y artista, quedan **89 740 pistas válidas**. Se conserva la primera fila de cada ID para los atributos y se reúnen sus géneros en una lista sin etiquetas repetidas.

### Diccionario de las 21 columnas

Los tipos de esta tabla corresponden a la lectura del archivo con pandas. Una columna numérica puede representar una categoría; no todo número debe usarse directamente como una magnitud continua.

| Columna | Tipo leído | Significado | Uso en este sistema |
| --- | --- | --- | --- |
| `Unnamed: 0` | Entero | Índice incluido al exportar el archivo | Se ignora para recomendar |
| `track_id` | Texto | Identificador de la pista | Identificar, seleccionar y eliminar repeticiones por ID |
| `artists` | Texto | Artista o conjunto de artistas; puede incluir nombres separados por `;` | Buscar, mostrar y evitar resultados repetidos por título/artista |
| `album_name` | Texto | Nombre del álbum | Disponible como metadato; no participa en el ranking |
| `track_name` | Texto | Título de la canción | Buscar, mostrar y evitar resultados repetidos por título/artista |
| `popularity` | Entero | Indicador de popularidad; valores observados entre 0 y 100 | No participa en la similitud |
| `duration_ms` | Entero | Duración en milisegundos | No se selecciona para el modelo |
| `explicit` | Booleano | Indicador de contenido explícito | No participa en la similitud ni filtra resultados |
| `danceability` | Decimal | Descriptor de bailabilidad | Característica del modelo |
| `energy` | Decimal | Descriptor de intensidad y actividad | Característica del modelo |
| `key` | Entero | Código de tonalidad musical | No se selecciona; requeriría una representación apropiada |
| `loudness` | Decimal | Sonoridad global en dB | Característica del modelo |
| `mode` | Entero | Código de modalidad musical | No se selecciona para el modelo |
| `speechiness` | Decimal | Descriptor de presencia de habla | Característica del modelo |
| `acousticness` | Decimal | Descriptor de carácter acústico | Característica del modelo |
| `instrumentalness` | Decimal | Descriptor de instrumentalidad | Característica del modelo |
| `liveness` | Decimal | Descriptor asociado a presencia de público o grabación en vivo | Característica del modelo |
| `valence` | Decimal | Descriptor de positividad musical | Característica del modelo |
| `tempo` | Decimal | Tempo en pulsaciones por minuto, BPM | Característica del modelo |
| `time_signature` | Entero | Código de compás musical | No se selecciona para el modelo |
| `track_genre` | Texto | Etiqueta de género asignada al registro | Se agrupa por ID y se muestra como contexto |

La selección final tiene **nueve columnas de características**. Es una decisión de diseño para explicar similitud sonora mediante atributos numéricos. La duración y los atributos musicales categóricos también podrían aportar contenido en otra versión, pero no intervienen en esta implementación.

### Tamaño, variedad y distribución de géneros

| Medida | Valor observado | Conjunto al que corresponde |
| --- | ---: | --- |
| Registros | 114 000 | CSV original |
| Columnas | 21 | CSV original |
| Identificadores distintos | 89 741 | CSV original |
| Etiquetas de género | 114 | CSV original |
| Filas por género | Exactamente 1 000 | CSV original |
| Canciones válidas sin repetir ID | 89 740 | Catálogo limpio |
| Cadenas distintas en `artists` | 31 437 | Catálogo limpio |
| Nombres de álbum distintos | 46 579 | Catálogo limpio |
| Registros con `explicit = True` | 7 704 | Catálogo limpio |
| Registros con `explicit = False` | 82 036 | Catálogo limpio |

Hay etiquetas como `acoustic`, `classical`, `electronic`, `hip-hop`, `jazz`, `k-pop`, `latin`, `pop`, `reggaeton`, `rock` y `salsa`. También aparecen etiquetas de idioma, región, estado de ánimo o actividad, como `spanish`, `brazil`, `sad` y `study`; por ello, la columna reúne categorías de distinta naturaleza.

**Interpretación importante:** las 1 000 filas por género describen el equilibrio del archivo original, no la distribución real de consumo musical ni el número de pistas únicas por género después de limpiar. Una misma pista puede pertenecer a varias etiquetas.

Las 31 437 cadenas de artistas no equivalen necesariamente a 31 437 personas o grupos: una cadena puede contener una colaboración. Del mismo modo, dos álbumes diferentes pueden compartir nombre; contar nombres distintos no identifica de forma inequívoca todos los álbumes.

### Calidad de datos y limpieza aplicada

1. **Valores faltantes:** una misma fila tiene `artists`, `album_name` y `track_name` vacíos. No hay faltantes en las nueve características numéricas del archivo. La fila se descarta porque falta información necesaria para identificarla ante el usuario.
2. **Repeticiones por ID:** después del descarte anterior, se eliminan 24 259 filas adicionales que repiten `track_id`. Se obtiene una representación por pista.
3. **Duplicados exactos:** contando todas las columnas no existen filas idénticas porque el índice de exportación cambia. Si se ignora `Unnamed: 0`, aparecen **450 filas repetidas exactamente**. Esta cifra no debe confundirse con las 24 259 repeticiones por ID: son criterios distintos y no se suman como dos etapas de eliminación.
4. **Géneros:** se reúnen las etiquetas de todas las filas válidas de un ID. El género se conserva para describir la canción, no para calcular la puntuación.
5. **Atributos numéricos:** la implementación convierte a número, trata valores no finitos como ausentes y contempla imputación por mediana. En este CSV se imputan **0 valores**.
6. **Versiones con distinto ID:** durante la recomendación se omiten combinaciones repetidas de título y artista normalizados. Esto no garantiza identificar todas las versiones, remixes o grabaciones equivalentes.

El balance de filas es:

```text
114 000 filas originales
−     1 fila sin los metadatos necesarios
−24 259 repeticiones adicionales de ID
=89 740 canciones en el catálogo limpio
```

### Estadísticas de los atributos utilizados

Estas cifras se calcularon sobre las **89 740 canciones del catálogo limpio**, conservando la primera fila por ID. Los valores están en sus **unidades originales**, antes de estandarizar. Las medias se redondean a cuatro decimales.

| Característica | Mínimo observado | Media | Máximo observado |
| --- | ---: | ---: | ---: |
| Bailabilidad | 0.0000 | 0.5622 | 0.9850 |
| Energía | 0.0000 | 0.6345 | 1.0000 |
| Valencia | 0.0000 | 0.4695 | 0.9950 |
| Acústica | 0.0000 | 0.3283 | 0.9960 |
| Instrumentalidad | 0.0000 | 0.1734 | 1.0000 |
| Voz hablada | 0.0000 | 0.0874 | 0.9650 |
| Presencia de público | 0.0000 | 0.2170 | 1.0000 |
| Tempo (BPM) | 0.0000 | 122.0581 | 243.3720 |
| Sonoridad (dB) | -49.5310 | -8.4990 | 4.5320 |

El tempo medio es aproximadamente **122.06 BPM** y la sonoridad media, **−8.50 dB**. Estos números describen el archivo analizado, no toda la música disponible en Spotify.

Se observan valores de tempo iguales a 0 y una duración máxima de aproximadamente **87.29 minutos** en el catálogo limpio. Son casos que merecen revisión si se desarrolla una auditoría más profunda; el programa no los considera automáticamente errores ni aplica un filtro de valores extremos. La duración no afecta este modelo porque no forma parte del vector.

La diferencia entre escalas justifica estandarizar: comparar directamente un tempo cercano a 122 con una energía cercana a 0.63 introduciría un efecto de las unidades en la similitud.

### Ejemplo real de un registro

La primera fila del CSV corresponde a **Comedy**, de **Gen Hoshino**:

| Campo | Valor |
| --- | --- |
| ID | `5SuOikwiRyPMVoIQDJUgSV` |
| Álbum | Comedy |
| Género de esta fila | acoustic |
| Duración | 230 666 ms, aproximadamente 3 min 51 s |
| Popularidad registrada | 73 |
| Contenido explícito | False |
| Bailabilidad | 0.676 |
| Energía | 0.461 |
| Valencia | 0.715 |
| Acústica | 0.0322 |
| Instrumentalidad | 0.00000101 |
| Voz hablada | 0.143 |
| Presencia de público | 0.358 |
| Tempo | 87.917 BPM |
| Sonoridad | −6.746 dB |

En el orden elegido por el programa, su vector original es:

```text
[0.676, 0.461, 0.715, 0.0322, 0.00000101,
 0.143, 0.358, 87.917, -6.746]
```

Después, cada posición se estandariza con la media y desviación de su propia columna. El identificador, el título, la popularidad y el género no se añaden a este vector.

### Qué información no contiene para este proyecto

El CSV no incluye una tabla de usuarios, valoraciones personales, historial de escucha, clics o juicios de relevancia. Tampoco contiene archivos de audio, letras ni imágenes de portada. Por eso permite demostrar similitud entre canciones a partir de descriptores, pero no permite medir directamente satisfacción del usuario o precisión de recomendación.

### Texto breve para presentar el dataset

“Trabajé con un archivo CSV de 114 000 registros y 21 columnas. Incluye títulos, artistas, identificadores, géneros y características numéricas del audio. Hay 114 etiquetas, con 1 000 filas por etiqueta en el archivo original. Como una pista puede aparecer varias veces, limpié los registros y conservé 89 740 canciones válidas. Para recomendar seleccioné nueve descriptores de audio; los metadatos sirven para buscar y explicar, mientras que la popularidad no participa en el cálculo.”

## 3. Representación — 45 segundos

“Una canción se convierte en un vector de nueve números. La comparación utiliza esos números, no su nombre ni su popularidad.”

| Característica | Interpretación para la exposición |
| --- | --- |
| Bailabilidad | Descriptor de qué tan adecuado es el audio para bailar |
| Energía | Descriptor de intensidad y actividad |
| Valencia | Descriptor de positividad musical; no mide la emoción real del oyente |
| Acústica | Descriptor de carácter acústico |
| Instrumentalidad | Descriptor de ausencia de voz cantada |
| Voz hablada | Descriptor de presencia de habla |
| Presencia de público | Descriptor asociado con grabaciones en vivo |
| Tempo | Velocidad en pulsaciones por minuto, BPM |
| Sonoridad | Nivel global expresado en decibelios, dB |

Los siete primeros se expresan en una escala de 0 a 1 en este dataset. El sistema utiliza los descriptores proporcionados; no los calcula desde un archivo de audio.

## 4. Escalado y similitud — 60 segundos

“Tempo y energía tienen unidades distintas. Estandarizo cada columna para compararlas en unidades de desviación estándar.”

Para una característica j:

```text
z_j = (x_j − media_j) / desviación_j
v_j = raíz(peso_j) × z_j
coseno(a, b) = suma(v_aj × v_bj) / (norma(v_a) × norma(v_b))
```

La media y desviación se calculan sobre el catálogo limpio. Un z positivo está por encima de la media; uno negativo, por debajo. Si una columna es constante, StandardScaler usa escala 1. Los pesos iniciales son 1.

“Un coseno cercano a 1 representa direcciones similares de los vectores estandarizados. Un valor cercano a 0 indica poca alineación y uno negativo, direcciones opuestas. No significa que una persona tenga esa probabilidad de disfrutar la canción.”

Se usa raíz del peso porque el producto escalar multiplica dos componentes. Así, un peso 3 aporta un factor 3 al numerador, en lugar de 9. La normalización también cambia con los pesos.

## 5. Demostración — 90 segundos

1. Usa **Blinding Lights**, de **The Weeknd**, con todos los pesos en 1 y seis recomendaciones.
2. Explica que el sistema calcula una puntuación contra el catálogo y ordena de mayor a menor.
3. Selecciona el primer resultado y muestra **¿Por qué se parecen?**.
4. Señala que el radar compara siete atributos de 0 a 1; tempo y sonoridad están en las barras y en la tabla.
5. Abre **Ver el cálculo exacto de esta recomendación**. La suma de los nueve aportes coincide con la puntuación, salvo redondeo visual.
6. Pon energía en 3 y acústica en 0; pulsa **Encontrar canciones** y observa el ranking actualizado.
7. Pulsa **Restablecer pesos** y vuelve a recomendar para regresar al punto de partida.

Con el CSV entregado y los pesos iniciales, el primer resultado calculado es **平凡人的自傳 - Rap Version**, de **ONE PROMISE**, con coseno aproximado **0.992188**. Que aparezca un artista o idioma distinto es coherente con el diseño: ni el idioma ni el artista participan en la similitud.

La lista “Cercanía en” elige los tres atributos activos con menor diferencia absoluta entre valores z. Es una explicación descriptiva de cercanía, no una descomposición causal del ranking. La tabla de aportes sí descompone exactamente el coseno.

## 6. Cierre — 30 segundos

“Este recomendador es interpretable: puedo ver los atributos que se comparan y modificar su importancia. Funciona sin historial de usuarios. Su límite es que parecerse en estos nueve descriptores no garantiza que una canción me guste.”

## Preguntas que pueden hacerte

**¿Por qué es basado en contenido?**

Porque la puntuación depende solo de características de los ítems: en este caso, descriptores del audio. No se calculan vecinos entre usuarios ni se utiliza una matriz usuario–canción.

**¿Es un modelo híbrido?**

No. Todos los componentes del cálculo provienen del contenido musical. Los pesos definidos manualmente solo modifican la importancia de esos atributos.

**¿Se entrena una red neuronal?**

No. Se ajusta un transformador de escala y se hace recuperación por similitud. No todo sistema de recomendación necesita una red neuronal o aprendizaje supervisado.

**¿Por qué no se usa popularidad?**

Porque la popularidad mide interacción o exposición, no el contenido sonoro. La implementación no la usa como señal ni como desempate.

**¿Por qué no se incluye género?**

Incluir género también podría ser contenido, pero este proyecto toma una decisión más delimitada: compara exclusivamente nueve descriptores de audio. El género solo ayuda a interpretar el resultado.

**¿Por qué no hay división train/test ni accuracy?**

Aquí se indexa un catálogo sin etiquetas de relevancia ni interacciones. El ajuste del escalador no pretende predecir etiquetas de un conjunto de prueba. Se valida el cálculo mediante pruebas. Para medir calidad de recomendación harían falta juicios de relevancia o un protocolo de evaluación adicional; no se inventa una métrica de acierto.

**¿El valor 0.99 significa que las canciones son casi idénticas?**

Significa que los vectores estandarizados apuntan en direcciones muy similares. El coseno ignora su magnitud; no garantiza identidad de melodía, letra, idioma o experiencia auditiva. Tampoco significa 99 % de precisión.

**¿Qué pasa si todos los pesos valen cero?**

La aplicación rechaza el cálculo y pide activar al menos una característica. Un vector nulo no tiene dirección y su coseno no está definido.

**¿Cómo se evitan duplicados?**

Se conserva una fila por ID al preparar el catálogo. Al recomendar, se excluye la referencia y se omiten resultados con la misma combinación normalizada de título y artista. Distintos títulos de remixes o versiones pueden seguir apareciendo.

**¿Qué cuesta calcularlo?**

Para N canciones y d = 9 atributos, el cálculo de vectores y puntuaciones por consulta cuesta O(Nd). La ordenación completa cuesta O(N log N). La memoria principal es O(Nd); no se guarda una matriz de similitud N × N.

## Ejemplo numérico simplificado para explicar la fórmula

Este ejemplo es didáctico: los números no corresponden a canciones del dataset. Supón que, después de estandarizar, solo mostramos dos características y todos sus pesos valen 1:

```text
Canción A = [1, 2]
Canción B = [2, 1]
Canción C = [-1, -2]

Producto escalar A · B = (1 × 2) + (2 × 1) = 4
Norma de A = √(1² + 2²) = √5
Norma de B = √(2² + 1²) = √5
Similitud(A, B) = 4 / (√5 × √5) = 0.8

Producto escalar A · C = (1 × −1) + (2 × −2) = −5
Similitud(A, C) = −5 / (√5 × √5) = −1
```

B queda antes que C porque su vector está más alineado con A. En el sistema real se aplica la misma operación con nueve características y los pesos seleccionados. Un coseno de 0.8 no equivale a 80 % de precisión.

## Implementación: qué hace cada componente

| Componente | Responsabilidad |
| --- | --- |
| Python | Ejecuta la preparación de datos, las recomendaciones y el servidor local |
| pandas | Lee el CSV, limpia registros y agrupa géneros por ID |
| scikit-learn: StandardScaler | Calcula y aplica la estandarización de los atributos |
| NumPy | Realiza operaciones con vectores, pesos y puntuaciones |
| HTML y CSS | Organizan y presentan la interfaz |
| JavaScript y SVG | Gestionan la interacción y dibujan las comparaciones |

El archivo `recommender.py` contiene el algoritmo. `app.py` expone la búsqueda y las recomendaciones a la interfaz. La carpeta `static/` contiene la parte visual. La aplicación usa el CSV local; no necesita conectarse a Spotify para recomendar.

### Pseudocódigo del algoritmo

```text
Leer el dataset
Descartar registros sin identificación, título o artista
Agrupar géneros y conservar una fila por ID
Seleccionar las nueve características
Completar valores numéricos faltantes con la mediana
Estandarizar cada columna usando el catálogo limpio

Recibir canción base, cantidad K y pesos
Validar los pesos y localizar la canción base
Multiplicar los vectores por la raíz de los pesos
Calcular sus normas y excluir vectores nulos
Calcular el coseno entre la base y cada candidato
Ordenar los candidatos por similitud descendente
Excluir la referencia y combinaciones repetidas de título y artista
Devolver hasta K canciones con sus valores y aportes
```

## Cómo interpretar las visualizaciones

| Elemento de la interfaz | Qué debes explicar |
| --- | --- |
| Lista de recomendaciones | Presenta las canciones en orden descendente de similitud coseno |
| Radar | Compara siete características con escala original de 0 a 1; no representa por sí solo todo el cálculo |
| Barras comparativas | Muestran las nueve características; tempo y sonoridad tienen escalas visuales propias |
| Tabla del cálculo | Muestra valores originales, valores estandarizados, pesos y aportes al coseno |
| Controles de pesos | Permiten ignorar un atributo con 0 o aumentar su importancia hasta 3 |
| Pestaña «Cómo funciona» | Resume la limpieza, representación, estandarización y comparación |

Verde identifica la canción base y violeta la recomendada. Las cifras junto a las barras permiten leer los valores sin depender únicamente del color.

## Validación y resultados del proyecto

Se ejecutaron diez pruebas automatizadas y todas pasaron. Comprueban:

1. Los conteos de limpieza y la ausencia de valores no finitos en los vectores.
2. La coincidencia del ranking y sus puntuaciones con el coseno de scikit-learn.
3. El cálculo con pesos y la igualdad entre la suma de aportes y la similitud.
4. La exclusión de la canción base y de títulos repetidos por artista.
5. La búsqueda sin distinguir mayúsculas y el tratamiento literal del texto.
6. El rechazo de pesos inválidos, negativos, no finitos o completamente nulos.
7. El manejo de identificadores inexistentes y cantidades fuera del rango permitido.
8. La selección exclusiva de características de audio y la independencia respecto de popularidad.
9. La imputación por mediana y la agrupación de géneros.
10. El tratamiento de vectores nulos.

También se comprobó en el navegador la búsqueda por artista y la generación de recomendaciones. **Estas verificaciones prueban el funcionamiento de la implementación; no demuestran que las recomendaciones gusten a los usuarios.**

## Ventajas y limitaciones

**Ventajas:** funciona sin historial de usuarios, explica sus resultados, permite ajustar la importancia de los atributos y compara todo el catálogo limpio sin almacenar una matriz de similitud entre todos los pares.

**Limitaciones:** depende de la calidad de los descriptores; no interpreta letra, contexto cultural ni gusto personal; el coseno ignora la magnitud del vector; la estandarización es sensible a valores extremos; los atributos correlacionados pueden introducir redundancia; y las recomendaciones pueden tener poca diversidad. Las canciones nuevas requieren descriptores compatibles e incorporarse al catálogo al volver a cargarlo.

## Conclusión para la exposición

“Se implementó un sistema de recomendación basado exclusivamente en contenido que compara nueve características de audio. La estandarización permite trabajar con distintas unidades y la similitud coseno ordena las canciones según su cercanía direccional. La interfaz hace visible el proceso mediante gráficos, pesos ajustables y una tabla de aportes. El resultado es una demostración funcional e interpretable de recomendación musical, cuya similitud matemática no debe confundirse con satisfacción del usuario.”

## Fuentes del cálculo

La estandarización sigue la definición de [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html). La similitud sigue el producto escalar normalizado descrito en [cosine_similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html). Las pruebas comparan el cálculo propio con esta última función.
