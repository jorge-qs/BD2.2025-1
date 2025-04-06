import struct
import os

class Venta:
    def __init__(self, id, nombre, cantidad, precio, fecha, next = -1, archive = 1):
        self.id = id
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio = precio
        self.fecha = fecha
        self.next = next # next pointer or -2 if was deleted
        self.archive = archive

    def print(self):
        print(self.id, self.nombre, self.cantidad, self.precio, self.fecha, self.next, self.archive)
    
    def pack(self):
        return struct.pack(FORMAT, self.id, self.nombre.encode(), self.cantidad, self.precio, self.fecha.encode(), self.next, self.archive)

FORMAT = 'i30sif10sii' # id = int, nombre = 30, cantidad = int, precio = float, fecha = 10, next = int, archive = int
RECORD_SIZE = struct.calcsize(FORMAT)
HEADER_SIZE = struct.calcsize("ii")

def readRecordFromFile(filename:str, pointer:int) -> Venta:
    with open(filename, "rb") as file:
        file.seek(pointer)
        record = file.read(RECORD_SIZE)
        assert(record)
        id, nombre, cantidad, precio, fecha, next, archive = struct.unpack(FORMAT, record)
        return Venta(id, nombre.decode().strip(), cantidad, precio, fecha.decode().strip(), next, archive)

def getNumberRecordsFile(filename:str) -> int:
    with open(filename, "rb") as file:
        file.seek(0, 2)
        return file.tell()//RECORD_SIZE # Retorna numero de registros en el archivo

class SequentialFile:
    def __init__(self, filename, auxfile):
        self.filename = filename
        self.auxfile = auxfile
        if not os.path.exists(self.filename):
            self._initialize_file() # if archive doesn't exists
        else:
            with open(self.filename, "rb+") as file:
                file.seek(0,2)
                if(file.tell == 0): # if archive is empty
                    self._initialize_file()

        if not os.path.exists(self.auxfile):
            self._initialize_auxfile() # if archive doesn't exists

    def _initialize_file(self):
        with open(self.filename, "wb") as file:
            file.write(struct.pack("ii", -1, 1))

    def _initialize_auxfile(self):
        with open(self.auxfile, "wb") as file:
            file.seek(0,2)
    
    def _read_header_file(self):
        with open(self.filename, "rb") as file:
            next, archive = struct.unpack("ii", file.read(HEADER_SIZE))
            return [next, archive]
    
    def _binarySearchInFile(self, id):
        # binary search for find the rightest record less or equal than id
        beg = 0
        end = getNumberRecordsFile(self.filename) - 1
        res = -1
        while(beg <= end):
            mid = (beg + end)//2
            cur_mid:Venta = readRecordFromFile(self.filename, HEADER_SIZE + mid * RECORD_SIZE)
            if(cur_mid.id <= id):
                res = mid
                beg = mid + 1
            else:
                end = mid - 1
        return res
    
    def _binaryRemoveInFile(self, id):
        # binary search for find the rightest record less than id
        beg = 0
        end = getNumberRecordsFile(self.filename) - 1
        res = -1
        while(beg <= end):
            mid = (beg + end)//2
            cur_mid:Venta = readRecordFromFile(self.filename, HEADER_SIZE + mid * RECORD_SIZE)
            if(cur_mid.id < id):
                res = mid
                beg = mid + 1
            else:
                end = mid - 1
        return res
    
    def _getArchiveInfo(self, archive):
        filename = self.filename
        header = HEADER_SIZE
        if(archive == 1): 
            filename = self.auxfile
            header = 0
        return [filename, header]
        

    def joinFiles(self):
        [next, archive] = self._read_header_file()
        with open("new_" + self.filename, "x") as file:
            print("file has been created")
        
        with open("new_" + self.filename, "rb+") as file:
            print("writing on new file...")
            file.write(struct.pack("ii", 0,0)) # header
            cont = 1 # count records, used for assign pointer

            while(next != -1):
                [filename, header] = self._getArchiveInfo(archive)
                record:Venta = readRecordFromFile(filename, header + next * RECORD_SIZE)
                archive = record.archive # file of next record
                next = record.next
                record.archive = 0
                if(record.next != -1): # if not the last
                    record.next = cont # assign next pointer
                file.write(record.pack())
                cont+=1
        
        os.remove(self.filename) # delete old filename
        open(self.auxfile, "wb").close() # clear aux file
        os.rename("new_" + self.filename, self.filename) # rename new file
                

    def insert(self, venta:Venta):
        res = self._binarySearchInFile(venta.id) # search the correct position
        numAux = getNumberRecordsFile(self.auxfile)
        
        if(res == -1):
            # file is empty
            [venta.next, venta.archive] = self._read_header_file()
            if(venta.next != -1):
                [filename, header] = self._getArchiveInfo(venta.archive)
                firstRecord = readRecordFromFile(filename, header + venta.next * RECORD_SIZE)
                if(firstRecord.id == venta.id):
                    print(f"new record with id: {venta.id} is already in auxfile and is the firstone")
                    return
            
            print(f"writing new record with id: {venta.id} in auxfile")
            with open(self.filename, "rb+") as file:
                file.seek(0)
                file.write(struct.pack("ii", numAux, 1))
            
            with open(self.auxfile, "rb+") as file:
                file.seek(0,2)
                file.write(venta.pack())
        else:
            record:Venta = readRecordFromFile(self.filename, HEADER_SIZE + res * RECORD_SIZE)
            
            if(record.id == venta.id):
                print(f"venta with id: {venta.id} is already in principal file")
                return

            pointer_record = res
            archive_record = 0
            if(record.archive == 0):
                # append next to that record
                venta.next = record.next # asignando next pointer a la nueva venta
                venta.archive = record.archive
                record.next = numAux # posicion de la nueva venta
                record.archive = 1
                print(f"found record with id: {record.id} in principal file at position: {pointer_record}")
                with open(self.filename, "rb+") as file:
                    file.seek(HEADER_SIZE + pointer_record * RECORD_SIZE)
                    file.write(record.pack()) # write record with new next pointer on filename

                with open(self.auxfile, "rb+") as file:
                    file.seek(0,2)
                    file.write(venta.pack()) # write venta on auxfile
            else:
                cur_record = record
                if(cur_record.next != -1):
                    next_record:Venta = readRecordFromFile(self.auxfile, record.next * RECORD_SIZE)
                    while(next_record.next != -1 and next_record.archive == 1 and next_record.id <= venta.id):
                        archive_record = cur_record.archive
                        pointer_record = cur_record.next
                        cur_record = next_record
                        next_record:Venta = readRecordFromFile(self.auxfile, next_record.next * RECORD_SIZE)

                    if next_record.next == -1 or next_record.archive == 0:
                        if(next_record.id <= venta.id):
                            archive_record = cur_record.archive
                            pointer_record = cur_record.next
                            cur_record = next_record

                print(f"found record with id: {cur_record.id} in archive: {archive_record} at position: {pointer_record}")
                if(cur_record.id == venta.id):
                    print(f"venta with id: {venta.id} is already in aux file")
                    return
                
                venta.next = cur_record.next
                venta.archive = cur_record.archive
                cur_record.next = numAux # posicion del ultimo ingresado
                cur_record.archive = 1

                print(f"writing new record with id: {venta.id} in auxfile")
                with open(self.auxfile, "rb+") as file:
                    file.seek(0,2)
                    file.write(venta.pack()) # write venta on auxfile

                [filename, header] = self._getArchiveInfo(archive_record)
                with open(filename, "rb+") as file:
                    file.seek(header + pointer_record * RECORD_SIZE)
                    file.write(cur_record.pack()) # write venta on filename

        numAux = getNumberRecordsFile(self.auxfile)
        numFile = getNumberRecordsFile(self.filename)
        if(pow(2, numAux) > numFile):
            print(f"Joining files since principal file has: {numFile} records and aux file has: {numAux} records")
            self.joinFiles()


    def search(self, key:str):
        res = self._binarySearchInFile(key)
        if (res == -1):
            [next, archive] = self._read_header_file()
            assert(archive == 1)
            if(next == -1):
                print("auxfile is empty, record not found")
                return
            record:Venta = readRecordFromFile(self.auxfile, next * RECORD_SIZE)
            if(record.id == key):
                print(f"RECORD FOUND in aux file with Id: {key}")
                record.print()
                return record
            
        else: 
            record:Venta = readRecordFromFile(self.filename, HEADER_SIZE + res * RECORD_SIZE)
            if(record.id == key):
                print(f"RECORD FOUND in principal file with Id: {key}")
                record.print()
                return record
        pointer = 0
        numAux = getNumberRecordsFile(self.auxfile)
        while(pointer < numAux * RECORD_SIZE):
            record:Venta = readRecordFromFile(self.auxfile, pointer)
            if(record.id == key and record.next != -2):
                print(f"RECORD FOUND in auxfile with Id: {key}")
                record.print()
                return record
            pointer += RECORD_SIZE
        
        print(f"record with id: {key} not found")
    
    def remove(self, key:str):
        res = self._binaryRemoveInFile(key)
        res_archive = 0
        if (res == -1):
            [next, archive] = self._read_header_file()
            assert(archive == 1)
            if(next == -1):
                print("auxfile is empty, record not found")
                return
            [filename, header] = self._getArchiveInfo(archive)
            record:Venta = readRecordFromFile(filename, header + next * RECORD_SIZE)
            if(record.id == key):
                print(f"record with id: {record.id} was found on auxfile")
                with open(self.filename, "rb+") as file:
                    file.seek(0)
                    print(f"rewriting header with new next pointer: {record.next}")
                    file.write(struct.pack("ii", record.next, record.archive))
                
                with open(self.auxfile, "rb+") as file:
                    file.seek(res * RECORD_SIZE)
                    record.next = -2
                    print(f"deleting record with id: {record.id}")
                    file.write(record.pack())
                    return
            res = next
            res_archive = archive

        assert(res != -1)
        [filename_ini, header_ini] = self._getArchiveInfo(res_archive)
        record:Venta = readRecordFromFile(filename_ini, header_ini + res * RECORD_SIZE)
        next = record.next
        archive = record.archive
        if(archive == 0):
            next_record = readRecordFromFile(self.filename, HEADER_SIZE + next *RECORD_SIZE)
            if(next_record.id == key):
                print(f"record with id: {next_record.id} was found on principal file")
                with open(self.filename, "rb+") as file:
                    file.seek(HEADER_SIZE + record.next * RECORD_SIZE)
                    print(f"deleting record with id: {next_record.id}")
                    record.next = next_record.next
                    next_record.next = -2
                    file.write(next_record.pack())

                with open(filename_ini, "rb+") as file:
                    file.seek(header_ini + res * RECORD_SIZE)
                    print(f"rewriting record before with id: {record.next} to new next pointer: {record.next}")
                    record.archive = next_record.archive
                    file.write(record.pack())
            else:
                print(f"record with id: {key} wasn't found")
            return

        cur_pointer = res
        cur_archive = 0
        while(next != -1):
            [filename, header] = self._getArchiveInfo(archive)
            next_record = readRecordFromFile(filename, header + next * RECORD_SIZE)
            if(next_record.id > key):
                print(f"record with id: {key} wasn't found")
                return
            if(next_record.id == key):
                print(f"record with id: {next_record.id} was found on file: {archive}")
                break
            cur_pointer = next 
            cur_archive = archive
            next = next_record.next
            archive = next_record.archive
        
        if(next == -1):
            print(f"getting at the last part of file, record with id: {key} wasn't found")
            return
        
        [filename, header] = self._getArchiveInfo(cur_archive)
        cur_record = readRecordFromFile(filename, header + cur_pointer * RECORD_SIZE)
        [next_filename, next_header] = self._getArchiveInfo(cur_record.archive)
        next_record = readRecordFromFile(next_filename, next_header + cur_record.next * RECORD_SIZE)

        assert(next_record.id == key)
        with open(next_filename, "rb+") as file:
            file.seek(next_header + cur_record.next * RECORD_SIZE)
            cur_record.next = next_record.next
            next_record.next = -2
            print(f"deleting record with id: {next_record.id}")
            file.write(next_record.pack())

        cur_record.archive = next_record.archive
        with open(filename, "rb+") as file:
            file.seek(header + cur_pointer * RECORD_SIZE)
            print(f"rewriting record before with id: {cur_record.id} to new next pointer: {cur_record.next}")
            file.write(cur_record.pack())
            

    



f = SequentialFile("data.dat", "aux.dat")
a1 = Venta(1, "Manzana1", 3, 2.5, "05-04-2025")
a2 = Venta(2, "Manzana2", 3, 2.5, "05-04-2025")
a3 = Venta(3, "Manzana3", 3, 2.5, "05-04-2025")
a4 = Venta(4, "Manzana4", 3, 2.5, "05-04-2025")
a5 = Venta(5, "Manzana5", 3, 2.5, "05-04-2025")
a6 = Venta(6, "Manzana6", 3, 2.5, "05-04-2025")
a7 = Venta(7, "Manzana7", 3, 2.5, "05-04-2025")




def pruebaInsert1():
    f.insert(a1)
    f.insert(a2)
    f.insert(a3)
    f.insert(a4)
    f.insert(a5)
    f.insert(a6)


def pruebaInsert2():
    f.insert(a2)
    f.insert(a1)
    f.insert(a5)
    f.insert(a4)
    f.insert(a3)
    f.insert(a6)

def pruebaSearch():
    f.insert(a1)
    f.insert(a2)
    f.insert(a3)
    f.insert(a4)
    f.insert(a5)
    f.insert(a6)
    f.search(2)
    f.search(4)
    f.search(5)
    
def pruebaSearch2():
    f.insert(a2)
    f.insert(a1)
    f.insert(a5)
    f.insert(a4)
    f.insert(a3)
    f.insert(a6)
    f.search(2)
    f.search(4)
    f.search(3)

def pruebaSearch3():
    f.insert(a2)
    f.insert(a1)
    f.insert(a5)
    f.search(3)

def pruebaSearch4():
    f.insert(a2)
    f.insert(a3)
    f.insert(a5)
    f.insert(a6)
    f.insert(a4)
    f.insert(a1)
    f.search(7)

def pruebaSearch5():
    f.search(1)
    f.insert(a1)
    f.insert(a2)
    f.search(1)

def pruebaRemove1():
    f.insert(a1)
    f.insert(a2)
    f.insert(a3)
    f.insert(a4)
    f.remove(2)


def pruebaRemove2():
    f.insert(a1)
    f.insert(a2)
    f.insert(a3)
    f.insert(a4)
    f.insert(a5)
    f.insert(a6)
    f.remove(5)
    f.remove(6)

def pruebaRemove3():
    f.insert(a2)
    f.insert(a3)
    f.insert(a5)
    f.insert(a6)
    f.insert(a4)
    f.insert(a1)
    f.remove(4)

def pruebaRemove4():
    f.insert(a2)
    f.insert(a3)
    f.insert(a5)
    f.insert(a6)
    f.insert(a4)
    f.insert(a1)
    f.remove(2)

pruebaRemove4()
