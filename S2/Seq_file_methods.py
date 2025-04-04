import struct
import os

VENTAS_FORMAT = "=i30sif10s"

VENTAS_SIZE = struct.calcsize(VENTAS_FORMAT)


class SequentialFile:
  def __init__(self, main_filename="sales_main.dat", aux_filename="sales_aux.dat", k=10):
    self.main_file = main_filename
    self.aux_file = aux_filename
    self.k =k

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


  def load (self):
    records = []
    for filename in [self.main_file, self.aux_file]:
      header = self._reader_header(filename)
      with open(filename, "rb") as f:
        f.seek(4)
        for _ in range(header):
          data = f.read(VENTAS_SIZE)

          if len(data) < VENTAS_SIZE:
            break
          sale = unpack_sale(data)

          if sale["id"] != -1:
            records.append(sale)

    records.sort(key=lambda s: s["id"])
    return records

  def insert (self, sale):
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
          if sale["id"] == sale_id and sale ["id"] != -1:
            return sale
    return None


  def remove(self, sale_id):
    found = False
    for filename in [self.main_file, self.aux_file]:
      header = self._reader_header(filename)
      with open(filename, "rb+") as f:
        f.seek(4)
        for i in range(header):
          por_file = f.tell()
          data = f.read(VENTAS_SIZE)
          if len(data) < VENTAS_SIZE:
            break
          sale = unpack_sale(data)

          if sale["id"] == sale_id:
            sale["id"] = -1
            f.seek(por_file)
            f.write(pack_sale(sale))
            found = True
            break
      if found:
        break
    if not found:
      print("Registro no encontrado para eliminación")


  def rangeSearch(self, init_id, end_id):
    recs = self.load()
    return [r for r in recs if init_id <= r["id"] <= end_id]


  def rebuild(self):
    all_records = self.load()
    with open(self.main_file, "wb") as f:
      f.write(struct.pack("i", len(all_records)))
      for r in all_records:
        f.write(pack_sale(r))

    with open(self.aux_file, "wb") as f:
      f.write(struct.pack("i", 0))

    print("Reconstrucción del archivo principal completada.")

if __name__ == "__main__":
    test_sales = []
    for i in range(1, 21):
        sale = {
            "id": i,
            "product": f"Producto_{i}",
            "qty": (i % 10) + 1,
            "price": 100.0 + i,
            "date": "2025-03-30"
        }
        test_sales.append(sale)

    seq_file = SequentialFile(main_filename="sales_main.dat", aux_filename="sales_aux.dat", k=5)

    print("Insertando registros en el archivo secuencial...")
    for sale in test_sales:
        seq_file.insert(sale)

    records = seq_file.load()
    print("Registros cargados (ordenados):")
    for rec in records:
        print(rec)

    print("\nBuscando venta con id 10:")
    result = seq_file.search(10)
    print(result)

    print("\nBúsqueda por rango (id 5 a 15):")
    for r in seq_file.rangeSearch(5, 15):
        print(r)

    print("\nEliminando venta con id 10")
    seq_file.remove(10)
    records = seq_file.load()
    print("Registros tras eliminación:")
    for rec in records:
        print(rec)

