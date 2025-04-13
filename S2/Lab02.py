#!pip install seaborn
import seaborn as sns
import struct
import os
import time
import matplotlib.pyplot as plt


VENTAS_FORMAT = "=i30sif10s"
VENTAS_SIZE = struct.calcsize(VENTAS_FORMAT)

def pack_sale(sale):

    product_bytes = sale["product"].ljust(30)[:30].encode("utf-8")
    date_bytes = sale["date"].ljust(10)[:10].encode("utf-8")
    return struct.pack(VENTAS_FORMAT, sale["id"], product_bytes, sale["qty"], sale["price"], date_bytes)

def unpack_sale(data):

    id_val, product_bytes, qty, price, date_bytes = struct.unpack(VENTAS_FORMAT, data)
    return {
        "id": id_val,
        "product": product_bytes.decode("utf-8").rstrip("\x00").strip(),
        "qty": qty,
        "price": price,
        "date": date_bytes.decode("utf-8").strip()
    }

##########################################
### Implementación del Sequential File ###
##########################################

FORMAT = 'i30sif10sii' # id = int, nombre = 30, cantidad = int, precio = float, fecha = 10, next = int, archive = int
RECORD_SIZE = struct.calcsize(FORMAT)
HEADER_SIZE = struct.calcsize("ii")

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

#####################################################
## Implementación del Archivo AVL con Persistencia ##
#####################################################

# Es importante la implementación con persistencia (memoria secundaria), ya que , los datos del árbol se conservan incluso después de que la aplicación se cierre o se reinicie. 
# En un sistema real de bases de datos, los datos deben sobrevivir a un apagón o reinicio.

AVL_NODE_FORMAT = "=i30sif10siii"
AVL_NODE_SIZE = struct.calcsize(AVL_NODE_FORMAT)
AVL_HEADER_SIZE = 4

#Con SALE_SIZE ya definido

class AVLNode:
    def __init__(self, sale, left=-1, right=-1, height=1):
        self.sale = sale
        self.left = left
        self.right = right
        self.height = height

    def pack(self):
        sale_data = pack_sale(self.sale)
        extra = struct.pack("iii", self.left, self.right, self.height)
        return sale_data + extra

    @staticmethod
    def unpack(data):
        sale_data = data[:VENTAS_SIZE]
        extra = data[VENTAS_SIZE:]
        sale = unpack_sale(sale_data)
        left, right, height = struct.unpack("iii", extra)
        return AVLNode(sale, left, right, height)

class AVLFile:
    def __init__(self, filename="sales_avl.dat"):
        self.filename = filename
        if not os.path.exists(self.filename) or os.path.getsize(self.filename) < AVL_HEADER_SIZE:
            with open(self.filename, "wb") as f:
                f.write(struct.pack("i", -1))  # Raíz = -1

    def _read_root(self):
        with open(self.filename, "rb") as f:
            f.seek(0)
            return struct.unpack("i", f.read(AVL_HEADER_SIZE))[0]

    def _write_root(self, root_index):
        with open(self.filename, "rb+") as f:
            f.seek(0)
            f.write(struct.pack("i", root_index))

    def _read_node(self, index):
        with open(self.filename, "rb") as f:
            pos = AVL_HEADER_SIZE + index * AVL_NODE_SIZE
            f.seek(pos)
            data = f.read(AVL_NODE_SIZE)
            if len(data) < AVL_NODE_SIZE:
                return None
            return AVLNode.unpack(data)

    def _write_node(self, index, node):
        with open(self.filename, "rb+") as f:
            pos = AVL_HEADER_SIZE + index * AVL_NODE_SIZE
            f.seek(pos)
            f.write(node.pack())

    def _append_node(self, node):
        with open(self.filename, "ab") as f:
            f.write(node.pack())
        size = os.path.getsize(self.filename)
        new_index = (size - AVL_HEADER_SIZE) // AVL_NODE_SIZE
        return new_index

    def load_tree(self):
        nodes = []
        root_index = self._read_root()
        with open(self.filename, "rb") as f:
            f.seek(AVL_HEADER_SIZE)
            while True:
                data = f.read(AVL_NODE_SIZE)
                if not data or len(data) < AVL_NODE_SIZE:
                    break
                node = AVLNode.unpack(data)
                nodes.append(node)
        return root_index, nodes

    def rebuild_file(self, root_index, nodes):
        with open(self.filename, "wb") as f:
            f.write(struct.pack("i", root_index))
            for node in nodes:
                f.write(node.pack())

    # Métodos AVL en memoria integrados con persistencia
    def _height(self, idx, nodes):
        return nodes[idx].height if idx != -1 else 0

    def _update_height(self, idx, nodes):
        nodes[idx].height = max(self._height(nodes[idx].left, nodes),
                                  self._height(nodes[idx].right, nodes)) + 1

    def _balance_factor(self, idx, nodes):
        return self._height(nodes[idx].left, nodes) - self._height(nodes[idx].right, nodes)

    def _right_rotate(self, y_idx, nodes):
        y = nodes[y_idx]
        x_idx = y.left
        x = nodes[x_idx]
        T2 = x.right
        x.right = y_idx
        y.left = T2
        self._update_height(y_idx, nodes)
        self._update_height(x_idx, nodes)
        return x_idx

    def _left_rotate(self, x_idx, nodes):
        x = nodes[x_idx]
        y_idx = x.right
        y = nodes[y_idx]
        T2 = y.left
        y.left = x_idx
        x.right = T2
        self._update_height(x_idx, nodes)
        self._update_height(y_idx, nodes)
        return y_idx

    def _insert(self, idx, sale, nodes):
        if idx == -1:
            new_node = AVLNode(sale)
            new_index = len(nodes)
            nodes.append(new_node)
            return new_index
        if sale["id"] < nodes[idx].sale["id"]:
            nodes[idx].left = self._insert(nodes[idx].left, sale, nodes)
        elif sale["id"] > nodes[idx].sale["id"]:
            nodes[idx].right = self._insert(nodes[idx].right, sale, nodes)
        else:
            return idx
        self._update_height(idx, nodes)
        bf = self._balance_factor(idx, nodes)
        if bf > 1 and sale["id"] < nodes[nodes[idx].left].sale["id"]:
            return self._right_rotate(idx, nodes)
        if bf < -1 and sale["id"] > nodes[nodes[idx].right].sale["id"]:
            return self._left_rotate(idx, nodes)
        if bf > 1 and sale["id"] > nodes[nodes[idx].left].sale["id"]:
            nodes[idx].left = self._left_rotate(nodes[idx].left, nodes)
            return self._right_rotate(idx, nodes)
        if bf < -1 and sale["id"] < nodes[nodes[idx].right].sale["id"]:
            nodes[idx].right = self._right_rotate(nodes[idx].right, nodes)
            return self._left_rotate(idx, nodes)
        return idx

    def insert(self, sale):
        root, nodes = self.load_tree()
        if root == -1:
            new_node = AVLNode(sale)
            nodes.append(new_node)
            new_root = 0
        else:
            new_root = self._insert(root, sale, nodes)
        self.rebuild_file(new_root, nodes)

    def _search(self, idx, sale_id, nodes):
        if idx == -1:
            return None
        if nodes[idx].sale["id"] == sale_id:
            return nodes[idx].sale
        elif sale_id < nodes[idx].sale["id"]:
            return self._search(nodes[idx].left, sale_id, nodes)
        else:
            return self._search(nodes[idx].right, sale_id, nodes)

    def search(self, sale_id):
        root, nodes = self.load_tree()
        return self._search(root, sale_id, nodes)

    def _inorder(self, idx, nodes, result):
        if idx == -1:
            return
        self._inorder(nodes[idx].left, nodes, result)
        result.append(nodes[idx].sale)
        self._inorder(nodes[idx].right, nodes, result)

    def rangeSearch(self, init_id, end_id):
        root, nodes = self.load_tree()
        result = []
        self._inorder(root, nodes, result)
        return [sale for sale in result if init_id <= sale["id"] <= end_id]

    def _min_value_node(self, idx, nodes):
        current = idx
        while nodes[current].left != -1:
            current = nodes[current].left
        return current

    def _delete(self, idx, sale_id, nodes):
        if idx == -1:
            return idx
        if sale_id < nodes[idx].sale["id"]:
            nodes[idx].left = self._delete(nodes[idx].left, sale_id, nodes)
        elif sale_id > nodes[idx].sale["id"]:
            nodes[idx].right = self._delete(nodes[idx].right, sale_id, nodes)
        else:
            if nodes[idx].left == -1 or nodes[idx].right == -1:
                temp = nodes[idx].left if nodes[idx].left != -1 else nodes[idx].right
                if temp == -1:
                    idx = -1
                    return idx
                else:
                    idx = temp
            else:
                temp = self._min_value_node(nodes[idx].right, nodes)
                nodes[idx].sale = nodes[temp].sale
                nodes[idx].right = self._delete(nodes[idx].right, nodes[temp].sale["id"], nodes)
        if idx == -1:
            return idx
        self._update_height(idx, nodes)
        bf = self._balance_factor(idx, nodes)
        if bf > 1 and self._balance_factor(nodes[idx].left, nodes) >= 0:
            return self._right_rotate(idx, nodes)
        if bf > 1 and self._balance_factor(nodes[idx].left, nodes) < 0:
            nodes[idx].left = self._left_rotate(nodes[idx].left, nodes)
            return self._right_rotate(idx, nodes)
        if bf < -1 and self._balance_factor(nodes[idx].right, nodes) <= 0:
            return self._left_rotate(idx, nodes)
        if bf < -1 and self._balance_factor(nodes[idx].right, nodes) > 0:
            nodes[idx].right = self._right_rotate(nodes[idx].right, nodes)
            return self._left_rotate(idx, nodes)
        return idx

    def remove(self, sale_id):
        root, nodes = self.load_tree()
        new_root = self._delete(root, sale_id, nodes)
        self.rebuild_file(new_root, nodes)


#####################################################
##     Test y comparación de métodos (gráficos)    ##
#####################################################

def evaluate_performance(seq_file : SequentialFile, avl_file : AVLFile, test_sales):
    """
    Mide el tiempo de ejecución de las operaciones para Sequential File y AVL File.
    Retorna dos diccionarios con los tiempos.
    """
    seq_times = {}
    avl_times = {}

    # --- Sequential File ---
    # Reiniciar archivos para medición consistente.
    for fname in [seq_file.filename, seq_file.auxfile]:
        if os.path.exists(fname):
            os.remove(fname)
    seq_file.__init__(seq_file.filename, seq_file.auxfile)

    start = time.time()
    for sale in test_sales:
        seq_file.insert(sale)
    end = time.time()
    seq_times["insert"] = end - start

    start = time.time()
    for sale in test_sales:
        seq_file.search(sale["id"])
    end = time.time()
    seq_times["search"] = end - start

    #start = time.time()
    #seq_file.rangeSearch(test_sales[0]["id"], test_sales[-1]["id"])
    #end = time.time()
    #seq_times["rangeSearch"] = end - start

    start = time.time()
    seq_file.remove(test_sales[0]["id"])
    end = time.time()
    seq_times["remove"] = end - start

    # --- AVL File ---
    if os.path.exists(avl_file.filename):
        os.remove(avl_file.filename)
    avl_file.__init__(avl_file.filename)

    start = time.time()
    for sale in test_sales:
        avl_file.insert(sale)
    end = time.time()
    avl_times["insert"] = end - start

    start = time.time()
    for sale in test_sales:
        avl_file.search(sale["id"])
    end = time.time()
    avl_times["search"] = end - start

    start = time.time()
    avl_file.rangeSearch(test_sales[0]["id"], test_sales[-1]["id"])
    end = time.time()
    avl_times["rangeSearch"] = end - start

    start = time.time()
    avl_file.remove(test_sales[0]["id"])
    end = time.time()
    avl_times["remove"] = end - start

    return seq_times, avl_times

def plot_results(seq_times, avl_times):
    """
    Genera una gráfica comparativa con los tiempos de ejecución para cada operación.
    """
    sns.set_style("darkgrid")
    operations = list(seq_times.keys())
    seq_values = [seq_times[op] for op in operations]
    avl_values = [avl_times[op] for op in operations]
    x = range(len(operations))
    bar_width = 0.35

    plt.figure(figsize=(10,6))
    plt.bar([i - bar_width/2 for i in x], seq_values, width=bar_width,
            color="skyblue", edgecolor="black", label="Sequential File")
    plt.bar([i + bar_width/2 for i in x], avl_values, width=bar_width,
            color="salmon", edgecolor="black", label="AVL File")

    plt.xticks(x, operations, fontsize=12)
    plt.ylabel("Tiempo (segundos)", fontsize=12)
    plt.title("Comparación de Tiempos: Sequential File vs AVL File", fontsize=14, fontweight="bold")
    plt.legend(fontsize=12)
    for i, v in enumerate(seq_values):
        plt.text(i - bar_width/2, v + 0.001, f"{v:.5f}", ha="center", va="bottom", fontsize=10, color="blue", rotation=45)
    for i, v in enumerate(avl_values):
        plt.text(i + bar_width/2, v + 0.001, f"{v:.5f}", ha="center", va="bottom", fontsize=10, color="red", rotation=45)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # Crear datos de prueba: 100 registros de ejemplo.
    test_sales = []
    for i in range(1, 101):
        sale = {
            "id": i,
            "product": f"Producto_{i}",
            "qty": (i % 10) + 1,
            "price": 100.0 + i,
            "date": "2025-03-30"
        }
        test_sales.append(sale)

    # Instanciar las estructuras
    seq_file = SequentialFile("data.dat", "aux.dat")
    avl_file = AVLFile("sales_avl.dat")

    # Evaluación de desempeño
    seq_times, avl_times = evaluate_performance(seq_file, avl_file, test_sales)

    print("=== Tiempos de Ejecución ===")
    print("Sequential File:")
    for op, t in seq_times.items():
        print(f"{op}: {t:.6f} s")
    print("AVL File:")
    for op, t in avl_times.items():
        print(f"{op}: {t:.6f} s")

    # Graficar resultados comparativos
    plot_results(seq_times, avl_times)
