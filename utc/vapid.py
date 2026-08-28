"""One-off: generate the VAPID keypair that signs push notifications.

    pip install pywebpush
    python -m utc.vapid

Put the public key in docs/config.json ("vapidPublicKey") and commit it; put the
private key in Settings → Secrets and variables → Actions as VAPID_PRIVATE_KEY.
The private key is never committed — whoever holds it can send notifications to
every subscribed phone."""
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64u(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def main():
    key = ec.generate_private_key(ec.SECP256R1())
    private = b64u(key.private_numbers().private_value.to_bytes(32, "big"))
    public = b64u(key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
    print("VAPID keypair — generated fresh, shown only here.\n")
    print("Public key → docs/config.json  \"vapidPublicKey\" (commit this):\n")
    print(f"  {public}\n")
    print("Private key → GitHub Actions secret VAPID_PRIVATE_KEY (never commit this):\n")
    print(f"  {private}")


if __name__ == "__main__":
    main()
