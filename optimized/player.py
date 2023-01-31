'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import random
import eval7
import itertools

# strongest to weakest buckets according to standard
buckets = {1: {"AAo", "KKo", "QQo", "JJo", "AKs"},
           2: {"TTo", "AQs", "AJs", "KQs", "AKo"},
           3: {"99o", "ATs", "KJs", "QJs", "JTs", "AQo"},
           4: {"88o", "KTs", "QTs", "J9s", "T9s", "98s", "AJo", "KQo"},
           5: {"77o", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s", "Q9s", "T8s", "97s", "87s", "76s", "KJo", "QJo", "JTo"},
           6: {"66o", "55o", "K9s", "J8s", "86s", "75s", "54s", "ATo", "KTo", "QTo"},
           7: {"44o", "33o", "22o", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s", "Q8s", "T7s", "64s", "53s", "43s", "J9o", "T9o", "98o"},
           8: {"J7s", "96s", "85s", "74s", "42s", "32s", "A9o", "K9o", "Q9o", "J8o", "T8o", "87o", "76o", "65o", "54o"},
           9: {'A3o', '53o', 'T5s', '83o', 'K3o', '63s', '97o', 'J5o', '95o', 'Q3o', 'A8o', 'J4o', 'J3s', 'T5o', 'Q4o', 'K4o', '73o', 'K6o', 'T4s', 'T4o', '95s', '94o', 'T2s', 'J7o', 'Q5o', '96o', 'A4o', 'J3o', 'Q6o', 'Q7o', '52s', '83s', '92s', 'A6o', '82s', 'J6s', '64o', 'K2o', '93s', 'A5o', '62s', 'K5o', '72o', '63o', '72s', '52o', '73s', '92o', 'T7o', '75o', 'Q8o', '82o', 'T3s', '84s', 'T2o', 'J2s', '85o', 'A7o', 'J2o', '74o', 'Q5s', 'Q4s', 'Q6s', '62o', 'A2o', 'Q2s', '86o', 'J6o', 'J4s', 'T3o', 'T6s', '94s', 'T6o', '84o', 'Q7s', '43o', '32o', 'K8o', 'J5s', 'Q2o', '93o', 'Q3s', '65s', '42o', 'K7o'}
           }
probabilities = [0,
                 14/663,
                 15/663,
                 17/663,
                 25/663,
                 47/663,
                 34/663,
                 51/663,
                 66/663,
                 394/663]
# probabilities of a random hand being in each bucket


def parse_hold(hole):
    '''
    input: [eval7.Card('2s'), eval7.Card('7c')]

    parses given hole cards into buckets
    return bucket key
    used to find which bucket a given card is in
    '''
    cards = []
    for c in hole:
        cards.append(str(c))

    suited = "o"
    if cards[0][1] == cards[1][1]:
        suited = "s"

    pair = [cards[0][0] + cards[1][0] + suited,
            cards[1][0] + cards[0][0] + suited]

    bucket = 9
    for k in buckets.keys():
        for p in pair:
            if p in buckets[k]:
                bucket = k
    return bucket


def generate_set(key):
    '''
    input: integer from 1 to 9
    generates all 2 hand combos from those given in U_key
    this function is used to narrow the hole card ranges for opponent for the MONTE CARLO simulations
    in preflop
    '''
    # variable inits
    in_bounds = set()
    suits = {'c', 'd', 'h', 's'}
    opp = {('c', 'd'), ('c', 'h'), ('c', 's'), ('d', 'c'), ('d', 'h'), ('d', 's'),
           ('h', 'c'), ('h', 'd'), ('h', 's'), ('s', 'c'), ('s', 'd'), ('s', 'h')}
    pairs = list(itertools.combinations(suits, 2))
    card_combos = buckets[key]

    # actual code
    for card in card_combos:
        num1, num2, o_or_s = card[0], card[1], card[2]
        if num1 == num2:
            for pair in pairs:  # pairs, 6
                in_bounds.add(
                    (eval7.Card(num1+pair[0]), eval7.Card(num2+pair[1])))
        else:
            if o_or_s == "s":
                for suit in suits:  # suited, 4
                    in_bounds.add(
                        (eval7.Card(num1+suit), eval7.Card(num2+suit)))
            else:
                for tup in opp:  # opposite, 12
                    in_bounds.add(
                        (eval7.Card(num1+tup[0]), eval7.Card(num2+tup[1])))
    return in_bounds


def assignTopPair(hole, community):
    '''
    from yesterday's pdf

    if called, alters the opponents hold cards 
    by assigning the best pair that can be created with given community cards

    if no such pair exists because all cards of max rank, e.x. Ace, are already in community/our hand, returns None

    similar parameters to calc_strenght function, ex.
    hole = ['2d', 'Th']
    community = ['4c', '5s', 'Kc']
    '''
    deck = eval7.Deck()
    hole_cards = [eval7.Card(card) for card in hole]
    community_cards = [eval7.Card(card) for card in community]
    remove_cards = hole_cards + community_cards
    for card in remove_cards:
        deck.cards.remove(card)  # remove hole and community cards

    # find highest community card
    hash = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    max_rank = ('2', 2)
    for c in community:
        rank = c[0]
        if hash[rank] > max_rank[1]:
            max_rank = (rank, hash[rank])
    print(max_rank)

    # tries to assign hole card
    new_opp_hand = None
    suits = ['c', 'd', 'h', 's']
    while not suits:
        suitIndex = random.randint(0, len(suits) - 1)
        suit = suits[suitIndex]
        suits.pop(suitIndex)
        card = max_rank[0] + suit
        if eval7.Card(card) in deck:  # if one exists, create new hand
            new_opp_hand = []
            new_opp_hand.append(card)  # max rank
            deck.cards.remove(eval7.Card(card))
            deck.shuffle()
            new_opp_hand.append(str(deck[0]))  # random card
            break
    return new_opp_hand


def assignNutCard(hole, community):
    '''
    from yesterday's pdf

    if called, alters the opponents hold cards 
    by assigning the best nuts that can be created with given community cards

    similar parameters to calc_strenght function, ex.
    hole = ['2d', 'Th']
    community = ['4c', '5s', 'Kc']
    TODO: I have code for flop community and non-flop (>3 cards). When flop, the code considers best 5 hand combo
    of 2 hole and 3 flop
    When non-flop, the code considers best 5 hand combo of 1 hole and 4 community cards
    Because the pdf paper only consider one hole card but for flop round, idk what to do (there wouldn't be 5 cards)
    '''
    deck = eval7.Deck()
    hole_cards = [eval7.Card(card) for card in hole]
    community_cards = [eval7.Card(card) for card in community]
    remove_cards = hole_cards + community_cards
    for card in remove_cards:
        deck.cards.remove(card)  # remove hole and community cards

    best_nuts = (None, 0)

    if len(community) == 3:  # flop
        possible_holes = list(itertools.combinations(deck, 2))
        possible_communities = list(itertools.combinations(community_cards, 3))
        for hole in possible_holes:
            for rest in possible_communities:
                if eval7.evaluate(hole+rest) > best_nuts[1]:
                    best_nuts = ([str(hole[0]), str(hole[1])],
                                 eval7.evaluate(hole+rest))
    else:
        possible_communities = list(itertools.combinations(community_cards, 4))
        # if len(possible_communities) > 500: #trying to limit the time
        #     possible_communities = possible_communities[:500]
        for opp_hole_card in deck:  # 50ish
            for rest in possible_communities:  # 1000ish
                if eval7.evaluate([opp_hole_card]+list(rest)) > best_nuts[1]:
                    second_hole = None
                    while not second_hole:
                        deck.shuffle()
                        this = deck.deal(1)[0]
                        if this != opp_hole_card:
                            second_hole = this
                    print([opp_hole_card]+list(rest))  # best hand
                    best_nuts = ([str(opp_hole_card), str(second_hole)],
                                 eval7.evaluate([opp_hole_card]+list(rest)))
    return best_nuts


def calc_strength_preflop(hole, iters, opp_f_c_r=[1/3, 1/3, 1/3]):
    ''' 
    Adding opp_f_c_r with assumption that it already exists

    Using MC with iterations to evalute preflop hand strength 
    Args: 
    hole - our hole cards 
    iters - number of times we run MC 
    opp_f_c_r - (f,c,r) tuple
    '''
    deck = eval7.Deck()
    hole_cards = [eval7.Card(card) for card in hole]

    for card in hole_cards:  # removing our hole cards from the deck
        deck.cards.remove(card)

    # **************************************************************
    # NEW CODE: estimate best_hole_hands
    # TODO best possible bucket value (need to change, depends on the opponent's move)
    best_bound = 1

    raise_prob = opp_f_c_r[2]  # ex. the player only raises in 9% of the cases
    worst_bound = 1
    best_cards = probabilities[1]
    while raise_prob > best_cards:
        worst_bound += 1
        best_cards += probabilities[worst_bound]

    possible_holes = {}
    index = 0
    for key in range(best_bound, worst_bound+1):
        set_cards = generate_set(key)
        for opp_hand in set_cards:
            possible_holes[index] = opp_hand
            index += 1
    print("possible_holes, ", len(possible_holes))
    # **************************************************************

    # the score is the number of times we win, tie, or lose
    score = 0
    length = len(possible_holes)

    for _ in range(iters):  # MC the probability of winning
        deck.shuffle()

        # **************************************************************
        # NEW CODE
        rand = random.randint(0, length-1)
        opp_hole = list(possible_holes[rand])
        # **************************************************************

        _COMM = 5

        alt_community = deck.peek(_COMM)
        # the community cards that we draw in the MC

        our_hand = hole_cards + alt_community
        opp_hand = opp_hole + alt_community

        our_hand_value = eval7.evaluate(our_hand)
        opp_hand_value = eval7.evaluate(opp_hand)

        if our_hand_value > opp_hand_value:
            score += 2
        if our_hand_value == opp_hand_value:
            score += 1
        else:
            score += 0

    hand_strength = score/(2*iters)  # win probability

    return hand_strength


class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.
        Arguments:
        Nothing.
        Returns:
        Nothing.
        '''

    def calc_strength(self, hole, iters, community=[]):
        ''' 
        Using MC with iterations to evalute hand strength 
        Args: 
        hole - our hole carsd 
        iters - number of times we run MC 
        community - community cards
        '''

        deck = eval7.Deck()  # deck of cards
        # our hole cards in eval7 friendly format
        hole_cards = [eval7.Card(card) for card in hole]

        # If the community cards are not empty, we need to remove them from the deck
        # because we don't want to draw them again in the MC
        if community != []:
            community_cards = [eval7.Card(card) for card in community]
            for card in community_cards:  # removing the current community cards from the deck
                deck.cards.remove(card)

        for card in hole_cards:  # removing our hole cards from the deck
            deck.cards.remove(card)

        # the score is the number of times we win, tie, or lose
        score = 0

        for _ in range(iters):  # MC the probability of winning
            deck.shuffle()

            # Let's see how many community cards we still need to draw
            if len(community) >= 5:  # red river case
                # check the last community card to see if it is red
                if community[-1][1] == 'h' or community[-1][1] == 'd':
                    _COMM = 1
                else:
                    _COMM = 0
            else:
                # number of community cards we need to draw
                _COMM = 5 - len(community)

            _OPP = 2

            draw = deck.peek(_COMM + _OPP)

            opp_hole = draw[:_OPP]
            # the community cards that we draw in the MC
            alt_community = draw[_OPP:]

            if community == []:  # if there are no community cards, we only need to compare our hand to the opp hand
                our_hand = hole_cards + alt_community
                opp_hand = opp_hole + alt_community
            else:

                our_hand = hole_cards + community_cards + alt_community
                opp_hand = opp_hole + community_cards + alt_community

            our_hand_value = eval7.evaluate(our_hand)
            opp_hand_value = eval7.evaluate(opp_hand)

            if our_hand_value > opp_hand_value:
                score += 2

            if our_hand_value == opp_hand_value:
                score += 1
            else:
                score += 0

        hand_strength = score/(2*iters)  # win probability

        return hand_strength

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.
        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.
        Returns:
        Nothing.
        '''
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        # the total number of seconds your bot has left to play this game
        game_clock = game_state.game_clock
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        my_cards = round_state.hands[active]  # your cards
        big_blind = bool(active)  # True if you are the big blind

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.
        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.
        Returns:
        Nothing.
        '''
        my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        previous_state = terminal_state.previous_state  # RoundState before payoffs
        street = previous_state.street  # 0, 3, 4, or 5 representing when this round ended
        my_cards = previous_state.hands[active]  # your cards
        # opponent's cards or [] if not revealed
        opp_cards = previous_state.hands[1-active]

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.
        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.
        Returns:
        Your action.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        street = round_state.street
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.deck[:street]  # the board cards
        # the number of chips you have contributed to the pot this round of betting
        my_pip = round_state.pips[active]
        # the number of chips your opponent has contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]
        # the number of chips you have remaining
        my_stack = round_state.stacks[active]
        # the number of chips your opponent has remaining
        opp_stack = round_state.stacks[1-active]
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        # the number of chips you have contributed to the pot
        my_contribution = STARTING_STACK - my_stack
        # the number of chips your opponent has contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack
        net_upper_raise_bound = round_state.raise_bounds()
        stacks = [my_stack, opp_stack]  # keep track of our stacks

        my_action = None

        min_raise, max_raise = round_state.raise_bounds()
        pot_total = my_contribution + opp_contribution

        # raise logic
        if street < 3:  # preflop
            raise_amount = int(my_pip + continue_cost +
                               0.4*(pot_total + continue_cost))
        else:  # postflop
            raise_amount = int(my_pip + continue_cost +
                               0.75*(pot_total + continue_cost))

        # # ensure raises are legal
        # getting the max of the min raise and the raise amount
        raise_amount = max([min_raise, raise_amount])
        # getting the min of the max raise and the raise amount
        raise_amount = min([max_raise, raise_amount])
        # # we want to do this so that we don't raise more than the max raise or less than the min raise

        if (RaiseAction in legal_actions and (raise_amount <= my_stack)):
            temp_action = RaiseAction(raise_amount)
        elif (CallAction in legal_actions and (continue_cost <= my_stack)):
            temp_action = CallAction()
        elif CheckAction in legal_actions:
            temp_action = CheckAction()
        else:
            temp_action = FoldAction()

        _MONTE_CARLO_ITERS = 100

        # running monte carlo simulation when we have community cards vs when we don't
        if street < 3:
            strength = self.calc_strength(my_cards, _MONTE_CARLO_ITERS)
        else:
            strength = self.calc_strength(
                my_cards, _MONTE_CARLO_ITERS, board_cards)

        if continue_cost > 0:
            _SCARY = 0
            if continue_cost > 6:
                _SCARY = 0.1
            if continue_cost > 15:
                _SCARY = .2
            if continue_cost > 50:
                _SCARY = 0.35

            strength = max(0, strength - _SCARY)
            pot_odds = continue_cost/(pot_total + continue_cost)

            if strength >= pot_odds:  # nonnegative EV decision
                if strength > 0.5 and random.random() < strength:
                    my_action = temp_action
                else:
                    my_action = CallAction()

            else:  # negative EV
                my_action = FoldAction()

        else:  # continue cost is 0
            if random.random() < strength:
                my_action = temp_action
            else:
                my_action = CheckAction()

        return my_action


if __name__ == '__main__':
    # run_bot(Player(), parse_args())
    # UNCOMMENT ABOVE TO RUN ENGINE
    # ____________________________________________________

    deck = eval7.Deck()
    deck.shuffle()

    # Test Calculate_strength_preflrop
    hole = deck.deal(2)
    print("hole,", hole)
    print(calc_strength_preflop([str(hole[0]), str(hole[1])], 100))

    # #Test Parse_hold
    # hole = deck.deal(2)
    # hole2 = [eval7.Card('7s'), eval7.Card('8h')]
    # print(hole2)
    # # print(hole)
    # print(parse_hold(hole2))

    # #Test assignTopPair
    cards = deck.deal(2+3)
    hole = cards[:2]
    flop = cards[2:]
    print(hole, flop)
    print(assignTopPair(['5s', 'Ac'], ['Tc','Td', 'Th', 'Ts']))

    # #Test Nut
    # print(assignNutCard(['5s','Ac'], ['8h','6h','Tc', 'Ah','8s','2c','7c']))

    # #Test Generate_set
    # count = 0
    # for i in range(1, 10):
    #     print(i, len(generate_set(i)))
    #     count += len(generate_set(i))
    # print(count) #should be 1326

    # #Test Buckets
    # count = 0
    # for i in buckets:
    #     count += len(buckets[i])
    # print(count) #should be 169
