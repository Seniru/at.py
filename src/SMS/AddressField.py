from enum import Enum
import io

from .UserDataEncoding import Default

class AddressField:

	class NumberTypes(Enum):
		"""An enum class containing the types of all the numbers.
		"""
		UNKNOWN 			= 0b0000000
		INTERNATIONAL 		= 0b0010000
		NATIONAL			= 0b0100000
		NETWORK_SPECIFIC 	= 0b0110000
		SUBSCRIBER 			= 0b1000000
		ALPHANUMERIC		= 0b1010000
		ABBREVIATED 		= 0b1100000
		RESERVED 			= 0b1110000

	class NumberingPlanIdentifications(Enum):
		"""An enum class containing all the numbering plan identifications.
		"""
		UNKNOWN 	= 0b0000
		ISDN 		= 0b0001
		DATA 		= 0b0011
		TELEX 		= 0b0100
		NATIONAL 	= 0b1000
		PRIVATE 	= 0b1001
		ERMES 		= 0b1010
		RESERVED 	= 0b1111


	def __init__(self, address_type, number):
		self.address_type = address_type
		self.number = number
		self.type_of_number = AddressField.NumberTypes(address_type & 0b1110000).name
		self.numbering_plan_identification = AddressField.NumberingPlanIdentifications(address_type & 0b1111).name
		self.is_international = address_type == 0x91

	def __str__(self):
		return f"<AddressField number={self.number}, type='{self.type_of_number}', numbering_plan_identification='{self.numbering_plan_identification}', is_international={self.is_international}>"


	def __repr__(self):
		return str(self)

	@classmethod
	def read_address_field(cls, buffer: io.StringIO, addr_len: int = None):
		l = addr_len or int(buffer.read(2), 16)
		address_type = int(buffer.read(2), 16)
		is_alphanumeric = (address_type & 0b1110000) == AddressField.NumberTypes.ALPHANUMERIC.value
		number = ""

		for i in range(0, l, 2):
			number += buffer.read(2)[::1 if is_alphanumeric else -1]
		
		number = Default.decode(number) if is_alphanumeric else number.upper().replace("F", "")

		return AddressField(
			address_type,
			number
		)
