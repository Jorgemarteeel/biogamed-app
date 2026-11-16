"""Read-only board review contracts, independent from game sessions."""
import math
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Bank = Literal['LYMPHOCYTE', 'MACROPHAGE', 'SPLEEN', 'FLASK', 'SYRINGE']
Kind = Literal['START', 'QUESTION', 'VIRUS', 'DNA', 'BRAIN', 'FINISH']

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

class Vertex(StrictModel):
    x: float
    y: float

class Cell(StrictModel):
    id: int = Field(strict=True, ge=1, le=140)
    order: int = Field(strict=True, ge=1, le=140)
    label: str = Field(min_length=1)
    source_label: str = Field(min_length=1)
    kind: Kind
    bank: Bank | None
    level: int = Field(strict=True, ge=1, le=4)
    vertices: tuple[Vertex, ...] = Field(min_length=3)

class Effect(StrictModel):
    status: Literal['OBSERVED', 'PENDING']
    description: str = Field(min_length=1)
    move_delta: int | None = Field(default=None, strict=True)
    resolve_landing: bool | None = None
    skip_next_turn: bool | None = None
    seconds: int | None = Field(default=None, strict=True, gt=0)

class Board(StrictModel):
    version: Literal['trivial-original-board-v1']
    source_sha256: str = Field(pattern='^[0-9a-f]{64}$')
    width: int = Field(strict=True, gt=0)
    height: int = Field(strict=True, gt=0)
    effects: dict[Kind, Effect]
    cells: tuple[Cell, ...] = Field(min_length=140, max_length=140)

    @model_validator(mode='after')
    def valid_board(self):
        if set(self.effects) != {'START','QUESTION','VIRUS','DNA','BRAIN','FINISH'}:
            raise ValueError('Missing effect definition')
        brain = self.effects['BRAIN']
        if brain.status != 'PENDING' or any(getattr(brain,k) is not None for k in ['move_delta','resolve_landing','skip_next_turn','seconds']):
            raise ValueError('Cerebro rules must remain unconfigured')
        if [c.id for c in self.cells] != list(range(1, 141)) or any(c.order != c.id for c in self.cells):
            raise ValueError('Expected exactly the ordered cells 1–140')
        if self.cells[0].kind != 'START' or self.cells[-1].kind != 'FINISH':
            raise ValueError('Expected start at 1 and finish at 140')
        source_banks = {'Linfocito':'LYMPHOCYTE','Macrófago':'MACROPHAGE','Bazo':'SPLEEN','Erlenmeyer':'FLASK','Jeringuilla':'SYRINGE'}
        source_kinds = {'Salida':'START','Llegada':'FINISH','Virus':'VIRUS','ADN':'DNA','Cerebro':'BRAIN'}
        for c in self.cells:
            label = 'Jeringuilla' if c.id == 14 else c.source_label
            expected_kind = 'QUESTION' if label in source_banks else source_kinds.get(label)
            if c.label != label or c.kind != expected_kind or c.bank != source_banks.get(label):
                raise ValueError('Cell does not match its source type and bank')
            if c.id == 14 and c.source_label != 'Jeriguinlla':
                raise ValueError('Expected documented correction of cell 14')
            expected = 1 if c.id <= 57 else 2 if c.id <= 98 else 3 if c.id <= 123 else 4
            if c.level != expected:
                raise ValueError('Level does not match original segment')
            if c.id not in (1,140) and c.kind in ('START','FINISH'):
                raise ValueError('Unexpected start/finish')
            if (c.kind == 'QUESTION') != (c.bank is not None):
                raise ValueError('Question cells require a bank; special cells cannot have one')
            if any(not math.isfinite(v.x) or not math.isfinite(v.y) or not 0 <= v.x <= self.width or not 0 <= v.y <= self.height for v in c.vertices):
                raise ValueError('Invalid board coordinates')
        return self

class Binding(StrictModel):
    bank: Bank
    kind: Literal['category', 'topic']
    id: int = Field(strict=True, gt=0)

    @model_validator(mode='after')
    def pending_bank(self):
        if self.bank == 'SPLEEN':
            raise ValueError('Bazo is awaiting subject-matter confirmation; no substitute binding allowed')
        return self

class CoverageRequest(StrictModel):
    bindings: list[Binding] = Field(default_factory=list, max_length=4)

    @model_validator(mode='after')
    def unique_banks(self):
        if len({b.bank for b in self.bindings}) != len(self.bindings):
            raise ValueError('Only one explicit destination per bank')
        return self
