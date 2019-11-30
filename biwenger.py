import sys
from functools import reduce
from datetime import datetime, date, timedelta
from biwengerClient import BiwengerClient


def get_sold_players_amount(team_id, full_board):
    return sum(
        [content['amount'] for movement in full_board if movement['type'] in ['transfer', 'adminTransfer']
         for content in movement['content'] if content['from']['id'] == team_id]
    )

def get_bought_players_amount(team_id, full_board):
    return sum(
        [content['amount'] for movement in full_board if movement['type'] in ['transfer', 'market']
         for content in movement['content'] if 'to' in content and content['to']['id'] == team_id]
    )


def get_sold_initial_players(team_id, full_board):
    bought_players = [content['player'] for movement in full_board if movement['type'] in ['transfer', 'market']
         for content in movement['content'] if 'to' in content and content['to']['id'] == team_id]

    return [bClient.player(content['player'])
            for movement in full_board if movement['type'] == 'transfer'
            for content in movement['content'] if
            content['from']['id'] == team_id and content['player'] not in bought_players]


def get_not_sold_starting_players(team):
    return [bClient.player(player['id']) for player in team['players'] if player['owner']['price'] == 0]


def get_starting_players(team, full_board):
    return get_sold_initial_players(team['id'], full_board) + get_not_sold_starting_players(team);


def get_awards_amount(team_id, full_board):
    return sum(
        [result['bonus'] for movement in full_board if movement['type'] == 'roundFinished'
         for result in movement['content']['results'] if result['user']['id'] == team_id and 'bonus' in result]
    )


def day_before(millis_date):
    date_before = datetime.fromtimestamp(millis_date) - timedelta(days=1)
    return int(date_before.strftime("%y%m%d"))


def get_maximum_overbid_player(team, full_board):
    bought_players = [{'player': content['player'], 'overbid': content['amount'] - price[1],
                       'overbidPercent': (content['amount'] - price[1]) / price[1] * 100}
                      for movement in full_board if movement['type'] in ['transfer', 'market']
                      for content in movement['content'] if 'to' in content and content['to']['id'] == team['id']
                      for price in bClient.player(content['player'])['prices'] if
                      price[0] == day_before(movement['date'])]

    maximum_overbid_player = max(bought_players, key=lambda x: x['overbid'])
    return {**maximum_overbid_player, 'player': bClient.player(maximum_overbid_player['player'])}


def money(number):
    return "€%s" % group(number)


def group(number):
    s = '%d' % number
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))


def millis_to_date(millis):
    return datetime.fromtimestamp(millis)


def millis_to_formatted_date(millis):
    return int(millis_to_date(millis).strftime("%y%m%d"))


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(round(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(round(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(round(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        return str(round(day_diff / 30)) + " months ago"
    return str(round(day_diff / 365)) + " years ago"


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

    start_not_sold_players = [price[1] for player in get_not_sold_starting_players(team)
                              for price in player['prices'] if price[0] == join_date]
    start_not_sold_players_amount = sum(start_not_sold_players)

    start_sold_players = [price[1] for player in get_sold_initial_players(team_id, full_board)
                          for price in player['prices'] if price[0] == join_date]
    start_sold_players_amount = sum(start_sold_players)

    return (40000000 - start_not_sold_players_amount - start_sold_players_amount) \
           + sold_players_amount + awards_amount - bought_players_amount


def players_ranking():
    full_board = bClient.full_board()
    league = bClient.league()

    ranking = []
    for standing in league['standings']:
        team = bClient.team(standing['id'])

        daily_increment = sum([bClient.player(player['id'])['priceIncrement'] for player in team['players']])

        last_access = pretty_date(team['lastAccess'])

        cash = get_player_cash(team, full_board)
        team_value = int([standing['teamValue'] for standing in league['standings'] if standing['id'] == int(team['id'])][0])
        # team_value = int(standing['teamValue'])
        max_bid = cash + (team_value / 4)

        ranking.append({'name': team['name'], 'cash': cash, 'teamValue': team_value, 'totalValue': cash + team_value,
                        'maxBid': max_bid, 'dailyIncrement': daily_increment, 'lastAccess': last_access})

    ranking.sort(key=lambda x: x['totalValue'], reverse=True)
    print('%16s \t%12s \t%12s \t%11s \t%11s \t%10s \t%15s' % (
        'Name', 'Total Value', 'Team Value', 'Cash', 'Max Bid', 'Daily Inc', 'Last Access'))
    [print('%16s \t%12s \t%12s \t%11s \t%11s \t%10s \t%15s' % (
        player['name'],
        money(player['totalValue']),
        money(player['teamValue']),
        money(player['cash']),
        money(player['maxBid']),
        money(player['dailyIncrement']),
        player['lastAccess']))
     for player in ranking]


def analyze_teams():
    full_board = bClient.full_board()
    league = bClient.league()

    for standing in league['standings']:
        print('\n\t\t\t<< %s >>\n' % standing['name'])

        team = bClient.team(standing['id'])
        players = [bClient.player(player['id']) for player in team['players']]

        max_overbid_player = get_maximum_overbid_player(team, full_board)

        cash = get_player_cash(team, full_board)
        team_value = [standing['teamValue'] for standing in league['standings'] if standing['id'] == team['id']][0]

        sold_players_amount = get_sold_players_amount(team['id'], full_board)
        bought_players_amount = get_bought_players_amount(team['id'], full_board)
        awards_amount = get_awards_amount(team['id'], full_board)

        max_bid = cash + (team_value / 4)

        # yesterday = date.today() - timedelta(days=1)
        # diffTeamValue = team_value_by_date(team, date.today()) - team_value_by_date(team, yesterday)
        daily_total_increment = reduce(lambda x, y: x + y['priceIncrement'], players, 0)

        players_data = [{**player, 'priceIncrementRelative': player['priceIncrement'] / player['price'] * 100}
                        for player in players]
        players_data.sort(key=lambda x: x['priceIncrementRelative'], reverse=True)

        print('################################################################')
        print('\tJugadores Vendidos: %s' % money(sold_players_amount))
        print('\tJugadores Comprados: %s' % money(bought_players_amount))
        print('\tPremios: %s' % money(awards_amount))
        print('\tMax Overbid: %s - %s (%i%%)' % (
            max_overbid_player['player']['name'],
            money(max_overbid_player['overbid']),
            max_overbid_player['overbidPercent']))
        print('################################################################')
        [print('%22s \t%11s \t%9s \t%6.2f%%' % (
            playerData['name'], money(playerData['price']), money(playerData['priceIncrement']),
            playerData['priceIncrementRelative'])) for playerData in players_data]
        print('################################################################')
        print('\tCaja: %s (Maxima puja: %s)  ' % ((money(cash)), money(max_bid)))
        print('\tValor de equipo: %s ' % (money(team_value)))
        print('\tIncremento diario: %s ' % (money(daily_total_increment)))
        print('\tTotal: %s           ' % (money(cash + team_value)))
        print('################################################################\n')


def is_team_movement(content, team_id):
    return ('from' in content.keys() and content['from']['id'] == team_id) or \
           ('to' in content.keys() and content['to']['id'] == team_id)



def map_movement(content, team_id ):
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
        print('\n\t\t\t<< %s >>\n' % standing['name'])
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

        print('%26s %13s %13s %13s ' % ('Player', 'Initial', 'Final', 'Profit'))
        [print('%22s%4s %13s %13s %13s ' %
               (history_player['player']['name'],
                '(x)' if history_player['owned'] else '',
                money(history_player['buyAmount']),
                money(history_player['sellAmount']),
                money(history_player['sellAmount'] - history_player['buyAmount'])))
         for history_player in history]

        total = sum([history_player['sellAmount'] - history_player['buyAmount']
                     for history_player in history])

        print('Total: %11s' % money(total))


def analyze_offers():
    offers = [{**offer, 'player': player, 'offerPercentage': offer_percentage(player['price'], offer['amount'])}
              for offer in bClient.market()['offers'] if offer['type'] == 'purchase' and 'fromID' in offer
              for player in bClient.players(offer['requestedPlayers'])]

    offers.sort(key=lambda x: x['offerPercentage'], reverse=True)

    [print('%22s \t%11s(%10s) \t%s \t%6.2f%%' % (
        offer['player']['name'],
        money(offer['amount']),
        money(offer['amount'] - offer['player']['price']),
        millis_to_date(offer['until']),
        offer_percentage(offer['player']['price'], offer['amount'])))
     for offer in offers]


def get_last_increments(player, increments):
    last_prices = [price[1] for price in player['prices'][-increments:]]

    return [(last_prices[ind + 1] - last_prices[ind]) / 1000
            for ind, x in enumerate(last_prices) if (len(last_prices) - 1) > ind > -1]


def analyze_my_players_value():
    my_players = [bClient.player(player['id']) for player in bClient.team(4095989)['players']]
    my_players_info = [{'name': player['name'], 'increments': get_last_increments(player, 40)} for player in my_players]

    for player_info in my_players_info:
        print('%22s\t' % player_info['name'], end='')
        [print('%6s\t' % increment, end='') for increment in player_info['increments']]
        print('')


bClient = BiwengerClient()

operation = sys.argv[1]
locals()[sys.argv[1]]()
