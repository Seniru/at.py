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
from asyncio.futures import Future
from typing import Awaitable, Callable, Tuple, Union
import serial

class Phone(serial.Serial):
	"""	An asynchronous and event-based AT terminal implementation using
	asyncio and serial.
	"""

	def __init__(self, port: str, loop: Union[asyncio.AbstractEventLoop, None] = None):
		super().__init__(port)
		self.loop = loop or asyncio.get_running_loop()
		self.ready = False
		self.at_resp_complete = True
		self._waiters: dict[str, Tuple[(Callable, Future)]] = {}

	@staticmethod
	async def from_ports(ports: Union[list[str], None] = None, loop: Union[asyncio.AbstractEventLoop, None] = None):
		if ports == None:
			from serial.tools import list_ports
			ports = list(map(lambda port: port.usb_description(), list_ports.comports()))
		for port in ports:
			phone = Phone(port, loop)
			phone.ready = True
			await phone.exec_AT()
			phone.timeout = 4
			if phone.read(6) == b"\r\nOK\r\n":
				# close and reinitialize the comport instance if the port is accessible
				phone.close()
				del phone
				return Phone(port, loop)
		raise ConnectionError("Attempt to connect to the serial ports has been failed")

	async def start(self):
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
		while self.readable():
			try:
				if self.inWaiting() != 0:
					in_buffer = self.read_all()
					for line in in_buffer.splitlines():
						if line != b"":
							line = line.decode("utf-8")
							await self.loop.create_task(self._handle_messages(line))
							await self.dispatch("message", line)
			except KeyboardInterrupt:
				self.close()
				await self.dispatch("close")
				self.loop.stop()
				break

	async def _handle_messages(self, message: str):
		if message == "OK" or message.startswith("+"):
			self.at_resp_complete = True
			await self.dispatch("response", message)
		
	async def exec_AT(self, cmd: Union[str, None] = None):
		if not self.ready:
			raise Exception("Module not ready!")
		if not self.at_resp_complete:
			raise Exception("Previous AT command has not completed yet!")
		cmd = cmd or ""
		print(f">>> AT{cmd}")
		self.at_resp_complete = False
		self.loop.run_in_executor(None, self.write, bytes(f"AT{cmd}\r", "utf-8"))

	def event(self, evt: Callable):
		name = evt.__name__
		if not name.startswith("on_"):
			raise ValueError("{} is not a qualified event name".format(name))
		setattr(self, name, evt)
		return evt

	async def _run_event(self, evt: str, *args, **kwargs):
		fn: Union[Callable, None] = getattr(self, "on_{}".format(evt), None)
		if fn:
			await fn(*args, **kwargs)

	async def dispatch(self, evt: str, *args, **kwargs):
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

	async def wait_for(self, evt: str, cond: Union[Callable, None] = None, timeout: Union[int, None] = 4):
		fn = getattr(self, "on_{}".format(evt), None)
		cond = cond or (lambda *args, **kwargs: True)
		if not self._waiters.get(evt):
			self._waiters[evt] = []
		fut = self.loop.create_future()
		self._waiters[evt].append((cond, fut))
		return await asyncio.wait_for(fut, timeout)

