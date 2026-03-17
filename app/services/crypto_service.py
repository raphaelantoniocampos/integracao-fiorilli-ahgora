import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

class CryptoService:
    def __init__(self):
        # Generate an ephemeral RSA key pair for the lifetime of this service instance
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self._public_key = self._private_key.public_key()

    def get_public_key_pem(self) -> str:
        """Returns the public key in PEM format to be sent to the frontend."""
        pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode("utf-8")

    def decrypt(self, encrypted_data_b64: str) -> str:
        """Decrypts a base64 encoded string encrypted with the public key via RSA-OAEP."""
        encrypted_data = base64.b64decode(encrypted_data_b64)
        decrypted_data = self._private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted_data.decode("utf-8")

# Singleton instance for the application
crypto_service = CryptoService()
