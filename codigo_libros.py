
import json

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

    def prestar(self):
        if self.cantidad > 0 and self.disponible:
            self.cantidad -= 1
            if self.cantidad == 0:
                self.disponible = False
            print(f"Libro prestado: {self.titulo}. Quedan {self.cantidad} copias.")
        else:
            print(f"El libro '{self.titulo}' no está disponible o está agotado.")

    def devolver(self):
        self.cantidad += 1
        self.disponible = True
        print(f"Libro devuelto: {self.titulo}. Copias actuales: {self.cantidad}")

    def __str__(self):
        estado = "Disponible" if self.disponible else "Agotado"
        return f"{self.titulo} - {self.autor} (ISBN: {self.isbn}) | Stock: {self.cantidad} | Estado: {estado}"


class Usuario:
    def __init__(self, nombre, id_usuario):
        self.nombre = nombre
        self.id_usuario = id_usuario
        self.libros_prestados = []

    def __str__(self):
        return f'Usuario: {self.nombre} | ID: {self.id_usuario} | Libros en préstamo: {len(self.libros_prestados)}'


class Biblioteca:
    def __init__(self, nombre):
        self.nombre = nombre
        self.catalogo = []
        self.usuarios = []

    def agregar_libro(self, libro):
        self.catalogo.append(libro)

    def cargar_libros_desde_json(self, ruta_archivo):
        '''Lee un archivo JSON y convierte los datos en objetos Libro.'''
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                datos = json.load(archivo)
                for item in datos:
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
                    self.agregar_libro(nuevo_libro)
            print(f"--- Carga de JSON completada: {len(self.catalogo)} libros en catálogo ---")
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo '{ruta_archivo}'.")
        except json.JSONDecodeError:
            print("Error: El archivo JSON tiene un formato inválido.")

    def modificar_cantidad_libro(self, isbn, nueva_cantidad):
        libro = self.buscar_libro(isbn)
        if libro:
            if nueva_cantidad >= 0:
                libro.cantidad = nueva_cantidad
                libro.disponible = nueva_cantidad > 0
                print(f"Admin: Inventario actualizado -> '{libro.titulo}' ahora tiene {libro.cantidad} copias.")
            else:
                print("Error: La cantidad no puede ser negativa.")
        else:
            print(f"Error: ISBN {isbn} no encontrado en el catálogo.")

    def agregar_usuario(self, usuario):
        self.usuarios.append(usuario)
        print(f'Usuario agregado: {usuario.nombre}')

    def buscar_libro(self, isbn):
        for libro in self.catalogo:
            if libro.isbn == isbn:
                return libro
        return None

    def buscar_usuario(self, id_usuario):
        for usuario in self.usuarios:
            if usuario.id_usuario == id_usuario:
                return usuario
        return None

    def prestar_libro(self, isbn, usuario):
        libro = self.buscar_libro(isbn)

        if libro is None:
            print(f"ISBN {isbn} no encontrado en el catálogo.")
        else:
            if libro.disponible and libro.cantidad > 0:
                libro.prestar()
                usuario.libros_prestados.append(libro)
            else:
                print(f"El libro '{libro.titulo}' no está disponible.")

    def devolver_libro(self, isbn, usuario):
        libro = self.buscar_libro(isbn)

        if libro is None:
            print(f"ISBN {isbn} no encontrado en el catálogo.")
        else:
            if libro in usuario.libros_prestados:
                libro.devolver()
                usuario.libros_prestados.remove(libro)
            else:
                print("Este usuario no tiene registrado ese libro.")

    def mostrar_catalogo(self):
        if len(self.catalogo) == 0:
            print("El catálogo está vacío.")
        else:
            print(f"Catálogo - {self.nombre}")
            for libro in self.catalogo:
                print(libro)


if __name__ == "__main__":
    print("SISTEMA DE PRÉSTAMOS DE BIBLIOTECA \n")

    biblioteca = Biblioteca("Biblioteca Melinda")

    print("--- Obteniendo datos ---")
    biblioteca.cargar_libros_desde_json("libros.json")

    usuario1 = Usuario("Manolito Perez", "m-003")
    usuario2 = Usuario("Víctor Rincón", "m-004")

    print("--- Usuarios registrados ---")
    print(usuario1)
    print(usuario2)
    print()

    print("--- Catálogo inicial ---")
    # biblioteca.mostrar_catalogo() # Descomentar para ver la lista completa
    print("Catálogo cargado correctamente. (Oculto para no saturar consola)\n")

    print("--- Realizando préstamos ---")
    biblioteca.prestar_libro("978-0307474728", usuario1)
    biblioteca.prestar_libro("978-0156012195", usuario2)
    print()

    print("--- Intentando prestar libro no disponible o agotado ---")
    biblioteca.prestar_libro("978-0156012195", usuario1)
    print()

    print("--- Estado de usuarios después de préstamos ---")
    print(usuario1)
    print(usuario2)
    print()

    print("--- Realizando devolución ---")
    biblioteca.devolver_libro("978-0307474728", usuario1)
    print()

    print("--- Estado final de usuarios ---")
    print(usuario1)
    print(usuario2)
    print()
