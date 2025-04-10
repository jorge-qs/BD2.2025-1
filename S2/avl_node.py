import struct
import os

class VentaAVL:
    # Formato: id (int), nombre (30 bytes), cantidad (int), precio (float),
    # fecha (10 bytes), left (int), right (int), height (int)
    FORMAT = 'i30sif10siii'
    RECORD_SIZE = struct.calcsize(FORMAT)
    
    def __init__(self, id_venta=-1, nombre="", cantidad=0, precio=0.0, fecha="",
                 left=-1, right=-1, height=0):
        self.id_venta = id_venta
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio = precio
        self.fecha = fecha
        self.left = left
        self.right = right
        self.height = height
        
    def pack(self) -> bytes:
        # Utilice ljust para llenar espacios en blanco, igual que usar encode y demás.
        nombre_p = self.nombre.encode('utf-8')[:30].ljust(30, b' ')
        fecha_p = self.fecha.encode('utf-8')[:10].ljust(10, b' ')
        return struct.pack(self.FORMAT, self.id_venta, nombre_p, self.cantidad, 
                           self.precio, fecha_p, self.left, self.right, self.height)
    
    def unpack(self, data: bytes):
        datos = struct.unpack(self.FORMAT, data)
        self.id_venta = datos[0]
        self.nombre = datos[1].decode('utf-8').strip()  # Se eliminan los espacios en blanco
        self.cantidad = datos[2]
        self.precio = round(datos[3], 2)
        self.fecha = datos[4].decode('utf-8').strip()
        self.left = datos[5]
        self.right = datos[6]
        self.height = datos[7]
        
    def __str__(self):
        return (f"ID: {self.id_venta}, Producto: {self.nombre}, Cantidad: {self.cantidad}, "
                f"Precio: {self.precio}, Fecha: {self.fecha}, Left: {self.left}, "
                f"Right: {self.right}, Height: {self.height}")

class AVLArchivo:
    HEADER_FORMAT = 'i'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    
    def __init__(self, filename: str):
        self.filename = filename
        # Si el archivo no existe se crea con la cabecera (raíz = -1: árbol vacío)
        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as f:
                self.root = -1
                f.write(struct.pack(self.HEADER_FORMAT, self.root))
        else:
            with open(self.filename, 'rb') as f:
                header = f.read(self.HEADER_SIZE)
                if header:
                    self.root = struct.unpack(self.HEADER_FORMAT, header)[0]
                else:
                    self.root = -1
    
    def get_node(self, pos: int) -> VentaAVL | None:
        if pos < 0:
            return None
        with open(self.filename, 'rb') as f:
            f.seek(self.HEADER_SIZE + pos * VentaAVL.RECORD_SIZE)
            data = f.read(VentaAVL.RECORD_SIZE)
            if not data:
                return None
            nodo = VentaAVL()
            nodo.unpack(data)
            return nodo
    
    def write_node(self, pos: int, nodo: VentaAVL):
        with open(self.filename, 'r+b') as f:
            f.seek(self.HEADER_SIZE + pos * VentaAVL.RECORD_SIZE)
            f.write(nodo.pack())
            
    def append_node(self, nodo: VentaAVL) -> int:
        with open(self.filename, 'ab') as f:
            pos = (f.tell() - self.HEADER_SIZE) // VentaAVL.RECORD_SIZE
            f.write(nodo.pack())
            return pos
        
    def update_header(self, root: int):
        self.root = root
        with open(self.filename, 'r+b') as f:
            f.seek(0)
            f.write(struct.pack(self.HEADER_FORMAT, root))
    
    def node_height(self, pos: int) -> int:
        nodo = self.get_node(pos)
        return nodo.height if nodo else -1
    
    def calc_height(self, pos: int) -> int:
        if pos == -1:
            return -1
        nodo = self.get_node(pos)
        left_height = self.node_height(nodo.left) if nodo.left != -1 else -1
        right_height = self.node_height(nodo.right) if nodo.right != -1 else -1
        return max(left_height, right_height) + 1
    
    def balance_factor(self, pos: int) -> int:
        nodo = self.get_node(pos)
        if nodo is None:
            return 0
        left_height = self.node_height(nodo.left) if nodo.left != -1 else -1
        right_height = self.node_height(nodo.right) if nodo.right != -1 else -1
        return left_height - right_height
    
    def right_rotate(self, pos: int) -> int:
        """
        Realiza rotación a la derecha y retorna la nueva posición de la raíz del subárbol.
        """
        nodo = self.get_node(pos)
        left_pos = nodo.left
        left_node = self.get_node(left_pos)
        # Realizamos la rotación
        nodo.left = left_node.right
        self.write_node(pos, nodo)
        left_node.right = pos
        # Actualizamos alturas
        nodo.height = self.calc_height(pos)
        left_node.height = self.calc_height(left_pos)
        self.write_node(left_pos, left_node)
        return left_pos
    
    def left_rotate(self, pos: int) -> int:
        """
        Realiza rotación a la izquierda y retorna la nueva posición de la raíz del subárbol.
        """
        nodo = self.get_node(pos)
        right_pos = nodo.right
        right_node = self.get_node(right_pos)
        nodo.right = right_node.left
        self.write_node(pos, nodo)
        right_node.left = pos
        # Actualizamos alturas
        nodo.height = self.calc_height(pos)
        right_node.height = self.calc_height(right_pos)
        self.write_node(right_pos, right_node)
        return right_pos
    
    def rebalance(self, pos: int) -> int:
        """
        Rebalancea el subárbol cuya raíz se encuentra en pos.
        """
        nodo = self.get_node(pos)
        nodo.height = self.calc_height(pos)
        bf = self.balance_factor(pos)
        # Caso desequilibrio izquierda
        if bf > 1:
            if self.balance_factor(nodo.left) < 0:
                nodo.left = self.left_rotate(nodo.left)
                self.write_node(pos, nodo)
            return self.right_rotate(pos)
        # Caso desequilibrio derecha
        if bf < -1:
            if self.balance_factor(nodo.right) > 0:
                nodo.right = self.right_rotate(nodo.right)
                self.write_node(pos, nodo)
            return self.left_rotate(pos)
        self.write_node(pos, nodo)
        return pos
    
    def _insert_recursive(self, pos: int, nuevo: VentaAVL) -> int:
        if pos == -1:
            return self.append_node(nuevo)
        nodo = self.get_node(pos)
        if nuevo.id_venta < nodo.id_venta:
            nodo.left = self._insert_recursive(nodo.left, nuevo)
        elif nuevo.id_venta > nodo.id_venta:
            nodo.right = self._insert_recursive(nodo.right, nuevo)
        else:
            # Si el ID ya existe, no se inserta (debería agregar manejo de duplicados?)
            return pos
        self.write_node(pos, nodo)
        pos = self.rebalance(pos)
        return pos
    
    def insert(self, nuevo: VentaAVL):

        if self.root == -1:
            self.root = self.append_node(nuevo)
            self.update_header(self.root)
        else:
            self.root = self._insert_recursive(self.root, nuevo)
            self.update_header(self.root)
    
    def _search_recursive(self, pos: int, id_venta: int) -> int:
        if pos == -1:
            return -1
        nodo = self.get_node(pos)
        if nodo.id_venta == id_venta:
            return pos
        if id_venta < nodo.id_venta:
            return self._search_recursive(nodo.left, id_venta)
        else:
            return self._search_recursive(nodo.right, id_venta)
    
    def search(self, id_venta: int) -> VentaAVL | None:
        pos = self._search_recursive(self.root, id_venta)
        if pos == -1:
            return None
        return self.get_node(pos)
    
    def _min_value_node(self, pos: int) -> int:
        current = pos
        while True:
            nodo = self.get_node(current)
            if nodo.left == -1:
                break
            current = nodo.left
        return current
    
    def _delete_recursive(self, pos: int, id_venta: int) -> int:
        if pos == -1:
            return -1
        nodo = self.get_node(pos)
        if id_venta < nodo.id_venta:
            nodo.left = self._delete_recursive(nodo.left, id_venta)
        elif id_venta > nodo.id_venta:
            nodo.right = self._delete_recursive(nodo.right, id_venta)
        else:
            # Nodo encontrado
            if nodo.left == -1 or nodo.right == -1:
                temp = nodo.left if nodo.left != -1 else nodo.right
                return temp  # Puede ser -1 si es hoja
            else:
                # Si tiene dos hijos, se busca el sucesor en orden.
                succ_pos = self._min_value_node(nodo.right)
                succ = self.get_node(succ_pos)
                # Se copian los datos del sucesor al nodo actual.
                nodo.id_venta = succ.id_venta
                nodo.nombre = succ.nombre
                nodo.cantidad = succ.cantidad
                nodo.precio = succ.precio
                nodo.fecha = succ.fecha
                nodo.right = self._delete_recursive(nodo.right, succ.id_venta)
        self.write_node(pos, nodo)
        pos = self.rebalance(pos)
        return pos
        
    def delete(self, id_venta: int):
        """
        Elimina un nodo (por ID) y reestructura el árbol AVL.
        """
        self.root = self._delete_recursive(self.root, id_venta)
        self.update_header(self.root)
    
    def _range_inorder(self, pos: int, id_min: int, id_max: int, resultados: list):
        if pos == -1:
            return
        nodo = self.get_node(pos)
        if nodo.left != -1:
            self._range_inorder(nodo.left, id_min, id_max, resultados)
        if id_min <= nodo.id_venta <= id_max:
            resultados.append(nodo)
        if nodo.right != -1:
            self._range_inorder(nodo.right, id_min, id_max, resultados)
    
    def range_search(self, id_min: int, id_max: int) -> list[VentaAVL]:
        resultados = []
        self._range_inorder(self.root, id_min, id_max, resultados)
        return resultados

# ──────────────────────────────
# Funciones de prueba (tests) para cada método del AVL

def test_avl_insertion():
    print("Prueba de inserción:")
    file_name = "avl_test.dat"

  if os.path.exists(file_name):
        os.remove(file_name)
    avl = AVLArchivo(file_name)
    
    nodos = [
        VentaAVL(10, "Producto10", 5, 2.5, "2025-01-10"),
        VentaAVL(5,  "Producto5",  3, 1.5, "2025-01-05"),
        VentaAVL(15, "Producto15", 10, 3.0, "2025-01-15"),
        VentaAVL(2,  "Producto2",  7, 0.9, "2025-01-02"),
        VentaAVL(7,  "Producto7",  4, 2.1, "2025-01-07")
    ]
    
    for nodo in nodos:
        avl.insert(nodo)
    
    raiz = avl.get_node(avl.root)
    print("Raíz del AVL:", raiz)
    return avl

def test_avl_search(avl: AVLArchivo):
    print("\nPrueba de búsqueda:")
    id_busqueda = 7
    nodo = avl.search(id_busqueda)
    if nodo:
        print(f"Se encontró el nodo con ID {id_busqueda}:", nodo)
    else:
        print(f"Nodo con ID {id_busqueda} no encontrado.")
    
    id_busqueda = 99
    nodo = avl.search(id_busqueda)
    if nodo:
        print(f"Se encontró el nodo con ID {id_busqueda}:", nodo)
    else:
        print(f"Nodo con ID {id_busqueda} no encontrado.")

def test_avl_range_search(avl: AVLArchivo):
    print("\nPrueba de búsqueda por rango (IDs 3 a 12):")
    resultados = avl.range_search(3, 12)
    for nodo in resultados:
        print(nodo)

def test_avl_deletion(avl: AVLArchivo):
    print("\nPrueba de eliminación:")
    id_eliminar = 5
    print(f"Eliminando el nodo con ID {id_eliminar}...")
    avl.delete(id_eliminar)
    nodo = avl.search(id_eliminar)
    if nodo:
        print(f"El nodo con ID {id_eliminar} sigue existiendo:", nodo)
    else:
        print(f"El nodo con ID {id_eliminar} fue eliminado correctamente.")
    raiz = avl.get_node(avl.root)
    print("Raíz del AVL después de la eliminación:", raiz)

if __name__ == '__main__':
    avl_instance = test_avl_insertion()
    test_avl_search(avl_instance)
    test_avl_range_search(avl_instance)
    test_avl_deletion(avl_instance)
