import abc


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

    def encode(text):
        raise NotImplementedError

class UCS2(UserDataEncoding):

    def __init__(self, msgClass = None):
        super().__init__(msgClass)

    def decode():
        raise NotImplementedError

    def encode():
        raise NotImplementedError