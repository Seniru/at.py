import abc
from base64 import encode


class UserDataEncoding(abc.ABC):
    
    def __init__(self, msgClass = None):
        super().__init__()
        self.msgClass = msgClass

    @abc.abstractclassmethod
    def encode(self):
        raise NotImplementedError

    @abc.abstractclassmethod
    def decode(self):
        raise NotImplementedError


class Default(UserDataEncoding):

    def __init__(self, msgClass = None):
        super().__init__(msgClass)

    def decode(pdu):
        decoded = [] # (len = len(octets) + 1)
        octets = [pdu[i:i+2] for i in range(0, len(pdu), 2)]
        bits = "".join(list(map(lambda octet: "".join(list(reversed(format(int(octet, 16), "08b")))), octets)))
        i, b = 0, ""
        for bit in bits:
            b += bit
            i += 1
            if i == 7:
                decoded.append(chr(int("".join(list(reversed(b))), 2)))
                i, b = 0, ""
        return "".join(decoded)

    def encode(text: str):
        chars = list(text)
        bits = ""
        for char in chars:
            bits = format(ord(char), "07b") + bits
        return "".join(
            [format(int(bits[max(i-8, 0):i], 2), "02X") for i in range(len(bits), -1, -8)]
        )

class UCS2(UserDataEncoding):

    def __init__(self, msgClass = None):
        super().__init__(msgClass)

    def decode(pdu):
        return bytes([int(pdu[i:i+2], 16) for i in range(0, len(pdu), 2)]).decode("utf-16be")

    def encode(text: str):
        import binascii
        return binascii.hexlify(text.encode("utf-16be")).upper().decode("utf8")