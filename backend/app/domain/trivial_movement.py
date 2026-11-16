"""Pure deterministic movement. No HTTP, ORM, RNG, question selection or I/O writes."""
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from app.schemas.trivial_board import Board, Bank

VERSION = 'trivial-original-board-v1'


class Phase(str, Enum):
    READY = 'READY'
    QUESTION_REQUIRED = 'QUESTION_REQUIRED'
    RULE_PENDING = 'RULE_PENDING'
    TURN_ENDED = 'TURN_ENDED'
    GOAL_REACHED = 'GOAL_REACHED'


@dataclass(frozen=True)
class QuestionRequirement:
    cell: int
    bank: Bank
    level: int

    def __post_init__(self):
        if type(self.cell) is not int or not 1 <= self.cell <= 140:
            raise ValueError('Invalid question cell')
        if self.bank not in ('LYMPHOCYTE', 'MACROPHAGE', 'SPLEEN', 'FLASK', 'SYRINGE'):
            raise ValueError('Invalid question bank')
        if type(self.level) is not int or not 1 <= self.level <= 4:
            raise ValueError('Invalid question level')


@dataclass(frozen=True)
class MovementState:
    position: int = 1
    board_version: str = VERSION
    phase: Phase = Phase.READY
    skip_next_own_turn: bool = False
    question: QuestionRequirement | None = None
    pending_rule: str | None = None

    def __post_init__(self):
        if type(self.position) is not int or not 1 <= self.position <= 140:
            raise ValueError('Position must be an integer in 1..140')
        if self.board_version != VERSION or not isinstance(self.phase, Phase):
            raise ValueError('Unsupported version or phase')
        if type(self.skip_next_own_turn) is not bool:
            raise ValueError('Invalid penalty')
        if self.skip_next_own_turn and self.phase != Phase.TURN_ENDED:
            raise ValueError('Penalty requires an ended turn')
        if (self.phase == Phase.GOAL_REACHED) != (self.position == 140):
            raise ValueError('Goal state must identify cell 140')
        if self.question is not None and not isinstance(self.question, QuestionRequirement):
            raise ValueError('Invalid question requirement')
        needs_question = self.phase == Phase.QUESTION_REQUIRED or self.pending_rule == 'BAZO_PENDING'
        if needs_question != (self.question is not None):
            raise ValueError('Inconsistent question state')
        if self.question and self.question.cell != self.position:
            raise ValueError('Question must match current position')
        if self.phase == Phase.RULE_PENDING:
            if self.pending_rule not in ('BRAIN_PENDING', 'BAZO_PENDING'):
                raise ValueError('Unknown pending rule')
        elif self.pending_rule is not None:
            raise ValueError('Pending rule requires a blocked state')


@dataclass(frozen=True)
class Event:
    kind: str
    origin: int
    destination: int
    roll: int | None = None


@dataclass(frozen=True)
class Transition:
    state: MovementState
    events: tuple[Event, ...]


def load_board() -> Board:
    """Read the same checked-in definition as Entrega A, without its HTTP/DB service."""
    path = Path(__file__).resolve().parents[1] / 'data/trivial_board_v1.json'
    return Board.model_validate_json(path.read_text(encoding='utf-8'))


class MovementEngine:
    def __init__(self, board: Board):
        # Validate even a caller's model_copy/model_construct; freeze our own projection.
        definition = Board.model_validate(board.model_dump())
        expected = {
            'DNA': (3, True, None),
            'VIRUS': (-3, False, True),
        }
        for kind, values in expected.items():
            effect = definition.effects[kind]
            if effect.status != 'OBSERVED' or (effect.move_delta, effect.resolve_landing, effect.skip_next_turn) != values:
                raise ValueError('Unsupported effect definition for this engine version')
        self._version = definition.version
        self._cells = definition.cells

    def _validate_state(self, state: MovementState):
        if not isinstance(state, MovementState):
            raise ValueError('Expected MovementState')
        if state.board_version != self._version:
            raise ValueError('State and board versions differ')
        cell = self._cells[state.position - 1]
        if state.question:
            expected = QuestionRequirement(cell.id, cell.bank, cell.level) if cell.kind == 'QUESTION' else None
            if state.question != expected:
                raise ValueError('Question does not match board')
            if (state.question.bank == 'SPLEEN') != (state.pending_rule == 'BAZO_PENDING'):
                raise ValueError('Bazo cannot be resolved while pending')
        if state.pending_rule == 'BRAIN_PENDING' and cell.kind != 'BRAIN':
            raise ValueError('Cerebro pending at wrong cell')

    def move(self, state: MovementState, roll: int) -> Transition:
        """Apply an externally supplied die result; never generate randomness."""
        self._validate_state(state)
        if type(roll) is not int or not 1 <= roll <= 6:
            raise ValueError('Die result must be an integer in 1..6')
        if state.phase != Phase.READY:
            raise ValueError('Movement requires READY; unresolved arrivals cannot be skipped')
        position = min(140, state.position + roll)
        events = [Event('ROLLED', state.position, position, roll)]
        while True:
            cell = self._cells[position - 1]
            events.append(Event('LANDED', position, position))
            if cell.kind == 'DNA':
                target = min(140, position + 3)
                events.append(Event('DNA_ADVANCE', position, target))
                position = target
                continue
            if cell.kind == 'VIRUS':
                target = max(1, position - 3)
                events.extend((Event('VIRUS_RETREAT', position, target),
                               Event('TURN_ENDED', target, target),
                               Event('PENALTY_SET', target, target)))
                final = replace(state, position=target, phase=Phase.TURN_ENDED, skip_next_own_turn=True)
            elif cell.kind == 'BRAIN':
                events.append(Event('RULE_PENDING', position, position))
                final = replace(state, position=position, phase=Phase.RULE_PENDING, pending_rule='BRAIN_PENDING')
            elif cell.kind == 'QUESTION':
                question = QuestionRequirement(position, cell.bank, cell.level)
                pending = cell.bank == 'SPLEEN'
                events.append(Event('RULE_PENDING' if pending else 'QUESTION_REQUIRED', position, position))
                final = replace(state, position=position, phase=Phase.RULE_PENDING if pending else Phase.QUESTION_REQUIRED,
                                question=question, pending_rule='BAZO_PENDING' if pending else None)
            elif cell.kind == 'FINISH':
                # The prototype checks the final position only AFTER handleLanding returns.
                events.append(Event('GOAL_REACHED', position, position))
                final = replace(state, position=position, phase=Phase.GOAL_REACHED)
            else:
                raise ValueError('Unexpected landing type; no fallback empty-cell rule')
            return Transition(final, tuple(events))

    def begin_own_turn(self, state: MovementState) -> Transition:
        """Called once by a future scheduler, only when this participant's turn is due.

        This does not choose participants or determine when the next own turn occurs.
        A skipped turn remains ended; the caller must not invoke it twice for one turn.
        """
        self._validate_state(state)
        if state.phase != Phase.TURN_ENDED:
            raise ValueError('Only an ended turn can enter a new own turn')
        if state.skip_next_own_turn:
            return Transition(replace(state, skip_next_own_turn=False),
                              (Event('OWN_TURN_SKIPPED', state.position, state.position),))
        return Transition(replace(state, phase=Phase.READY),
                          (Event('OWN_TURN_READY', state.position, state.position),))
