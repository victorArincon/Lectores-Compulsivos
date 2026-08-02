# Bitácora — Trabajo de Frontend (Dev 2)

Registro cronológico de lo realizado para la parte de interfaz de usuario del proyecto de Biblioteca.

## 1. Diagnóstico del punto de partida

- Se revisó el proyecto existente: solo había `codigo_libros.py` (clases `Libro`, `Usuario`, `Biblioteca`) y `libros.json` (20 libros). No existía Flask, `templates/`, `static/` ni ningún archivo de frontend.
- Se confirmó la división de trabajo en 3 personas: Dev1 (modelo/backend), Dev2 (interfaz — este trabajo), Dev3 (integración Flask/rutas).

## 2. Plan de implementación

- Se definió que el frontend usaría una plantilla Bootstrap gratuita ya armada (no HTML/CSS desde cero), y se comparó **SB Admin 2** vs. los ejemplos oficiales de Bootstrap 5 vs. CoreUI Free.
- Se eligió **SB Admin 2** (Start Bootstrap, licencia MIT) por traer ya listas las pantallas necesarias (login, dashboard con sidebar, tabla de datos) sin requerir Node/build tools.
- Se acordó trabajar de forma independiente del resto del equipo mediante un mini servidor Flask propio (`preview_app.py`) con datos de prueba hardcodeados, para poder ver las páginas funcionando sin esperar al backend real.
- Plan guardado en `docs`/plan mode como referencia de las tareas a ejecutar.

## 3. Revisión y corrección de `codigo_libros.py`

- Se detectó un error de sintaxis real: en las líneas 132 y 149 había un salto de línea literal dentro de un `print("...")`, dejando la cadena sin cerrar.
- Se corrigió reemplazando el salto de línea literal por `\n` escapado en la misma línea.
- Se verificó con `python -m py_compile codigo_libros.py` → sin errores.
- Revisión rápida de estilo "ponytail" (buscar líneas de más/sobre-ingeniería): el archivo ya es lean y no requirió más cambios.

## 4. Descarga e instalación de la plantilla SB Admin 2

- Se descargó el repositorio desde `https://github.com/StartBootstrap/startbootstrap-sb-admin-2` y se extrajo temporalmente.
- Se copiaron a `static/` los archivos ya compilados de la plantilla:
  - `static/css/sb-admin-2.min.css`
  - `static/js/sb-admin-2.min.js`
  - `static/vendor/` (bootstrap, jquery, jquery-easing, fontawesome-free, datatables, chart.js)
- Se mostró un preview de `login.html`, `index.html` (dashboard) y `tables.html` de la plantilla original en el navegador para decidir si era la indicada. Se confirmó seguir con SB Admin 2.
- Se eliminaron el ZIP y la carpeta extraída una vez copiados los assets necesarios (no forman parte del proyecto final).

## 5. Construcción de los templates Jinja2

Se crearon a partir del markup de SB Admin 2, quitando el contenido de ejemplo (gráficos, tarjetas de estadísticas ficticias, dropdowns de notificaciones) y dejándolo enfocado en lo que necesita la biblioteca:

- **`templates/base.html`**: layout con sidebar (Catálogo / Mis Préstamos / Salir) y topbar con el usuario logueado. Define `{% block content %}`.
- **`templates/login.html`**: pantalla de login standalone con formulario (`usuario`, `password`) que hace POST al endpoint `login`, con manejo de mensaje de error opcional.
- **`templates/catalogo.html`**: extiende `base.html`. Tabla con `{% for libro in libros %}`, columnas Título/Autor/ISBN/Cantidad/Estado, badge verde "Disponible" / rojo "Agotado", y botón "Prestar" o "Devolver" según disponibilidad.
- **`templates/mis_prestamos.html`**: extiende `base.html`. Tabla reducida a `libros_prestados`, solo con botón "Devolver".

## 6. Herramienta de preview independiente

- Se creó `requirements.txt` (solo `Flask`) y `preview_app.py`: una mini app Flask con una lista `LIBROS_DEMO` hardcodeada (mismos campos que `libros.json`) y las rutas `login`, `catalogo`, `prestar`, `devolver`, `mis_prestamos`, `logout` — estos nombres de endpoint son el "contrato" que Dev3 debe respetar al construir el `app.py` real, para que los templates no necesiten cambios.
- Se instaló Flask (`pip install -r requirements.txt`) y se corrió `python preview_app.py`.

## 7. Verificación

- Se comprobó por HTTP que todas las rutas devuelven código 200: `/login`, `/catalogo`, `/mis-prestamos`, y los assets estáticos (`static/css/sb-admin-2.min.css`, `static/vendor/jquery/jquery.min.js`).
- Se verificó que el catálogo renderiza correctamente 3 libros "Disponible" y 1 "Agotado" (el libro con `cantidad: 0`), confirmando que la lógica de badges y botones en `catalogo.html` funciona.
- Se abrieron las páginas en el navegador para inspección visual final.

## 8. Cambio de plantilla: de SB Admin 2 a diseño oscuro con portadas reales

Tras ver el preview en el navegador, se decidió que SB Admin 2 (panel de admin con sidebar) se veía demasiado simple/corporativo para una biblioteca. Se pivotó a un diseño propio más moderno:

- **Se descartó SB Admin 2 por completo** (se quitó `vendor/`, `sb-admin-2.min.css/js` de `static/`).
- **Se instaló Bootstrap 5.3 (self-hosted, sin CDN)** — usa el modo oscuro nativo (`data-bs-theme="dark"`), sin dependencia de jQuery/Font Awesome/DataTables.
- Se creó `static/css/custom.css` con estilos propios: tarjetas de libro con hover, portadas y fondo del login.
- **`templates/base.html`**: navbar oscuro simple (en vez de sidebar), marca **"Lectores Compulsivos"**.
- **`templates/login.html`**: tarjeta centrada oscura con la marca nueva.
- **`templates/catalogo.html`** y **`templates/mis_prestamos.html`**: pasaron de tabla a **grid de tarjetas** (`row-cols-2/3/4`), una por libro.
- Se quitaron todos los emojis del proyecto (navbar y login) a pedido explícito.

### Portadas reales de los libros

El usuario preguntó por qué el catálogo mostraba pocos libros: era porque `preview_app.py` usaba una lista `LIBROS_DEMO` de solo 4 libros hardcodeados a mano, no los 20 reales de `libros.json` (esto era una decisión de la vista previa de Dev2, no una limitación del proyecto). Se corrigió:

- **`preview_app.py`** ahora carga `LIBROS_DEMO` directamente de `libros.json` con `json.load`, mostrando los 20 libros reales.
- El usuario pidió portadas de verdad en vez de un recuadro de color con el título. Se agregó un campo **`"portada"`** a cada uno de los 20 libros en `libros.json`, con una URL de imagen real:
  - Para 15 libros se usó la API pública de portadas de Open Library por ISBN: `https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg` (verificado con `curl` que cada una devuelve una imagen real, no el placeholder de "sin portada").
  - Para 5 libros sin portada por ISBN (la trilogía de R.F. Kuang, "El Señor de los Anillos: La Comunidad del Anillo" y "Pensar rápido, pensar despacio") se buscó por título/autor en `https://openlibrary.org/search.json` para obtener un `cover_i` y se usó `https://covers.openlibrary.org/b/id/{cover_i}-M.jpg`, verificando también con `curl` que cada una es una imagen real (no un placeholder de 43 bytes).
- **`codigo_libros.py`**: se agregó el atributo `portada` a la clase `Libro` (parámetro opcional, `default=""`) y se actualizó `cargar_libros_desde_json` para leerlo del JSON (`item.get('portada', '')`), de modo que el dato fluya también cuando Dev3 conecte el backend real — no solo en el preview de Dev2. Se coordinó como una adición mínima y retrocompatible (no rompe nada de lo que ya tenía Dev1).
- **`templates/catalogo.html`** y **`templates/mis_prestamos.html`**: la portada ahora es `<img class="book-cover-img" src="{{ libro.portada }}">`; si algún libro no trajera el campo `portada` (por ejemplo si Dev1 agrega libros nuevos sin ese dato), cae de respaldo al recuadro de color con el título, para que la plantilla nunca se rompa por un dato faltante.
- Se volvió a verificar con `curl` que las 20 tarjetas del catálogo renderizan `<img class="book-cover-img">`, que el `<title>` no lleva emoji, y que `codigo_libros.py` sigue compilando sin errores tras los cambios.

## 9. Mejora de resolución y corrección de portadas incorrectas

- **Resolución:** las portadas se pidieron en tamaño "M" (mediano, ~180px). Se cambiaron todas a tamaño **"L"** (grande, ~350-500px) reemplazando `-M.jpg` por `-L.jpg` en la URL de cada libro en `libros.json`. Verificado con `curl` que el tamaño en bytes de la imagen sube notablemente (ej. de ~17 KB a ~45 KB), confirmando mejor resolución real.
- **Hallazgo importante:** al investigar los datos para el objetivo 2 (sinopsis/páginas/año), se detectó que **6 de los 20 ISBN de `libros.json` no corresponden al libro real** en la base de datos de Open Library — parecen ISBN de relleno copiados de tutoriales, no los ISBN verdaderos de esos libros. Al consultar `https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data` se comprobó que el ISBN devolvía un libro distinto:
  - "Orgullo y Prejuicio" → el ISBN traía "Cien años de soledad"
  - "1984" → el ISBN traía "The Little Prince"
  - "El proceso" → el ISBN traía "Momentos estelares de la ciencia"
  - "Crimen y castigo" → el ISBN traía "La niña de oro y otros relatos"
  - "Los hermanos Karamazov" → el ISBN traía un libro de "Análisis de series temporales" (nada que ver)
  - "Drácula" → el ISBN traía un libro de Nietzsche
  - Esto significa que las portadas que se habían puesto para esos 6 libros (obtenidas confiando en el ISBN) eran de otro libro.
- **Corrección:** para esos 6 libros se volvió a buscar por **título + autor** en `https://openlibrary.org/search.json?q={titulo}+{autor}`, se tomó el `cover_i` del resultado correcto, y se armó la URL `https://covers.openlibrary.org/b/id/{cover_i}-L.jpg`. Se verificó con `curl` que cada imagen nueva es real y de buen tamaño antes de guardarla en `libros.json`.
- Los otros 14 libros sí tenían ISBN correctos (coincide el título real con el esperado) o ya se habían resuelto por búsqueda de título/autor desde el paso anterior (los 5 que no tenían portada por ISBN).

### Fuentes de datos externas usadas (para citar en la presentación)

Todo el contenido de portadas viene de **Open Library** (proyecto sin fines de lucro de Internet Archive, datos abiertos, sin necesidad de API key):

- **Open Library Covers API** — imágenes de portada: `https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg` o `https://covers.openlibrary.org/b/id/{cover_id}-L.jpg`. Documentación: `https://openlibrary.org/dev/docs/api/covers`
- **Open Library Books API** (bibkeys) — usada para *verificar* que cada ISBN correspondía al libro correcto: `https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data`
- **Open Library Search API** — usada para encontrar el `cover_id` correcto cuando el ISBN no traía portada o traía la de otro libro: `https://openlibrary.org/search.json?q={titulo}+{autor}`. Documentación: `https://openlibrary.org/dev/docs/api/search`

Todas estas consultas se hicieron una sola vez para completar el campo `portada` en `libros.json` (no se llaman en cada carga de página; el archivo JSON ya guarda la URL final).

## 10. Modal de detalle de libro (páginas, año, sinopsis, biografía del autor)

### Campos nuevos en `libros.json`

Se agregaron 4 campos nuevos a cada uno de los 20 libros: `paginas` (int), `anio_publicacion` (int), `sinopsis` (str) y `autor_bio` (str). Son opcionales con valores por defecto (`None`/`""`) tanto en `Libro.__init__` (`codigo_libros.py`) como en las plantillas, para que un libro nuevo sin estos campos no rompa la página (cae a "No disponible" / "Sinopsis no disponible." / "Biografía no disponible.").

Al poblar estos campos se revisó a mano cada uno de los 20 libros (no solo se confió en el script automático) y aparecieron algunos problemas de datos que se corrigieron manualmente:

- **Dune**: el script de enriquecimiento marcó "OK" pero había emparejado el libro con el work de *Children of Dune* (la tercera novela de la saga, 1976) en vez de *Dune* (1965) — mismatch silencioso, la sinopsis y páginas traídas eran de otro libro. Se corrigió buscando el work id correcto (`/works/OL893414W`) filtrando por título exacto "Dune".
- **El proceso**: `anio_publicacion` venía en 1825 desde Open Library, un valor imposible (Kafka nació en 1883). Se corrigió a mano a 1925 (año real de publicación póstuma).
- **La guerra de la amapola / La república del dragón / El dios en llamas** (trilogía de R.F. Kuang): la búsqueda por título en español no encontró nada en Open Library, porque esa trilogía solo está catalogada bajo sus títulos originales en inglés (*The Poppy War* / *The Dragon Republic* / *The Burning God*). Se buscaron manualmente por título en inglés + autor y se cargaron sus datos (páginas, año, sinopsis, autor_bio de R.F. Kuang) a los 3 registros en español.

Verificado con `curl` contra el servidor de preview que cada uno de los 20 modales (`libroModal1`...`libroModal20` en `/catalogo`, `prestamoModal1`/`prestamoModal2` en `/mis-prestamos`) muestra el título, autor y fragmento de sinopsis/bio que corresponde a **ese mismo libro** y no a otro (se prestó atención especial a Dune, a la trilogía de Kuang y a los libros cuya portada se había corregido antes por mismatch de ISBN — ver sección 9 — para descartar el mismo tipo de error también en el contenido del modal). No se encontró ningún cruce de datos entre libros.

### APIs externas usadas (para citar en la presentación)

Además de las ya citadas en la sección 9 (portadas), para el contenido del modal se usaron estas APIs de Open Library, **llamadas una sola vez para poblar `libros.json`, nunca en tiempo de ejecución** (la página nunca llama a Open Library al cargar):

- **Open Library Search API**: `https://openlibrary.org/search.json?q={titulo}+{autor}` — para encontrar el `work` correspondiente a cada libro.
- **Open Library Works API**: `https://openlibrary.org/works/{id}.json` — campo `description`, usado como `sinopsis`.
- **Open Library Authors API**: `https://openlibrary.org/authors/{id}.json` — campo `bio`, usado como `autor_bio`.

### Macro `templates/modal_libro.html`

Se creó un macro Jinja2 reutilizable, `modal_libro(libro, modal_id)`, que arma un modal Bootstrap 5 completo (portada, autor, año, páginas, sinopsis y biografía del autor) a partir de un objeto `libro` y un `modal_id` único. Se importa con `{% from "modal_libro.html" import modal_libro %}` y se invoca una vez por libro dentro del `{% for %}` de cada plantilla:

- `templates/catalogo.html`: `{{ modal_libro(libro, "libroModal" ~ loop.index) }}`, con un botón "Detalles" (`data-bs-toggle="modal" data-bs-target="#libroModal{{ loop.index }}"`) por tarjeta, junto al botón "Prestar"/"Devolver" existente.
- `templates/mis_prestamos.html`: mismo patrón, con IDs `prestamoModal{{ loop.index }}`.

Todo funciona con los atributos nativos `data-bs-toggle`/`data-bs-target` de Bootstrap 5 — **cero JavaScript propio**. Se verificó estructuralmente (vía `curl` + grep) que el botón "Detalles" solo abre el modal y que los formularios `<form method="POST" action="/catalogo/prestar|devolver/{isbn}">` de "Prestar"/"Devolver" están fuera del `<div class="modal fade">` (el `</form>` cierra antes de que empiece el modal), por lo que ambas acciones son independientes y no interfieren entre sí.

### Cosas menores conocidas (no bloqueantes)

- El `autor_bio` de **Sapiens** (Yuval Noah Harari) y de **Drácula** (Bram Stoker) está vacío en el dataset (Open Library no tenía biografía para esos autores); el modal muestra el texto de respaldo "Biografía no disponible.", esto es esperado y no un bug.
- **Limpieza post-revisión (2026-08-01):** la revisión final de la rama detectó que varias `sinopsis`/`autor_bio` traían cruft crudo de Open Library que sí se renderizaba literalmente (el template no usa `|safe`): pies de página de enlaces de referencia (`[1]: http://...`), marcadores de cita `([Source][1])`/`**Source*`, divisores `----------` y listas de categorización (`Also contained in:` / `See also:`) sin valor narrativo. Se limpiaron con un script puntual en los libros de Orwell, Coelho, Kafka (ambos libros), Dostoyevski (ambos libros), King (ambos libros), Kuang (los tres libros), García Márquez y Tolkien.
- **Traducción completa al español (2026-08-01):** el usuario pidió traducir todo el contenido de `sinopsis`/`autor_bio` al español, ya que Open Library los entrega mayormente en inglés (y en el caso de Drácula, en portugués). Se tradujeron a mano los 20 libros, conservando el contenido narrativo real y quitando de paso los párrafos en otros idiomas que traía la fuente (alemán en la biografía de Kafka, ruso en la de Dostoyevski, italiano en la sinopsis de "El nombre de la rosa", portugués en la sinopsis de Drácula). Verificado que no queden artefactos de markdown (`*énfasis*`, `[enlaces]`, la palabra "source") en el archivo final.

## Estado final / entregable

- **Entregado por Dev2:** `templates/` y `static/` completos y funcionales.
- **No entregado / no corresponde a Dev2:** `preview_app.py` y `requirements.txt` son solo herramientas de desarrollo para probar la vista de forma aislada; Dev3 los reemplaza por el `app.py` real que importa las clases de Dev1 y usa los mismos nombres de endpoint.
- **Pendiente para el equipo:** Dev1 debe terminar la jerarquía `Admin`/`UsuarioRegular`, el cálculo de días de préstamo con `datetime`, y la persistencia con `json.dump` — y si agrega libros nuevos al catálogo, mantener el campo `portada` (URL de imagen) para que se vea igual de bien que los 20 libros actuales. Dev3 debe construir `app.py` con las rutas reales usando estos mismos templates.
