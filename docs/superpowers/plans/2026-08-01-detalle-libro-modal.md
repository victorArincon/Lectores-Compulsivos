# Detalle de Libro (Modal) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Al hacer clic en "Detalles" sobre cualquier libro del catálogo (o de "Mis Préstamos"), desplegar un modal de Bootstrap con: número de páginas, año de publicación, sinopsis, y una mini biografía del autor — usando datos reales obtenidos una sola vez de Open Library y guardados en `libros.json`, sin escribir JavaScript a mano.

**Architecture:** Los datos nuevos (`paginas`, `anio_publicacion`, `sinopsis`, `autor_bio`) se obtienen una única vez con un script Python que consulta las APIs públicas de Open Library (Search → Works → Authors) y se guardan como campos estáticos en `libros.json`, exactamente como se hizo antes con `portada`. La UI usa un modal de Bootstrap 5 por libro, generado con un macro Jinja2 reutilizable (`templates/modal_libro.html`), disparado por un botón "Detalles" con atributos `data-bs-toggle`/`data-bs-target` — cero JavaScript propio, todo lo maneja el bundle de Bootstrap que ya está en `static/js/bootstrap.bundle.min.js`.

**Tech Stack:** Python (`urllib.request` + `json`, ya usados para `portada`), Jinja2 macros, Bootstrap 5 modal (data attributes, sin JS custom).

## Global Constraints
- Cero JavaScript escrito a mano — todo el comportamiento del modal se apoya en atributos `data-bs-toggle="modal"` / `data-bs-target="#..."` de Bootstrap 5, ya cargado en `base.html`.
- Las llamadas a las APIs de Open Library se hacen **una sola vez** (al enriquecer `libros.json`), nunca en cada request de Flask — igual que se hizo con `portada`.
- Si un libro no tiene sinopsis o biografía disponible en Open Library, el modal debe mostrar un texto de respaldo (`"Sinopsis no disponible."` / `"Biografía no disponible."`), nunca romper la página.
- El botón "Detalles" no debe interferir con el botón "Prestar"/"Devolver" de la misma tarjeta (deben ser controles independientes, uno abre el modal, el otro envía el formulario).
- Todo dato nuevo debe documentarse en `BITACORA_DEV2.md` con la API exacta usada, para que se pueda citar en la presentación.

---

## Contexto

Ya existe `libros.json` con 20 libros, cada uno con `titulo, autor, isbn, categoria, cantidad, disponible, portada`. El campo `portada` se agregó recientemente con URLs reales de Open Library; en ese proceso se descubrió que **6 de los 20 ISBN no correspondían al libro real** (parecían ISBN de relleno de tutoriales), por lo que las portadas de esos 6 se corrigieron buscando por **título + autor** en vez de confiar en el ISBN. La misma lección aplica aquí: para pedir páginas/sinopsis/año/biografía **no se debe confiar en el ISBN**, hay que buscar por título+autor con la Open Library Search API.

Se validó el pipeline completo con 4 libros de prueba (`1984`, `El nombre de la rosa`, `Sapiens`, y confirmando el patrón `description`/`bio` a veces viene como string y a veces como `{"value": "..."}`):

1. `GET https://openlibrary.org/search.json?q={titulo}+{autor}&limit=1&fields=title,author_name,author_key,cover_i,first_publish_year,key,number_of_pages_median` → da de una sola llamada: `key` (obra, ej. `/works/OL1168083W`), `author_key` (ej. `["OL118077A"]`), `first_publish_year`, `number_of_pages_median`.
2. `GET https://openlibrary.org{key}.json` (la obra) → campo `description` (sinopsis; puede ser `str` o `{"value": "str"}` o no venir).
3. `GET https://openlibrary.org/authors/{author_key}.json` → campo `bio` (biografía; mismo formato variable, puede faltar) y `birth_date`.

Confirmado con `curl`/Python que esta cadena de 3 llamadas funciona y trae datos reales (ej. para "1984": 318 páginas, año 1949, sinopsis y biografía de Orwell completas).

## Estructura de archivos

```
Fudamento/
├── libros.json                      # se le agregan 4 campos nuevos por libro
├── codigo_libros.py                 # Libro carga los 4 campos nuevos (igual que portada)
├── preview_app.py                   # sin cambios (ya carga todo libros.json)
└── templates/
    ├── modal_libro.html             # NUEVO: macro Jinja reutilizable del modal de detalle
    ├── catalogo.html                # se agrega botón "Detalles" + import/uso del macro
    └── mis_prestamos.html           # se agrega botón "Detalles" + import/uso del macro
```

## Tareas

### Task 1: Enriquecer `libros.json` con páginas, año, sinopsis y biografía del autor

**Files:**
- Modify: `libros.json`

**Interfaces:**
- Produces: cada libro en `libros.json` gana 4 campos nuevos: `"paginas"` (int o `null`), `"anio_publicacion"` (int o `null`), `"sinopsis"` (string, `""` si no hay), `"autor_bio"` (string, `""` si no hay).

- [ ] **Paso 1: Ejecutar el script de enriquecimiento**

Ejecutar (desde la raíz del proyecto, con conexión a internet):

```bash
PYTHONIOENCODING=utf-8 python3 - <<'EOF'
import json, time, urllib.request, urllib.parse

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "LectoresCompulsivos/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def texto(campo):
    if isinstance(campo, dict):
        return campo.get("value", "") or ""
    return campo or ""

with open("libros.json", encoding="utf-8") as f:
    libros = json.load(f)

for libro in libros:
    titulo_busqueda = libro["titulo"].split(":")[0].strip()
    q = urllib.parse.quote(f"{titulo_busqueda} {libro['autor']}")
    try:
        search = fetch(f"https://openlibrary.org/search.json?q={q}&limit=1&fields=title,author_name,author_key,first_publish_year,key,number_of_pages_median")
        docs = search.get("docs", [])
        if not docs:
            print(f"SIN RESULTADOS: {libro['titulo']}")
            libro["paginas"] = None
            libro["anio_publicacion"] = None
            libro["sinopsis"] = ""
            libro["autor_bio"] = ""
            continue

        doc = docs[0]
        print(f"OK: '{libro['titulo']}' -> encontrado '{doc.get('title')}' de {doc.get('author_name')}")

        libro["paginas"] = doc.get("number_of_pages_median")
        libro["anio_publicacion"] = doc.get("first_publish_year")

        work = fetch(f"https://openlibrary.org{doc['key']}.json")
        libro["sinopsis"] = texto(work.get("description"))

        if doc.get("author_key"):
            author = fetch(f"https://openlibrary.org/authors/{doc['author_key'][0]}.json")
            libro["autor_bio"] = texto(author.get("bio"))
        else:
            libro["autor_bio"] = ""

        time.sleep(0.3)  # ser buen ciudadano de la API pública
    except Exception as e:
        print(f"ERROR con '{libro['titulo']}': {e}")
        libro.setdefault("paginas", None)
        libro.setdefault("anio_publicacion", None)
        libro.setdefault("sinopsis", "")
        libro.setdefault("autor_bio", "")

with open("libros.json", "w", encoding="utf-8") as f:
    json.dump(libros, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("\nlibros.json enriquecido.")
EOF
```

- [ ] **Paso 2: Revisar manualmente la salida impresa "OK: '...' -> encontrado '...'"**

Para cada línea, confirmar que el título encontrado en Open Library corresponde de verdad al libro esperado (misma lección del campo `portada`: algunos títulos ambiguos pueden traer el libro equivocado). Si alguno no coincide, corregirlo a mano con un script puntual como el usado para las 6 portadas incorrectas, ej.:

```python
import json
with open("libros.json", encoding="utf-8") as f:
    libros = json.load(f)
for libro in libros:
    if libro["isbn"] == "978-XXXXXXXXXX":  # el que salió mal
        libro["paginas"] = 250
        libro["anio_publicacion"] = 1950
        libro["sinopsis"] = "..."
        libro["autor_bio"] = "..."
with open("libros.json", "w", encoding="utf-8") as f:
    json.dump(libros, f, ensure_ascii=False, indent=2)
    f.write("\n")
```

- [ ] **Paso 3: Verificar que el JSON sigue siendo válido**

```bash
python3 -c "import json; libros = json.load(open('libros.json', encoding='utf-8')); print(len(libros), 'libros,', sum(1 for l in libros if l.get('sinopsis')), 'con sinopsis')"
```

Esperado: `20 libros, N con sinopsis` (N puede ser menor a 20 si algún libro no tenía datos en Open Library — está bien, el resto del plan maneja ese caso con texto de respaldo).

---

### Task 2: Cargar los campos nuevos en la clase `Libro`

**Files:**
- Modify: `codigo_libros.py`

**Interfaces:**
- Consumes: campos `paginas`, `anio_publicacion`, `sinopsis`, `autor_bio` de cada entrada de `libros.json` (Tarea 1).
- Produces: `Libro.paginas`, `Libro.anio_publicacion`, `Libro.sinopsis`, `Libro.autor_bio` — atributos disponibles para las plantillas (Tarea 3-5), igual patrón que `Libro.portada` ya existente.

- [ ] **Paso 1: Escribir la verificación**

```bash
python3 -c "
from codigo_libros import Biblioteca
b = Biblioteca('Prueba')
b.cargar_libros_desde_json('libros.json')
libro = b.catalogo[0]
assert hasattr(libro, 'paginas'), 'falta atributo paginas'
assert hasattr(libro, 'anio_publicacion'), 'falta atributo anio_publicacion'
assert hasattr(libro, 'sinopsis'), 'falta atributo sinopsis'
assert hasattr(libro, 'autor_bio'), 'falta atributo autor_bio'
print('OK, atributos presentes:', libro.paginas, libro.anio_publicacion)
"
```

- [ ] **Paso 2: Ejecutar y confirmar que falla**

Expected: `AttributeError: 'Libro' object has no attribute 'paginas'` (porque `Libro.__init__` todavía no acepta ese parámetro).

- [ ] **Paso 3: Modificar `Libro.__init__`**

Ubicación actual (ya tiene `portada` de un cambio anterior):

```python
class Libro:
    def __init__(self, titulo, autor, isbn, cantidad=0, disponible=True, portada=""):
        self.titulo = titulo
        self.autor = autor
        self.isbn = isbn
        self.cantidad = cantidad
        self.disponible = disponible
        self.portada = portada
```

Reemplazar por:

```python
class Libro:
    def __init__(self, titulo, autor, isbn, cantidad=0, disponible=True, portada="",
                 paginas=None, anio_publicacion=None, sinopsis="", autor_bio=""):
        self.titulo = titulo
        self.autor = autor
        self.isbn = isbn
        self.cantidad = cantidad
        self.disponible = disponible
        self.portada = portada
        self.paginas = paginas
        self.anio_publicacion = anio_publicacion
        self.sinopsis = sinopsis
        self.autor_bio = autor_bio
```

- [ ] **Paso 4: Modificar `cargar_libros_desde_json`**

Ubicación actual:

```python
                    nuevo_libro = Libro(
                        titulo=item['titulo'],
                        autor=item['autor'],
                        isbn=item['isbn'],
                        cantidad=item.get('cantidad', 0),
                        disponible=item.get('disponible', True),
                        portada=item.get('portada', '')
                    )
```

Reemplazar por:

```python
                    nuevo_libro = Libro(
                        titulo=item['titulo'],
                        autor=item['autor'],
                        isbn=item['isbn'],
                        cantidad=item.get('cantidad', 0),
                        disponible=item.get('disponible', True),
                        portada=item.get('portada', ''),
                        paginas=item.get('paginas'),
                        anio_publicacion=item.get('anio_publicacion'),
                        sinopsis=item.get('sinopsis', ''),
                        autor_bio=item.get('autor_bio', '')
                    )
```

- [ ] **Paso 5: Volver a ejecutar la verificación del Paso 1**

Expected: `OK, atributos presentes: 318 1949` (los valores reales dependen de lo que trajo la Tarea 1 para el primer libro del catálogo).

- [ ] **Paso 6: Confirmar que el archivo sigue sin errores de sintaxis**

```bash
python -m py_compile codigo_libros.py && echo "SIN ERRORES"
```

---

### Task 3: Crear el macro reutilizable `templates/modal_libro.html`

**Files:**
- Create: `templates/modal_libro.html`

**Interfaces:**
- Consumes: un objeto `libro` (dict u objeto `Libro`, con `.titulo .autor .paginas .anio_publicacion .sinopsis .autor_bio .portada`) y un `modal_id` (string único, ej. `"libroModal3"`).
- Produces: macro Jinja `modal_libro(libro, modal_id)` que renderiza un `<div class="modal">` completo de Bootstrap 5, importable desde cualquier template con `{% from "modal_libro.html" import modal_libro %}`.

- [ ] **Paso 1: Escribir la verificación (render con Jinja2 puro, sin levantar Flask)**

```bash
python3 -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))
tpl = env.from_string('{% from \"modal_libro.html\" import modal_libro %}{{ modal_libro(libro, \"libroModalTest\") }}')
libro = {'titulo': 'Prueba', 'autor': 'Autor X', 'paginas': 300, 'anio_publicacion': 1999, 'sinopsis': 'Una sinopsis de prueba.', 'autor_bio': 'Una bio de prueba.', 'portada': 'https://example.com/x.jpg'}
html = tpl.render(libro=libro)
assert 'libroModalTest' in html
assert 'Una sinopsis de prueba.' in html
assert 'Una bio de prueba.' in html
assert '300 páginas' in html
print('OK, macro renderiza correctamente')
"
```

- [ ] **Paso 2: Ejecutar y confirmar que falla**

Expected: `jinja2.exceptions.TemplateNotFound: modal_libro.html` (el archivo todavía no existe).

- [ ] **Paso 3: Crear `templates/modal_libro.html`**

```jinja
{% macro modal_libro(libro, modal_id) %}
<div class="modal fade" id="{{ modal_id }}" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content">
            <div class="modal-header border-secondary-subtle">
                <h5 class="modal-title">{{ libro.titulo }}</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Cerrar"></button>
            </div>
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-4">
                        {% if libro.portada %}
                        <img src="{{ libro.portada }}" class="img-fluid rounded" alt="Portada de {{ libro.titulo }}">
                        {% endif %}
                    </div>
                    <div class="col-8">
                        <p class="mb-1"><strong>Autor:</strong> {{ libro.autor }}</p>
                        <p class="mb-1">
                            <strong>Año de publicación:</strong>
                            {{ libro.anio_publicacion if libro.anio_publicacion else "No disponible" }}
                        </p>
                        <p class="mb-1">
                            <strong>Páginas:</strong>
                            {{ (libro.paginas ~ " páginas") if libro.paginas else "No disponible" }}
                        </p>
                    </div>
                </div>
                <hr class="border-secondary-subtle">
                <h6>Sinopsis</h6>
                <p class="small">{{ libro.sinopsis if libro.sinopsis else "Sinopsis no disponible." }}</p>
                <h6>Sobre {{ libro.autor }}</h6>
                <p class="small">{{ libro.autor_bio if libro.autor_bio else "Biografía no disponible." }}</p>
            </div>
            <div class="modal-footer border-secondary-subtle">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
            </div>
        </div>
    </div>
</div>
{% endmacro %}
```

- [ ] **Paso 4: Volver a ejecutar la verificación del Paso 1**

Expected: `OK, macro renderiza correctamente`

---

### Task 4: Integrar el modal en `templates/catalogo.html`

**Files:**
- Modify: `templates/catalogo.html`

**Interfaces:**
- Consumes: `modal_libro(libro, modal_id)` de la Tarea 3.

- [ ] **Paso 1: Importar el macro y agregar el botón "Detalles" + el modal dentro del `{% for %}` existente**

Ubicación actual (dentro de `{% block content %}`, justo después de `{% extends "base.html" %}`):

```jinja
{% extends "base.html" %}

{% block title %}Catálogo{% endblock %}
{% block heading %}Catálogo de Libros{% endblock %}

{% block content %}
```

Agregar el import justo debajo del `{% block content %}`:

```jinja
{% extends "base.html" %}

{% block title %}Catálogo{% endblock %}
{% block heading %}Catálogo de Libros{% endblock %}

{% block content %}
{% from "modal_libro.html" import modal_libro %}
```

Dentro del `{% for libro in libros %}`, dentro de `<div class="card-body ...">`, agregar el botón "Detalles" antes del bloque `<div class="mt-auto">` que ya tiene Prestar/Devolver, y el modal justo después de cerrar el `<div class="card">` (mismo nivel que `</div>` del `.col`):

```jinja
                <p class="card-text small mb-2">
                    {% if libro.disponible %}
                    <span class="badge text-bg-success">Disponible</span>
                    {% else %}
                    <span class="badge text-bg-danger">Agotado</span>
                    {% endif %}
                    <span class="text-secondary">· {{ libro.cantidad }} en stock</span>
                </p>
                <button type="button" class="btn btn-outline-info btn-sm mb-2" data-bs-toggle="modal" data-bs-target="#libroModal{{ loop.index }}">
                    Detalles
                </button>
                <div class="mt-auto">
                    {% if libro.disponible %}
                    <form method="POST" action="{{ url_for('prestar', isbn=libro.isbn) }}">
                        <button type="submit" class="btn btn-primary btn-sm w-100">Prestar</button>
                    </form>
                    {% else %}
                    <form method="POST" action="{{ url_for('devolver', isbn=libro.isbn) }}">
                        <button type="submit" class="btn btn-outline-secondary btn-sm w-100">Devolver</button>
                    </form>
                    {% endif %}
                </div>
            </div>
        </div>
        {{ modal_libro(libro, "libroModal" ~ loop.index) }}
    </div>
    {% endfor %}
```

(El `{{ modal_libro(...) }}` va **fuera** de `<div class="card">` pero todavía dentro de `<div class="col">`, antes de `{% endfor %}` — así cada libro tiene su propio modal con un `id` único `libroModal1`, `libroModal2`, etc.)

- [ ] **Paso 2: Verificar con `curl` que las 20 tarjetas traen su botón y su modal**

Con el servidor de preview corriendo (`python preview_app.py`):

```bash
curl -s http://127.0.0.1:5000/catalogo | grep -c "data-bs-toggle=\"modal\""
curl -s http://127.0.0.1:5000/catalogo | grep -c "class=\"modal fade\" id=\"libroModal"
```

Expected: ambos comandos devuelven `20`.

- [ ] **Paso 3: Verificación visual en el navegador**

Abrir `http://127.0.0.1:5000/catalogo`, hacer clic en "Detalles" de 2-3 libros distintos y confirmar que el modal muestra título, autor, año, páginas, sinopsis y biografía correctos para cada uno — y que el botón "Prestar"/"Devolver" de la misma tarjeta sigue funcionando por separado (no abre el modal).

---

### Task 5: Integrar el modal en `templates/mis_prestamos.html`

**Files:**
- Modify: `templates/mis_prestamos.html`

**Interfaces:**
- Consumes: `modal_libro(libro, modal_id)` de la Tarea 3 (mismo macro, sin duplicar código).

- [ ] **Paso 1: Aplicar el mismo patrón de la Tarea 4**

Ubicación actual:

```jinja
{% extends "base.html" %}

{% block title %}Mis Préstamos{% endblock %}
{% block heading %}Mis Préstamos{% endblock %}

{% block content %}
<div class="row row-cols-2 row-cols-md-3 row-cols-lg-4 g-4">
    {% for libro in libros_prestados %}
```

Agregar el import y el botón + modal:

```jinja
{% extends "base.html" %}

{% block title %}Mis Préstamos{% endblock %}
{% block heading %}Mis Préstamos{% endblock %}

{% block content %}
{% from "modal_libro.html" import modal_libro %}
<div class="row row-cols-2 row-cols-md-3 row-cols-lg-4 g-4">
    {% for libro in libros_prestados %}
    <div class="col">
        <div class="card book-card border-secondary-subtle">
            {% if libro.portada %}
            <img class="book-cover-img" src="{{ libro.portada }}" alt="Portada de {{ libro.titulo }}">
            {% else %}
            <div class="book-cover cover-{{ loop.index0 % 6 }}">
                {{ libro.titulo }}
            </div>
            {% endif %}
            <div class="card-body d-flex flex-column">
                <h6 class="card-title mb-1">{{ libro.titulo }}</h6>
                <p class="card-text text-secondary small mb-2">{{ libro.autor }}</p>
                <button type="button" class="btn btn-outline-info btn-sm mb-2" data-bs-toggle="modal" data-bs-target="#prestamoModal{{ loop.index }}">
                    Detalles
                </button>
                <div class="mt-auto">
                    <form method="POST" action="{{ url_for('devolver', isbn=libro.isbn) }}">
                        <button type="submit" class="btn btn-outline-secondary btn-sm w-100">Devolver</button>
                    </form>
                </div>
            </div>
        </div>
        {{ modal_libro(libro, "prestamoModal" ~ loop.index) }}
    </div>
    {% else %}
    <div class="col-12">
        <p class="text-secondary text-center">No tienes libros prestados actualmente.</p>
    </div>
    {% endfor %}
</div>
{% endblock %}
```

(Se usa el prefijo `prestamoModal` en vez de `libroModal` para que los `id` nunca choquen si algún día ambas vistas se combinan en una sola página.)

- [ ] **Paso 2: Verificar con `curl`**

```bash
curl -s http://127.0.0.1:5000/mis-prestamos | grep -c "data-bs-toggle=\"modal\""
```

Expected: `2` (con los datos de prueba actuales de `preview_app.py`, que muestra 2 libros prestados).

---

### Task 6: Verificación visual manual end-to-end y actualización de la bitácora

**Files:**
- Modify: `BITACORA_DEV2.md`

- [ ] **Paso 1: Reiniciar el servidor de preview**

```bash
python preview_app.py
```

- [ ] **Paso 2: Recorrido manual completo**

- Abrir `/catalogo`, hacer clic en "Detalles" de al menos 3 libros distintos (uno con sinopsis/bio completas, uno de los que tenía ISBN corregido, y uno de los 5 que no tenían portada por ISBN) y confirmar que cada modal muestra su propia información, no la de otro libro.
- Confirmar que "Prestar"/"Devolver" siguen funcionando sin abrir el modal por accidente.
- Abrir `/mis-prestamos` y repetir la prueba de "Detalles" ahí.

- [ ] **Paso 3: Agregar una sección a `BITACORA_DEV2.md`** documentando:
  - Los campos nuevos agregados a `libros.json` (`paginas`, `anio_publicacion`, `sinopsis`, `autor_bio`).
  - Las APIs exactas usadas: Open Library Search API (`https://openlibrary.org/search.json`), Open Library Works API (`https://openlibrary.org/works/{id}.json`), Open Library Authors API (`https://openlibrary.org/authors/{id}.json`), con nota de que se llamaron una sola vez para poblar el JSON.
  - El nuevo macro `templates/modal_libro.html` y cómo se integró en `catalogo.html` y `mis_prestamos.html` sin JavaScript propio.

---

## Coordinación con el equipo

- Los 4 campos nuevos (`paginas`, `anio_publicacion`, `sinopsis`, `autor_bio`) son opcionales con valores por defecto (`None`/`""`) tanto en `Libro.__init__` como en las plantillas — si Dev1 agrega un libro nuevo sin estos campos, la página no se rompe, solo muestra "No disponible" / "Sinopsis no disponible.".
- No se toca `preview_app.py` ni se agregan rutas Flask nuevas — todo el modal es contenido estático renderizado por Jinja2, así que no hay nada nuevo que Dev3 tenga que conectar además de lo que ya sabía (mismos endpoints `catalogo`/`mis_prestamos`).
