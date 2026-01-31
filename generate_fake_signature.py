import hmac
import hashlib
import uuid

# MUST MATCH what is in payments.py
KEY_SECRET = "5678" 

# 1. Paste the Order ID you got from 'create-order' here:
ORDER_ID = "order_3393eab4-e025-" 

PAYMENT_ID = f"pay_fake_{str(uuid.uuid4())[:10]}"

# 3. Generate the Signature
msg = f"{ORDER_ID}|{PAYMENT_ID}"
signature = hmac.new(
    bytes(KEY_SECRET, 'utf-8'),
    bytes(msg, 'utf-8'),
    hashlib.sha256
).hexdigest()

print("--- COPY THESE INTO POSTMAN /verify-payment ---")
print(f'"gateway_order_id": "{ORDER_ID}",')
print(f'"gateway_payment_id": "{PAYMENT_ID}",')
print(f'"gateway_signature": "{signature}"')