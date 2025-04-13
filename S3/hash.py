import struct
import os

fb = 4
M = 3

class Record():
	FORMAT = "i" * (fb + 2)
	RECORD_SIZE = struct.calcsize(FORMAT)
	def __init__(self, ar = [-1 for i in range(fb)], next = -1, cant = 0):
		self.ar = ar
		self.next = next
		self.cant = cant
	
	def pack(self) -> bytes:
		# packing record
		return 
	def unpack(self, record:bytes):
		# unpacking record
		return
	
class StaticHash():
	HEADER_FORMAT = "i"
	HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
	def __init__(self, filename):
		self.filename = filename
		self.initialize_file(filename) # inicializando el file
		self.mod = self.get_header()

	def initialize_file(self, filename):
		header = 6
		self.put_header(header)
		for i in range(header):
			self.patch(i, Record())
	
	def get(self, pos) -> Record | None:
		# reading record at position pos
		return Record()
	
	def post(self, data: Record) -> int:
		# writing at the end of file
		# return position of the record
		return 0
	
	def getAux(self, pos: int, filename: str):
		# reading record at position pos in filename
		return 0
	
	def patch(self, pos, data: Record) -> None:
		# writing record at position pos
		return None

	def put_header(self, header):
		# writing new header
		return None
		
	def getLastPosition(self, header):
		record = Record()
		with open(self.filename, "rb") as file:
			file.seek(0,2)
			return file.tell() // record.RECORD_SIZE
		return -1
	
	def get_header(self):
		# getting header value (mod)
		return self.mod

	def insertAux(self, pos, id):
		record = self.get(pos)
		if(record.cant < fb):
			ite = 0
			while(record.ar[ite] != -1):
				#searching position for id
				ite+=1
				assert(ite < len(record.ar)) # shouldn't pass lenght
			record.ar[ite] = id
			record.cant += 1
		else:
			if(record.next != -1):
				self.insertAux(record.next, id)
			else:
				new_record = Record()
				new_record[0] = id
				new_record.cant = 1 # inserting id on new_record

				next = self.post(new_record) # adding new record at the end of file

				record.next = next
				self.patch(pos, record) # rewriting with new next pointer


	def insert(self, id):
		self.insertAux(id % self.mod, id)
		if(self.getDepth(id % self.mod) > M):
			self.reHashing()
	
	def seachAux(self, pos, id) -> int:
		record = self.get(pos)
		for i in record.ar:
			if(i == id):
				# return all register with id
				return id
		if(record.next == -1):
			# id not found
			return None
		return self.searchAux(self, record.next, id)
	
	def search(self, id):
		return self.searchAux(id % self.mod, id)
	
	def deleteAux(self, bef, pos, id) -> list[2]: # return before position at current position of record in file
		record = self.get(pos)
		for i in range(record.ar): # searching over all record
			if(record.ar[i] == id):
				# deleting record
				record.ar[i] = -1
				record.cant -= 1
				return [bef, pos]
		if(record.next == -1):
			return [-1, -1]
		return self.deleteAux(self, pos, record.next, id)
	
	def getLastPointer(self, pos) -> int: # get last pointer following the next pointers
		record = self.get(pos)
		if(record.next == -1):
			return pos
		return self.getLastPointer(record.next)
	
	def getDepth(self, pos) -> int: # number of buckets with overflows
		record = self.get(pos)
		if(record.next == -1):
			return 1
		return self.getDepth(record.next) + 1

	def delete(self, id):
		[bef, cur] = self.deleteAux(-1, id % self.mod, id)
		if(bef == -1):
			return
		record_bef = self.get(bef)
		record_cur = self.get(cur)
		if(record_cur.cant != 0):
			return
		# if is empty, nex pointer of bef is the next of cur (skipping record)
		record_bef.next = record_cur.next
		self.patch(bef, record_bef)
		last_position = self.getLastPointer(id % self.mod)
		
		# append this empty record to the last record
		last_record = self.get(last_position)
		last_record.next = cur
		self.patch(last_position, last_record)

		record_cur.next = -1 # now this is the last
		self.patch(cur, record_cur)

		if(self.getDepth(id % self.mod) > M):
			print("depth should't pass")
			# throw error

	def reHashing(self):
		old_filename = "old_" + self.filename
		os.rename(self.filename, old_filename) # rename new file
		self.mod = 2 * self.mod # duplicating mod
		self.put_header(self.mod)
		for i in range(self.mod):
			self.post(Record()) # initializing filename again

		for i in range(self.getLastPosition()):
			record:Record = self.getAux(i, old_filename)
			assert(record != None)
			for j in record.ar:
				self.insert(j % self.mod, j)

		os.remove(old_filename)		
