from ..Message import Message
from .AddressField import AddressField
from .SMSBase import SMSBase

class SMSStatusReport(SMSBase):

	def __init__(self) -> None:
		super().__init__()

	def from_payload():
		raise NotImplementedError

	def to_PDU():
		raise NotImplementedError
