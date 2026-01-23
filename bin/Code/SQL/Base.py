import atexit
import sqlite3

from Code.SQL import DBF, DBFcache


class DBBase:
    """
    Hace referencia a una base de datos.
    Establece la conexion y permite cerrarla.
    """

    def __init__(self, path_file):
        self.path_file = path_file
        self.conexion = sqlite3.connect(self.path_file)

        cursor = self.conexion.cursor()
        cursor.execute("PRAGMA page_size = 4096")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.close()

        atexit.register(self.cerrar)

    def cerrar(self):
        """
        Cierra la conexion a esta base de datos
        """
        if self.conexion:
            self.conexion.close()
            self.conexion = None

    def existeTabla(self, tabla):
        cursor = self.conexion.cursor()
        cursor.execute(f"pragma table_info({tabla})")
        li_fields = cursor.fetchall()
        cursor.close()
        return not (li_fields is None or len(li_fields) == 0)

    def dbf(self, ctabla, select, condicion="", orden=""):
        """
        Acceso a una tabla con un navegador tipo DBF, con lectura inicial de los RowIDs

        @param ctabla: name de la tabla
        @param select: lista de campos separados por comas
        @param condicion: sentencia de condicion SQL
        @param orden: sentencia de orden SQL
        """
        return DBF.DBF(self.conexion, ctabla, select, condicion, orden)

    def dbfCache(self, ctabla, select, condicion="", orden=""):
        """

        @param ctabla: name de la tabla
        @param select: lista de campos separados por comas
        @param condicion: sentencia de condicion SQL
        @param orden: sentencia de orden SQL
        """
        return DBFcache.DBFcache(self.conexion, ctabla, select, condicion, orden)

    def dbfT(self, ctabla, select, condicion="", orden=""):
        """
        Acceso a una tabla con un navegador tipo DBF, con lectura completa de todos los datos.

        @param ctabla: name de la tabla
        @param select: lista de campos separados por comas
        @param condicion: sentencia de condicion SQL
        @param orden: sentencia de orden SQL
        """
        return DBF.DBFT(self.conexion, ctabla, select, condicion, orden)

    def generarTabla(self, tb):
        cursor = self.conexion.cursor()
        cursor.execute("PRAGMA page_size = 4096")
        cursor.execute("PRAGMA synchronous = NORMAL")
        tb.crearBase(cursor)
        cursor.close()


class TablaBase:
    """
    Definicion generica de una tabla.
    """

    def __init__(self, name):
        self.li_fields = []
        self.liIndices = []
        self.name = name

    def crearBase(self, cursor):
        li = [x.create().rstrip() for x in self.li_fields]
        sql = f"CREATE TABLE {self.name} ({', '.join(li)});"
        cursor.execute(sql)

        for x in self.liIndices:
            c = "UNIQUE " if x.siUnico else ""
            cursor.execute(f"CREATE {c}INDEX [{x.name}] ON '{self.name}'({x.campos});")

    def nuevoCampo(self, name, tipo, notNull=False, primaryKey=False, autoInc=False):
        campo = Campo(name, tipo, notNull, primaryKey, autoInc)
        self.li_fields.append(campo)

    def nuevoIndice(self, name, campos, siUnico=False):
        indice = Indice(name, campos, siUnico)
        self.liIndices.append(indice)


class Campo:
    """
    Definicion generica de un campo de una tabla.
    """

    def __init__(self, name, tipo, notNull=False, primaryKey=False, autoInc=False):
        self.name = name
        self.tipo = tipo
        self.notNull = notNull
        self.primaryKey = primaryKey
        self.autoInc = autoInc

    def create(self):
        parts = [self.name, self.tipo]
        if self.notNull:
            parts.append("NOT NULL")
        if self.primaryKey:
            parts.append("PRIMARY KEY")
        if self.autoInc:
            parts.append("AUTOINCREMENT")
        return " ".join(parts)


class Indice:
    """
    Definicion generica de un indice de una tabla.
    """

    def __init__(self, name, campos, siUnico=False):
        self.name = name
        self.campos = campos
        self.siUnico = siUnico
