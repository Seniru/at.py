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

import re
from typing import Any, Optional, Union
from enum import Enum

class Message:
	"""The base class to handle all types of messages / responses.
	"""

	class types(Enum):
		"""An enum class containing the types of all the messages.
		"""
		EXECUTE			= ""
		BASIC_RESPONSE 	= "<"
		RESPONSE		= ":"
		SET 			= "="
		READ 			= "?"
		TEST 			= "=?"


	def __init__(self, prefix: str, command: str, type: types, outbound: bool = True, parameters: Any = None):
		"""Creates a Message instance

		Args:
			prefix (str): The prefix of the command (AT for example).
			command (str): The commamd. Useful to identify the function of the command.
			type (types): The type. Check #types class for more information.
			outbound (bool optional): True if the message is an outbound message, False if it's
			an inbound message. Defaults to True.
			parameters (Any, optional): The parameter body. Defaults to None.
		"""
		self.prefix = prefix
		self.command = command
		self.type = type
		self.outbound = outbound
		self.parameters = parameters or []

	def __str__(self):
		"""`__str__` magicmethod to be used in str().

		Returns:
			str: A stringified version of the message.
		"""
		return "{}{}{}{}".format(
			self.prefix or "",
			self.command,
			"" if self.type.value == "<" else self.type.value,
			(" " if self.type == __class__.types.RESPONSE else "") + self._stringify_params(self.parameters)
		)

	def __repr__(self):
		"""`__repr__` magicmethod to be used in repr().

		Returns:
			str: Representation of the object.
		"""
		return f"Message<prefix={self.prefix}, command={self.command}, type={self.type}, outbound={self.outbound}, parameters={self.parameters}, body='{str(self)}'>"

	@classmethod
	def from_payload(cls, payload: Union[bytes, str]):
		"""A class method to instantiate a Message from the payload.

		Args:
			payload (Union[bytes, str]): The payload. Usually comes from "message" or "response" events.

		Returns:
			Message: The Message object
		"""
		payload = (payload.decode("utf-8") if type(payload) == bytes else payload)

		if payload in (
			"OK",
			"CONNECT",
			"RING",
			"NO CARRIER",
			"ERROR",
			"NO DIALTONE",
			"BUSY",
			"NO ANSWER "
		): # basic responses
			return Message(None, payload, cls.types.BASIC_RESPONSE, False, None)

		elif payload.startswith("AT"):
			match = re.match(r"([+\\\^$@#&%]?\w+)(:|=\?|=|\?|\s)?(.*)", payload[2:])
			resp_type = cls.types(match[2]) if match[2] else cls.types.EXECUTE
			return Message("AT", match[1], resp_type, True, cls._parse_parameters(match[3]))
		elif match := re.match(r"([+\\\^$@#&%]?[\w\s]+):(.*)", payload):
			return Message(None, match[1], cls.types.RESPONSE, False, cls._parse_parameters(match[2]))


	@classmethod
	def _parse_parameters(cls, parambody: Union[str, list] = None, skip_tokenization: bool = False):
		"""Helper method to parse parameters from the payload.

		Args:
			parambody (Union[str, list], optional): Parameter body. Defaults to None.
			skip_tokenization (bool, optional): If it should skip the tokenization part (if
			the parambody is already tokenized). Defaults to False.

		Returns:
			list: Parameters
		"""
		# tokenization
		parambody = parambody or ""
		tokens = None
		if skip_tokenization:
			tokens = parambody
		else:
			parambody = parambody.strip()
			tokens = []
			literal: Union[str, None] = None
			for c in parambody:
				if c == "(":
					# content = True for open brackets
					tokens.append({ "type": "bracket", "content": True })
				elif c == ")":
					# content = True for closed brackets
					if literal:
						tokens.append({ "type": "literal", "content": literal })
						literal = None
					tokens.append({ "type": "bracket", "content": False})
				elif c == ",":
					if literal:
						tokens.append({ "type": "literal", "content": literal })
						literal = None
					tokens.append({ "type": "separator", "content": None })
				else:
					if not literal:
						literal = ""
					literal += c
			if literal:
				tokens.append({ "type": "literal", "content": literal })

		# parse the tokens and prepare the params
		#print(tokens)
		i = 0
		params = []
		open_list, cont = False, None
		while i < len(tokens):
			if open_list:
				open_brackets, cont = 0, []
				# check until a closed bracket is found
				while (not (tokens[i]["type"] == "bracket" and not tokens[i]["content"])) or open_brackets != 0:
					if tokens[i]["type"] == "bracket":
						if tokens[i]["content"]: # found open bracket
							open_brackets += 1
						else:
							open_brackets -= 1
							# check if we have came to and end of this list
							if open_brackets == 0:
								break
					else:
						cont.append(tokens[i])

					i += 1
				# recursively parse the list content and return it
				cont = cls._parse_parameters(cont, True)
				params.append(cont)
				open_list, cont = False, None
			else:
				if tokens[i]["type"] == "bracket":
					# ignore close brackets since they are handled above
					if tokens[i]["content"]:
						open_list, cont = True, []
				elif tokens[i]["type"] == "separator":
					if len(tokens) <= i and tokens[i+1]["type"] == "separator": params.append(None)
				elif m := re.match("(\d+)-(\d+)", tokens[i]["content"]):
					upper, lower = int(m[1]), int(m[2])
					params.append(range(upper, lower))
				else:
					val = tokens[i]["content"]
					try:
						num = int(val)
						params.append(num)
					except:
						params.append(val.strip("\""))
						
			i += 1			
		return params

	@classmethod
	def _stringify_params(cls, params: Optional[list] = None):
		"""Helper method to stringify parameters

		Args:
			params (Optional[list], optional): Parameters list. Defaults to None.

		Returns:
			str: Stringified message.
		"""
		if len(params) == 1 and type(params[0]) == str: return params[0]
		res = ""
		for param in params or []:
			if type(param) == list:
				res += "(" + cls._stringify_params(param) + "),"
			elif type(param) == str:
				res += "\"" + param + "\","
			elif type(param) == range:
				res += f"({param.start}-{param.stop}),"
			elif param == None:
				res += ","
			else:
				res += str(param) + ","
		return res[:-1]

