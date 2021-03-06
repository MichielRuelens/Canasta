from typing import List, Optional

from ai.ai_player import AIPlayer
from base.board import Board
from base.card import Card
from base.cards.card_series import CardSeries
from base.cards.deck import Deck
from base.cards.double_deck import DoubleDeck
from base.cards.hand import Hand
from base.cards.stack import Stack
from base.constants import Constants
from base.enums.game_phase import GamePhase
from base.enums.team_color import TeamColor
from base.game_history import GameHistory
from base.game_state import GameState
from base.human_player import HumanPlayer
from base.player import Player
from base.team import Team


class Game:

    def __init__(self, keep_history: bool = True):
        self.players = None  # type: Optional[List[Player]]
        self.teams = None  # type: Optional[List[Team]]
        self.current_player_index = None
        self.current_team_index = None
        self.board = None  # type: Optional[Board]
        self.keep_history = keep_history
        self.history = GameHistory()
        self.initialized = False

    def reset_game(self, initialize: bool = True, clear_history: bool = True):
        self.players = None  # type: Optional[List[Player]]
        self.teams = None  # type: Optional[List[Team]]
        self.current_player_index = None
        self.current_team_index = None
        self.board = None  # type: Optional[Board]
        if clear_history:
            self.history.clear()
        self.initialized = False
        if initialize:
            self.initialize_game()

    def initialize_game(self):
        if not self.initialized:
            self.current_player_index = 0
            self.current_team_index = 0
            # Initialize players
            self._initialize_players()
            # Create new deck
            deck = self._create_deck()
            # Deal player hands
            self._deal_hands(deck)
            # Set up board (deck and piles)
            self._initialize_board(deck)
            # Set up the initial stack (one card from deck)
            self._initialize_board_stack()
            # Set up game phase
            self.board.set_phase(GamePhase.DRAW_PHASE)
            self.initialized = True
            if self.keep_history:
                self.history.add(self, None)

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    @property
    def current_team(self) -> Team:
        return self.teams[self.current_team_index]

    @property
    def red_team(self) -> Optional[Team]:
        if self.teams:
            return self.teams[0]
        return None

    @property
    def blue_team(self) -> Optional[Team]:
        if self.teams:
            return self.teams[1]
        return None

    def play_single_step(self, verbose: bool = False):
        """Play a single action in a game of canasta."""
        if not self.initialized:
            raise Exception("Game not initialized")
        if not self.is_finished():
            if verbose:
                self.print()
                print("Current player: {}".format(self.current_player_index))
            action = self.players[self.current_player_index].play_single_step(self.get_state(), verbose=verbose)
            if self.keep_history:
                self.history.add(self, action)
            if self.board.phase == GamePhase.END_TURN_PHASE:
                self._next_player_turn()

    def get_state(self) -> GameState:
        """Return the current GameState of this Board."""
        return GameState(self.board, self.players,
                         self.current_player_index, self.current_team_index,
                         self.get_red_team_score(include_opponent_cards=False),
                         self.get_blue_team_score(include_opponent_cards=False))

    def get_red_team_score(self, include_opponent_cards: bool = True):
        """
        :param include_opponent_cards: if True, include the opponents cards values in the score
        :return: the total score for the red team.
        """
        opponent_cards = []
        if include_opponent_cards:
            for player in self.blue_team.players:
                opponent_cards.extend(player.hand.get_raw_cards())
        return self._get_team_score(self.red_team, self.board.red_team_series, opponent_cards)

    def get_blue_team_score(self, include_opponent_cards: bool = True):
        """
        :param include_opponent_cards: if True, include the opponents cards values in the score
        :return: the total score for the blue team.
        """
        opponent_cards = []
        if include_opponent_cards:
            for player in self.red_team.players:
                opponent_cards.extend(player.hand.get_raw_cards())
        return self._get_team_score(self.blue_team, self.board.blue_team_series, opponent_cards)

    @staticmethod
    def _get_team_score(team: Team, team_series: List[CardSeries], opponent_cards: List[Card]) -> int:
        """Return the total score for given team, its card series and the oppposing teams cards."""
        total_score = 0
        for series in team_series:
            total_score += series.get_total_value()
        for card in opponent_cards:
            total_score += card.get_score()
        if team.has_grabbed_pile():
            total_score += 100
        # TODO: Add 100 points for finishing the game by drawing a card from the deck
        return total_score

    def is_finished(self) -> bool:
        """
        Return True if the game is finished.

        The game can finish in the following ways:
            - The deck is empty and there are no piles remaining to serve as the new deck.
            - A player has no cards left while having already picked their teams pile and having a pure on the board.
        """
        if self.board.deck.is_empty() and self.board.num_piles_remaining() == 0:
            # No cards left to play
            return True
        for player in self.players:
            if player.hand.is_empty() and player.team.has_grabbed_pile() and self.board.team_has_pure(player.team):
                # Player finished the game
                return True
        return False

    def _next_player_turn(self) -> None:
        """Increment the player and team counters to indicate it's now the next players turn."""
        self.current_player_index += 1
        self.current_player_index %= Constants.NUM_PLAYERS
        self.current_team_index += 1
        self.current_team_index %= Constants.NUM_TEAMS
        self.board.set_phase(GamePhase.DRAW_PHASE)

    def _initialize_players(self) -> None:
        self.players = [AIPlayer(i) if i in Constants.AI_PLAYER_INDEXES else HumanPlayer(i)
                        for i in range(Constants.NUM_PLAYERS)]
        team_red = Team(players=[self.players[0], self.players[2]], color=TeamColor.RED)
        self.players[0].set_team(team_red)
        self.players[2].set_team(team_red)
        team_blue = Team(players=[self.players[1], self.players[3]], color=TeamColor.BLUE)
        self.players[1].set_team(team_blue)
        self.players[3].set_team(team_blue)
        self.teams = [team_red, team_blue]

    @staticmethod
    def _create_deck() -> Deck:
        deck = DoubleDeck(with_jokers=True)
        deck.shuffle()
        return deck

    def _deal_hands(self, deck: Deck):
        """Deal cards from the deck to each player to create a their starting hands."""
        # Draw cards from the deck
        hands = [Hand(deck.deal_n(Constants.NUM_CARDS_IN_STARTING_HAND)) for _ in range(len(self.players))]
        # Hand the cards to each player
        for i, player in enumerate(self.players):
            player.deal(hands[i])

    def _initialize_board(self, deck):
        left_pile_cards = Stack(deck.deal_n(Constants.NUM_CARDS_IN_PILE))
        right_pile_cards = Stack(deck.deal_n(Constants.NUM_CARDS_IN_PILE))
        self.board = Board(deck=deck, left_pile=left_pile_cards, right_pile=right_pile_cards)

    def _initialize_board_stack(self):
        """Deal 1 card onto the stack."""
        card = self.board.deck.deal()
        self.board.stack.put(card)

    def print(self):
        if self.players is not None:
            for player in self.players:
                print(player)
        else:
            print("No players.")
        if self.board is not None:
            print(self.board)
        else:
            print("No board.")
