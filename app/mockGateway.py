import uuid
import hashlib
import hmac
import json

# --- 1. THE FAKE BANK (Simulation Layer) ---
# This class mimics the 'razorpay' library.
class MockRazorpayClient:
    def __init__(self, auth):
        self.key_id = auth[0]
        self.key_secret = auth[1]
        self.order = self.Order(self) # Nested class to mimic client.order.create
        
    class Order:
        def __init__(self, client):
            self.client = client
            
        def create(self, data):
            # Simulate generating a random Order ID like Razorpay does
            fake_id = f"order_{str(uuid.uuid4())[:14]}"
            return {
                "id": fake_id,
                "amount": data["amount"],
                "currency": data["currency"],
                "status": "created"
            }

    def utility_verify_payment_signature(self, params):
        # This mimics the math Razorpay does to verify the transaction
        # Formula: HMAC_SHA256(order_id + "|" + payment_id, secret)
        
        msg = f"{params['razorpay_order_id']}|{params['razorpay_payment_id']}"
        
        generated_signature = hmac.new(
            bytes(self.key_secret, 'utf-8'),
            bytes(msg, 'utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != params['razorpay_signature']:
            raise ValueError("Invalid Signature")
        return True