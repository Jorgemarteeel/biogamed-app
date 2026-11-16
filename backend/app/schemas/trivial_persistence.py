"""Internal typed commands. No route exposes these schemas or a client-supplied die."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ParticipantSpec(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    user_id: UUID | None = None
    guest_name: str | None = Field(default=None, max_length=255)

    @model_validator(mode='after')
    def identity(self):
        if self.user_id is not None:
            if self.guest_name is not None:
                raise ValueError('Registered names come from the account')
        elif not self.guest_name or not self.guest_name.strip():
            raise ValueError('A guest needs a name')
        return self


class InternalSetup(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    operation_id: UUID
    play_mode: Literal['LOCAL', 'ONLINE']
    participants: tuple[ParticipantSpec, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode='after')
    def roster(self):
        accounts = [p.user_id for p in self.participants if p.user_id is not None]
        if len(accounts) != len(set(accounts)):
            raise ValueError('Accounts must be distinct')
        if self.play_mode == 'LOCAL' and (len(accounts) != 1 or self.participants[0].user_id is None):
            raise ValueError('Local: host first, then up to three guests')
        if self.play_mode == 'ONLINE' and (len(self.participants) < 2 or len(accounts) != len(self.participants)):
            raise ValueError('Online: two to four distinct accounts')
        return self


class MoveCommand(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    operation_id: UUID
    expected_version: int = Field(strict=True, ge=1)
    participant_slot: int = Field(strict=True, ge=1, le=4)
    turn_number: int = Field(strict=True, ge=1)

class SavedMovementConfiguration(BaseModel):
    """Version-one persisted configuration; absent schema_version means original v1."""
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: Literal[1] = 1
    scope: Literal['MOVEMENT_ONLY']
    participants_closed: Literal[True]
    turn_order: tuple[int, ...] = Field(min_length=1, max_length=4)
    pending_rules: tuple[str, ...]

    @model_validator(mode='before')
    @classmethod
    def strict_values(cls, value):
        if isinstance(value, dict):
            if type(value.get('schema_version', 1)) is not int or type(value.get('participants_closed')) is not bool:
                raise ValueError('Invalid configuration flags/version')
            order = value.get('turn_order')
            if not isinstance(order, (list, tuple)) or any(type(slot) is not int for slot in order):
                raise ValueError('Invalid turn order')
        return value

    @model_validator(mode='after')
    def preserved_pending_rules(self):
        expected = {'BAZO', 'BRAIN', 'CORRECT_TURN', 'EXHAUSTION', 'ABANDONMENT'}
        if len(self.turn_order) != len(set(self.turn_order)):
            raise ValueError('Repeated turn slot')
        if len(self.pending_rules) != len(expected) or set(self.pending_rules) != expected:
            raise ValueError('Unsupported partial rules')
        return self
