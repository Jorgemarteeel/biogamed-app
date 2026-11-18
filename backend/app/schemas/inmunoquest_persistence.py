"""Trusted internal commands. No HTTP contract or client-selected dice."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.inmunoquest_rules import Bank
from app.schemas.trivial_persistence import ParticipantSpec


class InternalSetup(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    operation_id: UUID
    play_mode: Literal['LOCAL', 'ONLINE']
    subject_id: int | None = Field(default=None, strict=True, gt=0)
    participants: tuple[ParticipantSpec, ...] = Field(min_length=2, max_length=6)

    @model_validator(mode='after')
    def identities(self):
        accounts = [p.user_id for p in self.participants if p.user_id is not None]
        if len(accounts) != len(set(accounts)):
            raise ValueError('Accounts must be distinct')
        if self.participants[0].user_id is None:
            raise ValueError('Host must occupy the first seat')
        if self.play_mode == 'LOCAL' and len(accounts) != 1:
            raise ValueError('Local: one registered host and one to five guests')
        if self.play_mode == 'ONLINE' and len(accounts) != len(self.participants):
            raise ValueError('Online: two to six distinct registered accounts')
        return self


class Command(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    operation_id: UUID
    kind: Literal['order', 'advance', 'virus', 'choose_bank']
    expected_version: int = Field(strict=True, ge=1)
    participant_slot: int = Field(strict=True, ge=1, le=6)
    turn_number: int | None = Field(default=None, strict=True, ge=1)
    bank: Bank | None = None

    @model_validator(mode='after')
    def action_arguments(self):
        if (self.kind == 'choose_bank') != (self.bank is not None):
            raise ValueError('Only a bank choice requires a bank')
        if (self.kind == 'order') != (self.turn_number is None):
            raise ValueError('Ordering has no active turn; other actions require its number')
        return self
