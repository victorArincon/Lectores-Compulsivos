import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from codigo_libros import Libro, Usuario, Biblioteca

app = Flask(__name__)

app.secret_key = "clave_secreta_fija_lectores_compulsivos"
app.config["Sesion permanete"] = False

biblioteca = Biblioteca("Lectores Compulsivos")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ARCHIVO_USUARIOS = os.path.join(BASE_DIR, "usuarios.json")
ARCHIVO_LIBROS = os.path.join(BASE_DIR, "libros.json")
ARCHIVO_SUGERENCIAS = os.path.join(BASE_DIR, "sugerencias.json")
ARCHIVO_SOLICITUDES = os.path.join(BASE_DIR, "solicitudes_registro.json")


def cargar_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        admin_default = {
            "admin": {
                "nombre": "Administrador Principal",
                "password": "R409LCxDsGxq560fE6Pd4kqf87xgj",
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
        pass


def cargar_solicitudes():
    if not os.path.exists(ARCHIVO_SOLICITUDES):
        return []
    try:
        with open(ARCHIVO_SOLICITUDES, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def guardar_solicitudes(solicitudes):
    try:
        with open(ARCHIVO_SOLICITUDES, "w", encoding="utf-8") as f:
            json.dump(solicitudes, f, ensure_ascii=False, indent=4)
    except OSError:
        pass


def cargar_sugerencias():
    if not os.path.exists(ARCHIVO_SUGERENCIAS):
        return []
    try:
        with open(ARCHIVO_SUGERENCIAS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def guardar_sugerencias(sugerencias):
    try:
        with open(ARCHIVO_SUGERENCIAS, "w", encoding="utf-8") as f:
            json.dump(sugerencias, f, ensure_ascii=False, indent=4)
    except OSError:
        pass


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
            "categoria": getattr(libro, 'categoria', 'General'),
            "portada": portada_val,
            "prestado_a": prestados_lista,
            "espera": getattr(libro, 'espera', []),
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


def inicializar_biblioteca():
    if os.path.exists(ARCHIVO_LIBROS):
        biblioteca.cargar_libros_desde_json(ARCHIVO_LIBROS)
        try:
            with open(ARCHIVO_LIBROS, "r", encoding="utf-8") as f:
                datos_json = json.load(f)

            for libro_obj in biblioteca.catalogo:
                datos = next((d for d in datos_json if d.get("isbn") == libro_obj.isbn), {})
                setattr(libro_obj, 'portada', datos.get("portada", getattr(libro_obj, 'imagen', '')))
                setattr(libro_obj, 'categoria', datos.get("categoria", "General"))
                setattr(libro_obj, 'espera', datos.get("espera", []))

                prestados = datos.get("prestado_a", [])
                if isinstance(prestados, str):
                    prestados = [prestados] if prestados else []

                prestados_normalizados = []
                for p in prestados:
                    if isinstance(p, str):
                        prestados_normalizados.append({
                            "uid": p,
                            "fecha_limite": (datetime.now().date() + timedelta(days=7)).isoformat(),
                            "extension_solicitada": None
                        })
                    else:
                        if "extension_solicitada" not in p:
                            p["extension_solicitada"] = None
                        prestados_normalizados.append(p)

                setattr(libro_obj, 'prestado_a', prestados_normalizados)
                libro_obj.cantidad = datos.get("cantidad", 3)
                libro_obj.disponible = datos.get("disponible", True)

                for p in prestados_normalizados:
                    uid = p.get("uid") if isinstance(p, dict) else p
                    usr = biblioteca.buscar_usuario(uid)
                    if not usr:
                        usr = Usuario(uid.capitalize(), uid)
                        biblioteca.agregar_usuario(usr)
                    if libro_obj not in usr.libros_prestados:
                        usr.libros_prestados.append(libro_obj)
        except Exception as e:
            print(f"Aviso al cargar estado previo: {e}")

inicializar_biblioteca()


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

        if usuario_input in usuarios_db:
            pass_registrada = usuarios_db[usuario_input]["password"]

            if pass_registrada == password_input or check_password_hash(pass_registrada, password_input):
                session.clear()
                session["usuario_id"] = usuario_input
                session["usuario_nombre"] = usuarios_db[usuario_input]["nombre"]
                session["is_admin"] = usuarios_db[usuario_input].get("is_admin", False)

                usuario = biblioteca.buscar_usuario(usuario_input)
                if not usuario:
                    usuario = Usuario(session["usuario_nombre"], usuario_input)
                    biblioteca.agregar_usuario(usuario)

                return redirect(url_for("catalogo"))

        error = "Usuario o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/registro", methods=["GET", "POST"])
def registro():
    mensaje = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        nombre = request.form.get("nombre", "").strip()
        password = request.form.get("password", "").strip()

        usuarios_db = cargar_usuarios()
        solicitudes = cargar_solicitudes()

        if username in usuarios_db or any(s["username"] == username for s in solicitudes):
            mensaje = {"tipo": "danger", "texto": "El nombre de usuario ya existe o tiene una solicitud pendiente."}
        elif not username or not password or not nombre:
            mensaje = {"tipo": "warning", "texto": "Todos los campos son obligatorios."}
        else:
            solicitudes.append({
                "username": username,
                "nombre": nombre,
                "password": password,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            guardar_solicitudes(solicitudes)
            mensaje = {"tipo": "success", "texto": "¡Solicitud enviada con éxito! Un administrador debe aprobarla para que puedas iniciar sesión."}

    return render_template("registro.html", mensaje=mensaje)


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/crear_usuario", methods=["GET", "POST"])
def crear_usuario():
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado. Solo administradores pueden ver esto.", 403

    mensaje = None
    usuarios_db = cargar_usuarios()
    solicitudes = cargar_solicitudes()

    if request.method == "POST":
        accion = request.form.get("accion")

        if accion == "crear":
            username = request.form.get("username", "").strip()
            nombre = request.form.get("nombre", "").strip()
            password = request.form.get("password", "").strip()
            is_admin = request.form.get("is_admin") == "on"

            if username in usuarios_db:
                mensaje = {"tipo": "danger", "texto": "El nombre de usuario ya existe."}
            elif not username or not password or not nombre:
                mensaje = {"tipo": "warning", "texto": "Todos los campos de texto son obligatorios."}
            else:
                usuarios_db[username] = {
                    "nombre": nombre,
                    "password": password,
                    "is_admin": is_admin
                }
                guardar_usuarios(usuarios_db)
                mensaje = {"tipo": "success", "texto": f"Usuario '{username}' creado exitosamente."}

        elif accion == "aceptar_solicitud":
            target_username = request.form.get("username")
            solicitud_encontrada = next((s for s in solicitudes if s["username"] == target_username), None)
            if solicitud_encontrada:
                usuarios_db[solicitud_encontrada["username"]] = {
                    "nombre": solicitud_encontrada["nombre"],
                    "password": solicitud_encontrada["password"],
                    "is_admin": False
                }
                guardar_usuarios(usuarios_db)
                solicitudes = [s for s in solicitudes if s["username"] != target_username]
                guardar_solicitudes(solicitudes)
                mensaje = {"tipo": "success", "texto": f"Solicitud de '{target_username}' aceptada."}

        elif accion == "rechazar_solicitud":
            target_username = request.form.get("username")
            solicitudes = [s for s in solicitudes if s["username"] != target_username]
            guardar_solicitudes(solicitudes)
            mensaje = {"tipo": "warning", "texto": f"Solicitud de '{target_username}' rechazada."}

        elif accion == "cambiar_password":
            target_username = request.form.get("username")
            nueva_pass = request.form.get("nueva_password", "").strip()
            if target_username in usuarios_db and nueva_pass:
                usuarios_db[target_username]["password"] = nueva_pass
                guardar_usuarios(usuarios_db)
                mensaje = {"tipo": "success", "texto": f"Contraseña actualizada para '{target_username}'."}
            else:
                mensaje = {"tipo": "danger", "texto": "La nueva contraseña no puede estar vacía."}

        elif accion == "eliminar_usuario":
            target_username = request.form.get("username")
            if target_username in usuarios_db and target_username != "admin":
                del usuarios_db[target_username]
                guardar_usuarios(usuarios_db)
                mensaje = {"tipo": "success", "texto": f"Usuario '{target_username}' eliminado con éxito."}
            else:
                mensaje = {"tipo": "danger", "texto": "No se puede eliminar al administrador principal."}

        usuarios_db = cargar_usuarios()
        solicitudes = cargar_solicitudes()

    return render_template("crear_usuario.html", mensaje=mensaje, usuarios=usuarios_db, solicitudes=solicitudes)


@app.route("/mis-alquileres", methods=["GET"])
@app.route("/mis_alquileres", methods=["GET"])
def mis_alquileres():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session.get("usuario_id")
    alquileres_usuario = []

    for libro in biblioteca.catalogo:
        prestados = getattr(libro, 'prestado_a', [])
        for p in prestados:
            current_uid = p.get("uid") if isinstance(p, dict) else p
            if current_uid == uid:
                fecha_limite_str = p.get("fecha_limite") if isinstance(p, dict) else None
                extension_solicitada = p.get("extension_solicitada") if isinstance(p, dict) else None

                dias_restantes = None
                vencido = False
                fechas_ext = {"7": "", "14": "", "21": ""}

                if fecha_limite_str:
                    try:
                        f_limite = datetime.fromisoformat(fecha_limite_str).date()
                        hoy = datetime.now().date()
                        delta = (f_limite - hoy).days
                        dias_restantes = delta
                        if delta < 0:
                            vencido = True

                        fechas_ext = {
                            "7": (f_limite + timedelta(days=7)).strftime("%d/%m/%Y"),
                            "14": (f_limite + timedelta(days=14)).strftime("%d/%m/%Y"),
                            "21": (f_limite + timedelta(days=21)).strftime("%d/%m/%Y")
                        }
                    except Exception:
                        pass

                tiene_espera = bool(getattr(libro, 'espera', []))

                alquileres_usuario.append({
                    "libro": libro,
                    "fecha_limite": fecha_limite_str,
                    "dias_restantes": dias_restantes,
                    "vencido": vencido,
                    "extension_solicitada": extension_solicitada,
                    "tiene_espera": tiene_espera,
                    "fechas_ext": fechas_ext
                })

    return render_template(
        "mis_alquileres.html",
        prestamos=alquileres_usuario,
        usuario_actual=usuario.nombre
    )


@app.route("/solicitar-extension/<string:isbn>", methods=["POST"])
def solicitar_extension(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)

    if libro and getattr(libro, 'espera', []):
        flash(f"No puedes solicitar una extensión para '{libro.titulo}' porque hay usuarios en lista de espera.", "danger")
        return redirect(url_for("mis_alquileres"))

    try:
        dias_extra = int(request.form.get("dias_extra", 7))
        if dias_extra not in [7, 14, 21]:
            dias_extra = 7
    except ValueError:
        dias_extra = 7

    if libro and hasattr(libro, 'prestado_a'):
        for p in libro.prestado_a:
            current_uid = p.get("uid") if isinstance(p, dict) else p
            if current_uid == uid:
                p["extension_solicitada"] = dias_extra
                flash(f"Solicitud de extensión de {dias_extra} días enviada para '{libro.titulo}'.", "success")
                break

    asegurar_portadas_y_guardar()
    return redirect(url_for("mis_alquileres"))


@app.route("/sugerencias", methods=["GET", "POST"])
def sugerencias():
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        autor = request.form.get("autor", "").strip()
        comentario = request.form.get("comentario", "").strip()

        if not titulo or not autor:
            flash("El título y el autor del libro son obligatorios.", "danger")
        else:
            sugs = cargar_sugerencias()
            sugs.append({
                "usuario": usuario.nombre,
                "uid": session.get("usuario_id", ""),
                "titulo": titulo,
                "autor": autor,
                "comentario": comentario,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            guardar_sugerencias(sugs)
            flash("¡Sugerencia enviada con éxito!", "success")
            return redirect(url_for("catalogo"))

    return render_template("sugerencias.html", usuario_actual=usuario.nombre)


@app.route("/prestar/<string:isbn>", methods=["POST"])
def prestar(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    try:
        dias = int(request.form.get("dias", 7))
        if dias not in [7, 14, 21]:
            dias = 7
    except ValueError:
        dias = 7

    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)

    if not hasattr(libro, 'prestado_a') or not isinstance(libro.prestado_a, list):
        libro.prestado_a = []

    usuarios_con_libro = [p.get("uid") if isinstance(p, dict) else p for p in libro.prestado_a]
    if uid in usuarios_con_libro:
        flash("Ya tienes una copia alquilada de este libro. No puedes alquilar el mismo dos veces.", "warning")
        return redirect(url_for("catalogo"))

    if libro and libro.cantidad > 0:
        libro.cantidad -= 1
        if libro.cantidad == 0:
            libro.disponible = False

        fecha_limite = datetime.now().date() + timedelta(days=dias)
        libro.prestado_a.append({
            "uid": uid,
            "fecha_limite": fecha_limite.isoformat(),
            "extension_solicitada": None
        })

        if libro not in usuario.libros_prestados:
            usuario.libros_prestados.append(libro)

        flash(f"Has alquilado '{libro.titulo}' por {dias} días con éxito.", "success")

    asegurar_portadas_y_guardar()
    return redirect(url_for("catalogo"))


@app.route("/reservar/<string:isbn>", methods=["POST"])
def reservar(isbn):
    usuario = obtener_o_crear_usuario_actual()
    if not usuario:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)

    if not libro:
        flash("Libro no encontrado.", "danger")
        return redirect(url_for("catalogo"))

    if not hasattr(libro, 'espera'):
        libro.espera = []

    usuarios_con_libro = [p.get("uid") if isinstance(p, dict) else p for p in getattr(libro, 'prestado_a', [])]

    if uid in usuarios_con_libro:
        flash("Ya tienes este libro en tu poder, no puedes reservarlo.", "warning")
    elif uid in libro.espera:
        flash("Ya te encuentras en la lista de espera para este libro.", "warning")
    else:
        libro.espera.append(uid)
        flash(f"Te has unido a la lista de espera para '{libro.titulo}'. Turno #{len(libro.espera)}.", "success")

    asegurar_portadas_y_guardar()
    return redirect(url_for("catalogo"))


@app.route("/admin/prestamos", methods=["GET"])
def admin_prestamos():
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado. Solo administradores.", 403

    prestamos_activos = []
    for libro in biblioteca.catalogo:
        prestados = getattr(libro, 'prestado_a', [])
        for p in prestados:
            if isinstance(p, dict):
                uid = p.get("uid")
                fecha_limite = p.get("fecha_limite")
                extension_solicitada = p.get("extension_solicitada")
            else:
                uid = p
                fecha_limite = "No especificada"
                extension_solicitada = None

            usr = biblioteca.buscar_usuario(uid)
            nombre_usr = usr.nombre if usr else uid

            prestamos_activos.append({
                "isbn": libro.isbn,
                "titulo": libro.titulo,
                "uid": uid,
                "nombre_usuario": nombre_usr,
                "fecha_limite": fecha_limite,
                "extension_solicitada": extension_solicitada,
                "espera_count": len(getattr(libro, 'espera', []))
            })

    return render_template("admin_prestamos.html", prestamos=prestamos_activos, usuario_actual=session.get("usuario_nombre"))


@app.route("/admin/resolver-extension/<string:isbn>/<string:uid>/<string:accion>", methods=["POST"])
def admin_resolver_extension(isbn, uid, accion):
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado.", 403

    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    if libro and hasattr(libro, 'prestado_a'):
        if getattr(libro, 'espera', []):
            flash("No se puede aprobar la extensión porque hay usuarios en lista de espera.", "danger")
            return redirect(url_for("admin_prestamos"))

        for p in libro.prestado_a:
            current_uid = p.get("uid") if isinstance(p, dict) else p
            if current_uid == uid and isinstance(p, dict):
                dias_extra = p.get("extension_solicitada")
                if accion == "aceptar" and dias_extra:
                    try:
                        f_actual = datetime.fromisoformat(p["fecha_limite"]).date()
                        nueva_fecha = f_actual + timedelta(days=dias_extra)
                        p["fecha_limite"] = nueva_fecha.isoformat()
                        flash(f"Extensión aceptada para '{libro.titulo}' (+{dias_extra} días).", "success")
                    except Exception:
                        pass
                elif accion == "rechazar":
                    flash(f"Extensión rechazada para '{libro.titulo}'.", "warning")

                p["extension_solicitada"] = None
                break

    asegurar_portadas_y_guardar()
    return redirect(url_for("admin_prestamos"))


@app.route("/admin/confirmar_devolucion/<string:isbn>/<string:uid>", methods=["POST"])
def admin_confirmar_devolucion(isbn, uid):
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado. Solo administradores.", 403

    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    usuario = biblioteca.buscar_usuario(uid)

    if libro and hasattr(libro, 'prestado_a'):
        nuevo_prestado_a = [p for p in libro.prestado_a if (p.get("uid") if isinstance(p, dict) else p) != uid]
        libro.prestado_a = nuevo_prestado_a

        if hasattr(libro, 'espera') and libro.espera:
            siguiente_uid = libro.espera.pop(0)
            nueva_fecha_limite = datetime.now().date() + timedelta(days=7)
            libro.prestado_a.append({
                "uid": siguiente_uid,
                "fecha_limite": nueva_fecha_limite.isoformat(),
                "extension_solicitada": None
            })
            flash(f"Devolución confirmada. El libro '{libro.titulo}' fue reasignado automáticamente al siguiente en espera ({siguiente_uid}).", "success")
        else:
            libro.cantidad += 1
            libro.disponible = True
            flash(f"Devolución confirmada para el libro '{libro.titulo}'. Stock restaurado.", "success")

        if usuario and libro in usuario.libros_prestados:
            usuario.libros_prestados.remove(libro)

    asegurar_portadas_y_guardar()
    return redirect(url_for("admin_prestamos"))


@app.route("/admin/sugerencias", methods=["GET"])
def admin_sugerencias():
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado.", 403
    sugs = cargar_sugerencias()
    return render_template("admin_sugerencias.html", sugerencias=sugs, usuario_actual=session.get("usuario_nombre"))


@app.route("/admin/eliminar_sugerencia/<int:index>", methods=["POST"])
def admin_eliminar_sugerencia(index):
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado.", 403

    sugs = cargar_sugerencias()
    if 0 <= index < len(sugs):
        eliminada = sugs.pop(index)
        guardar_sugerencias(sugs)
        flash(f"Sugerencia de '{eliminada.get('titulo', 'Libro')}' eliminada correctamente.", "success")
    else:
        flash("Sugerencia no encontrada.", "danger")

    return redirect(url_for("admin_sugerencias"))


@app.route("/admin/agregar_stock/<string:isbn>", methods=["POST"])
def admin_agregar_stock(isbn):
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acceso denegado. Solo administradores.", 403

    try:
        cantidad_extra = int(request.form.get("cantidad_extra", 1))
        if cantidad_extra < 1:
            cantidad_extra = 1
    except ValueError:
        cantidad_extra = 1

    libro = next((l for l in biblioteca.catalogo if l.isbn == isbn), None)
    if libro:
        libro.cantidad += cantidad_extra
        libro.disponible = True
        flash(f"Se agregaron {cantidad_extra} ejemplares al libro '{libro.titulo}'. Stock disponible actual: {libro.cantidad}", "success")
    else:
        flash("Libro no encontrado.", "danger")

    asegurar_portadas_y_guardar()
    return redirect(url_for("catalogo"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
