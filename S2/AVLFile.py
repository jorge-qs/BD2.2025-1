AVL_NODE_FORMAT = "=i30sif10siii"
AVL_NODE_SIZE = struct.calcsize(AVL_NODE_FORMAT)
AVL_HEADER_SIZE = 4
SALE_SIZE = struct.calcsize(VENTAS_FORMAT)

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
    sale_data = data[:SALE_SIZE]
    extra = data[SALE_SIZE:]
    sale = unpack_sale(sale_data)
    left, right, height = struct.unpack("iii",extra)
    return AVLNode(sale, left, right, height)

class AVLFile:
  def __init__(self, filename="sales_avl.dat"):
        self.filename = filename
        if not os.path.exists(self.filename) or os.path.getsize(self.filename) < AVL_HEADER_SIZE:
            with open(self.filename, "wb") as f:
                f.write(struct.pack("i", -1))

  def _read_root(self):
    with open(self.filename, "rb") as f:
      f.seek(0)
      return struct.unpack("i", f.read(AVL_HEADER_SIZE))[0]

  def _write_root(self, root_index):
    with open(self.filename, "rb+") as f:
      f.seek(0)
      f.write(struct.pack("i", root_index))

  def _read_node(self,index):
    with open(self.filename, "rb") as f:
      pos = AVL_HEADER_SIZE + index* AVL_NODE_SIZE
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


    #####################################
    # Métodos AVL en memoria integrados con persistencia
    #####################################
  def _height(self, idx, nodes):
        return nodes[idx].height if idx != -1 else 0

  def _update_height(self, idx, nodes):
    nodes[idx].height = max(self._height(nodes[idx].left, nodes),
                            self._height(nodes[idx].right, nodes)) + 1

  def _balance_factor(self,idx,nodes):
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
    return [sale for sale in result if init_id <= sale["id"]<=end_id]

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

  #pruebas

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

    avl_file = AVLFile("sales_avl.dat")

    print("Insertando registros en el árbol AVL persistente...")
    for sale in test_sales:
        avl_file.insert(sale)

    print("\nRegistros en el árbol AVL (in-order):")
    root, nodes = avl_file.load_tree()
    def inorder(idx, nodes, result):
        if idx == -1:
            return
        inorder(nodes[idx].left, nodes, result)
        result.append(nodes[idx].sale)
        inorder(nodes[idx].right, nodes, result)
    result = []
    inorder(root, nodes, result)
    for sale in result:
        print(sale)

    print("\nBuscando venta con id 10:")
    result_sale = avl_file.search(10)
    print(result_sale if result_sale is not None else "Venta no encontrada.")

    print("\nBúsqueda por rango (id 5 a 15):")
    for sale in avl_file.rangeSearch(5, 15):
        print(sale)

    print("\nEliminando venta con id 10...")
    avl_file.remove(10)
    print("Buscando venta con id 10 después de eliminar:")
    result_sale = avl_file.search(10)
    print(result_sale if result_sale is not None else "Venta no encontrada.")
