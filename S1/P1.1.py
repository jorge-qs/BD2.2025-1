# CODE HERE
import struct
import os

class Alumno:
	def __init__(self, codigo, nombre, apellidos, carrera, ciclo, mensualidad):
		self.codigo = codigo
		self.nombre = nombre
		self.apellidos = apellidos
		self.carrera = carrera
		self.ciclo = ciclo
		self.mensualidad = mensualidad
	
	def print(self):
		print(self.codigo, self.nombre, self.apellidos, self.carrera, self.ciclo, self.mensualidad)

FORMAT = '5s11s20s15sii'
RECORD_SIZE = struct.calcsize(FORMAT)
HEADER_SIZE = 4

class MoveTheLast:
	def __init__(self, filename):
		self.filename = filename
		if not os.path.exists(self.filename):
			self.initialize_file(filename) # if archive not exists
		else:
			with open(filename, "rb+") as file:
				file.seek(0,2)
				if(file.tell() == 0):
					self.initialize_file(filename) # if archive is empty
			
	def initialize_file(self, filename):
		with open(filename, "wb") as file:
			header = 0
			file.write(struct.pack("i", header))
	
	def readHeader(self):
		header = -1
		with open(self.filename, "rb") as file:
			file.seek(0)
			header = struct.unpack("i", file.read(HEADER_SIZE))[0]		
		return header
	
	def unpackRecord(self, record):
		if not record:
			return None
		codigo, nombre, apellidos, carrera, ciclo, mensualidad = struct.unpack(FORMAT, record)
		return Alumno(codigo.decode().strip(), nombre.decode().strip(), apellidos.decode().strip(), carrera.decode().strip(), ciclo, mensualidad)
	
	def packAlumno(self, alumno: Alumno):
		return struct.pack(FORMAT, alumno.codigo.encode(), alumno.nombre.encode(), alumno.apellidos.encode(), alumno.carrera.encode(), alumno.ciclo, alumno.mensualidad)
	
	def load(self):
		header = self.readHeader()
		alumnos = []
		with open(self.filename, "rb") as file:
			file.seek(HEADER_SIZE)
			for _ in range(header): # loop for all lines to header
				record = file.read(RECORD_SIZE)
				alumnos.append(self.unpackRecord(record))
		for alumno in alumnos:
			alumno.print()
		return alumnos

	
	def add(self, alumno:Alumno):
		header = self.readHeader()
		with open(self.filename, "rb+") as file:
			file.seek(HEADER_SIZE + header * RECORD_SIZE) # pointer at the end
			file.write(self.packAlumno(alumno))
			file.seek(0)
			file.write(struct.pack("i", header + 1)) # actualize header + 1
	
	def readRecord(self, pos:int):
		alumno = ""
		with open(self.filename, "rb") as file:
			file.seek(HEADER_SIZE + pos * RECORD_SIZE) # pointer at line pos
			record = file.read(RECORD_SIZE)
			alumno = self.unpackRecord(record)
		if not alumno:
			print("Record not found")
		else:
			alumno.print()
		return alumno
	
	def remove(self, pos:int):
		header = self.readHeader()
		with open(self.filename, "rb+") as file:
			if pos > header:
				print("No record in position:", pos)
			else:
				file.seek(HEADER_SIZE + (header - 1) * RECORD_SIZE) # pointer before the end line
				record = file.read(RECORD_SIZE)
				file.seek(HEADER_SIZE + pos * RECORD_SIZE)
				file.write(record)
				file.seek(0)
				file.write(struct.pack("i", header - 1)) # actualize header - 1

f = MoveTheLast("data.dat")
a = Alumno("P-123", "Eduardo", "Aragon", "CS", 5, 500)
b = Alumno("P-124", "Jorge", "Quenta", "DS", 5, 2000)
c = Alumno("P-125", "Jose", "Quenta", "DS", 5, 2000)
d = Alumno("P-126", "Maria", "Quenta", "CS", 5, 2000)

def func():
	f.add(a)
	f.add(b)
	f.add(c)
	f.load()
	print()
	f.readRecord(1)

#func()
#f.remove(1)
#f.load()
#f.add(d)
#f.readRecord(1)
f.load()