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


# Constantes para MOVE_THE_LAST
FORMAT = '5s11s20s15sii'     # 5s: código, 11s: nombre, 20s: apellidos, 15s: carrera, i: ciclo, i: mensualidad
RECORD_SIZE = struct.calcsize(FORMAT)
HEADER_SIZE = 4  # Se usan 4 bytes para el header (número de registros)

class MoveTheLast:
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(self.filename):
            self.initialize_file(filename)  # if archive not exists
        else:
            with open(filename, "rb+") as file:
                file.seek(0, 2)
                if file.tell() == 0:
                    self.initialize_file(filename)  # if archive is empty
            
    def initialize_file(self, filename):
        with open(filename, "wb") as file:
            header = 0
            file.write(struct.pack("i", header))
    
    def readHeader(self):
        header = -1
        with open(self.filename, "rb") as file:
            file.seek(0)
            header = struct.unpack("i", file.read(HEADER_SIZE))[0]		
        return header
    
    def unpackRecord(self, record):
        if not record:
            return None
        codigo, nombre, apellidos, carrera, ciclo, mensualidad = struct.unpack(FORMAT, record)
        return Alumno(codigo.decode().strip(), 
                      nombre.decode().strip(), 
                      apellidos.decode().strip(), 
                      carrera.decode().strip(), 
                      ciclo, 
                      mensualidad)
    
    def packAlumno(self, alumno: Alumno):
        return struct.pack(FORMAT, 
                           alumno.codigo.encode(), 
                           alumno.nombre.encode(), 
                           alumno.apellidos.encode(), 
                           alumno.carrera.encode(), 
                           alumno.ciclo, 
                           alumno.mensualidad)
    
    def load(self):
        header = self.readHeader()
        alumnos = []
        with open(self.filename, "rb") as file:
            file.seek(HEADER_SIZE)
            for _ in range(header):  # loop for all records indicated in header
                record = file.read(RECORD_SIZE)
                alumnos.append(self.unpackRecord(record))
        for alumno in alumnos:
            alumno.print()
        return alumnos

    def add(self, alumno: Alumno):
        header = self.readHeader()
        with open(self.filename, "rb+") as file:
            file.seek(HEADER_SIZE + header * RECORD_SIZE)  # pointer at the end
            file.write(self.packAlumno(alumno))
            file.seek(0)
            file.write(struct.pack("i", header + 1))  # actualize header + 1
    
    def readRecord(self, pos: int):
        with open(self.filename, "rb") as file:
            file.seek(HEADER_SIZE + pos * RECORD_SIZE)  # pointer at record pos
            record = file.read(RECORD_SIZE)
            alumno = self.unpackRecord(record)
        if not alumno:
            print("Record not found")
        else:
            alumno.print()
        return alumno
    
    def remove(self, pos: int):
        header = self.readHeader()
        with open(self.filename, "rb+") as file:
            if pos > header:
                print("No record in position:", pos)
            else:
                file.seek(HEADER_SIZE + (header - 1) * RECORD_SIZE)  # pointer at last record
                record = file.read(RECORD_SIZE)
                file.seek(HEADER_SIZE + pos * RECORD_SIZE)
                file.write(record)
                file.seek(0)
                file.write(struct.pack("i", header - 1))  # actualize header - 1

# Constantes para FREE_LIST
FORMAT_FREE = '5s11s20s15siii'     # Formato: añade un campo extra 'i' (nextDel)
RECORD_SIZE_FREE = struct.calcsize(FORMAT_FREE)
# HEADER_SIZE sigue siendo 4

class FreeList:
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(self.filename):
            self.initialize_file(filename)

    def initialize_file(self, filename):
        with open(filename, "wb") as file:
            MINUS_1 = -1
            header = struct.pack("i", MINUS_1)
            file.write(header)
    
    def readHeader(self):
        header = -1
        with open(self.filename, "rb") as file:
            file.seek(0)
            header = file.read(HEADER_SIZE)
            header = struct.unpack("i", header)[0]
        return header
    
    def read_record(self, pos):
        record = ""
        with open(self.filename, "rb") as file:
            file.seek(HEADER_SIZE + pos * RECORD_SIZE_FREE)
            record = file.read(RECORD_SIZE_FREE)
            if not record:
                return None
        return self.unpackRecord(record)
    
    def readRecord(self, pos):
        [alumno, nextDel] = self.read_record(pos)
        if nextDel == -2:
            alumno.print()
        else:
            print("record has been deleted")
    
    def packAlumno(self, alumno: Alumno, nextDel: int):
        return struct.pack(FORMAT_FREE, 
                           alumno.codigo.encode(), 
                           alumno.nombre.encode(), 
                           alumno.apellidos.encode(), 
                           alumno.carrera.encode(), 
                           alumno.ciclo, 
                           alumno.mensualidad, 
                           nextDel)
    
    def unpackRecord(self, record):
        if not record:
            return None
        codigo, nombre, apellidos, carrera, ciclo, mensualidad, nextDel = struct.unpack(FORMAT_FREE, record)
        return [Alumno(codigo.decode().strip(), 
                       nombre.decode().strip(), 
                       apellidos.decode().strip(), 
                       carrera.decode().strip(), 
                       ciclo, 
                       mensualidad), nextDel]
    
    def add(self, alumno: Alumno):
        header = self.readHeader()
        with open(self.filename, "rb+") as file:
            if header == -1:
                file.seek(0, os.SEEK_END)  # append to the end
                new_record = self.packAlumno(alumno, -2)
                file.write(new_record)
            else:
                old_pos = self.read_record(header)[1]
                # writing new record at the free slot indicated by header
                file.seek(HEADER_SIZE + header * RECORD_SIZE_FREE, 0)
                new_record = self.packAlumno(alumno, -2)
                file.write(new_record)
                # update header to point to next free space
                file.seek(0, 0)
                file.write(struct.pack("i", old_pos))
    
    def remove(self, pos: int):
        header = self.readHeader()
        with open(self.filename, "rb+") as file:
            # pointer to nextDel field of record to delete
            file.seek(HEADER_SIZE + ((pos + 1) * RECORD_SIZE_FREE) - 4, 0)
            file.write(struct.pack("i", header))
            file.seek(0, 0)
            file.write(struct.pack("i", pos))
    
    def load(self):
        alumnos = []
        with open(self.filename, "rb") as file:
            file.seek(HEADER_SIZE)
            while True:
                record = file.read(RECORD_SIZE_FREE)
                if not record:
                    break
                record = self.unpackRecord(record)
                if record[1] == -2:
                    alumnos.append(record[0])
        for alumno in alumnos:
            alumno.print()
        return alumnos



# ---------------------------------------------------------
# Funciones de test para mejorar la verificación de cada operación
# ---------------------------------------------------------
def print_records(records):
    for i, alumno in enumerate(records):
        print(f"Pos {i}: {alumno}")

def test_move_the_last():
    print("=== TEST: MOVE_THE_LAST ===")
    filename_move = "data_move.dat"
    if os.path.exists(filename_move):
        os.remove(filename_move)

    db_move = MoveTheLast(filename_move)

    # Agregar registros
    print("\nAgregando registros A, B, C:")
    a = Alumno("P-123", "Eduardo", "Aragon", "CS", 5, 500)
    b = Alumno("P-124", "Jorge", "Quenta", "DS", 5, 2000)
    c = Alumno("P-125", "Jose", "Quenta", "DS", 5, 2000)
    db_move.add(a)
    db_move.add(b)
    db_move.add(c)

    print("\nRegistros después de agregar:")
    records = db_move.load()
    print_records(records)

    # Leer un registro
    print("\nLeyendo registro en posición 1:")
    rec = db_move.readRecord(1)
    if rec:
        print("Registro leído:", rec)

    # Eliminar registro en posición 1
    print("\nEliminando registro en posición 1...")
    db_move.remove(1)

    print("\nRegistros después de eliminar en posición 1:")
    records = db_move.load()
    print_records(records)

    # Intentar leer el registro que fue eliminado
    print("\nIntentando leer el registro en la posición 1 (después de eliminación):")
    rec = db_move.readRecord(1)
    if rec is None:
        print("El registro fue eliminado correctamente.")

    # Probar eliminar en posición fuera de rango
    print("\nIntentando eliminar registro en posición 5 (fuera de rango):")
    db_move.remove(5)
    print("Test MOVE_THE_LAST completado.\n")

def test_free_list():
    print("=== TEST: FREE_LIST ===")
    filename_free = "data_free.dat"
    if os.path.exists(filename_free):
        os.remove(filename_free)

    db_free = FreeList(filename_free)

    # Agregar registros
    print("\nAgregando registros A, B, C:")
    a = Alumno("P-123", "Eduardo", "Aragon", "CS", 5, 500)
    b = Alumno("P-124", "Jorge", "Quenta", "DS", 5, 2000)
    c = Alumno("P-125", "Jose", "Quenta", "DS", 5, 2000)
    db_free.add(a)
    db_free.add(b)
    db_free.add(c)

    print("\nRegistros después de agregar:")
    records = db_free.load()
    print_records(records)

    # Leer registro en posición 1
    print("\nLeyendo registro en posición 1:")
    rec = db_free.readRecord(1)
    if rec:
        print("Registro leído:", rec)

    # Eliminar registro en posición 1
    print("\nEliminando registro en posición 1...")
    db_free.remove(1)

    print("\nRegistros después de eliminar en posición 1:")
    records = db_free.load()
    print_records(records)

    # Intentar leer el registro eliminado
    print("\nIntentando leer el registro en posición 1 (debe indicar eliminado):")
    rec = db_free.readRecord(1)
    if rec is None:
        print("Confirmado: el registro en posición 1 ha sido eliminado.")

    # Agregar un nuevo registro para reutilizar el espacio libre
    print("\nAgregando un nuevo registro D para reutilizar el espacio libre:")
    d = Alumno("P-126", "Maria", "Quenta", "CS", 5, 2000)
    db_free.add(d)

    print("\nRegistros después de agregar nuevo registro en espacio libre:")
    records = db_free.load()
    print_records(records)

    print("Test FREE_LIST completado.\n")

if __name__ == "__main__":
    test_move_the_last()
    test_free_list()
