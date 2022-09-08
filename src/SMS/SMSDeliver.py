import io

import src.SMS.UserDataEncoding as UserDataEncoding
from ..Message import Message
from .AddressField import AddressField
from .SMSBase import SMSBase
from .UserData import UserData

class SMSDeliver(SMSBase):

	def __init__(self) -> None:
		super().__init__()

	@classmethod
	def from_payload(cls, payload: str, encoding: UserDataEncoding = None):
		message, first_octet, buffer = cls.get_metadata(payload)
		message.has_more_messages = bool(first_octet & (1 << 2))
		message.has_reply_path = bool(first_octet & (1 << 3))
		message.has_user_data_header = bool(first_octet & (1 << 4))
		message.status_report_indication = bool(first_octet & (1 << 5))
		message.originating_address = AddressField.read_address_field(buffer)
		message.pid = int(buffer.read(2), 16)
		dcs = int(buffer.read(2), 16)
		message.timestamp = cls.parse_scts(buffer)
		message.user_data = UserData.read_user_data(buffer, UserData.get_encoding(dcs) or encoding)
		return message


	def to_PDU():
		raise NotImplementedError
