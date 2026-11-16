"""Pure movement tests: run with --noconftest (no app, HTTP or database fixtures)."""
from dataclasses import FrozenInstanceError
import sys

import pytest

from app.domain.trivial_movement import (
    MovementEngine, MovementState, Phase, QuestionRequirement, load_board,
)


@pytest.fixture
def engine():
    return MovementEngine(load_board())


def kinds(result):
    return [event.kind for event in result.events]


def test_initial_position_pure_deterministic_immutable(engine):
    state = MovementState()
    first = engine.move(state, 1)
    assert first == engine.move(state, 1)
    assert state == MovementState() and state.position == 1
    assert first.state.question == QuestionRequirement(2, 'LYMPHOCYTE', 1)
    assert first.state.phase == Phase.QUESTION_REQUIRED
    assert kinds(first) == ['ROLLED', 'LANDED', 'QUESTION_REQUIRED']
    with pytest.raises(FrozenInstanceError):
        first.state.position = 3
    # --noconftest keeps this suite independent of all web/ORM bootstrap.
    assert 'app.main' not in sys.modules and 'app.database' not in sys.modules
    assert 'fastapi' not in sys.modules and 'sqlalchemy' not in sys.modules


@pytest.mark.parametrize('roll', range(1, 7))
def test_all_valid_faces(engine, roll):
    result = engine.move(MovementState(position=10), roll)
    assert result.events[0].roll == roll
    assert result.events[0].destination == 10 + roll


@pytest.mark.parametrize('position,roll,destination,level', [
    (56, 2, 58, 2), (98, 1, 99, 3), (123, 1, 124, 4),
    (54, 3, 60, 2), (94, 3, 100, 3), (122, 2, 124, 4),
])
def test_levels_use_final_question_cell_including_dna(engine, position, roll, destination, level):
    result = engine.move(MovementState(position=position), roll)
    assert result.state.position == destination
    assert result.state.question.cell == destination
    assert result.state.question.level == level


@pytest.mark.parametrize('position,roll', [(134, 6), (138, 5), (139, 1), (139, 6)])
def test_finish_clamps_and_resolves_before_goal(engine, position, roll):
    result = engine.move(MovementState(position=position), roll)
    assert result.state.position == 140 and result.state.phase == Phase.GOAL_REACHED
    assert result.state.question is None
    assert kinds(result) == ['ROLLED', 'LANDED', 'GOAL_REACHED']
    with pytest.raises(ValueError):
        engine.move(result.state, 1)


def test_dna_resolves_bazo_pending_not_intermediate_cells(engine):
    result = engine.move(MovementState(position=3), 6)  # 9 ADN -> 12 Bazo
    assert result.state.question == QuestionRequirement(12, 'SPLEEN', 1)
    assert kinds(result) == ['ROLLED', 'LANDED', 'DNA_ADVANCE', 'LANDED', 'RULE_PENDING']
    assert [e.destination for e in result.events if e.kind == 'LANDED'] == [9, 12]


def test_dna_then_finish(engine):
    result = engine.move(MovementState(position=131), 6)  # 137 ADN -> 140
    assert result.state.phase == Phase.GOAL_REACHED
    assert kinds(result) == ['ROLLED', 'LANDED', 'DNA_ADVANCE', 'LANDED', 'GOAL_REACHED']


def test_virus_does_not_resolve_retreat_and_skips_only_next_own_turn(engine):
    result = engine.move(MovementState(position=2), 6)  # 8 Virus -> 5 Erlenmeyer, NOT resolved
    assert result.state.position == 5 and result.state.phase == Phase.TURN_ENDED
    assert result.state.skip_next_own_turn and result.state.question is None
    assert kinds(result) == ['ROLLED', 'LANDED', 'VIRUS_RETREAT', 'TURN_ENDED', 'PENALTY_SET']
    assert [e.destination for e in result.events if e.kind == 'LANDED'] == [8]
    with pytest.raises(ValueError):
        engine.move(result.state, 2)
    skipped = engine.begin_own_turn(result.state)
    assert skipped.state.position == 5 and skipped.state.phase == Phase.TURN_ENDED
    assert not skipped.state.skip_next_own_turn
    assert kinds(skipped) == ['OWN_TURN_SKIPPED']
    with pytest.raises(ValueError):
        engine.move(skipped.state, 2)
    # A different subsequent scheduled own turn; no participant order is inferred.
    ready = engine.begin_own_turn(skipped.state)
    assert ready.state.phase == Phase.READY and ready.state.position == 5
    assert kinds(ready) == ['OWN_TURN_READY']
    assert engine.move(ready.state, 1).state.question.cell == 6
    assert result.state.skip_next_own_turn  # Input is untouched by consumption.


@pytest.mark.parametrize('position,roll,rule,cell', [(1, 6, 'BRAIN_PENDING', 7), (1, 3, 'BAZO_PENDING', 4)])
def test_pending_rules_stop_without_fallback(engine, position, roll, rule, cell):
    result = engine.move(MovementState(position=position), roll)
    assert result.state.position == cell and result.state.phase == Phase.RULE_PENDING
    assert result.state.pending_rule == rule
    assert result.state.question == (QuestionRequirement(4, 'SPLEEN', 1) if cell == 4 else None)
    assert kinds(result)[-1] == 'RULE_PENDING'
    with pytest.raises(ValueError):
        engine.move(result.state, 1)
    with pytest.raises(ValueError):
        engine.begin_own_turn(result.state)


def test_corrected_jeringuilla_is_question_without_inventing_answer_rules(engine):
    result = engine.move(MovementState(position=13), 1)
    assert result.state.question == QuestionRequirement(14, 'SYRINGE', 1)
    with pytest.raises(ValueError):
        engine.move(result.state, 1)
    with pytest.raises(ValueError):
        engine.begin_own_turn(result.state)


@pytest.mark.parametrize('roll', [0, 7, -3, 1.0, '2', True, False, None])
def test_invalid_die(engine, roll):
    with pytest.raises(ValueError):
        engine.move(MovementState(), roll)


@pytest.mark.parametrize('fields', [
    {'position': 0}, {'position': 141}, {'position': True}, {'position': 2.0},
    {'board_version': 'future'}, {'phase': 'READY'}, {'position': 140},
    {'position': 139, 'phase': Phase.GOAL_REACHED}, {'skip_next_own_turn': 1},
    {'skip_next_own_turn': True}, {'phase': Phase.QUESTION_REQUIRED},
    {'pending_rule': 'BRAIN_PENDING'}, {'phase': Phase.RULE_PENDING},
    {'question': 'fake'},
    {'position': 2, 'phase': Phase.QUESTION_REQUIRED, 'question': QuestionRequirement(3, 'LYMPHOCYTE', 1)},
])
def test_invalid_states(fields):
    with pytest.raises(ValueError):
        MovementState(**fields)


@pytest.mark.parametrize('fields', [
    {'cell': True, 'bank': 'FLASK', 'level': 1},
    {'cell': 2, 'bank': 'invented', 'level': 1},
    {'cell': 2, 'bank': 'FLASK', 'level': True},
    {'cell': 2, 'bank': 'FLASK', 'level': 5},
])
def test_invalid_question_requirement(fields):
    with pytest.raises(ValueError):
        QuestionRequirement(**fields)


def test_state_board_mismatch_and_changed_effects_rejected(engine):
    wrong = MovementState(position=2, phase=Phase.QUESTION_REQUIRED,
                          question=QuestionRequirement(2, 'FLASK', 1))
    with pytest.raises(ValueError):
        engine.move(wrong, 1)
    with pytest.raises(ValueError):
        engine.move(None, 1)
    with pytest.raises(ValueError):
        engine.begin_own_turn(MovementState())
    board = load_board()
    changed = dict(board.effects)
    changed['DNA'] = changed['DNA'].model_copy(update={'move_delta': 4})
    with pytest.raises(ValueError):
        MovementEngine(board.model_copy(update={'effects': changed}))


def test_exhaustive_real_board_resolutions(engine):
    board = load_board()
    # Every legal movement origin and face: 834 cases, no live data or RNG.
    for origin in range(1, 140):
        for roll in range(1, 7):
            result = engine.move(MovementState(position=origin), roll)
            target = min(140, origin + roll)
            cell = board.cells[target - 1]
            if cell.kind == 'DNA':
                target = min(140, target + 3)
                cell = board.cells[target - 1]
            assert 1 <= result.state.position <= 140
            if cell.kind == 'VIRUS':
                assert result.state.position == max(1, target - 3)
                assert result.state.skip_next_own_turn and result.state.phase == Phase.TURN_ENDED
            elif cell.kind == 'BRAIN':
                assert result.state.pending_rule == 'BRAIN_PENDING'
            elif cell.kind == 'FINISH':
                assert result.state.phase == Phase.GOAL_REACHED
            else:
                assert result.state.question == QuestionRequirement(target, cell.bank, cell.level)
                assert result.state.pending_rule == ('BAZO_PENDING' if cell.bank == 'SPLEEN' else None)
