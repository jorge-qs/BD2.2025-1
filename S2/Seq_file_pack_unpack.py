import struct

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
      "product": product_bytes.decode("utf-8").rstrip("\x00"),
      "qty": qty,
      "price": price,
      "date": date_bytes.decode("utf-8").strip()
  }

if __name__ == "__main__":

  ejemplo_ventas = {
      "id": 123,
      "product": "Laptop MSI",
      "qty":2,
      "price": 1500.75,
      "date": "2025-04-01"
  }

  packed = pack_sale(ejemplo_ventas)
  print("Bytes empaquetados (tamaño =", len(packed), "):", packed)

  unpacked = unpack_sale(packed)
  print("Registro desempaquetado:", unpacked)
