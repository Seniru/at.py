"""
MIT License

Copyright (c) 2021 Seniru Pasan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from enum import Enum

from .Message import Message

class NumberingSchemes(Enum):
	"""Numbering schemes implemented in phonebooks
	"""
	NATIONAL 		= 0
	INTERNATIONAL 	= 1

class PhoneBookEntry:
	"""A Phonebook entry
	"""

	def __init__(self, idx: int, number: str, scheme: NumberingSchemes, contact_name: str):
		"""Constructor not recommended to called directly

		Args:
			idx (int): Index of the entry in the phonebook
			number (str): The phonebook entry number
			scheme (NumberingSchemes): Numbering scheme used (National or International)
			contact_name (str): The name the entry has been saved as
		"""
		self.index = idx
		self.number = number
		self.scheme = scheme
		self.contact_name = contact_name

	def __repr__(self):
		"""`__repr__` magicmethod to be used in repr().

		Returns:
			str: Representation of the object.
		"""
		return str(self)

	def __str__(self):
		"""`__str__` magicmethod to be used in repr().

		Returns:
			str: A stringified version of the object.
		"""
		return f"<PhoneBookEntry index={self.index}, number='{self.number}', scheme={self.scheme}, contactname='{self.contact_name}'>"

	@staticmethod
	def from_payload(payload: str):
		"""Creates a phonebook entry from a payload.

		Args:
			payload (str): Raw payload that was resulted upon requesting phonebook entries

		Returns:
			PhoneBookEntry: A phonebook entry
		"""
		params = Message.from_payload(payload).parameters
		return PhoneBookEntry(
			params[0],
			params[1],
			NumberingSchemes.NATIONAL if params[2] == 129 else NumberingSchemes.INTERNATIONAL,
			params[3]
		)

		