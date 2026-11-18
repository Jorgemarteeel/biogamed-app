"""Manual basic rules. Pure values only: no HTTP, ORM, files, clock or RNG.

Manual 2026-11-16; product decision 2026-11-18: finish at 140, no final question.
Legacy trivial_movement states are deliberately not accepted.
"""
from dataclasses import dataclass, replace
from enum import Enum
from collections.abc import Mapping

RULES_VERSION = "inmunoquest-manual-20261116-basic-v1"
BOARD_VERSION = "inmunoquest-manual-board-v1"

# Fixed by RULES_VERSION; changing the finish policy requires a new rules version.
START_CELL = 1
FINISH_CELL = 140


class Bank(str, Enum):
    LYMPHOCYTE = "LYMPHOCYTE"
    MACROPHAGE = "MACROPHAGE"
    SPLEEN = "SPLEEN"
    FLASK = "FLASK"
    DNA = "DNA"


class Kind(str, Enum):
    START = "START"
    QUESTION = "QUESTION"
    SYRINGE = "SYRINGE"
    BRAIN = "BRAIN"
    VIRUS = "VIRUS"
    FINISH = "FINISH"


class Phase(str, Enum):
    ORDERING = "ORDERING"
    READY = "READY"
    ROLL_AGAIN = "ROLL_AGAIN"
    VIRUS_ROLL = "VIRUS_ROLL"
    CHOOSE_BANK = "CHOOSE_BANK"
    QUESTION = "QUESTION"
    FINISHED = "FINISHED"


def integer(value, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"Expected integer in {lo}..{hi}")


@dataclass(frozen=True)
class Cell:
    number: int
    kind: Kind
    level: int
    bank: Bank | None = None


def cell_at(number: int) -> Cell:
    integer(number, START_CELL, FINISH_CELL)
    level = 1 if number <= 57 else 2 if number <= 98 else 3 if number <= 123 else 4
    if number in (START_CELL, FINISH_CELL):
        return Cell(number, Kind.START if number == START_CELL else Kind.FINISH, level)
    cycle = (Bank.LYMPHOCYTE, Bank.MACROPHAGE, Bank.SPLEEN, Bank.FLASK,
             Kind.SYRINGE, Kind.BRAIN, Kind.VIRUS, Bank.DNA)
    item = cycle[(number - 2) % 8]
    return Cell(number, Kind.QUESTION, level, item) if isinstance(item, Bank) else Cell(number, item, level)


@dataclass(frozen=True)
class Player:
    id: str
    position: int = START_CELL

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip() or len(self.id) > 120:
            raise ValueError("Participant identifier must be nonblank, at most 120 characters")
        integer(self.position, START_CELL, FINISH_CELL)


@dataclass(frozen=True)
class QuestionRequirement:
    cell: int
    bank: Bank
    level: int


@dataclass(frozen=True)
class State:
    players: tuple[Player, ...]
    order_groups: tuple[tuple[str, ...], ...]
    phase: Phase = Phase.ORDERING
    active_index: int | None = None
    chosen_bank: Bank | None = None
    rules_version: str = RULES_VERSION
    board_version: str = BOARD_VERSION

    def __post_init__(self):
        if self.rules_version != RULES_VERSION or self.board_version != BOARD_VERSION:
            raise ValueError("Unsupported saved rules/board version; no implicit conversion")
        if type(self.players) is not tuple or not 2 <= len(self.players) <= 6:
            raise ValueError("Expected 2–6 immutable participants")
        for p in self.players:
            if not isinstance(p, Player): raise ValueError("Invalid participant")
            p.__post_init__()
        ids = tuple(p.id for p in self.players)
        if len(set(ids)) != len(ids): raise ValueError("Participant IDs must be distinct")
        if type(self.order_groups) is not tuple or not self.order_groups or any(type(g) is not tuple or not g for g in self.order_groups):
            raise ValueError("Invalid immutable order groups")
        order = self.turn_order
        if any(not isinstance(x, str) for x in order) or len(order) != len(ids) or set(order) != set(ids):
            raise ValueError("Order must contain each participant exactly once")
        if not isinstance(self.phase, Phase): raise ValueError("Invalid phase")
        if self.chosen_bank is not None and not isinstance(self.chosen_bank, Bank): raise ValueError("Invalid bank")
        if self.phase == Phase.ORDERING:
            if self.active_index is not None or self.chosen_bank is not None or all(len(g) == 1 for g in self.order_groups) or any(p.position != START_CELL for p in self.players):
                raise ValueError("Inconsistent preparation")
            return
        if any(len(g) != 1 for g in self.order_groups): raise ValueError("Unresolved initial ties")
        integer(self.active_index, 0, len(ids)-1)
        active = self.active_player
        if any(p.position == FINISH_CELL for p in self.players if p.id != active.id): raise ValueError("Inactive winner")
        if (self.phase == Phase.FINISHED) != (active.position == FINISH_CELL): raise ValueError("Inconsistent victory")
        cell = cell_at(active.position)
        expected = {Phase.ROLL_AGAIN: Kind.SYRINGE, Phase.VIRUS_ROLL: Kind.VIRUS, Phase.CHOOSE_BANK: Kind.BRAIN}
        if self.phase in expected and cell.kind != expected[self.phase]: raise ValueError("Phase does not match cell")
        if self.phase == Phase.QUESTION:
            if cell.kind == Kind.BRAIN:
                if self.chosen_bank is None: raise ValueError("Choose a bank before requesting a question")
            elif cell.kind != Kind.QUESTION or self.chosen_bank is not None:
                raise ValueError("Invalid question requirement")
        elif self.chosen_bank is not None: raise ValueError("Unexpected bank selection")

    @property
    def turn_order(self):
        return tuple(p for group in self.order_groups for p in group)

    @property
    def pending_rollers(self):
        return tuple(p for group in self.order_groups if len(group) > 1 for p in group) if self.phase == Phase.ORDERING else ()

    @property
    def active_player(self):
        if self.active_index is None: return None
        return next(p for p in self.players if p.id == self.turn_order[self.active_index])

    @property
    def question(self):
        if self.phase != Phase.QUESTION: return None
        cell = cell_at(self.active_player.position)
        return QuestionRequirement(cell.number, self.chosen_bank if cell.kind == Kind.BRAIN else cell.bank, cell.level)

    @property
    def winner(self):
        return self.active_player.id if self.phase == Phase.FINISHED else None


@dataclass(frozen=True)
class Event:
    kind: str
    participant: str | None = None
    origin: int | None = None
    destination: int | None = None
    die: int | None = None
    bank: Bank | None = None
    level: int | None = None


@dataclass(frozen=True)
class Transition:
    state: State
    events: tuple[Event, ...]


class InmunoQuestEngine:
    def prepare(self, participants: tuple[str, ...]) -> State:
        if type(participants) is not tuple: raise ValueError("Use an immutable participant tuple")
        return State(tuple(Player(p) for p in participants), (participants,))

    def _check(self, state, phases):
        if not isinstance(state, State): raise ValueError("Expected manual State")
        state.__post_init__()
        if state.phase not in phases: raise ValueError("Action not allowed in this phase")

    def order_rolls(self, state: State, rolls: Mapping[str, int]) -> Transition:
        self._check(state, (Phase.ORDERING,))
        if not isinstance(rolls, Mapping) or set(rolls) != set(state.pending_rollers):
            raise ValueError("Supply exactly the participants still tied")
        for value in rolls.values(): integer(value, 1, 6)
        groups = []
        events = []
        for group in state.order_groups:
            if len(group) == 1:
                groups.append(group)
                continue
            events.extend(Event("ORDER_ROLLED", p, die=rolls[p]) for p in group)
            for score in sorted({rolls[p] for p in group}, reverse=True):
                groups.append(tuple(p for p in group if rolls[p] == score))
        finished = all(len(g) == 1 for g in groups)
        result = replace(state, order_groups=tuple(groups), phase=Phase.READY if finished else Phase.ORDERING,
                         active_index=0 if finished else None)
        events.append(Event("ORDER_READY" if finished else "TIEBREAK_REQUIRED"))
        if finished: events.append(Event("TURN_STARTED", result.active_player.id))
        return Transition(result, tuple(events))

    def advance(self, state: State, die: int) -> Transition:
        self._check(state, (Phase.READY, Phase.ROLL_AGAIN))
        integer(die, 1, 6)
        player = state.active_player
        target = min(FINISH_CELL, player.position + die)
        moved = replace(player, position=target)
        people = tuple(moved if p.id == moved.id else p for p in state.players)
        cell = cell_at(target)
        phase = (Phase.FINISHED if target == FINISH_CELL else Phase.ROLL_AGAIN if cell.kind == Kind.SYRINGE
                 else Phase.VIRUS_ROLL if cell.kind == Kind.VIRUS else Phase.CHOOSE_BANK if cell.kind == Kind.BRAIN else Phase.QUESTION)
        result = replace(state, players=people, phase=phase, chosen_bank=None)
        events = [Event("ADVANCED", player.id, player.position, target, die), Event("LANDED", player.id, target, target)]
        event = {Phase.FINISHED:"VICTORY", Phase.ROLL_AGAIN:"EXTRA_ROLL", Phase.VIRUS_ROLL:"RETREAT_ROLL_REQUIRED", Phase.CHOOSE_BANK:"BANK_CHOICE_REQUIRED", Phase.QUESTION:"QUESTION_REQUIRED"}[phase]
        events.append(Event(event, player.id, target, target, bank=result.question.bank if result.question else None, level=cell.level))
        return Transition(result, tuple(events))

    def choose_bank(self, state: State, bank: Bank) -> Transition:
        self._check(state, (Phase.CHOOSE_BANK,))
        if not isinstance(bank, Bank): raise ValueError("Expected one of the five banks")
        result = replace(state, phase=Phase.QUESTION, chosen_bank=bank)
        q = result.question
        return Transition(result, (Event("BANK_CHOSEN", state.active_player.id, bank=bank, level=q.level), Event("QUESTION_REQUIRED", state.active_player.id, q.cell, q.cell, bank=bank, level=q.level)))

    def _end(self, state):
        return replace(state, active_index=(state.active_index + 1) % len(state.players), phase=Phase.READY, chosen_bank=None)

    def retreat_virus(self, state: State, die: int) -> Transition:
        self._check(state, (Phase.VIRUS_ROLL,))
        integer(die, 1, 6)
        p = state.active_player
        target = max(START_CELL, p.position - die)
        players = tuple(replace(x, position=target) if x.id == p.id else x for x in state.players)
        # Switch participant and phase together; never resolve the retreat destination.
        result = self._end(replace(state, players=players, phase=Phase.READY))
        return Transition(result, (Event("VIRUS_RETREAT", p.id, p.position, target, die), Event("TURN_ENDED", p.id), Event("TURN_STARTED", result.active_player.id)))

    def evaluate(self, state: State, correct: bool) -> Transition:
        self._check(state, (Phase.QUESTION,))
        if type(correct) is not bool: raise ValueError("Human evaluation must be a boolean")
        p = state.active_player
        if correct:
            result = replace(state, phase=Phase.READY, chosen_bank=None)
            events = (Event("CORRECT", p.id), Event("ROLL_REQUIRED", p.id))
        else:
            result = self._end(state)
            events = (Event("INCORRECT", p.id), Event("TURN_ENDED", p.id), Event("TURN_STARTED", result.active_player.id))
        return Transition(result, events)
