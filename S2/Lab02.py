!pip install seaborn
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

class SequentialFile:
    def __init__(self, main_filename="sales_main.dat", aux_filename="sales_aux.dat", k=10):
        self.main_file = main_filename
        self.aux_file = aux_filename
        self.k = k

        # Inicializa ambos archivos (con un header de 4 bytes) si no existen o están vacíos.
        for fname, header_val in [(self.main_file, 0), (self.aux_file, 0)]:
            if not os.path.exists(fname) or os.path.getsize(fname) == 0:
                with open(fname, "wb") as f:
                    f.write(struct.pack("i", header_val))

    def _reader_header(self, filename):
        with open(filename, "rb") as f:
            f.seek(0)
            return struct.unpack("i", f.read(4))[0]

    def _write_header(self, filename, val):
        with open(filename, "rb+") as f:
            f.seek(0)
            f.write(struct.pack("i", val))

    def load(self):
        records = []
        for filename in [self.main_file, self.aux_file]:
            header = self._reader_header(filename)
            with open(filename, "rb") as f:
                f.seek(4)  # Saltar el header
                for _ in range(header):
                    data = f.read(VENTAS_SIZE)
                    if len(data) < VENTAS_SIZE:
                        break
                    sale = unpack_sale(data)
                    if sale["id"] != -1:
                        records.append(sale)
        records.sort(key=lambda s: s["id"])
        return records

    def insert(self, sale):
        aux_count = self._reader_header(self.aux_file)
        with open(self.aux_file, "ab") as f:
            f.write(pack_sale(sale))
        self._write_header(self.aux_file, aux_count + 1)
        if aux_count + 1 >= self.k:
            self.rebuild()

    def search(self, sale_id):
        for filename in [self.main_file, self.aux_file]:
            header = self._reader_header(filename)
            with open(filename, "rb") as f:
                f.seek(4)
                for _ in range(header):
                    data = f.read(VENTAS_SIZE)
                    if len(data) < VENTAS_SIZE:
                        break
                    sale = unpack_sale(data)
                    if sale["id"] == sale_id and sale["id"] != -1:
                        return sale
        return None

    def remove(self, sale_id):
        found = False
        for filename in [self.main_file, self.aux_file]:
            header = self._reader_header(filename)
            with open(filename, "rb+") as f:
                f.seek(4)
                for _ in range(header):
                    pos_file = f.tell()
                    data = f.read(VENTAS_SIZE)
                    if len(data) < VENTAS_SIZE:
                        break
                    sale = unpack_sale(data)
                    if sale["id"] == sale_id:
                        sale["id"] = -1
                        f.seek(pos_file)
                        f.write(pack_sale(sale))
                        found = True
                        break
            if found:
                break
        if not found:
            print("Registro no encontrado para eliminación.")

    def rangeSearch(self, init_id, end_id):
        recs = self.load()
        return [r for r in recs if init_id <= r["id"] <= end_id]

    def rebuild(self):
        all_records = self.load()
        with open(self.main_file, "wb") as f:
            f.write(struct.pack("i", len(all_records)))
            for sale in all_records:
                f.write(pack_sale(sale))
        with open(self.aux_file, "wb") as f:
            f.write(struct.pack("i", 0))
        print("Reconstrucción del archivo principal completada.")

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

def evaluate_performance(seq_file, avl_file, test_sales):
    """
    Mide el tiempo de ejecución de las operaciones para Sequential File y AVL File.
    Retorna dos diccionarios con los tiempos.
    """
    seq_times = {}
    avl_times = {}

    # --- Sequential File ---
    # Reiniciar archivos para medición consistente.
    for fname in [seq_file.main_file, seq_file.aux_file]:
        if os.path.exists(fname):
            os.remove(fname)
    seq_file.__init__(seq_file.main_file, seq_file.aux_file, seq_file.k)

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

    start = time.time()
    seq_file.rangeSearch(test_sales[0]["id"], test_sales[-1]["id"])
    end = time.time()
    seq_times["rangeSearch"] = end - start

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
    seq_file = SequentialFile(main_filename="sales_main.dat", aux_filename="sales_aux.dat", k=10)
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
