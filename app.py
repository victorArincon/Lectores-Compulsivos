'''version 1
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session

from codigo_libros import Libro, Usuario, Biblioteca

app = Flask(__name__)

#Clave aleatoria para forzar login al reiniciar el servidor
app.secret_key = os.urandom(24)
app.config["Sesion permanete"] = False

biblioteca = Biblioteca("Lectores Compulsivos")

#Usuarios vaalidos para iniciar sesion
USUARIOS_VALIDOS = {
    "U001": "1234",
    "alumno": "password"
}

# CONTROL DE CACHÉ

@app.after_request
def add_header(response):
    """Evita que el navegador guarde la página en memoria caché"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



# FUNCIONES AUXILIARES
def obtener_o_crear_usuario_actual():
    """Obtiene o crea el objeto Usuario en la biblioteca usando la sesión"""
    if "usuario_id" not in session:
        return None
    
    usuario_id = session["usuario_id"]
    usuario = biblioteca.buscar_usuario(usuario_id)
    
    if not usuario:
        nombre = session.get("usuario_nombre", usuario_id)
        usuario = Usuario(nombre, usuario_id)
        biblioteca.agregar_usuario(usuario)
        
    return usuario


def asegurar_portadas_y_guardar():
    """Guarda el catálogo en libros.json manteniendo la lista de préstamos activos y stock"""
    lista_datos = []
    for libro in biblioteca.catalogo:
        portada_val = getattr(libro, 'portada', getattr(libro, 'imagen', ''))
        
        prestados_lista = getattr(libro, 'prestado_a', [])
        if isinstance(prestados_lista, str):
            prestados_lista = [prestados_lista] if prestados_lista else []

        lista_datos.append({
            "titulo": libro.titulo,
            "autor": libro.autor,
            "isbn": libro.isbn,
            "cantidad": libro.cantidad,
            "disponible": libro.disponible,
            "portada": portada_val,
            "prestado_a": prestados_lista,
            "anio_publicacion": getattr(libro, 'anio_publicacion', None),
            "paginas": getattr(libro, 'paginas', None),
            "sinopsis": getattr(libro, 'sinopsis', ''),
            "autor_bio": getattr(libro, 'autor_bio', '')
        })
        
    with open("libros.json", "w", encoding="utf-8") as f:
        json.dump(lista_datos, f, ensure_ascii=False, indent=2)


#RUTAS DE LA APLICACIÓN
@app.route("/", methods=["GET"])
def index():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("catalogo"))


@app.route("/catalogo", methods=["GET"])
def catalogo():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))
        
    return render_template(
        "catalogo.html", 
        libros=biblioteca.catalogo, 
        usuario_actual=usuario.nombre
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario_input = request.form.get("usuario", "").strip()
        password_input = request.form.get("password", "").strip()

        if usuario_input in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usuario_input] == password_input:
            session.clear()
            session["usuario_id"] = usuario_input
            session["usuario_nombre"] = usuario_input.capitalize()
            
            usuario = biblioteca.buscar_usuario(usuario_input)
            if not usuario:
                usuario = Usuario(session["usuario_nombre"], usuario_input)
                biblioteca.agregar_usuario(usuario)
                
            return redirect(url_for("catalogo"))
        else:
            error = "Usuario o contraseña incorrectos. (Prueba: U001 / 1234)"
        
    return render_template("login.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/mis-prestamos", methods=["GET"])
@app.route("/mis_prestamos", methods=["GET"])
def mis_prestamos():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))
        
    uid = session.get("usuario_id")
    libros_prestados = []

    for libro in biblioteca.catalogo:
        prestados = getattr(libro, 'prestado_a', [])
        if isinstance(prestados, list):
            cant_prestada = prestados.count(uid)
            for _ in range(cant_prestada):
                libros_prestados.append(libro)
        elif prestados == uid:
            libros_prestados.append(libro)
        
    return render_template(
        "mis_prestamos.html", 
        libros_prestados=libros_prestados,
        usuario_actual=usuario.nombre
    )


@app.route("/prestar/<string:isbn>", methods=["POST"])
def prestar(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    
    if libro and libro.cantidad > 0:
        libro.cantidad -= 1
        if libro.cantidad == 0:
            libro.disponible = False

        if not hasattr(libro, 'prestado_a') or not isinstance(libro.prestado_a, list):
            libro.prestado_a = []
        libro.prestado_a.append(session["usuario_id"])

        if libro not in usuario.libros_prestados:
            usuario.libros_prestados.append(libro)

    asegurar_portadas_y_guardar()
    return redirect(url_for("catalogo"))


@app.route("/devolver/<string:isbn>", methods=["POST"])
def devolver(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    
    if libro and hasattr(libro, 'prestado_a') and isinstance(libro.prestado_a, list):
        if uid in libro.prestado_a:
            #Quitar el préstamo de la lista
            libro.prestado_a.remove(uid)
            #Devolver la copia al stock
            libro.cantidad += 1
            libro.disponible = True
            
            #Limpiar el objeto usuario si ya no le quedan copias de este libro
            if uid not in libro.prestado_a and libro in usuario.libros_prestados:
                usuario.libros_prestados.remove(libro)

    asegurar_portadas_y_guardar()
    return redirect(url_for("mis_prestamos"))



# EJECUCIÓN E INICIALIZACIÓN
if __name__ == "__main__":
    biblioteca.cargar_libros_desde_json("libros.json")
    
    try:
        with open("libros.json", "r", encoding="utf-8") as f:
            datos_json = json.load(f)
            
        for libro_obj in biblioteca.catalogo:
            datos = next((d for d in datos_json if d.get("isbn") == libro_obj.isbn), {})
            setattr(libro_obj, 'portada', datos.get("portada", getattr(libro_obj, 'imagen', '')))
            
            # Cargar préstamos de forma persistente y sincronizar stock al arrancar
            prestados = datos.get("prestado_a", [])
            if isinstance(prestados, str):
                prestados = [prestados] if prestados else []
            
            setattr(libro_obj, 'prestado_a', prestados)
            libro_obj.cantidad = datos.get("cantidad", 3)
            libro_obj.disponible = datos.get("disponible", True)

            # Sincronizar usuarios con préstamos activos
            for uid in prestados:
                usr = biblioteca.buscar_usuario(uid)
                if not usr:
                    usr = Usuario(uid.capitalize(), uid)
                    biblioteca.agregar_usuario(usr)
                if libro_obj not in usr.libros_prestados:
                    usr.libros_prestados.append(libro_obj)

    except Exception as e:
        print(f"Aviso al cargar estado previo: {e}")

    app.run(debug=True, port=5000)'''

'''version 2 

import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from codigo_libros import Libro, Usuario, Biblioteca

app = Flask(__name__)

# Clave fija para que no se cierren las sesiones al reiniciar el servidor
app.secret_key = "clave_secreta_fija_lectores_compulsivos"
app.config["Sesion permanete"] = False

biblioteca = Biblioteca("Lectores Compulsivos")
ARCHIVO_USUARIOS = "usuarios.json"


# FUNCIONES DE GESTIÓN DE USUARIOS EN JSON
def cargar_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        admin_default = {
            "admin": {
                "nombre": "Administrador Principal",
                "password": generate_password_hash("admin123"),
                "is_admin": True
            }
        }
        guardar_usuarios(admin_default)
        return admin_default
        
    with open(ARCHIVO_USUARIOS, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_usuarios(usuarios):
    with open(ARCHIVO_USUARIOS, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=4)


# CONTROL DE CACHÉ
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# FUNCIONES AUXILIARES
def obtener_o_crear_usuario_actual():
    if "usuario_id" not in session:
        return None
    
    usuario_id = session["usuario_id"]
    usuario = biblioteca.buscar_usuario(usuario_id)
    
    if not usuario:
        nombre = session.get("usuario_nombre", usuario_id)
        usuario = Usuario(nombre, usuario_id)
        biblioteca.agregar_usuario(usuario)
        
    return usuario


def asegurar_portadas_y_guardar():
    lista_datos = []
    for libro in biblioteca.catalogo:
        portada_val = getattr(libro, 'portada', getattr(libro, 'imagen', ''))
        
        prestados_lista = getattr(libro, 'prestado_a', [])
        if isinstance(prestados_lista, str):
            prestados_lista = [prestados_lista] if prestados_lista else []

        lista_datos.append({
            "titulo": libro.titulo,
            "autor": libro.autor,
            "isbn": libro.isbn,
            "cantidad": libro.cantidad,
            "disponible": libro.disponible,
            "portada": portada_val,
            "prestado_a": prestados_lista,
            "anio_publicacion": getattr(libro, 'anio_publicacion', None),
            "paginas": getattr(libro, 'paginas', None),
            "sinopsis": getattr(libro, 'sinopsis', ''),
            "autor_bio": getattr(libro, 'autor_bio', '')
        })
        
    with open("libros.json", "w", encoding="utf-8") as f:
        json.dump(lista_datos, f, ensure_ascii=False, indent=2)


# RUTAS DE LA APLICACIÓN
@app.route("/", methods=["GET"])
def index():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("catalogo"))


@app.route("/catalogo", methods=["GET"])
def catalogo():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))
        
    return render_template(
        "catalogo.html", 
        libros=biblioteca.catalogo, 
        usuario_actual=usuario.nombre
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario_input = request.form.get("usuario", "").strip()
        password_input = request.form.get("password", "").strip()

        usuarios_db = cargar_usuarios()

        if usuario_input in usuarios_db and check_password_hash(usuarios_db[usuario_input]["password"], password_input):
            session.clear()
            session["usuario_id"] = usuario_input
            session["usuario_nombre"] = usuarios_db[usuario_input]["nombre"]
            session["is_admin"] = usuarios_db[usuario_input].get("is_admin", False)
            
            usuario = biblioteca.buscar_usuario(usuario_input)
            if not usuario:
                usuario = Usuario(session["usuario_nombre"], usuario_input)
                biblioteca.agregar_usuario(usuario)
                
            return redirect(url_for("catalogo"))
        else:
            error = "Usuario o contraseña incorrectos."
        
    return render_template("login.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/crear_usuario", methods=["GET", "POST"])
def crear_usuario():
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado. Solo administradores pueden ver esto.", 403

    mensaje = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        nombre = request.form.get("nombre", "").strip()
        password = request.form.get("password", "").strip()
        is_admin = request.form.get("is_admin") == "on"

        usuarios_db = cargar_usuarios()

        if username in usuarios_db:
            mensaje = {"tipo": "danger", "texto": "El nombre de usuario ya existe."}
        elif not username or not password or not nombre:
            mensaje = {"tipo": "warning", "texto": "Todos los campos de texto son obligatorios."}
        else:
            usuarios_db[username] = {
                "nombre": nombre,
                "password": generate_password_hash(password),
                "is_admin": is_admin
            }
            guardar_usuarios(usuarios_db)
            mensaje = {"tipo": "success", "texto": f"Usuario '{username}' creado exitosamente."}

    return render_template("crear_usuario.html", mensaje=mensaje)


@app.route("/mis-prestamos", methods=["GET"])
@app.route("/mis_prestamos", methods=["GET"])
def mis_prestamos():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))
        
    uid = session.get("usuario_id")
    libros_prestados = []

    for libro in biblioteca.catalogo:
        prestados = getattr(libro, 'prestado_a', [])
        if isinstance(prestados, list):
            cant_prestada = prestados.count(uid)
            for _ in range(cant_prestada):
                libros_prestados.append(libro)
        elif prestados == uid:
            libros_prestados.append(libro)
        
    return render_template(
        "mis_prestamos.html", 
        libros_prestados=libros_prestados,
        usuario_actual=usuario.nombre
    )


@app.route("/prestar/<string:isbn>", methods=["POST"])
def prestar(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    
    if libro and libro.cantidad > 0:
        libro.cantidad -= 1
        if libro.cantidad == 0:
            libro.disponible = False

        if not hasattr(libro, 'prestado_a') or not isinstance(libro.prestado_a, list):
            libro.prestado_a = []
        libro.prestado_a.append(session["usuario_id"])

        if libro not in usuario.libros_prestados:
            usuario.libros_prestados.append(libro)

    asegurar_portadas_y_guardar()
    return redirect(url_for("catalogo"))


@app.route("/devolver/<string:isbn>", methods=["POST"])
def devolver(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    
    if libro and hasattr(libro, 'prestado_a') and isinstance(libro.prestado_a, list):
        if uid in libro.prestado_a:
            libro.prestado_a.remove(uid)
            libro.cantidad += 1
            libro.disponible = True
            
            if uid not in libro.prestado_a and libro in usuario.libros_prestados:
                usuario.libros_prestados.remove(libro)

    asegurar_portadas_y_guardar()
    return redirect(url_for("mis_prestamos"))


# EJECUCIÓN E INICIALIZACIÓN
if __name__ == "__main__":
    biblioteca.cargar_libros_desde_json("libros.json")
    
    try:
        with open("libros.json", "r", encoding="utf-8") as f:
            datos_json = json.load(f)
            
        for libro_obj in biblioteca.catalogo:
            datos = next((d for d in datos_json if d.get("isbn") == libro_obj.isbn), {})
            setattr(libro_obj, 'portada', datos.get("portada", getattr(libro_obj, 'imagen', '')))
            
            prestados = datos.get("prestado_a", [])
            if isinstance(prestados, str):
                prestados = [prestados] if prestados else []
            
            setattr(libro_obj, 'prestado_a', prestados)
            libro_obj.cantidad = datos.get("cantidad", 3)
            libro_obj.disponible = datos.get("disponible", True)

            for uid in prestados:
                usr = biblioteca.buscar_usuario(uid)
                if not usr:
                    usr = Usuario(uid.capitalize(), uid)
                    biblioteca.agregar_usuario(usr)
                if libro_obj not in usr.libros_prestados:
                    usr.libros_prestados.append(libro_obj)

    except Exception as e:
        print(f"Aviso al cargar estado previo: {e}")

    app.run(debug=True, port=5000)'''

'''version3
import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from codigo_libros import Libro, Usuario, Biblioteca

app = Flask(__name__)

# Clave fija para que no se cierren las sesiones al reiniciar el servidor
app.secret_key = "clave_secreta_fija_lectores_compulsivos"
app.config["Sesion permanete"] = False

biblioteca = Biblioteca("Lectores Compulsivos")
ARCHIVO_USUARIOS = "usuarios.json"


# FUNCIONES DE GESTIÓN DE USUARIOS EN JSON
def cargar_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        admin_default = {
            "admin": {
                "nombre": "Administrador Principal",
                "password": generate_password_hash("admin123"),
                "is_admin": True
            }
        }
        guardar_usuarios(admin_default)
        return admin_default
        
    with open(ARCHIVO_USUARIOS, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_usuarios(usuarios):
    with open(ARCHIVO_USUARIOS, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=4)


# CONTROL DE CACHÉ
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# FUNCIONES AUXILIARES
def obtener_o_crear_usuario_actual():
    if "usuario_id" not in session:
        return None
    
    usuario_id = session["usuario_id"]
    usuario = biblioteca.buscar_usuario(usuario_id)
    
    if not usuario:
        nombre = session.get("usuario_nombre", usuario_id)
        usuario = Usuario(nombre, usuario_id)
        biblioteca.agregar_usuario(usuario)
        
    return usuario


def asegurar_portadas_y_guardar():
    lista_datos = []
    for libro in biblioteca.catalogo:
        portada_val = getattr(libro, 'portada', getattr(libro, 'imagen', ''))
        
        prestados_lista = getattr(libro, 'prestado_a', [])
        if isinstance(prestados_lista, str):
            prestados_lista = [prestados_lista] if prestados_lista else []

        lista_datos.append({
            "titulo": libro.titulo,
            "autor": libro.autor,
            "isbn": libro.isbn,
            "cantidad": libro.cantidad,
            "disponible": libro.disponible,
            "portada": portada_val,
            "prestado_a": prestados_lista,
            "anio_publicacion": getattr(libro, 'anio_publicacion', None),
            "paginas": getattr(libro, 'paginas', None),
            "sinopsis": getattr(libro, 'sinopsis', ''),
            "autor_bio": getattr(libro, 'autor_bio', '')
        })
        
    with open("libros.json", "w", encoding="utf-8") as f:
        json.dump(lista_datos, f, ensure_ascii=False, indent=2)


# RUTAS DE LA APLICACIÓN
@app.route("/", methods=["GET"])
def index():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("catalogo"))


@app.route("/catalogo", methods=["GET"])
def catalogo():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))
        
    return render_template(
        "catalogo.html", 
        libros=biblioteca.catalogo, 
        usuario_actual=usuario.nombre
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario_input = request.form.get("usuario", "").strip()
        password_input = request.form.get("password", "").strip()

        usuarios_db = cargar_usuarios()

        if usuario_input in usuarios_db and check_password_hash(usuarios_db[usuario_input]["password"], password_input):
            session.clear()
            session["usuario_id"] = usuario_input
            session["usuario_nombre"] = usuarios_db[usuario_input]["nombre"]
            session["is_admin"] = usuarios_db[usuario_input].get("is_admin", False)
            
            usuario = biblioteca.buscar_usuario(usuario_input)
            if not usuario:
                usuario = Usuario(session["usuario_nombre"], usuario_input)
                biblioteca.agregar_usuario(usuario)
                
            return redirect(url_for("catalogo"))
        else:
            error = "Usuario o contraseña incorrectos."
        
    return render_template("login.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/crear_usuario", methods=["GET", "POST"])
def crear_usuario():
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado. Solo administradores pueden ver esto.", 403

    mensaje = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        nombre = request.form.get("nombre", "").strip()
        password = request.form.get("password", "").strip()
        is_admin = request.form.get("is_admin") == "on"

        usuarios_db = cargar_usuarios()

        if username in usuarios_db:
            mensaje = {"tipo": "danger", "texto": "El nombre de usuario ya existe."}
        elif not username or not password or not nombre:
            mensaje = {"tipo": "warning", "texto": "Todos los campos de texto son obligatorios."}
        else:
            usuarios_db[username] = {
                "nombre": nombre,
                "password": generate_password_hash(password),
                "is_admin": is_admin
            }
            guardar_usuarios(usuarios_db)
            mensaje = {"tipo": "success", "texto": f"Usuario '{username}' creado exitosamente."}

    return render_template("crear_usuario.html", mensaje=mensaje)


@app.route("/mis-prestamos", methods=["GET"])
@app.route("/mis_prestamos", methods=["GET"])
def mis_prestamos():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))
        
    uid = session.get("usuario_id")
    libros_prestados = []

    for libro in biblioteca.catalogo:
        prestados = getattr(libro, 'prestado_a', [])
        if isinstance(prestados, list):
            cant_prestada = prestados.count(uid)
            for _ in range(cant_prestada):
                libros_prestados.append(libro)
        elif prestados == uid:
            libros_prestados.append(libro)
        
    return render_template(
        "mis_prestamos.html", 
        libros_prestados=libros_prestados,
        usuario_actual=usuario.nombre
    )


@app.route("/prestar/<string:isbn>", methods=["POST"])
def prestar(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    
    # VALIDACIÓN: Si el usuario ya está en la lista de préstamos de este libro, lo bloqueamos
    if libro and hasattr(libro, 'prestado_a') and isinstance(libro.prestado_a, list):
        if uid in libro.prestado_a:
            flash("Ya tienes una copia de este libro. No puedes pedir el mismo dos veces.", "warning")
            return redirect(url_for("catalogo"))
    
    if libro and libro.cantidad > 0:
        libro.cantidad -= 1
        if libro.cantidad == 0:
            libro.disponible = False

        if not hasattr(libro, 'prestado_a') or not isinstance(libro.prestado_a, list):
            libro.prestado_a = []
        libro.prestado_a.append(uid)

        if libro not in usuario.libros_prestados:
            usuario.libros_prestados.append(libro)
            
        flash(f"Has pedido prestado '{libro.titulo}' con éxito.", "success")

    asegurar_portadas_y_guardar()
    return redirect(url_for("catalogo"))


@app.route("/devolver/<string:isbn>", methods=["POST"])
def devolver(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    
    if libro and hasattr(libro, 'prestado_a') and isinstance(libro.prestado_a, list):
        if uid in libro.prestado_a:
            libro.prestado_a.remove(uid)
            libro.cantidad += 1
            libro.disponible = True
            
            if uid not in libro.prestado_a and libro in usuario.libros_prestados:
                usuario.libros_prestados.remove(libro)
                
            flash(f"Has devuelto '{libro.titulo}' con éxito.", "success")

    asegurar_portadas_y_guardar()
    return redirect(url_for("mis_prestamos"))


# EJECUCIÓN E INICIALIZACIÓN
if __name__ == "__main__":
    biblioteca.cargar_libros_desde_json("libros.json")
    
    try:
        with open("libros.json", "r", encoding="utf-8") as f:
            datos_json = json.load(f)
            
        for libro_obj in biblioteca.catalogo:
            datos = next((d for d in datos_json if d.get("isbn") == libro_obj.isbn), {})
            setattr(libro_obj, 'portada', datos.get("portada", getattr(libro_obj, 'imagen', '')))
            
            prestados = datos.get("prestado_a", [])
            if isinstance(prestados, str):
                prestados = [prestados] if prestados else []
            
            setattr(libro_obj, 'prestado_a', prestados)
            libro_obj.cantidad = datos.get("cantidad", 3)
            libro_obj.disponible = datos.get("disponible", True)

            for uid in prestados:
                usr = biblioteca.buscar_usuario(uid)
                if not usr:
                    usr = Usuario(uid.capitalize(), uid)
                    biblioteca.agregar_usuario(usr)
                if libro_obj not in usr.libros_prestados:
                    usr.libros_prestados.append(libro_obj)

    except Exception as e:
        print(f"Aviso al cargar estado previo: {e}")

    app.run(debug=True, port=5000)'''

import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from codigo_libros import Libro, Usuario, Biblioteca

app = Flask(__name__)

# Clave fija para las sesiones
app.secret_key = "clave_secreta_fija_lectores_compulsivos"
app.config["Sesion permanete"] = False

biblioteca = Biblioteca("Lectores Compulsivos")

# --- RUTAS ABSOLUTAS PARA VERCEL Y LOCAL ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ARCHIVO_USUARIOS = os.path.join(BASE_DIR, "usuarios.json")
ARCHIVO_LIBROS = os.path.join(BASE_DIR, "libros.json")


# FUNCIONES DE GESTIÓN DE USUARIOS EN JSON
def cargar_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        admin_default = {
            "admin": {
                "nombre": "Administrador Principal",
                "password": generate_password_hash("admin123"),
                "is_admin": True
            }
        }
        guardar_usuarios(admin_default)
        return admin_default
        
    with open(ARCHIVO_USUARIOS, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_usuarios(usuarios):
    try:
        with open(ARCHIVO_USUARIOS, "w", encoding="utf-8") as f:
            json.dump(usuarios, f, ensure_ascii=False, indent=4)
    except OSError:
        # En entornos de solo lectura como Vercel, evitamos que crashee si intenta escribir
        pass


# CONTROL DE CACHÉ
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# FUNCIONES AUXILIARES
def obtener_o_crear_usuario_actual():
    if "usuario_id" not in session:
        return None
    
    usuario_id = session["usuario_id"]
    usuario = biblioteca.buscar_usuario(usuario_id)
    
    if not usuario:
        nombre = session.get("usuario_nombre", usuario_id)
        usuario = Usuario(nombre, usuario_id)
        biblioteca.agregar_usuario(usuario)
        
    return usuario


def asegurar_portadas_y_guardar():
    lista_datos = []
    for libro in biblioteca.catalogo:
        portada_val = getattr(libro, 'portada', getattr(libro, 'imagen', ''))
        
        prestados_lista = getattr(libro, 'prestado_a', [])
        if isinstance(prestados_lista, str):
            prestados_lista = [prestados_lista] if prestados_lista else []

        lista_datos.append({
            "titulo": libro.titulo,
            "autor": libro.autor,
            "isbn": libro.isbn,
            "cantidad": libro.cantidad,
            "disponible": libro.disponible,
            "portada": portada_val,
            "prestado_a": prestados_lista,
            "anio_publicacion": getattr(libro, 'anio_publicacion', None),
            "paginas": getattr(libro, 'paginas', None),
            "sinopsis": getattr(libro, 'sinopsis', ''),
            "autor_bio": getattr(libro, 'autor_bio', '')
        })
        
    try:
        with open(ARCHIVO_LIBROS, "w", encoding="utf-8") as f:
            json.dump(lista_datos, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# --- CARGA INICIAL (EJECUTADA SIEMPRE AL ARRANCAR, NO SOLO EN LOCAL) ---
def inicializar_biblioteca():
    if os.path.exists(ARCHIVO_LIBROS):
        biblioteca.cargar_libros_desde_json(ARCHIVO_LIBROS)
        try:
            with open(ARCHIVO_LIBROS, "r", encoding="utf-8") as f:
                datos_json = json.load(f)
                
            for libro_obj in biblioteca.catalogo:
                datos = next((d for d in datos_json if d.get("isbn") == libro_obj.isbn), {})
                setattr(libro_obj, 'portada', datos.get("portada", getattr(libro_obj, 'imagen', '')))
                
                prestados = datos.get("prestado_a", [])
                if isinstance(prestados, str):
                    prestados = [prestados] if prestados else []
                
                setattr(libro_obj, 'prestado_a', prestados)
                libro_obj.cantidad = datos.get("cantidad", 3)
                libro_obj.disponible = datos.get("disponible", True)

                for uid in prestados:
                    usr = biblioteca.buscar_usuario(uid)
                    if not usr:
                        usr = Usuario(uid.capitalize(), uid)
                        biblioteca.agregar_usuario(usr)
                    if libro_obj not in usr.libros_prestados:
                        usr.libros_prestados.append(libro_obj)
        except Exception as e:
            print(f"Aviso al cargar estado previo: {e}")

# Llamamos a la inicialización al arrancar la app para que Vercel cargue los libros
inicializar_biblioteca()


# RUTAS DE LA APLICACIÓN
@app.route("/", methods=["GET"])
def index():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("catalogo"))


@app.route("/catalogo", methods=["GET"])
def catalogo():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))
        
    return render_template(
        "catalogo.html", 
        libros=biblioteca.catalogo, 
        usuario_actual=usuario.nombre
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario_input = request.form.get("usuario", "").strip()
        password_input = request.form.get("password", "").strip()

        usuarios_db = cargar_usuarios()

        if usuario_input in usuarios_db and check_password_hash(usuarios_db[usuario_input]["password"], password_input):
            session.clear()
            session["usuario_id"] = usuario_input
            session["usuario_nombre"] = usuarios_db[usuario_input]["nombre"]
            session["is_admin"] = usuarios_db[usuario_input].get("is_admin", False)
            
            usuario = biblioteca.buscar_usuario(usuario_input)
            if not usuario:
                usuario = Usuario(session["usuario_nombre"], usuario_input)
                biblioteca.agregar_usuario(usuario)
                
            return redirect(url_for("catalogo"))
        else:
            error = "Usuario o contraseña incorrectos."
        
    return render_template("login.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/crear_usuario", methods=["GET", "POST"])
def crear_usuario():
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado. Solo administradores pueden ver esto.", 403

    mensaje = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        nombre = request.form.get("nombre", "").strip()
        password = request.form.get("password", "").strip()
        is_admin = request.form.get("is_admin") == "on"

        usuarios_db = cargar_usuarios()

        if username in usuarios_db:
            mensaje = {"tipo": "danger", "texto": "El nombre de usuario ya existe."}
        elif not username or not password or not nombre:
            mensaje = {"tipo": "warning", "texto": "Todos los campos de texto son obligatorios."}
        else:
            usuarios_db[username] = {
                "nombre": nombre,
                "password": generate_password_hash(password),
                "is_admin": is_admin
            }
            guardar_usuarios(usuarios_db)
            mensaje = {"tipo": "success", "texto": f"Usuario '{username}' creado exitosamente."}

    return render_template("crear_usuario.html", mensaje=mensaje)


@app.route("/mis-prestamos", methods=["GET"])
@app.route("/mis_prestamos", methods=["GET"])
def mis_prestamos():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))
        
    uid = session.get("usuario_id")
    libros_prestados = []

    for libro in biblioteca.catalogo:
        prestados = getattr(libro, 'prestado_a', [])
        if isinstance(prestados, list):
            cant_prestada = prestados.count(uid)
            for _ in range(cant_prestada):
                libros_prestados.append(libro)
        elif prestados == uid:
            libros_prestados.append(libro)
        
    return render_template(
        "mis_prestamos.html", 
        libros_prestados=libros_prestados,
        usuario_actual=usuario.nombre
    )


@app.route("/prestar/<string:isbn>", methods=["POST"])
def prestar(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    
    if libro and hasattr(libro, 'prestado_a') and isinstance(libro.prestado_a, list):
        if uid in libro.prestado_a:
            flash("Ya tienes una copia de este libro. No puedes pedir el mismo dos veces.", "warning")
            return redirect(url_for("catalogo"))
    
    if libro and libro.cantidad > 0:
        libro.cantidad -= 1
        if libro.cantidad == 0:
            libro.disponible = False

        if not hasattr(libro, 'prestado_a') or not isinstance(libro.prestado_a, list):
            libro.prestado_a = []
        libro.prestado_a.append(uid)

        if libro not in usuario.libros_prestados:
            usuario.libros_prestados.append(libro)
            
        flash(f"Has pedido prestado '{libro.titulo}' con éxito.", "success")

    asegurar_portadas_y_guardar()
    return redirect(url_for("catalogo"))


@app.route("/devolver/<string:isbn>", methods=["POST"])
def devolver(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    
    if libro and hasattr(libro, 'prestado_a') and isinstance(libro.prestado_a, list):
        if uid in libro.prestado_a:
            libro.prestado_a.remove(uid)
            libro.cantidad += 1
            libro.disponible = True
            
            if uid not in libro.prestado_a and libro in usuario.libros_prestados:
                usuario.libros_prestados.remove(libro)
                
            flash(f"Has devuelto '{libro.titulo}' con éxito.", "success")

    asegurar_portadas_y_guardar()
    return redirect(url_for("mis_prestamos"))


# EJECUCIÓN LOCAL
if __name__ == "__main__":
    app.run(debug=True, port=5000)   