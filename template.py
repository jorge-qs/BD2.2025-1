import os
import struct
import logging


class CustomLogger:
	def __init__ (self, name = "CustomLogger"):
		self.logger = logging.getLogger(name)
		self.logger.setLevel(logging.DEBUG)
		console_handler = logging.StreamHandler() # show in console
		console_handler.setLevel(logging.DEBUG) # minimum logs to appear

		formatter = logging.Formatter('%(levelname)s - %(message)s')
		console_handler.setFormatter(formatter) # format logs

		self.logger.addHandler(console_handler) # handler
	
	def foundRecord(self, file, pos, id):
		self.logger.info(f"Found record with id: {id} in file: {file} at position: {pos}")

	def notFoundRecord(self, file, pos):
		self.logger.warning(f"Not found record at position: {pos} in file: {file}")
	
	def invalidPosition(self, file, pos):
		self.logger.error(f"Tried to access invalid position: {pos} at file: {file}")

	def writingRecord(self, file, pos, id):
		self.logger.info(f"Writing record with id: {id} in file: {file} at position: {pos}")

	def warning(self, text):
		self.logger.warning(text)
	
	def error(self, text):
		self.logger.error(text)
	
	def info(self, text):
		self.logger.info(text)
	
	def debug(self, text):
		self.logger.debug(text)



class Venta:
	FORMAT = "i30sif10siii"
	RECORD_SIZE = struct.calcsize(FORMAT)
	def __init__(self, id = 0, nombre = "", cantidad = 0, precio = 0, fecha = "", left = -1, right = -1):
		self.id = id
		self.nombre = nombre
		self.cantidad = cantidad
		self.precio = precio
		self.fecha = fecha
		self.left = left
		self.right = right

	def print(self):
		print(self.id, self.nombre, self.cantidad, self.precio, self.fecha, self.left, self.right)

	def pack(self) -> bytes:
		return struct.pack(self.FORMAT, self.id, 
						   self.nombre.encode(), 
						   self.cantidad, 
						   self.precio, 
						   self.fecha.encode(), 
						   self.left, 
						   self.right)
	
	def unpack(self, record:bytes):
		id, nombre, cantidad, precio, fecha, left, right = struct.unpack(self.FORMAT, record)
		self.id = id
		self.nombre = nombre.decode().strip()
		self.cantidad = cantidad
		self.precio = precio
		self.fecha = fecha.decode().strip()
		self.left = left
		self.right = right

class AVL:
	HEADER_FORMAT = "i"
	HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
	def __init__(self, filename):

		self.logger = CustomLogger("AVLLogger")

		self.filename = filename
		if not os.path.exists(self.filename):
			self.logger.warning("Archive doesn't exists, initializing it")
			self.initialize_file(filename) # if archive not exists
		else:
			with open(filename, "rb+") as file:
				file.seek(0,2)
				if(file.tell() == 0):
					self.logger.warning("Archive is empty, initializing it")
					self.initialize_file(filename) # if archive is empty
			
	def initialize_file(self, filename):
		with open(filename, "wb") as file:
			header = 0
			file.write(struct.pack("i", header))

	def get(self, pos:int) -> Venta | None:
		if pos < 0:
			self.logger.invalidPosition(self.filename, pos)
			return None
		with open(self.filename, "rb") as file:
			data = Venta()
			file.seek(self.HEADER_SIZE + pos * data.RECORD_SIZE)
			data = file.read(data.RECORD_SIZE)
			if not data:
				self.logger.notFoundRecord(self.filename, pos)
				return None
			data.unpack(data)
			self.logger.foundRecord(self.filename, pos, data.id)
			return data
	
	def post(self, data: Venta) -> int:
		with open(self.filename, "rb+") as file:
			file.seek(0, 2)
			pos = (file.tell() - self.HEADER_SIZE) // data.RECORD_SIZE
			self.logger.writingRecord(self.filename, pos, data.id)
			file.write(data.pack())

			return pos
	
	def patch(self, pos, data: Venta):
		with open(self.filename, "rb+") as file:
			file.seek(self.HEADER_SIZE + pos * data.RECORD_SIZE)
			self.logger.writingRecord(self.filename, pos, data.id)
			file.write(data.pack())

	def put_header(self, header):
		with open(self.filename, "rb+") as file:
			self.logger.info(f"Writing header with: {header}")
			file.write(struct.pack(self.HEADER_FORMAT, header))
	
	def get_header(self):
		with open(self.filename, "rb") as file:
			header = struct.unpack(self.HEADER_FORMAT,file.read(self.HEADER_SIZE))
			self.logger.info(f"Getting header: {header}")
	

import unittest
import tempfile

class TestAVLFile(unittest.TestCase):
	def setUp(self):
		self.principal = tempfile.NamedTemporaryFile(delete = False)
		self.avl = AVL(self.principal.name)

	def tearDown(self):
		os.remove(self.principal.name)
		os.remove(self.aux.name)
	
	def testInsert(self):
		venta = Venta(1, "Producto", 2, 3, "02-03-2025")
		self.avl.insert(venta)

		record = self.avl.get(0)
		self.assertIsNotNone(record)
		self.assertEqual(record.id, 1)