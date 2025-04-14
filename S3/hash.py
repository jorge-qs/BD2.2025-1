import struct
import os

fb = 4
M = 3

class Bucket():
	FORMAT = "i" * (fb + 2)
	BUCKET_SIZE = struct.calcsize(FORMAT)
	def __init__(self, ar = [-1 for i in range(fb)], next = -1, cant = 0):
		self.ar = ar
		self.next = next
		self.cant = cant
	
	def pack(self) -> bytes:
		# packing bucket
		return 
	def unpack(self, bucket:bytes):
		# unpacking bucket
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
			self.patch(i, Bucket())
	
	def get(self, pos) -> Bucket | None:
		# reading bucket at position pos
		return Bucket()
	
	def post(self, data: Bucket) -> int:
		# writing at the end of file
		# return position of the bucket
		return 0
	
	def getAux(self, pos: int, filename: str):
		# reading bucket at position pos in filename
		return 0
	
	def patch(self, pos, data: Bucket) -> None:
		# writing bucket at position pos
		return None

	def put_header(self, header):
		# writing new header
		return None
		
	def getLastPosition(self, header):
		bucket = Bucket()
		with open(self.filename, "rb") as file:
			file.seek(0,2)
			return file.tell() // bucket.bucket_SIZE
		return -1
	
	def get_header(self):
		# getting header value (mod)
		return self.mod

	def insertAux(self, pos, id):
		bucket = self.get(pos)
		if(bucket.cant < fb):
			ite = 0
			while(bucket.ar[ite] != -1):
				#searching position for id
				ite+=1
				assert(ite < len(bucket.ar)) # shouldn't pass lenght
			bucket.ar[ite] = id
			bucket.cant += 1
		else:
			if(bucket.next != -1):
				self.insertAux(bucket.next, id)
			else:
				new_bucket = Bucket()
				new_bucket[0] = id
				new_bucket.cant = 1 # inserting id on new_bucket

				next = self.post(new_bucket) # adding new bucket at the end of file

				bucket.next = next
				self.patch(pos, bucket) # rewriting with new next pointer


	def insert(self, id):
		self.insertAux(id % self.mod, id)
		if(self.getDepth(id % self.mod) > M):
			self.reHashing()
	
	def seachAux(self, pos, id) -> int:
		bucket = self.get(pos)
		for i in bucket.ar:
			if(i == id):
				# return all register with id
				return id
		if(bucket.next == -1):
			# id not found
			return None
		return self.searchAux(self, bucket.next, id)
	
	def search(self, id):
		return self.searchAux(id % self.mod, id)
	
	def deleteAux(self, bef, pos, id) -> list[2]: # return before position at current position of bucket in file
		bucket = self.get(pos)
		for i in range(bucket.ar): # searching over all bucket
			if(bucket.ar[i] == id):
				# deleting bucket
				bucket.ar[i] = -1
				bucket.cant -= 1
				return [bef, pos]
		if(bucket.next == -1):
			return [-1, -1]
		return self.deleteAux(self, pos, bucket.next, id)
	
	def getLastPointer(self, pos) -> int: # get last pointer following the next pointers
		bucket = self.get(pos)
		if(bucket.next == -1):
			return pos
		return self.getLastPointer(bucket.next)
	
	def getDepth(self, pos) -> int: # number of buckets with overflows
		bucket = self.get(pos)
		if(bucket.next == -1):
			return 1
		return self.getDepth(bucket.next) + 1

	def delete(self, id):
		[bef, cur] = self.deleteAux(-1, id % self.mod, id)
		if(bef == -1):
			return
		bucket_bef = self.get(bef)
		bucket_cur = self.get(cur)
		if(bucket_cur.cant != 0):
			return
		# if is empty, nex pointer of bef is the next of cur (skipping bucket)
		bucket_bef.next = bucket_cur.next
		self.patch(bef, bucket_bef)
		last_position = self.getLastPointer(id % self.mod)
		
		# append this empty bucket to the last bucket
		last_bucket = self.get(last_position)
		last_bucket.next = cur
		self.patch(last_position, last_bucket)

		bucket_cur.next = -1 # now this is the last
		self.patch(cur, bucket_cur)

		if(self.getDepth(id % self.mod) > M):
			print("depth should't pass")
			# throw error

	def reHashing(self):
		old_filename = "old_" + self.filename
		os.rename(self.filename, old_filename) # rename new file
		self.mod = 2 * self.mod # duplicating mod
		self.put_header(self.mod)
		for i in range(self.mod):
			self.post(Bucket()) # initializing filename again

		for i in range(self.getLastPosition()):
			bucket:Bucket = self.getAux(i, old_filename)
			assert(bucket != None)
			for j in bucket.ar:
				self.insert(j % self.mod, j)

		os.remove(old_filename)		
