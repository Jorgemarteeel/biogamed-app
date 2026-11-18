"""Run with --noconftest: no app, HTTP, database, RNG or services."""
from dataclasses import replace, FrozenInstanceError
import copy
import sys
import pytest
from app.domain.inmunoquest_rules import (
    InmunoQuestEngine, State, Player, Phase, Bank, Kind, Event, cell_at,
    START_CELL, FINISH_CELL, RULES_VERSION,
)

@pytest.fixture
def engine(): return InmunoQuestEngine()

def ready(engine, position=1, players=('a','b')):
    state=engine.order_rolls(engine.prepare(players),dict(zip(players,range(len(players),0,-1)))).state
    return replace(state,players=tuple(replace(p,position=position) if p.id=='a' else p for p in state.players))


def test_pure_repeatable_immutable(engine):
    s=ready(engine);before=copy.deepcopy(s)
    first=engine.advance(s,1)
    assert first==engine.advance(s,1) and s==before
    assert first.state.question.bank==Bank.LYMPHOCYTE
    assert isinstance(first.events,tuple)
    with pytest.raises(FrozenInstanceError):first.state.players[0].position=99
    assert not {'app.main','app.database','fastapi','sqlalchemy'} & sys.modules.keys()

@pytest.mark.parametrize('count',[2,3,4,5,6])
def test_participants_and_descending_order(engine,count):
    ids=tuple(str(i) for i in range(count));s=engine.prepare(ids);rolls={p:i+1 for i,p in enumerate(ids)};saved=dict(rolls)
    result=engine.order_rolls(s,rolls)
    assert result.state.turn_order==tuple(reversed(ids)) and result.state.active_player.id==ids[-1]
    assert rolls==saved and s.phase==Phase.ORDERING

def test_multiple_tie_groups_preserve_priority_and_only_tied_players_reroll(engine):
    s=engine.prepare(('a','b','c','d','e','f'))
    s=engine.order_rolls(s,dict(a=6,b=6,c=4,d=4,e=2,f=1)).state
    assert s.pending_rollers==('a','b','c','d')
    s=engine.order_rolls(s,dict(a=1,b=1,c=6,d=5)).state
    assert s.order_groups==( ('a','b'),('c',),('d',),('e',),('f',) )
    with pytest.raises(ValueError):engine.order_rolls(s,dict(a=2,b=3,c=6))
    result=engine.order_rolls(s,dict(a=2,b=3))
    assert result.state.turn_order==('b','a','c','d','e','f')
    assert result.state.phase==Phase.READY

@pytest.mark.parametrize('origin,die,bank',[(1,1,Bank.LYMPHOCYTE),(1,2,Bank.MACROPHAGE),(1,3,Bank.SPLEEN),(1,4,Bank.FLASK),(3,6,Bank.DNA)])
def test_all_five_banks_including_dna_without_automatic_movement(engine,origin,die,bank):
    s=engine.advance(ready(engine,origin),die).state
    assert s.phase==Phase.QUESTION and s.question.bank==bank and s.active_player.position==origin+die

@pytest.mark.parametrize('origin,die,level',[(56,1,1),(57,1,2),(97,1,2),(98,1,3),(122,1,3),(123,1,4),(138,1,4)])
def test_ring_boundaries(engine,origin,die,level):
    result=engine.advance(ready(engine,origin),die).state
    assert cell_at(result.active_player.position).level==level


def test_syringe_same_turn_can_recur_after_an_evaluated_question(engine):
    s=engine.advance(ready(engine),5).state # 6 syringe
    assert s.phase==Phase.ROLL_AGAIN and s.active_player.id=='a'
    s=engine.advance(s,4).state # 10 question
    s=engine.evaluate(s,True).state
    result=engine.advance(s,4) # 14 syringe
    assert result.state.phase==Phase.ROLL_AGAIN and result.state.active_player.id=='a'
    assert result.events[-1].kind=='EXTRA_ROLL'
    # Adjacent syringes are eight apart: direct consecutive arrivals cannot occur with a d6.
    for n in range(2,140):
        if cell_at(n).kind==Kind.SYRINGE:
            assert all(cell_at(min(140,n+d)).kind!=Kind.SYRINGE for d in range(1,7))


def test_syringe_can_lead_to_virus(engine):
    s=engine.advance(ready(engine),5).state
    s=engine.advance(s,2).state
    assert s.phase==Phase.VIRUS_ROLL and s.active_player.position==8

@pytest.mark.parametrize('die',range(1,7))
def test_virus_uses_second_roll_without_resolving_destination(engine,die):
    s=engine.advance(ready(engine,7),1).state
    with pytest.raises(ValueError):engine.advance(s,1)
    result=engine.retreat_virus(s,die)
    assert next(p.position for p in result.state.players if p.id=='a')==8-die
    assert result.state.active_player.id=='b' and result.state.question is None
    assert [e.kind for e in result.events]==['VIRUS_RETREAT','TURN_ENDED','TURN_STARTED']
    assert s.active_player.position==8 and s.phase==Phase.VIRUS_ROLL


def test_virus_crosses_ring_and_does_not_skip_next_own_turn(engine):
    s=engine.advance(ready(engine,103),1).state # Virus 104
    s=engine.retreat_virus(s,6).state # 98, no landing resolution
    assert s.players[0].position==98
    s=engine.evaluate(engine.advance(s,1).state,False).state # b fails
    assert s.active_player.id=='a' and s.phase==Phase.READY
    s=engine.advance(s,1).state
    assert s.question.level==3 and s.question.bank==Bank.MACROPHAGE

@pytest.mark.parametrize('bank',list(Bank))
def test_brain_requires_choice_and_keeps_level(engine,bank):
    s=engine.advance(ready(engine,94),1).state # Cerebro 95, level 2
    assert s.phase==Phase.CHOOSE_BANK and s.question is None
    with pytest.raises(ValueError):engine.evaluate(s,True)
    result=engine.choose_bank(s,bank)
    assert result.state.question.bank==bank and result.state.question.level==2
    with pytest.raises(ValueError):engine.choose_bank(result.state,bank)

@pytest.mark.parametrize('correct',[True,False])
def test_human_evaluation_position_turn_and_repetition(engine,correct):
    s=engine.advance(ready(engine),1).state
    result=engine.evaluate(s,correct)
    assert result.state.players==s.players and result.state.question is None
    assert result.state.active_player.id==('a' if correct else 'b')
    assert result.state.phase==Phase.READY
    with pytest.raises(ValueError):engine.evaluate(result.state,correct)

@pytest.mark.parametrize('position,die',[(139,1),(134,6),(139,6),(138,6)])
def test_exact_and_overshoot_victory_at_140_without_final_question(engine,position,die):
    result=engine.advance(ready(engine,position),die)
    assert result.state.winner=='a' and result.state.active_player.position==140
    assert result.state.phase==Phase.FINISHED and result.state.question is None
    assert result.events[-1].kind=='VICTORY'
    for action in [lambda:engine.advance(result.state,1),lambda:engine.evaluate(result.state,True),lambda:engine.retreat_virus(result.state,1)]:
        with pytest.raises(ValueError):action()


def test_139_is_normal_macrophage_question_without_victory(engine):
    s=engine.advance(ready(engine,138),1).state
    assert s.winner is None and s.phase==Phase.QUESTION
    assert s.question.bank==Bank.MACROPHAGE and s.question.level==4
    assert engine.evaluate(s,False).state.winner is None
    s=engine.evaluate(s,True).state
    assert engine.advance(s,1).state.winner=='a'

@pytest.mark.parametrize('die',[0,7,-1,True,False,1.0,'2',None])
def test_invalid_rolls(engine,die):
    with pytest.raises(ValueError):engine.advance(ready(engine),die)
    with pytest.raises(ValueError):engine.retreat_virus(engine.advance(ready(engine,7),1).state,die)
    with pytest.raises(ValueError):engine.order_rolls(engine.prepare(('a','b')),{'a':die,'b':1})

@pytest.mark.parametrize('ids',[(),('a',),tuple('abcdefg'),('a','a'),('a',' '),['a','b']])
def test_invalid_participants(engine,ids):
    with pytest.raises(ValueError):engine.prepare(ids)


def test_invalid_actions_versions_and_states(engine):
    s=ready(engine)
    for action in [lambda:engine.retreat_virus(s,2),lambda:engine.choose_bank(s,Bank.DNA),lambda:engine.evaluate(s,True),lambda:engine.order_rolls(s,{'a':1,'b':2})]:
        with pytest.raises(ValueError):action()
    for change in [{'rules_version':'legacy'},{'board_version':'legacy'},{'active_index':True},{'phase':Phase.FINISHED},{'phase':Phase.VIRUS_ROLL},{'order_groups':(('a',),('a',))},{'players':list(s.players)}]:
        with pytest.raises(ValueError):replace(s,**change)
    brain=engine.advance(ready(engine),6).state
    with pytest.raises(ValueError):engine.choose_bank(brain,'DNA')
    q=engine.choose_bank(brain,Bank.DNA).state
    with pytest.raises(ValueError):engine.evaluate(q,1)


def test_legacy_engine_is_a_separate_compatibility_boundary(engine):
    from app.domain.trivial_movement import MovementState, MovementEngine, load_board
    with pytest.raises(ValueError):engine.advance(MovementState(),1)
    with pytest.raises(ValueError):MovementEngine(load_board()).move(ready(engine),1)


def test_complete_board_definition():
    from collections import Counter
    cells=tuple(cell_at(n) for n in range(1,141))
    assert cells[0].kind==Kind.START and cells[-1].kind==Kind.FINISH
    counts=Counter(c.bank for c in cells if c.kind==Kind.QUESTION)
    assert counts=={Bank.LYMPHOCYTE:18,Bank.MACROPHAGE:18,Bank.SPLEEN:17,Bank.FLASK:17,Bank.DNA:17}
    assert all(sum(c.kind==k for c in cells)==17 for k in [Kind.SYRINGE,Kind.BRAIN,Kind.VIRUS])
    for n in [0,141,True,2.0,'2']:
        with pytest.raises(ValueError):cell_at(n)


def test_all_arrivals_and_action_inputs_are_immutable_and_repeatable(engine):
    for origin in range(1,140):
        for die in range(1,7):
            initial=ready(engine,origin);saved=copy.deepcopy(initial)
            transition=engine.advance(initial,die)
            assert initial==saved and transition==engine.advance(initial,die)
            s=transition.state;before=copy.deepcopy(s)
            if s.phase==Phase.VIRUS_ROLL:
                for d in range(1,7):
                    result=engine.retreat_virus(s,d)
                    assert result==engine.retreat_virus(s,d)
                    assert 1<=result.state.players[0].position<140
                    assert result.state.question is None
            elif s.phase==Phase.CHOOSE_BANK:
                for bank in Bank:
                    chosen=engine.choose_bank(s,bank)
                    assert chosen==engine.choose_bank(s,bank)
                    for correct in [False,True]:
                        assert engine.evaluate(chosen.state,correct)==engine.evaluate(chosen.state,correct)
            elif s.phase==Phase.QUESTION:
                for correct in [False,True]:assert engine.evaluate(s,correct)==engine.evaluate(s,correct)
            assert s==before

@pytest.mark.parametrize('phase', list(Phase))
def test_only_compatible_actions_are_accepted_in_each_phase(engine, phase):
    states = {
        Phase.ORDERING: engine.prepare(('a', 'b')),
        Phase.READY: ready(engine),
        Phase.ROLL_AGAIN: engine.advance(ready(engine), 5).state,
        Phase.VIRUS_ROLL: engine.advance(ready(engine, 7), 1).state,
        Phase.CHOOSE_BANK: engine.advance(ready(engine), 6).state,
        Phase.QUESTION: engine.advance(ready(engine), 1).state,
        Phase.FINISHED: engine.advance(ready(engine, 139), 1).state,
    }
    state = states[phase]
    saved = copy.deepcopy(state)
    actions = {
        'order': lambda: engine.order_rolls(state, {'a': 2, 'b': 1}),
        'advance': lambda: engine.advance(state, 1),
        'retreat': lambda: engine.retreat_virus(state, 1),
        'choose': lambda: engine.choose_bank(state, Bank.DNA),
        'evaluate': lambda: engine.evaluate(state, False),
    }
    allowed = {
        Phase.ORDERING: 'order', Phase.READY: 'advance',
        Phase.ROLL_AGAIN: 'advance', Phase.VIRUS_ROLL: 'retreat',
        Phase.CHOOSE_BANK: 'choose', Phase.QUESTION: 'evaluate',
        Phase.FINISHED: None,
    }
    for name, action in actions.items():
        if name == allowed[phase]:
            assert action() == action()
        else:
            with pytest.raises(ValueError):
                action()
        assert state == saved


def test_turns_and_events_follow_rolled_order_not_participant_seats(engine):
    initial = engine.prepare(('a', 'b', 'c'))
    ordered = engine.order_rolls(initial, {'a': 1, 'b': 6, 'c': 3})
    assert ordered.state.turn_order == ('b', 'c', 'a')
    assert ordered.events[-1] == Event('TURN_STARTED', 'b')
    syringe = engine.advance(ordered.state, 5)
    assert all(e.participant == 'b' for e in syringe.events)
    virus = engine.advance(syringe.state, 2)
    assert virus.events[-1] == Event('RETREAT_ROLL_REQUIRED', 'b', 8, 8, level=1)
    retreat = engine.retreat_virus(virus.state, 4)
    assert retreat.events == (
        Event('VIRUS_RETREAT', 'b', 8, 4, 4),
        Event('TURN_ENDED', 'b'), Event('TURN_STARTED', 'c'),
    )
    assert retreat.state.players == (Player('a'), Player('b', 4), Player('c'))
    question = engine.advance(retreat.state, 1)
    assert question.events == (
        Event('ADVANCED', 'c', 1, 2, 1), Event('LANDED', 'c', 2, 2),
        Event('QUESTION_REQUIRED', 'c', 2, 2, bank=Bank.LYMPHOCYTE, level=1),
    )
    incorrect = engine.evaluate(question.state, False)
    assert incorrect.events == (
        Event('INCORRECT', 'c'), Event('TURN_ENDED', 'c'), Event('TURN_STARTED', 'a'),
    )
    assert incorrect.state.players == question.state.players
    assert incorrect.state.active_player.id == 'a'


def test_brain_evaluation_and_victory_events_match_resulting_state(engine):
    brain = engine.advance(ready(engine, 94), 1)
    chosen = engine.choose_bank(brain.state, Bank.DNA)
    assert chosen.events == (
        Event('BANK_CHOSEN', 'a', bank=Bank.DNA, level=2),
        Event('QUESTION_REQUIRED', 'a', 95, 95, bank=Bank.DNA, level=2),
    )
    correct = engine.evaluate(chosen.state, True)
    assert correct.events == (Event('CORRECT', 'a'), Event('ROLL_REQUIRED', 'a'))
    assert correct.state.active_player.id == 'a'
    assert correct.state.question is None and correct.state.chosen_bank is None
    victory = engine.advance(ready(engine, 138), 6)
    assert victory.events == (
        Event('ADVANCED', 'a', 138, 140, 6), Event('LANDED', 'a', 140, 140),
        Event('VICTORY', 'a', 140, 140, level=4),
    )
    assert victory.state.winner == victory.events[-1].participant


def test_approved_finish_policy_is_fixed_for_this_rules_version():
    assert RULES_VERSION == 'inmunoquest-manual-20261116-basic-v1'
    assert START_CELL == 1 and FINISH_CELL == 140
    assert cell_at(139).kind == Kind.QUESTION
    assert cell_at(FINISH_CELL).kind == Kind.FINISH


@pytest.mark.parametrize('participant', [None, True, 1, '', '  ', 'x' * 121])
def test_invalid_participant_identity_is_rejected(engine, participant):
    with pytest.raises(ValueError):
        engine.prepare(('a', participant))


def test_states_reject_missing_active_participant_or_inactive_winner(engine):
    state = ready(engine)
    for changes in (
        {'active_index': -1}, {'active_index': 2},
        {'order_groups': (('a',), ('missing',))},
        {'players': (Player('a'), Player('b', 140))},
    ):
        with pytest.raises(ValueError):
            replace(state, **changes)
