import io

import src.SMS.UserDataEncoding as UserDataEncoding

class UserData:

	def __init__(self, encoding, raw_data):
		self.encoding = encoding
		self.raw_data = raw_data
		self.content = encoding.__class__.decode(raw_data)

	def __str__(self):
		import textwrap
		
		raw = textwrap.shorten(self.raw_data, 30)
		content = textwrap.shorten(self.content, 30)
		return f"<UserData encoding={self.encoding}, raw='{raw}', content='{content}'"

	def __repr__(self):
		return str(self)

	@classmethod
	def read_user_data(cls, buffer: io.StringIO, encoding: str):
		udl = int(buffer.read(2), 16)
		ud = buffer.read(udl * 2)
		return UserData(
			encoding,
			ud
		)

	@classmethod
	def get_encoding(cls, dcs):
		msgClass = dcs & 1
		if dcs & 0b1100 == 0:
			return UserDataEncoding.Default(msgClass)
		elif dcs & 0b1100 == 0b1000:
			return UserDataEncoding.UCS2(msgClass)
		return None