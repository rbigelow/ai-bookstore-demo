import uuid


class PaymentService:
    """Mock payment service designed to be replaceable with real gateways."""

    @staticmethod
    def charge(amount, payment_method, payment_token=None):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if payment_method not in {"card", "wallet", "mock"}:
            raise ValueError("Unsupported payment method")
        return f"pay_{payment_method}_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def refund(payment_reference):
        if not payment_reference:
            raise ValueError("payment_reference is required")
        return f"refund_{payment_reference}"
