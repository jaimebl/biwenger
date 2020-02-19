from biwengerClient import BiwengerClient
from config_parser import properties
from time_ago import pretty_time_ago

from tabulate import tabulate
from argparse import ArgumentParser
from statistics import mean
from functools import reduce
from datetime import datetime, timedelta
from collections import Counter

POSITIONS = {1: 'PT', 2: 'DF', 3: 'MC', 4: 'DL'}


def get_sold_players_amount(team_id, full_board):
    return sum(content['amount'] for movement in full_board if movement['type'] in ['transfer', 'adminTransfer']
               for content in movement['content'] if content['from']['id'] == team_id)


def get_sold_players(team_id, full_board):
    return (content['player'] for movement in full_board if movement['type'] in ['transfer', 'adminTransfer']
            for content in movement['content'] if content['from']['id'] == team_id)


def get_bought_players_amount(team_id, full_board):
    return sum(
        content['amount'] for movement in full_board if movement['type'] in ['transfer', 'market']
        for content in movement['content'] if 'to' in content and content['to']['id'] == team_id
    )


def get_total_bought_players(team_id, full_board):
    return [content['player'] for movement in full_board if movement['type'] in ['transfer', 'market']
            for content in movement['content'] if 'to' in content and content['to']['id'] == team_id]


def get_bought_players(team_id, full_board):
    total_bought_players = get_total_bought_players(team_id, full_board);
    bought_dict = {player_id: total_bought_players.count(player_id) for player_id in total_bought_players}

    sold_players = list(get_sold_players(team_id, full_board))
    sold_dict = {player_id: sold_players.count(player_id) for player_id in sold_players}

    diff_dict = Counter(bought_dict)
    diff_dict.subtract(sold_dict)

    return (player_id for player_id in diff_dict if diff_dict[player_id] != -1)


def get_sold_initial_players(team_id, full_board):
    return (bClient.player(content['player'])
            for movement in full_board if movement['type'] == 'transfer'
            for content in movement['content'] if
            content['from']['id'] == team_id and content['player'] not in get_bought_players(team_id, full_board))


def get_not_sold_starting_players(team):
    return (bClient.player(player['id']) for player in team['players']
            if 'price' not in player['owner'].keys() or player['owner']['price'] == 0)


def get_starting_players(team, full_board):
    return list(get_sold_initial_players(team['id'], full_board)) + list(get_not_sold_starting_players(team))


def get_round_name(movement):
    return ' '.join(movement['content']['round']['name'].split()[0:2])


def get_awards_amount(team_id, full_board):
    round_finished_list = {
        get_round_name(movement): movement['content']
        for movement in reversed(full_board) if movement['type'] == 'roundFinished'
    }

    return sum(
        result['bonus'] for content in round_finished_list.values()
        for result in content['results'] if result['user']['id'] == team_id and 'bonus' in result
    )


def day_before(millis_date):
    date_before = datetime.fromtimestamp(millis_date) - timedelta(days=1)
    return int(date_before.strftime("%y%m%d"))


def get_maximum_overbid_player(team_id, full_board):
    bought_players = [{'player': content['player'], 'overbid': content['amount'] - price[1],
                       'overbidPercent': (content['amount'] - price[1]) / price[1] * 100}
                      for movement in full_board if movement['type'] in ['transfer', 'market']
                      for content in movement['content'] if 'to' in content and content['to']['id'] == team_id
                      for price in bClient.player(content['player'])['prices'] if
                      price[0] == day_before(movement['date'])]

    maximum_overbid_player = max(bought_players, key=lambda x: x['overbid'])
    return {**maximum_overbid_player, 'player': bClient.player(maximum_overbid_player['player'])}


def money(amount):
    return f'€{amount:0,.0f}'


def millis_to_date(millis):
    return datetime.fromtimestamp(millis)


def millis_to_formatted_date(millis):
    return int(millis_to_date(millis).strftime("%y%m%d"))


def full_pretty_time_ago(time):
    return f'{pretty_time_ago(time)} ({millis_to_date(time)})'


# def team_value_by_date(team, date):
#     teamPlayers = [player['id'] for player in team['players']]
#
#     teamPlayerValues = [price[1] for player in teamPlayers
#                         for price in bClient.player(player)['prices'] if price[0] == int(date.strftime("%y%m%d"))]
#
#     return sum(teamPlayerValues)


def offer_percentage(current_price, offer_amount):
    return (offer_amount - current_price) / current_price * 100


def get_player_cash(team, full_board):
    join_date = millis_to_formatted_date(team['joinDate'])
    team_id = int(team['id'])

    sold_players_amount = get_sold_players_amount(team_id, full_board)
    bought_players_amount = get_bought_players_amount(team_id, full_board)
    awards_amount = get_awards_amount(team_id, full_board)

    start_not_sold_players_amount = sum(
        get_player_price(player, join_date) for player in get_not_sold_starting_players(team)
    )

    start_sold_players_amount = sum(
        get_player_price(player, join_date) for player in get_sold_initial_players(team_id, full_board)
    )

    initial_cash = 40000000 - start_not_sold_players_amount - start_sold_players_amount
    return initial_cash + sold_players_amount + awards_amount - bought_players_amount


def get_player_price(player, date):
    # return next(price[1] for price in bClient.player(player['id'])['prices'] if price[0] == date)
    return next(price[1] for price in player['prices'] if price[0] == date)


def get_global_player_performance(player):
    avg_points_home = float(player['pointsHome'] / player['playedHome']) if player['playedHome'] else 0.0
    avg_points_away = float(player['pointsAway'] / player['playedAway']) if player['playedAway'] else 0.0

    return (avg_points_home + avg_points_away) / 2


def is_next_match_home(team):
    return team['id'] == team['nextMatch']['home']['id']


def get_global_next_player_performance(player):
    team = player['team']
    if not team:
        return 0.0
    if is_next_match_home(team):
        return float(player['pointsHome'] / player['playedHome']) if player['playedHome'] else 0.0
    else:
        return float(player['pointsAway'] / player['playedAway']) if player['playedAway'] else 0.0


def get_recent_player_performance(player):
    fitness_avg = [rate for rate in player['fitness'] if isinstance(rate, int)]

    if not fitness_avg: return 0.0
    if len(fitness_avg) == 1: return float(fitness_avg[0])

    return float(mean(fitness_avg))


def players_ranking():
    full_board = bClient.full_board()
    league = bClient.league()

    players = []
    for standing in league['standings']:
        team = bClient.team(standing['id'])

        daily_increment = sum([bClient.player(player['id'])['priceIncrement'] for player in team['players']])

        cash = get_player_cash(team, full_board)
        team_value = int(standing['teamValue'])

        max_bid = cash + (team_value / 4)

        players.append({'name': team['name'], 'cash': cash, 'teamValue': team_value, 'totalValue': cash + team_value,
                        'maxBid': max_bid, 'dailyIncrement': daily_increment, 'lastAccess': team['lastAccess']})

    players.sort(key=lambda x: x['totalValue'], reverse=True)

    print_data = [[player["name"],
                   money(player["totalValue"]),
                   money(player["teamValue"]),
                   money(player["cash"]),
                   money(player["maxBid"]),
                   money(player["dailyIncrement"]),
                   full_pretty_time_ago(player["lastAccess"])]
                  for player in players]

    print(tabulate(print_data,
                   headers=['Name', 'Total Value', 'Team Value', 'Cash', 'Max Bid', 'Daily Inc', 'Last Access'],
                   tablefmt='orgtbl', stralign='right'))


def analyze_teams():
    full_board = bClient.full_board()
    league = bClient.league()

    for standing in league['standings']:
        team = bClient.team(standing['id'])
        team_id = int(team['id'])

        players = [bClient.player(player['id']) for player in team['players']]

        # max_overbid_player = get_maximum_overbid_player(team_id, full_board)

        cash = get_player_cash(team, full_board)
        team_value = [standing['teamValue'] for standing in league['standings'] if standing['id'] == team_id][0]

        sold_players_amount = get_sold_players_amount(team_id, full_board)
        bought_players_amount = get_bought_players_amount(team_id, full_board)
        awards_amount = get_awards_amount(team_id, full_board)

        max_bid = cash + (team_value / 4)

        daily_total_increment = reduce(lambda x, y: x + y['priceIncrement'], players, 0)

        players_data = [{
            **player,
            'priceIncrementRelative': player['priceIncrement'] / player['price'] * 100,
            'performance_avg_global': get_global_player_performance(player),
            'performance_avg_global_next': get_global_next_player_performance(player),
            'performance_avg_recent': get_recent_player_performance(player),
            'performance_calculated':
                (get_global_player_performance(player) +
                 get_recent_player_performance(player) +
                 get_recent_player_performance(player)) / 3,
            'performance_calculated_next':
                (get_global_next_player_performance(player) +
                 get_recent_player_performance(player) +
                 get_recent_player_performance(player)) / 3,
        }
            for player in players]
        players_data.sort(key=lambda x: x['performance_calculated_next'], reverse=True)

        header = [
            f'\n\t\t\t<< {standing["name"]} >>\n',
            '#' * 64,
            f'\tJugadores Vendidos: {money(sold_players_amount)}',
            f'\tJugadores Comprados: {money(bought_players_amount)}',
            f'\tPremios: {money(awards_amount)}',
            '#' * 64,
        ]

        content = [f'{player_data["name"]:^20s} {POSITIONS[player_data["position"]]} '
                   f'\t{money(player_data["price"]):>12s}'
                   f'\t{money(player_data["priceIncrement"]):>9s}'
                   f'\t{player_data["priceIncrementRelative"]:>6.2f}%'
                   f'\t{player_data["performance_avg_global"]:>6.2f}({player_data["performance_avg_global_next"]:.2f})'
                   f'\t{player_data["performance_avg_recent"]:>6.2f}'
                   f'\t{player_data["performance_calculated"]:>6.2f}({player_data["performance_calculated_next"]:.2f})'
                   for player_data in players_data]

        footer = [
            '#' * 64,
            f'\tCaja: {money(cash)} (Maxima puja: {money(max_bid)})',
            f'\tValor de equipo: {money(team_value)}',
            f'\tIncremento diario: {money(daily_total_increment)}',
            f'\tTotal: {money(cash + team_value)}',
            '#' * 64
        ]

        # print(f'\tMax Overbid: {max_overbid_player["player"]["name"]} - '
        #       f'{format_money(max_overbid_player["overbid"])} '
        #       f'({max_overbid_player["overbidPercent"]:.2f}%)')

        print('\n'.join(header + content + footer), end='\n\n')


def is_team_movement(content, team_id):
    return ('from' in content.keys() and content['from']['id'] == team_id) or \
           ('to' in content.keys() and content['to']['id'] == team_id)


def map_movement(content, team_id):
    if 'from' in content.keys() and content['from']['id'] == team_id:
        return 'sell'
    elif 'to' in content.keys() and content['to']['id'] == team_id:
        return 'buy'
    else:
        return 'unknown'


def get_historic_price(player, date):
    return [price[1] for price in player['prices'] if price[0] == date][0]


def trade_history():
    full_board = bClient.full_board()
    league = bClient.league()

    for standing in league['standings']:
        team = bClient.team(standing['id'])
        join_date = millis_to_formatted_date(team['joinDate'])

        # get team movements
        movements = [{'movementType': map_movement(content, standing['id']),
                      'amount': content['amount'],
                      'player': bClient.player(content['player'])}
                     for movement in reversed(full_board) if movement['type'] in ['transfer', 'adminTransfer', 'market']
                     for content in movement['content'] if is_team_movement(content, standing['id'])]

        # initialize history with starting and bought players
        history = [{'player': player,
                    'buyAmount': get_historic_price(player, join_date),
                    'sellAmount': None,
                    'owned': True}
                   for player in get_starting_players(team, full_board)] + \
                  [{'player': movement['player'], 'buyAmount': movement['amount'], 'sellAmount': None, 'owned': True}
                   for movement in movements if movement['movementType'] == 'buy']

        # update history for sold players
        for movement in movements:
            if movement['movementType'] == 'sell':
                for idx, history_movement in enumerate(history):
                    if history_movement['player']['id'] == movement['player']['id'] \
                            and history_movement['sellAmount'] is None:
                        history[idx] = {**history_movement, 'sellAmount': movement['amount'], 'owned': False}
                        break

        # update history for non sold players
        history = [{**history_player, 'sellAmount': history_player['player']['price']}
                   if history_player['sellAmount'] is None else history_player
                   for history_player in history]

        history.sort(key=lambda x: x['sellAmount'] - x['buyAmount'], reverse=True)

        total = sum([history_player['sellAmount'] - history_player['buyAmount']
                     for history_player in history])

        header = [
            f'\n\t\t\t<< {standing["name"]} >>\n',
            f'{"Player":>26s}{"Initial":>14s}{"Final":>14s}{"Profit":>14s}'
        ]

        content = [f'{history_player["player"]["name"]:>22s}{"(x)" if history_player["owned"] else "":4s}'
                   f'{money(history_player["buyAmount"]):>14s}'
                   f'{money(history_player["sellAmount"]):>14s}'
                   f'{money(history_player["sellAmount"] - history_player["buyAmount"]):>14s}'
                   for history_player in history]

        footer = [
            f'Total: {money(total):>11s}'
        ]

        print('\n'.join(header + content + footer))


def get_player_price_yesterday(player):
    return player['prices'][-2][1]


def analyze_offers():
    offers = [{**offer, 'player': player,
               'offerPercentage': offer_percentage(player["price"], offer['amount'])}
              for offer in bClient.market()['offers'] if offer['type'] == 'purchase' and 'fromID' in offer
              for player in bClient.players(offer['requestedPlayers'])]

    offers.sort(key=lambda x: x['offerPercentage'], reverse=True)

    for offer in offers:
        print(f'{offer["player"]["name"]:^20s}'
              f'\t{money(offer["amount"]):>13s}({money(offer["amount"] - offer["player"]["price"]):>10s})'
              f'\t{millis_to_date(offer["until"])}'
              f'\t{offer["offerPercentage"]:>6.2f}%')


def get_last_increments(player, increments):
    last_prices = [price[1] for price in player['prices'][-increments:]]

    return [(last_prices[ind + 1] - last_prices[ind]) / 1000
            for ind, x in enumerate(last_prices) if (len(last_prices) - 1) > ind > -1]


def analyze_my_players_value():
    my_players = [bClient.player(player['id']) for player in bClient.team(properties['X_USER'])['players']]
    my_players_info = [{'name': player['name'], 'increments': get_last_increments(player, 40)} for player in my_players]

    for player_info in my_players_info:
        print(f'{player_info["name"]:>22s}\t', end='')
        for increment in player_info['increments']:
            print(f'{str(increment):>6s}', end='')
        print('')


def parse_args():
    parser = ArgumentParser(description='Analyze data retrieved from biwenger and prints a report.')
    parser.add_argument("operation", help="an operation to execute", type=str, metavar=('op'),
                        choices=['players_ranking',
                                 'analyze_teams',
                                 'analyze_offers',
                                 'analyze_my_players_value',
                                 'trade_history'])
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    bClient = BiwengerClient()
    locals()[args.operation]()
    print(f'Requests: {bClient.num_requests} ({bClient.num_cached_requests} cached)')
