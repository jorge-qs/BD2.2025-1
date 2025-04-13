GLOBAL_DEPTH = 8        
BUCKET_CAPACITY = 3     

def hash_function(key):
    # Función hash simple; se asume que key es un entero.
    return key

def binary_hash(key):
    """
    Retorna la representación binaria del valor hash de 'key' como cadena,
    rellenando con ceros a la izquierda hasta tener al menos GLOBAL_DEPTH bits.
    """
    h = hash_function(key)
    return format(h, 'b').zfill(GLOBAL_DEPTH)


class Bucket:
    def __init__(self, identifier, local_depth, capacity):
        self.identifier = identifier          
        self.local_depth = local_depth        
        self.capacity = capacity              
        self.records = []                    
        self.overflow = None                  

    def is_full(self):
        return len(self.records) >= self.capacity

    def insert(self, key):
        self.records.append(key)

    def search(self, key):
        if key in self.records:
            return True
        elif self.overflow:
            return self.overflow.search(key)
        else:
            return False

    def delete(self, key):
        if key in self.records:
            self.records.remove(key)
            return True
        elif self.overflow:
            return self.overflow.delete(key)
        else:
            return False

    def all_records(self):
        # Retorna todos los registros incluyendo los almacenados en los buckets encadenados.
        all_rec = self.records.copy()
        if self.overflow:
            all_rec.extend(self.overflow.all_records())
        return all_rec

    def clear(self):
        # Reinicia el bucket (sin borrar el overflow, se usan para reinsertar registros)
        self.records = []
        self.overflow = None


class ExtendibleHash:
    def __init__(self, global_depth, bucket_capacity):
        self.global_depth = global_depth          
        self.bucket_capacity = bucket_capacity
        self.directory = {}
        bucket0 = Bucket(identifier="0", local_depth=1, capacity=bucket_capacity)
        bucket1 = Bucket(identifier="1", local_depth=1, capacity=bucket_capacity)
        self.directory["0"] = bucket0
        self.directory["1"] = bucket1

    def get_bucket(self, key):
        
        bstr = binary_hash(key)  # Cadena binaria de tamaño GLOBAL_DEPTH
        for d in range(1, self.global_depth + 1):
            suffix = bstr[-d:]   # Tomar los últimos d bits
            if suffix in self.directory:
                return self.directory[suffix]
        return None

    def update_directory_after_split(self, old_bucket, bucket0, bucket1):
        old_id = old_bucket.identifier
        new_id_0 = old_id + "0"
        new_id_1 = old_id + "1"
        if old_id in self.directory:
            del self.directory[old_id]
        self.directory[new_id_0] = bucket0
        self.directory[new_id_1] = bucket1

    def split_bucket(self, bucket):

        old_local_depth = bucket.local_depth
        new_local_depth = old_local_depth + 1
        old_id = bucket.identifier
        new_id_0 = old_id + "0"
        new_id_1 = old_id + "1"

        # Crear dos nuevos buckets con la nueva profundidad local.
        bucket0 = Bucket(identifier=new_id_0, local_depth=new_local_depth, capacity=self.bucket_capacity)
        bucket1 = Bucket(identifier=new_id_1, local_depth=new_local_depth, capacity=self.bucket_capacity)
        
        # Obtener todos los registros del bucket (incluyendo los de overflow)
        all_keys = bucket.all_records()
        
        # Vaciar el bucket original para reinserción.
        bucket.clear()
        
        # Redistribuir cada registro según su sufijo de longitud new_local_depth.
        for key in all_keys:
            bstr = binary_hash(key)
            suffix = bstr[-new_local_depth:]
            if suffix == new_id_0:
                bucket0.insert(key)
            elif suffix == new_id_1:
                bucket1.insert(key)
            else:
                # Por diseño, el sufijo debe coincidir con uno de los dos.
                bucket0.insert(key)
        # Actualizar el directorio: eliminar la entrada del bucket original y agregar las nuevas.
        self.update_directory_after_split(bucket, bucket0, bucket1)

    def insert(self, key):
        bucket = self.get_bucket(key)
        if not bucket.is_full():
            bucket.insert(key)
        else:
            # El bucket está lleno.
            if bucket.local_depth < self.global_depth:
                # Se puede aplicar el split (dividir el bucket y agregar una nueva entrada al índice).
                self.split_bucket(bucket)
                # Reintentar la inserción una vez actualizado el índice.
                self.insert(key)
            else:
                # Se ha alcanzado la profundidad global; aplicar chaining (encadenamiento) para overflow.
                current = bucket
                while current.is_full():
                    if current.overflow is None:
                        # Crear un nuevo bucket de overflow con misma identificación y profundidad.
                        current.overflow = Bucket(identifier=current.identifier,
                                                  local_depth=self.global_depth,
                                                  capacity=self.bucket_capacity)
                    current = current.overflow
                current.insert(key)

    def search(self, key):
        bucket = self.get_bucket(key)
        if bucket:
            return bucket.search(key)
        return False

    def delete(self, key):
        bucket = self.get_bucket(key)
        if bucket:
            return bucket.delete(key)
        return False


if __name__ == "__main__":
    EH = ExtendibleHash(global_depth=GLOBAL_DEPTH, bucket_capacity=BUCKET_CAPACITY)
    
    # Inserción de claves
    keys_to_insert = [5, 12, 7, 9, 20, 15, 3, 8, 27, 33, 42]
    for k in keys_to_insert:
        EH.insert(k)
    
    # Búsqueda de algunas claves
    print("Buscar 7:", EH.search(7))
    print("Buscar 11:", EH.search(11))
    
    # Eliminación de una clave
    EH.delete(7)
    print("Buscar 7 después de eliminar:", EH.search(7))
