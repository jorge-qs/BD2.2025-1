
GLOBAL_DEPTH = 8       
BUCKET_CAPACITY = 3    

def hash_function(key: int) -> int:
    return key

def get_binary_key(key: int, d: int) -> str:

    h = hash_function(key)
    # Representación binaria con al menos 'd' bits
    return format(h, 'b').zfill(d)[-d:]  # si 'h' sobrepasa d bits, se toman los d bits menos significativos


class Bucket:
  
    def __init__(self, local_depth: int, capacity: int):
        self.local_depth = local_depth
        self.capacity = capacity
        self.records = []
        self.overflow = None   # Bucket de overflow (si fuese necesario)

    def is_full(self) -> bool:
        return len(self.records) >= self.capacity

    def insert(self, key: int) -> None:
        self.records.append(key)

    def search(self, key: int) -> bool:
        if key in self.records:
            return True
        # Si no está, buscar en el overflow si existe
        if self.overflow:
            return self.overflow.search(key)
        return False

    def delete(self, key: int) -> bool:
        if key in self.records:
            self.records.remove(key)
            return True
        # Buscar en overflow
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

class Node:
    """
    Representa un nodo en el árbol digital (trie de bits).
    Puede ser:
      - Nodo interno (is_leaf = False): 
          * left_child (Node)
          * right_child (Node)
      - Nodo hoja (is_leaf = True):
          * bucket (Bucket)
    """
    def __init__(self, is_leaf: bool = True, bucket: Bucket = None):
        self.is_leaf = is_leaf
        self.bucket = bucket          # Sólo se usa si es hoja
        self.left_child = None        # Nodo hijo al tomar bit = 0
        self.right_child = None       # Nodo hijo al tomar bit = 1


class ExtendibleHashTree:
    def __init__(self, global_depth: int, bucket_capacity: int):
        self.global_depth = global_depth
        self.bucket_capacity = bucket_capacity

        # Creamos la raíz del árbol como un nodo interno 
        # que tendrá 2 hijos (0,1) equivalentes a los 2 buckets iniciales.
        self.root = Node(is_leaf=False)

        # Cada hijo es un nodo hoja con su bucket
        bucket0 = Bucket(local_depth=1, capacity=bucket_capacity)
        bucket1 = Bucket(local_depth=1, capacity=bucket_capacity)

        self.root.left_child = Node(is_leaf=True, bucket=bucket0)   # Sufijo "0"
        self.root.right_child = Node(is_leaf=True, bucket=bucket1)  # Sufijo "1"

    # -------------------------------------------------------------------------
    # Función auxiliar para recorrer el árbol digital (trie) según los bits de la key.
    # Retorna el nodo hoja donde se debería insertar/buscar/eliminar.
    # -------------------------------------------------------------------------
    def descend_tree(self, bits: str, idx: int, node: Node) -> Node:
        # Caso base: si node es hoja o si ya hemos consumido todos los bits
        if node.is_leaf or idx >= len(bits):
            return node
        
        # bit actual
        bit = bits[idx]
        if bit == '0':
            return self.descend_tree(bits, idx + 1, node.left_child)
        else:  # bit == '1'
            return self.descend_tree(bits, idx + 1, node.right_child)


    def insert(self, key: int) -> None:
        bits = get_binary_key(key, self.global_depth)  
        # Descender en el árbol para encontrar el nodo hoja correspondiente
        leaf_node = self.descend_tree(bits, 0, self.root)
        bucket = leaf_node.bucket
        
        # Verificar si el bucket tiene espacio
        if not bucket.is_full():
            bucket.insert(key)
        else:
            # El bucket está lleno; ver si podemos dividir (split) o si aplicamos overflow
            if bucket.local_depth < self.global_depth:
                self.split_leaf(leaf_node, bits)
                # Tras el split, reintentar la inserción
                self.insert(key)
            else:
                # Profundidad local == profundidad global: encadenar overflow
                self.handle_overflow(bucket, key)


    def handle_overflow(self, bucket: Bucket, key: int) -> None:
        current = bucket
        while current.is_full():
            if current.overflow is None:
                # Crear un bucket de overflow con la misma profundidad local
                new_bucket = Bucket(local_depth=bucket.local_depth, capacity=bucket.capacity)
                current.overflow = new_bucket
            current = current.overflow
        current.insert(key)

    # -------------------------------------------------------------------------
    # Split de un nodo hoja:
    #  1. Creamos un nodo interno en lugar del nodo hoja actual.
    #  2. Creamos 2 hojas hijas (bucket0 y bucket1) con local_depth = old_local_depth + 1.
    #  3. Redistribuimos los registros del bucket original (y su overflow) en los 2 nuevos buckets.
    #  4. Reemplazamos el nodo hoja en el árbol con el nodo interno.
    # -------------------------------------------------------------------------
    def split_leaf(self, leaf_node: Node, bits: str) -> None:
        old_bucket = leaf_node.bucket
        old_depth = old_bucket.local_depth
        new_depth = old_depth + 1

        # Crear un nodo interno para reemplazar la hoja actual
        internal_node = Node(is_leaf=False)

        # Crear los 2 nuevos buckets
        bucket0 = Bucket(local_depth=new_depth, capacity=old_bucket.capacity)
        bucket1 = Bucket(local_depth=new_depth, capacity=old_bucket.capacity)

        # Crear nodos hoja que apuntan a los nuevos buckets
        leaf0 = Node(is_leaf=True, bucket=bucket0)
        leaf1 = Node(is_leaf=True, bucket=bucket1)

        internal_node.left_child = leaf0
        internal_node.right_child = leaf1

        # Obtener todos los registros en el bucket original (incluyendo overflow)
        all_keys = old_bucket.all_records()

        # Vaciar el bucket original
        old_bucket.clear()

        # Reasignar cada registro a uno de los 2 nuevos buckets,
        # basándonos en los (new_depth) bits de la key
        for k in all_keys:
            bstr = get_binary_key(k, self.global_depth)
            # Tomamos los primeros new_depth bits (o la porción que se use) 
            # para decidir 0 o 1. Decidimos leer bit por bit
            # de izquierda a derecha y comparamos con la profundidad local.
            # Aquí, para mayor simplicidad, usaremos el bit (old_depth) de bstr:
            bit_position = old_depth  # bit que define a 0 o 1 en este split
            if bit_position < len(bstr):
                if bstr[bit_position] == '0':
                    bucket0.insert(k)
                else:
                    bucket1.insert(k)
            else:
                # Si no hay más bits, por convención lo enviamos a bucket0
                bucket0.insert(k)

        # Reemplazar el leaf_node con el nuevo nodo interno en el árbol
        # Como estamos en pseudocódigo, supondremos que 'leaf_node' está refereciado
        # directamente y podemos copiar los atributos del internal_node.
        leaf_node.is_leaf = False
        leaf_node.bucket = None
        leaf_node.left_child = internal_node.left_child
        leaf_node.right_child = internal_node.right_child

        # Ajustar la profundidad local del nodo ya no aplica, 
        # pues ahora es nodo interno y no mantiene 'local_depth'.


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
            return leaf_node.bucket.delete(key)
        return False

    # -------------------------------------------------------------------------
    # (Opcional) Rehashing / Contracción del árbol
    # -------------------------------------------------------------------------

if __name__ == "__main__":
    EHTree = ExtendibleHashTree(global_depth=GLOBAL_DEPTH, bucket_capacity=BUCKET_CAPACITY)

    keys_to_insert = [5, 12, 7, 9, 20, 15, 3, 8, 27, 33, 42]
    for key in keys_to_insert:
        EHTree.insert(key)

    print("Buscar 7:", EHTree.search(7))
    print("Buscar 11:", EHTree.search(11))

    EHTree.delete(7)
    print("Buscar 7 después de eliminar:", EHTree.search(7))
