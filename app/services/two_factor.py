from dataclasses import dataclass
import hashlib
import hmac
import time


@dataclass
class TwoFactorResult:
    verified: bool
    message: str


class TwoFactorService:
    """Firebase-ready 2FA service with local mock verification fallback."""

    @staticmethod
    def _expected_codes(user):
        seed = f"{user.id}:{user.password_hash}".encode("utf-8")
        codes = []
        for offset in (-1, 0, 1):
            timestep = int(time.time() // 30) + offset
            digest = hmac.new(seed, str(timestep).encode("utf-8"), hashlib.sha256).hexdigest()
            codes.append(str(int(digest[-8:], 16)).zfill(6)[-6:])
        return codes

    @staticmethod
    def verify_code(user, code):
        # In production, verify against Firebase MFA challenge session.
        if not user.two_factor_enabled:
            return TwoFactorResult(True, "2FA not required")
        if code and any(hmac.compare_digest(code, expected) for expected in TwoFactorService._expected_codes(user)):
            return TwoFactorResult(True, "2FA verification successful")
        return TwoFactorResult(False, "Invalid 2FA code")
