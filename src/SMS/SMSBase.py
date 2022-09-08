"""
MIT License

Copyright (c) 2022 Seniru Pasan

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

import abc
import io
from datetime import datetime, timezone, timedelta
from typing import Union

from .UserDataEncoding import UserDataEncoding
from .AddressField import AddressField
from ..Message import Message


class SMSBase(abc.ABC):
	"""The base class to handle SMS operations
	"""

	def __init__(self):
		self.status = None
		self.smsc_info = None
		self.has_more_messages = False
		self.has_reply_path = False
		self.has_user_data_header = False
		self.status_report_indication = False
		self.originating_address = None
		self.pid = None
		self.timestamp = None
		self.user_data = None

	def __str__(self):
		return  f"<{self.__class__.__qualname__} status={self.status}, smsc_info={self.smsc_info} mms={self.has_more_messages}, rp={self.has_reply_path}, udhi={self.has_user_data_header}, sri={self.status_report_indication}, oa={self.originating_address}, pid={self.pid}, scts={self.timestamp}, ud={self.user_data}>"


	def __repr__(self):
		return str(self)

	@abc.abstractmethod
	def to_PDU():
		raise NotImplementedError

	@classmethod
	def from_payload(cls, payload: Union[bytes, str], encoding: UserDataEncoding = None):
		message, first_octet, buffer = cls.get_metadata(payload)
		return cls.get_message_class(first_octet).from_payload(payload)

	@classmethod
	def get_metadata(cls, payload: Union[bytes, str]):
		data = payload.split("\n")
		meta = Message.from_payload(data[0])
		buffer = io.StringIO(data[1])
		smsc_info_length = int(buffer.read(2), 16)
		smsc_info = AddressField.read_address_field(buffer, (smsc_info_length - 1) * 2)
		first_octet = int(buffer.read(2), 16)
		message = cls.get_message_class(first_octet)()
		message.smsc_info = smsc_info
		message.status = meta.parameters[0]
		return message, first_octet, buffer


	@classmethod
	def get_message_class(cls, first_octet: int):
		from . import SMSDeliver, SMSDeliverReport, SMSSubmit, SMSSubmitReport, SMSStatusReport, SMSCommand
		return (
			SMSDeliver,
			SMSDeliverReport,
			SMSSubmit,
			SMSSubmitReport,
			SMSStatusReport,
			SMSCommand
		)[first_octet & 0b11]

	@classmethod
	def parse_scts(cls, buffer):
		year, month, day, hour, minute, second, tz = map(lambda o: int(o[::-1]), [
			buffer.read(2), buffer.read(2), buffer.read(2), buffer.read(2), buffer.read(2), buffer.read(2), buffer.read(2)
		])
		tz_offset = -1 if (tz & 0b1000000 > 1) else 1
		tz_secs = tz * 15 * 60
		return datetime(year, month, day, hour, minute, second, 0, timezone(timedelta(seconds = tz_offset * tz_secs)))
