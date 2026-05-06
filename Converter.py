class Converter:

    @staticmethod
    def StringToBytes(s: str) -> bytes:
        return s.encode("utf-8")

    @staticmethod
    def BytesToString(b: bytes) -> str:
        return b.decode("utf-8")
