import logging
from numbers import Number
from typing import TYPE_CHECKING

from base.actions.action import Action
from base.card import Card
from base.enums.game_phase import GamePhase

if TYPE_CHECKING:
    from base.board import Board
    from base.player import Player


class DiscardCardAction(Action):

    def __init__(self, card: Card):
        super().__init__()
        self.card = card

    def _key(self):
        """Return a tuple of all fields that should be checked in equality and hashing operations."""
        return self.card

    def get_reward(self) -> Number:
        return 1  # Basic reward to not discourage the discard behaviour.

    def validate(self, player: 'Player', board: 'Board', verbose: bool = False):
        # Check the board phase
        if board.phase != GamePhase.ACTION_PHASE:
            if verbose:
                logging.info("Invalid action {}. Reason: wrong phase - {}".format(self, board.phase))
            return False
        # Make sure the player discard a card it currently holds in its hand
        if self.card not in player.hand:
            return False
        return True

    def _execute(self, player: 'Player', board: 'Board'):
        card = player.hand.pop(self.card)
        board.stack.put(card)

    def _target_phase(self, player: 'Player', board: 'Board') -> GamePhase:
        if player.hand.is_empty():
            return GamePhase.NO_CARDS_END_TURN_PHASE
        return GamePhase.END_TURN_PHASE

    def __str__(self):
        execution_tag = "" if not self.is_executed else "(E) "
        return "{}Discard {}".format(execution_tag, self.card)
