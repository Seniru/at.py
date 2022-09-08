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

import asyncio
from pydoc import doc
from typing import Callable, Tuple, Union

import serial

from .Message import Message
from .PhoneBook import PhoneBookEntry
from .SMS import SMSBase


class Phone(serial.Serial):
	"""	An asynchronous and event-based AT terminal implementation using
	asyncio and serial.
	"""

	def __init__(self, port: str, loop: Union[asyncio.AbstractEventLoop, None] = None):
		"""Initializes the module on the specified comport. Optionally uses an asyncio EventLoop
		if provided. Check the following example to get an idea about how comports work in
		different platforms.

		```py
		loop = asyncio.get_event_loop()
		# in Windows platforms
		phone = Phone("COM1", loop)
		# in Unix-like platforms
		phone = Phone("/dev/ttyUSB1", loop)

		```

		Args:
			port (str): The port. Usually something like COM<N> in windows and /dev/ttyUSB<N> in unix-like
			where N is the id assigned to the port
			loop (Union[asyncio.AbstractEventLoop, None], optional): Asyncio EventLoop. Defaults to None.
		"""
		
		super().__init__(port)
		self.loop = loop or asyncio.get_running_loop()
		self.ready = False
		self.at_resp_complete = True
		self._waiters: dict[str, Tuple[(Callable, asyncio.Future)]] = {}

	@staticmethod
	async def from_ports(ports: Union[list[str], None] = None, loop: Union[asyncio.AbstractEventLoop, None] = None):
		"""Creates a phone instance from a given list of ports or all the comports available

		Args:
			ports (Union[list[str], None], optional): Lists of ports to attempt the connection. Defaults to None.
			loop (Union[asyncio.AbstractEventLoop, None], optional): Asyncio EventLoop. Defaults to None.

		Raises:
			ConnectionError: If the connection to the list of ports failed

		Returns:
			Phone: A phone instance created from the first successful port found in the `ports` list
		"""

		if ports == None:
			from serial.tools import list_ports
			ports = list(map(lambda port: port.device, list_ports.comports()))
		for port in ports:
			try:
				phone = Phone(port, loop)
				phone.ready = True
				await phone.exec_AT()
				phone.timeout = 4
				if phone.read(6) == b"\r\nOK\r\n":
					# close and reinitialize the comport instance if the port is accessible
					phone.close()
					del phone
					return Phone(port, loop)
			except (BrokenPipeError, OSError):
				pass
		raise ConnectionError("Attempt to connect to the serial ports has been failed")

	async def start(self):
		"""Starts the phone, resulting in collection of AT messages

		Raises:
			ConnectionRefusedError: If issuing of AT commands were failed in the initialization process.
			Try another port if this error occured.
		"""

		self.ready = True
		asyncio.create_task(self._collect())
		try:
			await self.exec_AT()
			self.ready = False
			await self.wait_for("response", lambda resp: resp == "OK")
			self.ready = True
			await self.dispatch("ready")
		except asyncio.exceptions.TimeoutError as e:
			if not self.ready: # to bypass timeout errors from other events
				raise ConnectionRefusedError("The module didn't respond with OK for initilization packet")
			raise e

	async def _collect(self):
		"""Start collecting messages from the input buffer
		"""
		in_buffer_waiting = None		
		while self.readable():
			try:
				if self.inWaiting() != 0:
					in_buffer = self.read_all()
					if in_buffer.endswith(b"\r\n"):
						if in_buffer_waiting is not None:
							in_buffer = in_buffer_waiting + in_buffer
							in_buffer_waiting = None
						for line in in_buffer.splitlines():
							if line != b"":
								line = line.decode("utf-8")	
								await self.loop.create_task(self._handle_messages(line))
								await self.dispatch("message", line)
					else:
						if in_buffer_waiting is None:
							in_buffer_waiting = in_buffer
						else:
							in_buffer_waiting += in_buffer

			except KeyboardInterrupt:
				self.close()
				await self.dispatch("close")
				self.loop.stop()
				break

	async def _handle_messages(self, message: str):
		"""Handles messages

		Args:
			message (str): The message
		"""
		if message in ("OK", "ERROR") or message.startswith("+"):
			self.at_resp_complete = True
			await self.dispatch("response", message)
		
	async def exec_AT(self, cmd: Union[Message, str] = None):
		
		"""Executes the AT command

		Args:
			cmd (Union[Message, str], optional): The command. Defaults to None.

		Raises:
			Exception: If the module hasn't initialized yet or the previous AT command didn't receive
			any response.
		"""
		if not self.ready:
			raise Exception("Module not ready!")
		if not self.at_resp_complete:
			raise Exception("Previous AT command has not completed yet!")
		cmd = cmd or ""
		self.at_resp_complete = False
		self.loop.run_in_executor(None, self.write, bytes(f"AT{cmd}\r", "utf-8"))

	def event(self, evt: Callable):
		"""A decorator to register an event to the instance

		Usage
		```py
		phone = Phone(addr, loop)

		@phone.event
		async def on_ready():
			print("The module is ready!")
		```

		Args:
			evt (Callable): The callable that is decorator is wrapped to

		Raises:
			ValueError: If the function name isn't a qualified event name.
			Qualified event names are those functions which starts with `on_`

		Returns:
			[Callable]: The event callable.
		"""
		name = evt.__name__
		if not name.startswith("on_"):
			raise ValueError("{} is not a qualified event name".format(name))
		setattr(self, name, evt)
		return evt

	async def _run_event(self, evt: str, *args, **kwargs):
		"""A helper method to run events

		Args:
			evt (str): The name of the event
		"""
		fn: Union[Callable, None] = getattr(self, "on_{}".format(evt), None)
		if fn:
			await fn(*args, **kwargs)

	async def dispatch(self, evt: str, *args, **kwargs):
		"""Dispatches an event. Causing any waiter or an event listening to this particular
		event to be executed.

		Args:
			evt (str): The name of the event

		Returns:
			[bool]: If the event has been handled. An event is handled if there is any waiter waiting
			or an event is registered under this name.
		"""
		fn: Union[Callable, None] = getattr(self, "on_{}".format(evt), None)
		if self._waiters.get(evt):
			to_remove: list[int] = []
			for i, (cond, fut) in enumerate(self._waiters.get(evt)):
				if fut.cancelled():
					to_remove.append(i)
				try:
					result = bool(cond(*args, **kwargs))
				except Exception as e:
					fut.set_exception(e)
					to_remove.append(i)
				else:
					if result:
						fut.set_result(args[0] if len(args) == 1 else args if len(args) > 1 else None)
						to_remove.append(i)
			for i in to_remove[::-1]:
				del self._waiters[evt][i]		   
		if fn:
			await self.loop.create_task(self._run_event(evt, *args, **kwargs))
			return True
		return False

	async def wait_for(self, evt: str, cond: Callable = None, timeout: int = 4):
		"""Waits for an event to occur. This causes the current coroutine to be in a waiting status.
		Optionally checks if the event matches a condition and occured within a given timeout.
		A nice example could be given as follows.

		```py
		await phone.exec_AT("+CIND=?")
		# wait for the response of the +CIND command
		resp = await phone.wait_for("response", lambda resp: resp.startswith("+CIND"), 4)
		resp = Message.from_payload(resp)
		# check for the available options of the +CIND (we did +CIND=? so that gives us a response with all
		# possible outputs for that command)
		print(resp.parameters)

		```


		Args:
			evt (str): The event the waiter should wait for
			cond (Callable, optional): The condition that must be fulfilled by the event.
			The waiter ignores the event if any supplied condition didn't pass. Defaults to None.
			timeout (int, optional): The timeout. Raises a timeout error if the waiting operation failed. Defaults to 4.

		Returns:
			[any]: If the event has any arguments passed, they are returned.
		"""
		fn = getattr(self, "on_{}".format(evt), None)
		cond = cond or (lambda *args, **kwargs: True)
		if not self._waiters.get(evt):
			self._waiters[evt] = []
		fut = self.loop.create_future()
		self._waiters[evt].append((cond, fut))
		return await asyncio.wait_for(fut, timeout)

	async def get_available_commands(self):
		"""Lists all of the commands supported by the module

		Returns:
			list[str]: the commands
		"""
		await self.exec_AT(Message("", "+CLAC", Message.types.EXECUTE))
		resp = await self.wait_for("response", lambda message: Message.from_payload(message).command == "+CLAC", timeout=4)
		#return [ Message.from_payload("AT" + cmd) for cmd in resp[:-1].split(",") ]
		return resp[:-1].split(",")



	async def list_phonebook_entries(self, start: int, stop: int = None):
		"""Lists the phonebook entries within the range

		Args:
			start (int): Start position
			stop (int, optional): Stop position, if `None` only return the start entry. Defaults to None.

		Returns:
			list[PhoneBookEntry]: Phonebook entires
		"""
		entries: list[PhoneBookEntry] = []
		await self.exec_AT(Message("", "+CPBR", Message.types.SET, parameters = [ start, stop or start ]))
		try:
			for i in range(start, (stop or start) + 1):
				resp = await self.wait_for("response", lambda message: Message.from_payload(message).command == "+CPBR", timeout=4)
				entries.append(PhoneBookEntry.from_payload(resp))
		except asyncio.exceptions.TimeoutError:
			pass
		return entries

	async def find_phonebook_entries(self, searchfor: str):
		"""Lists phonebook entries that matches with the search string

		NOTE: Method not tested

		Args:
			searchfor (str): The search string

		Returns:
			list[PhoneBookEntry]: Matched phonebook entries
		"""
		entries: list[PhoneBookEntry] = []
		await self.exec_AT(Message("", "+CPBF", Message.types.SET, parameters = [searchfor or ""]))

	async def read_message(self, entry=None):
		await self.exec_AT(Message("", "+CMGR", Message.types.SET, parameters = [entry or 1]))
		resp1 = await self.wait_for("response", lambda resp: resp.startswith("+CMGR"))
		resp2 = await self.wait_for("message")
		return SMSBase.from_payload(resp1 + "\n" + resp2)
