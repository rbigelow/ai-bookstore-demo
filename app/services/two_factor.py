from dataclasses import dataclass


@dataclass
class TwoFactorResult:
    verified: bool
    message: str


class TwoFactorService:
    """Firebase-ready 2FA service with local mock verification fallback."""

    @staticmethod
    def verify_code(user, code):
        # In production, verify against Firebase MFA challenge session.
        if not user.two_factor_enabled:
            return TwoFactorResult(True, "2FA not required")
        if code == "000000":
            return TwoFactorResult(True, "2FA verification successful")
        return TwoFactorResult(False, "Invalid 2FA code")
