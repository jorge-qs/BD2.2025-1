import struct
import os

GLOBAL_DEPTH = 8
BUCKET_CAPACITY = 3
HEADER_FORMAT = "ii"  

BUCKET_FORMAT = f"{GLOBAL_DEPTH}sii" + (f"{BUCKET_RECORD_SIZE}i" * BUCKET_CAPACITY) + "i"
BUCKET_SIZE = struct.calcsize(BUCKET_FORMAT)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def pad_str(s, length):
    return s.encode('utf-8')[:length].ljust(length, b' ')

def hash_function(key):
    return key

def binary_hash(key):
    h = hash_function(key)
    return format(h, 'b').zfill(GLOBAL_DEPTH)


class Bucket:
    def __init__(self, identifier, local_depth, capacity):
        self.identifier = identifier
        self.local_depth = local_depth
        self.capacity = capacity
        self.records = []   
        self.size = 0       
        self.overflow = -1  

    def is_full(self):
        return self.size >= self.capacity

    def insert(self, key):
        self.records.append(key)
        self.size += 1

    def search(self, key):
        if key in self.records:
            return True
        if self.overflow != -1:
            bucket = DiskStorage.read_bucket(self.overflow)
            return bucket.search(key)
        return False

    def delete(self, key):
        if key in self.records:
            self.records.remove(key)
            self.size -= 1
            return True
        if self.overflow != -1:
            bucket = DiskStorage.read_bucket(self.overflow)
            return bucket.delete(key)
        return False

    def all_records(self):
        all_rec = self.records.copy()
        if self.overflow != -1:
            bucket = DiskStorage.read_bucket(self.overflow)
            all_rec.extend(bucket.all_records())
        return all_rec

    def clear(self):
        self.records = []
        self.size = 0
        self.overflow = -1

    def pack(self):
        id_bytes = pad_str(self.identifier, GLOBAL_DEPTH)
        recs = self.records + [0]*(self.capacity - self.size)
        return struct.pack(BUCKET_FORMAT, id_bytes, self.local_depth, self.size, *recs, self.overflow)

    @classmethod
    def unpack(cls, data):
        unpacked = struct.unpack(BUCKET_FORMAT, data)
        id_bytes = unpacked[0]
        identifier = id_bytes.decode('utf-8').strip()
        local_depth = unpacked[1]
        size = unpacked[2]
        recs = list(unpacked[3:3+BUCKET_CAPACITY])
        overflow = unpacked[-1]
        bucket = cls(identifier, local_depth, BUCKET_CAPACITY)
        bucket.records = recs[:size]
        bucket.size = size
        bucket.overflow = overflow
        return bucket



class DiskStorage:
    filename = "hash_file.dat"

    @staticmethod
    def initialize_file(global_depth, initial_num_buckets):
        with open(DiskStorage.filename, "wb") as f:
            f.write(struct.pack(HEADER_FORMAT, global_depth, initial_num_buckets))

            bucket0 = Bucket("0", 1, BUCKET_CAPACITY)
            bucket1 = Bucket("1", 1, BUCKET_CAPACITY)
            f.write(bucket0.pack())
            f.write(bucket1.pack())

    @staticmethod
    def read_header():
        with open(DiskStorage.filename, "rb") as f:
            header_data = f.read(HEADER_SIZE)
            global_depth, num_buckets = struct.unpack(HEADER_FORMAT, header_data)
            return global_depth, num_buckets

    @staticmethod
    def write_header(global_depth, num_buckets):
        with open(DiskStorage.filename, "r+b") as f:
            f.seek(0)
            f.write(struct.pack(HEADER_FORMAT, global_depth, num_buckets))

    @staticmethod
    def read_bucket(pos):
        with open(DiskStorage.filename, "rb") as f:
            f.seek(HEADER_SIZE + pos * BUCKET_SIZE)
            data = f.read(BUCKET_SIZE)
            return Bucket.unpack(data)

    @staticmethod
    def write_bucket(bucket, pos):
        with open(DiskStorage.filename, "r+b") as f:
            f.seek(HEADER_SIZE + pos * BUCKET_SIZE)
            f.write(bucket.pack())

    @staticmethod
    def append_bucket(bucket):
        _, num_buckets = DiskStorage.read_header()
        with open(DiskStorage.filename, "r+b") as f:
            f.seek(0, os.SEEK_END)
            pos = num_buckets
            f.write(bucket.pack())
        DiskStorage.write_header(GLOBAL_DEPTH, num_buckets + 1)
        return pos


class ExtendibleHash:
    def __init__(self):
        if not os.path.exists(DiskStorage.filename):
            DiskStorage.initialize_file(GLOBAL_DEPTH, 2)
            self.directory = {"0": 0, "1": 1}
            self.global_depth = GLOBAL_DEPTH
        else:
            self.global_depth, num_buckets = DiskStorage.read_header()
            self.directory = {}
            for pos in range(num_buckets):
                bucket = DiskStorage.read_bucket(pos)
                if bucket.identifier not in self.directory:
                    self.directory[bucket.identifier] = pos

    def get_bucket(self, key):
        bstr = binary_hash(key)
        for d in range(1, self.global_depth + 1):
            prefix = bstr[:d]
            if prefix in self.directory:
                pos = self.directory[prefix]
                return DiskStorage.read_bucket(pos)
        return None

    def update_directory_after_split(self, old_bucket, bucket0, bucket1):
        old_id = old_bucket.identifier
        new_id_0 = "0" + old_id
        new_id_1 = "1" + old_id
        if old_id in self.directory:
            del self.directory[old_id]
        pos0 = DiskStorage.append_bucket(bucket0)
        pos1 = DiskStorage.append_bucket(bucket1)
        self.directory[new_id_0] = pos0
        self.directory[new_id_1] = pos1

    def split_bucket(self, bucket, pos):
        old_local_depth = bucket.local_depth
        new_local_depth = old_local_depth + 1
        old_id = bucket.identifier
        new_id_0 = "0" + old_id
        new_id_1 = "1" + old_id

        bucket0 = Bucket(new_id_0, new_local_depth, BUCKET_CAPACITY)
        bucket1 = Bucket(new_id_1, new_local_depth, BUCKET_CAPACITY)

        all_keys = bucket.all_records()
        bucket.clear()

        for key in all_keys:
            bstr = binary_hash(key)
            prefix = bstr[:new_local_depth]
            if prefix == new_id_0:
                bucket0.insert(key)
            elif prefix == new_id_1:
                bucket1.insert(key)
            else:
                bucket0.insert(key)
        self.update_directory_after_split(bucket, bucket0, bucket1)

    def insert(self, key):
        bucket = self.get_bucket(key)
        bstr = binary_hash(key)
        bucket_id = None
        for d in range(1, self.global_depth + 1):
            prefix = bstr[:d]
            if prefix in self.directory:
                bucket_id = prefix
                break
        pos = self.directory[bucket_id]
        if not bucket.is_full():
            bucket.insert(key)
            DiskStorage.write_bucket(bucket, pos)
        else:
            if bucket.local_depth < self.global_depth:
                self.split_bucket(bucket, pos)
                self.insert(key)
            else:
                current = bucket
                current_pos = pos
                while current.is_full():
                    if current.overflow == -1:
                        new_bucket = Bucket(current.identifier, self.global_depth, BUCKET_CAPACITY)
                        overflow_pos = DiskStorage.append_bucket(new_bucket)
                        current.overflow = overflow_pos
                        DiskStorage.write_bucket(current, current_pos)
                    current = DiskStorage.read_bucket(current.overflow)
                    current_pos = current.overflow  
                current.insert(key)
                DiskStorage.write_bucket(current, current_pos)

    def search(self, key):
        bucket = self.get_bucket(key)
        if bucket:
            return bucket.search(key)
        return False

    def delete(self, key):
        bucket = self.get_bucket(key)
        if bucket:
            result = bucket.delete(key)
            bstr = binary_hash(key)
            for d in range(1, self.global_depth + 1):
                prefix = bstr[:d]
                if prefix in self.directory:
                    pos = self.directory[prefix]
                    break
            DiskStorage.write_bucket(bucket, pos)
            return result
        return False


if __name__ == "__main__":
    EH = ExtendibleHash()

    keys_to_insert = [5, 12, 7, 9, 20, 15, 3, 8, 27, 33, 42]
    for k in keys_to_insert:
        EH.insert(k)

    print("Buscar 7:", EH.search(7))
    print("Buscar 11:", EH.search(11))

    EH.delete(7)
    print("Buscar 7 después de eliminar:", EH.search(7))
