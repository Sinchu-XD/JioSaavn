import base64
from pyDes import des, ECB, PAD_PKCS5


def decrypt(url):
    try:
        cipher = des(
            b"38346591",
            ECB,
            b"\0\0\0\0\0\0\0\0",
            pad=None,
            padmode=PAD_PKCS5
        )

        decoded = base64.b64decode(url.strip())
        decrypted = cipher.decrypt(decoded, padmode=PAD_PKCS5).decode("utf-8")

        return decrypted.replace("_96.mp4", "_320.mp4")

    except Exception:
        return None
