import asyncio
from src.at import Phone

import serial.tools.list_ports as a        
print(a.comports()[0].usb_description())
loop = asyncio.get_event_loop()

#phone = Phone("COM4", loop)
phone = loop.run_until_complete(Phone.from_ports(None, loop))
print(phone)

@phone.event
async def on_ready():
	print("[INFO] Module is ready!")
	await phone.exec_AT("+CSQ")
	resp = await phone.wait_for("response", lambda resp: resp.startswith("+CSQ"))
	print("[INFO]" , resp)
	#ok, k = await phone.wait_for("message")
	#print("yes ok", ok, k)

	await phone.exec_AT("+CIND?")

@phone.event
async def on_message(message):
	print("<<<", message)

@phone.event
async def on_close():
	print("[INFO] Connection has been closed!")

loop.run_until_complete(phone.start())
loop.run_forever()

