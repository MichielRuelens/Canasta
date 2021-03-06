import logging
from numbers import Number
from typing import List
from typing import TYPE_CHECKING

from base.actions.action import Action
from base.card import Card
from base.cards.card_series import CardSeries
from base.enums.game_phase import GamePhase

if TYPE_CHECKING:
    from base.board import Board
    from base.player import Player


class PutAction(Action):

    def __init__(self, cards: List[Card]):
        super().__init__()
        self.series = CardSeries(cards)

    def _key(self):
        """Return a tuple of all fields that should be checked in equality and hashing operations."""
        return self.series

    def get_reward(self) -> Number:
        """The reward for putting down a series is exactly equivalent to that series' value."""
        return self.series.get_total_value()

    def validate(self, player: 'Player', board: 'Board', verbose: bool = False):
        # Check the board phase
        if board.phase not in [GamePhase.ACTION_PHASE, GamePhase.PLAY_JOKER_PHASE]:
            if verbose:
                logging.info("Invalid action {}. Reason: wrong phase - {}".format(self, board.phase))
            return False
        # Make sure we replaying the joker if we're in play joker phase
        if board.phase == GamePhase.PLAY_JOKER_PHASE:
            if not any([card.is_joker() for card in self.series]):
                return False
        # Check if player is going to clear its hand and whether its allowed to do so
        if player.num_cards() <= len(self.series) + 1 and not board.player_may_clear_hand(player, self):
            return False
        # Make sure the player has all specified cards
        for card in self.series:
            if card not in player.hand:
                return False
        # Make sure the card series itself is valid
        if not self.series.is_valid():
            return False
        return True

    def _execute(self, player: 'Player', board: 'Board'):
        for card in self.series:
            player.hand.pop(card)
        team_series = board.get_series_for_player(player)
        team_series.append(self.series)

    def _target_phase(self, player: 'Player', board: 'Board') -> GamePhase:
        if player.hand.is_empty():
            return GamePhase.NO_CARDS_PHASE
        return GamePhase.ACTION_PHASE

    def will_create_pure(self, player: 'Player', board: 'Board') -> bool:
        """Return True if executing this action will create a pure canasta for the player."""
        if self.series.is_pure():
            return True
        return False

    def __str__(self):
        execution_tag = "" if not self.is_executed else "(E) "
        return "{}Put {}".format(execution_tag, self.series)
