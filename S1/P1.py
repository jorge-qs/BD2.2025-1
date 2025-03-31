import struct
import os

# ---------------------------------------------------------
# Clase que representa el registro Alumno.
# Esta definición es única para ambas estrategias.
# ---------------------------------------------------------
class Alumno:
    def __init__(self, codigo, nombre, apellidos, carrera, ciclo, mensualidad):
        self.codigo = codigo
        self.nombre = nombre
        self.apellidos = apellidos
        self.carrera = carrera
        self.ciclo = ciclo
        self.mensualidad = mensualidad

    def print(self):
        print(self.codigo, self.nombre, self.apellidos, self.carrera, self.ciclo, self.mensualidad)


# ---------------------------------------------------------
# Constantes y definiciones para la estrategia MOVE_THE_LAST.
# ---------------------------------------------------------
FORMAT_MOVE = '5s11s20s15sii'     # Formato: 5s (código), 11s (nombre), 20s (apellidos), 15s (carrera), i (ciclo), i (mensualidad)
RECORD_SIZE_MOVE = struct.calcsize(FORMAT_MOVE)
HEADER_SIZE = 4  # Se usan 4 bytes para el header (número de registros)

# ---------------------------------------------------------
# Clase para la estrategia MOVE_THE_LAST.
# Al eliminar, se mueve el último registro a la posición eliminada.
# ---------------------------------------------------------
class MoveTheLast:
    def __init__(self, filename):
        self.filename = filename
        # Si el archivo no existe o está vacío, se inicializa (se escribe un header con valor 0).
        if not os.path.exists(self.filename):
            self.initialize_file()
        else:
            with open(self.filename, "rb+") as file:
                file.seek(0, os.SEEK_END)
                if file.tell() == 0:
                    self.initialize_file()
    
    def initialize_file(self):
        with open(self.filename, "wb") as file:
            header = 0  # 0 registros
            file.write(struct.pack("i", header))
    
    def readHeader(self):
        with open(self.filename, "rb") as file:
            file.seek(0)
            header = struct.unpack("i", file.read(HEADER_SIZE))[0]
        return header
    
    def writeHeader(self, value):
        with open(self.filename, "rb+") as file:
            file.seek(0)
            file.write(struct.pack("i", value))
    
    def packAlumno(self, alumno: Alumno):
        return struct.pack(FORMAT_MOVE,
                           alumno.codigo.ljust(5)[:5].encode('utf-8'),
                           alumno.nombre.ljust(11)[:11].encode('utf-8'),
                           alumno.apellidos.ljust(20)[:20].encode('utf-8'),
                           alumno.carrera.ljust(15)[:15].encode('utf-8'),
                           alumno.ciclo,
                           alumno.mensualidad)
    
    def unpackRecord(self, record):
        if not record:
            return None
        codigo, nombre, apellidos, carrera, ciclo, mensualidad = struct.unpack(FORMAT_MOVE, record)
        return Alumno(codigo.decode('utf-8').strip(),
                      nombre.decode('utf-8').strip(),
                      apellidos.decode('utf-8').strip(),
                      carrera.decode('utf-8').strip(),
                      ciclo,
                      mensualidad)
    
    def add(self, alumno: Alumno):
        header = self.readHeader()
        with open(self.filename, "rb+") as file:
            # Se posiciona al final del bloque de registros
            file.seek(HEADER_SIZE + header * RECORD_SIZE_MOVE)
            file.write(self.packAlumno(alumno))
        self.writeHeader(header + 1)
    
    def load(self):
        header = self.readHeader()
        alumnos = []
        with open(self.filename, "rb") as file:
            file.seek(HEADER_SIZE)
            for _ in range(header):
                record = file.read(RECORD_SIZE_MOVE)
                alumnos.append(self.unpackRecord(record))
        # Imprime todos los registros cargados
        for alumno in alumnos:
            alumno.print()
        return alumnos
    
    def readRecord(self, pos: int):
        with open(self.filename, "rb") as file:
            file.seek(HEADER_SIZE + pos * RECORD_SIZE_MOVE)
            record = file.read(RECORD_SIZE_MOVE)
            if not record or len(record) < RECORD_SIZE_MOVE:
                print("Record not found")
                return None
            alumno = self.unpackRecord(record)
            alumno.print()
            return alumno
    
    def remove(self, pos: int):
        header = self.readHeader()
        if pos >= header:
            print("No record in position:", pos)
            return
        with open(self.filename, "rb+") as file:
            # Ubica el último registro
            file.seek(HEADER_SIZE + (header - 1) * RECORD_SIZE_MOVE)
            last_record = file.read(RECORD_SIZE_MOVE)
            # Sobrescribe el registro a eliminar con el último registro
            file.seek(HEADER_SIZE + pos * RECORD_SIZE_MOVE)
            file.write(last_record)
        self.writeHeader(header - 1)


# ---------------------------------------------------------
# Constantes y definiciones para la estrategia FREE_LIST.
# ---------------------------------------------------------
FORMAT_FREE = '5s11s20s15siii'     # Formato: añade un campo extra 'i' (nextDel)
RECORD_SIZE_FREE = struct.calcsize(FORMAT_FREE)

# ---------------------------------------------------------
# Clase para la estrategia FREE_LIST.
# En la eliminación se marca el registro como eliminado actualizando el campo nextDel.
# Se utiliza el header para apuntar al primer espacio libre.
# Se asume que un valor de nextDel igual a -2 indica que el registro está activo.
# ---------------------------------------------------------
class FreeList:
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(self.filename):
            self.initialize_file()
    
    def initialize_file(self):
        with open(self.filename, "wb") as file:
            # Se inicializa el header con -1, lo que indica que no hay espacios libres.
            file.write(struct.pack("i", -1))
    
    def readHeader(self):
        with open(self.filename, "rb") as file:
            file.seek(0)
            header = struct.unpack("i", file.read(HEADER_SIZE))[0]
        return header
    
    def writeHeader(self, value):
        with open(self.filename, "rb+") as file:
            file.seek(0)
            file.write(struct.pack("i", value))
    
    def packAlumno(self, alumno: Alumno, nextDel: int):
        return struct.pack(FORMAT_FREE,
                           alumno.codigo.ljust(5)[:5].encode('utf-8'),
                           alumno.nombre.ljust(11)[:11].encode('utf-8'),
                           alumno.apellidos.ljust(20)[:20].encode('utf-8'),
                           alumno.carrera.ljust(15)[:15].encode('utf-8'),
                           alumno.ciclo,
                           alumno.mensualidad,
                           nextDel)
    
    def unpackRecord(self, record):
        if not record:
            return None
        codigo, nombre, apellidos, carrera, ciclo, mensualidad, nextDel = struct.unpack(FORMAT_FREE, record)
        alumno = Alumno(codigo.decode('utf-8').strip(),
                        nombre.decode('utf-8').strip(),
                        apellidos.decode('utf-8').strip(),
                        carrera.decode('utf-8').strip(),
                        ciclo,
                        mensualidad)
        return alumno, nextDel
    
    def add(self, alumno: Alumno):
        header = self.readHeader()
        with open(self.filename, "rb+") as file:
            if header == -1:
                # No hay espacios libres: se añade al final del archivo.
                file.seek(0, os.SEEK_END)
                file.write(self.packAlumno(alumno, -2))  # -2 indica que el registro está activo.
            else:
                # Hay un espacio libre: se reutiliza ese registro.
                pos = header
                # Se lee el registro libre para obtener su puntero siguiente (nextDel).
                file.seek(HEADER_SIZE + pos * RECORD_SIZE_FREE)
                data = file.read(RECORD_SIZE_FREE)
                _, nextDel = self.unpackRecord(data)
                # Se escribe el nuevo registro en la posición libre.
                file.seek(HEADER_SIZE + pos * RECORD_SIZE_FREE)
                file.write(self.packAlumno(alumno, -2))
                # Se actualiza el header para que apunte al siguiente espacio libre.
                self.writeHeader(nextDel)
    
    def load(self):
        alumnos = []
        with open(self.filename, "rb") as file:
            file.seek(HEADER_SIZE)
            while True:
                data = file.read(RECORD_SIZE_FREE)
                if not data or len(data) < RECORD_SIZE_FREE:
                    break
                alumno, nextDel = self.unpackRecord(data)
                if nextDel == -2:  # Registro activo
                    alumnos.append(alumno)
        for alumno in alumnos:
            alumno.print()
        return alumnos
    
    def readRecord(self, pos: int):
        with open(self.filename, "rb") as file:
            file.seek(HEADER_SIZE + pos * RECORD_SIZE_FREE)
            data = file.read(RECORD_SIZE_FREE)
            if not data or len(data) < RECORD_SIZE_FREE:
                print("Record not found")
                return None
            alumno, nextDel = self.unpackRecord(data)
            if nextDel != -2:
                print("Record has been deleted")
                return None
            alumno.print()
            return alumno
    
    def remove(self, pos: int):
        header = self.readHeader()
        with open(self.filename, "rb+") as file:
            # Se posiciona en el campo nextDel del registro a eliminar (últimos 4 bytes)
            file.seek(HEADER_SIZE + ((pos + 1) * RECORD_SIZE_FREE) - 4)
            # Se escribe el puntero actual del header en ese registro.
            file.write(struct.pack("i", header))
        # Actualiza el header para que apunte al registro eliminado.
        self.writeHeader(pos)


# ---------------------------------------------------------
# Bloque de pruebas funcionales para ambas estrategias.
# ---------------------------------------------------------
if __name__ == "__main__":
    # Datos de ejemplo
    a = Alumno("P-123", "Eduardo", "Aragon", "CS", 5, 500)
    b = Alumno("P-124", "Jorge", "Quenta", "DS", 5, 2000)
    c = Alumno("P-125", "Jose", "Quenta", "DS", 5, 2000)
    d = Alumno("P-126", "Maria", "Quenta", "CS", 5, 2000)

    # ---------------------------
    # Pruebas con estrategia MOVE_THE_LAST
    # ---------------------------
    print("=== Estrategia MOVE_THE_LAST ===")
    filename_move = "data_move.dat"
    # Limpiar archivo previo si existe
    if os.path.exists(filename_move):
        os.remove(filename_move)
    db_move = MoveTheLast(filename_move)
    db_move.add(a)
    db_move.add(b)
    db_move.add(c)
    print("Registros después de agregar:")
    db_move.load()
    print("Leer registro en posición 1:")
    db_move.readRecord(1)
    db_move.remove(1)
    print("Después de eliminar registro en posición 1:")
    db_move.load()

    # ---------------------------
    # Pruebas con estrategia FREE_LIST
    # ---------------------------
    print("\n=== Estrategia FREE_LIST ===")
    filename_free = "data_free.dat"
    if os.path.exists(filename_free):
        os.remove(filename_free)
    db_free = FreeList(filename_free)
    db_free.add(a)
    db_free.add(b)
    db_free.add(c)
    print("Registros después de agregar:")
    db_free.load()
    print("Leer registro en posición 1:")
    db_free.readRecord(1)
    db_free.remove(1)
    print("Después de eliminar registro en posición 1:")
    db_free.load()
