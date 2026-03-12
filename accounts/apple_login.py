import jwt
import requests
from jwt.algorithms import RSAAlgorithm
from django.conf import settings

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"

def verify_apple_token(identity_token: str):
    apple_keys = requests.get(APPLE_KEYS_URL).json()["keys"]
    header = jwt.get_unverified_header(identity_token)
    key = next((k for k in apple_keys if k["kid"] == header["kid"]), None)
    if not key:
        raise ValueError("Invalid identity token")

    public_key = RSAAlgorithm.from_jwk(key)
    decoded = jwt.decode(
        identity_token,
        public_key,
        algorithms=["RS256"],
        audience=settings.APPLE_CLIENT_ID,
        issuer="https://appleid.apple.com",
    )
    return decoded
