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

FORMAT = '5s11s20s15siii'
RECORD_SIZE = struct.calcsize(FORMAT)
HEADER_SIZE = 4

class FreeList:
	def __init__(self, filename):
		self.filename = filename
		if not os.path.exists(self.filename):
			self.initialize_file(filename)

	def initialize_file(self, filename):
		with open(filename, "wb") as file:
			MINUS_1 = -1
			header = struct.pack("i", MINUS_1)
			file.write(header)
	
	def readHeader(self):
		header = -1
		with open(self.filename, "rb") as file:
			file.seek(0)
			header = file.read(HEADER_SIZE)
			header = struct.unpack("i", header)[0]
		
		return header
	
	def read_record(self, pos):
		record = ""
		with open(self.filename, "rb") as file:
			file.seek(HEADER_SIZE + pos * RECORD_SIZE)
			record = file.read(RECORD_SIZE)
			if not record:
				return None
		return self.unpackRecord(record)

	def readRecord(self, pos):
		[alumno, nextDel] = self.read_record(pos)
		if(nextDel == -2):
			alumno.print()
		else:
			print("record has been deleted")
	
	def packAlumno(self, alumno:Alumno, nextDel:int):
		return struct.pack(FORMAT, alumno.codigo.encode(), alumno.nombre.encode(), alumno.apellidos.encode(), alumno.carrera.encode(), alumno.ciclo, alumno.mensualidad, nextDel)

	def unpackRecord(self, record):
		if not record:
			return None
		codigo, nombre, apellidos, carrera, ciclo, mensualidad, nextDel = struct.unpack(FORMAT, record)
		return [Alumno(codigo.decode().strip(), nombre.decode().strip(), apellidos.decode().strip(), carrera.decode().strip(), ciclo, mensualidad), nextDel]

	def add(self, alumno: Alumno):
		header = self.readHeader()
		with open(self.filename, "rb+") as file:
			if header == -1:
				file.seek(0, 2) # append to the end
				new_record = self.packAlumno(alumno, -2)
				file.write(new_record)
			else:
				old_pos = self.read_record(header)[1]
				# writing new record
				file.seek(HEADER_SIZE + header * RECORD_SIZE, 0)
				new_record = self.packAlumno(alumno, -2)
				file.write(new_record)

				# writing new header
				file.seek(0, 0)
				file.write(struct.pack("i", old_pos))

	def remove(self, pos: int):
		header = self.readHeader()
		with open(self.filename, "rb+") as file:
			file.seek(HEADER_SIZE + ((pos + 1) * RECORD_SIZE) - 4, 0) # pointer at the nextDel position
			file.write(struct.pack("i", header))
			file.seek(0, 0)
			file.write(struct.pack("i", pos))
	
	def load(self):
		alumnos = []
		with open(self.filename, "rb") as file:
			file.seek(4, 0)
			while True:
				record = file.read(RECORD_SIZE) # also advance pointer 0.0
				if not record: break
				record = self.unpackRecord(record)
				if record[1] == -2:
					alumnos.append(record[0])

		for alumno in alumnos:
			alumno.print()

f = FreeList("lab1.dat")
a = Alumno("P-123", "Eduardo", "Aragon", "CS", 5, 500)
b = Alumno("P-124", "Jorge", "Quenta", "DS", 5, 2000)
c = Alumno("P-125", "Jose", "Quenta", "DS", 5, 2000)
d = Alumno("P-126", "Maria", "Quenta", "CS", 5, 2000)

def func1():
	f.add(a)
	f.add(b)
	f.add(c)
	f.readRecord(1)

#f.remove(2)
#f.readRecord(2)

#func1()
#f.add(b)
f.load()