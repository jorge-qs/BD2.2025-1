import os
import pickle

GLOBAL_DEPTH = 8       
BUCKET_CAPACITY = 3    

def hash_function(key: int) -> int:
    return key


def get_binary_key(key: int, d: int) -> str:
    h = hash_function(key)
    return format(h, 'b').zfill(d)[-d:]



class Bucket:
    def __init__(self, local_depth: int, capacity: int):
        self.local_depth = local_depth
        self.capacity = capacity
        self.records = []      
        self.overflow = None   

    def is_full(self) -> bool:
        return len(self.records) >= self.capacity

    def insert(self, key: int) -> None:
        self.records.append(key)

    def search(self, key: int) -> bool:
        if key in self.records:
            return True
        if self.overflow:
            return self.overflow.search(key)
        return False

    def delete(self, key: int) -> bool:
        if key in self.records:
            self.records.remove(key)
            return True
        if self.overflow:
            return self.overflow.delete(key)
        return False

    def all_records(self) -> list:
        result = self.records.copy()
        if self.overflow:
            result.extend(self.overflow.all_records())
        return result

    def clear(self) -> None:
        self.records = []
        self.overflow = None

    def __repr__(self):
        return f"Bucket(ld={self.local_depth}, recs={self.records}, overflow={self.overflow is not None})"


class Node:

    def __init__(self, is_leaf: bool = True, bucket: Bucket = None):
        self.is_leaf = is_leaf
        self.bucket = bucket          # Sólo se usa si es hoja
        self.left_child = None        # Nodo hijo para bit '0'
        self.right_child = None       # Nodo hijo para bit '1'

    def __repr__(self):
        if self.is_leaf:
            return f"Leaf({self.bucket})"
        else:
            return f"Internal(Left={self.left_child}, Right={self.right_child})"



class ExtendibleHashTree:
    def __init__(self, global_depth: int, bucket_capacity: int, filename: str):
        self.filename = filename
        # Si existe el archivo, cargar la estructura persistida
        if os.path.exists(self.filename):
            loaded_tree = ExtendibleHashTree.load_tree(self.filename)
            self.__dict__.update(loaded_tree.__dict__)
        else:
            self.global_depth = global_depth
            self.bucket_capacity = bucket_capacity
            # Inicializamos la raíz como nodo interno que apunta a dos nodos hoja
            self.root = Node(is_leaf=False)
            bucket0 = Bucket(local_depth=1, capacity=bucket_capacity)
            bucket1 = Bucket(local_depth=1, capacity=bucket_capacity)
            self.root.left_child = Node(is_leaf=True, bucket=bucket0)   # Prefijo "0"
            self.root.right_child = Node(is_leaf=True, bucket=bucket1)  # Prefijo "1"
            self.save()

    @staticmethod
    def load_tree(filename: str):
        with open(filename, "rb") as f:
            return pickle.load(f)

    def save(self):
        with open(self.filename, "wb") as f:
            pickle.dump(self, f)

    # Función auxiliar para descender en el árbol según los bits de la clave.
    def descend_tree(self, bits: str, idx: int, node: Node) -> Node:
        # Caso base: si el nodo es hoja o ya se han consumido todos los bits
        if node.is_leaf or idx >= len(bits):
            return node
        bit = bits[idx]
        if bit == '0':
            return self.descend_tree(bits, idx + 1, node.left_child)
        else:
            return self.descend_tree(bits, idx + 1, node.right_child)

    # Inserta una clave en el árbol
    def insert(self, key: int) -> None:
        bits = get_binary_key(key, self.global_depth)
        leaf_node = self.descend_tree(bits, 0, self.root)
        bucket = leaf_node.bucket

        if not bucket.is_full():
            bucket.insert(key)
            self.save()
        else:
            # Si el bucket está lleno, decidir entre hacer split o usar overflow
            if bucket.local_depth < self.global_depth:
                self.split_leaf(leaf_node, bits)
                # Después del split, se reintenta la inserción
                self.insert(key)
            else:
                # Cuando la profundidad local es igual a la global, se aplica overflow
                self.handle_overflow(bucket, key)
                self.save()

    # Manejo del overflow: se encadena un bucket de overflow si es necesario
    def handle_overflow(self, bucket: Bucket, key: int) -> None:
        current = bucket
        while current.is_full():
            if current.overflow is None:
                new_bucket = Bucket(local_depth=bucket.local_depth, capacity=bucket.capacity)
                current.overflow = new_bucket
            current = current.overflow
        current.insert(key)

    # División (split) de un nodo hoja que está lleno
    def split_leaf(self, leaf_node: Node, bits: str) -> None:
        old_bucket = leaf_node.bucket
        old_depth = old_bucket.local_depth
        new_depth = old_depth + 1

        # Crear un nodo interno para reemplazar el nodo hoja actual
        internal_node = Node(is_leaf=False)

        # Crear dos nuevos buckets con profundidad incrementada
        bucket0 = Bucket(local_depth=new_depth, capacity=old_bucket.capacity)
        bucket1 = Bucket(local_depth=new_depth, capacity=old_bucket.capacity)

        # Crear nodos hoja que contienen los nuevos buckets
        leaf0 = Node(is_leaf=True, bucket=bucket0)
        leaf1 = Node(is_leaf=True, bucket=bucket1)

        internal_node.left_child = leaf0
        internal_node.right_child = leaf1

        # Obtener todas las claves del bucket original (incluyendo overflow)
        all_keys = old_bucket.all_records()
        old_bucket.clear()

        # Reasignar cada clave a uno de los nuevos buckets según el bit que corresponda
        for k in all_keys:
            bstr = get_binary_key(k, self.global_depth)
            # Usamos el bit en la posición old_depth para decidir a qué bucket asignar
            if old_depth < len(bstr) and bstr[old_depth] == '0':
                bucket0.insert(k)
            else:
                bucket1.insert(k)

        # Reemplazar la hoja actual con el nuevo nodo interno (se copia la estructura)
        leaf_node.is_leaf = False
        leaf_node.bucket = None
        leaf_node.left_child = internal_node.left_child
        leaf_node.right_child = internal_node.right_child

        self.save()

    def search(self, key: int) -> bool:
        bits = get_binary_key(key, self.global_depth)
        leaf_node = self.descend_tree(bits, 0, self.root)
        if leaf_node.is_leaf and leaf_node.bucket:
            return leaf_node.bucket.search(key)
        return False

    def delete(self, key: int) -> bool:
        bits = get_binary_key(key, self.global_depth)
        leaf_node = self.descend_tree(bits, 0, self.root)
        if leaf_node.is_leaf and leaf_node.bucket:
            result = leaf_node.bucket.delete(key)
            self.save()
            return result
        return False

    # (Opcional) Aquí se podrían agregar métodos para rehashing o contracción del árbol

    def __repr__(self):
        return f"ExtendibleHashTree(global_depth={self.global_depth}, root={self.root})"



if __name__ == "__main__":
    filename = "ehtree.pkl"
    if os.path.exists(filename):
        os.remove(filename)

    EHTree = ExtendibleHashTree(global_depth=GLOBAL_DEPTH, bucket_capacity=BUCKET_CAPACITY, filename=filename)

    keys_to_insert = [5, 12, 7, 9, 20, 15, 3, 8, 27, 33, 42]
    for key in keys_to_insert:
        EHTree.insert(key)
        print(f"Insertado: {key}")

    print("Buscar 7:", EHTree.search(7))
    print("Buscar 11:", EHTree.search(11))

    EHTree.delete(7)
    print("Buscar 7 después de eliminar:", EHTree.search(7))
