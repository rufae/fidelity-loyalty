"""Modelos ORM: importarlos aquí los registra en `Base.metadata` para Alembic."""

from app.models.audit import AuditEvent
from app.models.card_access import MemberCardSession, MemberEmailToken
from app.models.ledger import LoyaltyTransaction, RewardRedemption
from app.models.loyalty import LoyaltyProgram, ProgramReward
from app.models.members import Member, Membership
from app.models.merchant import Merchant
from app.models.nfc import NfcTag, RedirectEvent, ReviewDestination
from app.models.user import MerchantUser, User, UserSession
from app.models.wallet import BackgroundJob, WalletPass

__all__ = [
    "AuditEvent",
    "BackgroundJob",
    "MemberCardSession",
    "MemberEmailToken",
    "LoyaltyProgram",
    "LoyaltyTransaction",
    "RewardRedemption",
    "Member",
    "Membership",
    "Merchant",
    "NfcTag",
    "RedirectEvent",
    "ReviewDestination",
    "MerchantUser",
    "ProgramReward",
    "User",
    "UserSession",
    "WalletPass",
]
