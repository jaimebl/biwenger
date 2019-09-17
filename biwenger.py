import sys
from functools import reduce
from datetime import datetime, date, timedelta
from biwengerClient import BiwengerClient


def get_sold_players_amount(team, full_board):
    return sum(
        [content['amount'] for movement in full_board if movement['type'] == 'transfer'
         for content in movement['content'] if content['from']['id'] == team['id']]
    )


def get_sold_by_admin_players_amount(team, full_board):
    return sum(
        [content['amount'] for movement in full_board if movement['type'] == 'adminTransfer'
         for content in movement['content'] if content['from']['id'] == team['id']]
    )


def get_bought_players_amount(team, full_board):
    return sum(
        [content['amount'] for movement in full_board if movement['type'] == 'market'
         for content in movement['content'] if content['to']['id'] == team['id']]
    )


def get_sold_initial_players(team, full_board):
    bought_players = [content['player'] for movement in full_board if movement['type'] == 'market'
                      for content in movement['content'] if content['to']['id'] == team['id']]

    return [content['player']
            for movement in full_board if movement['type'] == 'transfer'
            for content in movement['content'] if
            content['from']['id'] == team['id'] and content['player'] not in bought_players]


def get_awards_amount(team, full_board):
    return sum(
        [result['bonus'] for movement in full_board if movement['type'] == 'roundFinished'
         for result in movement['content']['results'] if result['user']['id'] == team['id'] and 'bonus' in result]
    )


def get_starting_players(team):
    return [player['id'] for player in team['players'] if player['owner']['price'] == 0]


def day_before(millis_date):
    date_before = datetime.fromtimestamp(millis_date) - timedelta(days=1)
    return int(date_before.strftime("%y%m%d"))


def get_maximum_overbid_player(team, full_board):
    bought_players = [{'player': content['player'], 'overbid': content['amount'] - price[1],
                       'overbidPercent': (content['amount'] - price[1]) / price[1] * 100}
                      for movement in full_board if movement['type'] == 'market'
                      for content in movement['content'] if content['to']['id'] == team['id']
                      for price in bClient.player(content['player'])['prices'] if
                      price[0] == day_before(movement['date'])]

    return max(bought_players, key=lambda x: x['overbid'])


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

    sold_players_amount = get_sold_players_amount(team, full_board)
    sold_by_admin_players_amount = get_sold_by_admin_players_amount(team, full_board)
    bought_players_amount = get_bought_players_amount(team, full_board)
    awards_amount = get_awards_amount(team, full_board)

    start_not_sold_players = [price[1] for player in get_starting_players(team)
                              for price in bClient.player(player)['prices'] if price[0] == join_date]
    start_not_sold_players_amount = sum(start_not_sold_players)

    start_sold_players = [price[1] for player in get_sold_initial_players(team, full_board)
                          for price in bClient.player(player)['prices'] if price[0] == join_date]
    start_sold_players_amount = sum(start_sold_players)

    return (40000000 - start_not_sold_players_amount - start_sold_players_amount) \
           + sold_players_amount + sold_by_admin_players_amount + awards_amount - bought_players_amount


def players_ranking(full_board, league):
    ranking = []
    for standing in league['standings']:
        team = bClient.team(standing['id'])

        cash = get_player_cash(team, full_board)
        team_value = [standing['teamValue'] for standing in league['standings'] if standing['id'] == team['id']][0]
        max_bid = cash + (team_value / 4)

        ranking.append({'name': team['name'], 'cash': cash, 'teamValue': team_value, 'totalValue': cash + team_value,
                        'maxBid': max_bid})

    ranking.sort(key=lambda x: x['totalValue'], reverse=True)
    print('%22s \t%11s \t%11s \t%11s \t%11s' % ('Name', 'Total Value', 'Team Value', 'Cash', 'Max Bid'))
    [print('%22s \t%11s \t%11s \t%11s \t%11s' % (
        player['name'],
        money(player['totalValue']),
        money(player['teamValue']),
        money(player['cash']),
        money(player['maxBid'])))
     for player in ranking]


def analyze_teams(full_board, league):
    for standing in league['standings']:
        print('\n\t\t\t<< %s >>\n' % standing['name'])

        team = bClient.team(standing['id'])
        players = [bClient.player(player['id']) for player in team['players']]

        max_overbid_player = get_maximum_overbid_player(team, full_board)

        cash = get_player_cash(team, full_board)
        team_value = [standing['teamValue'] for standing in league['standings'] if standing['id'] == team['id']][0]

        sold_players_amount = get_sold_players_amount(team, full_board)
        sold_by_admin_players_amount = get_sold_by_admin_players_amount(team, full_board)
        bought_players_amount = get_bought_players_amount(team, full_board)
        awards_amount = get_awards_amount(team, full_board)

        max_bid = cash + (team_value / 4)

        # yesterday = date.today() - timedelta(days=1)
        # diffTeamValue = team_value_by_date(team, date.today()) - team_value_by_date(team, yesterday)
        daily_total_increment = reduce(lambda x, y: x + y['priceIncrement'], players, 0)

        players_data = [{**player, 'priceIncrementRelative': player['priceIncrement'] / player['price'] * 100} for
                        player
                        in players]
        players_data.sort(key=lambda x: x['priceIncrementRelative'], reverse=True)

        print('################################################################')
        print('\tJugadores Vendidos: %s' % money(sold_players_amount + sold_by_admin_players_amount))
        print('\tJugadores Comprados: %s' % money(bought_players_amount))
        print('\tPremios: %s' % money(awards_amount))
        print('\tMax Overbid: %s - %s (%i%%)' % (
            bClient.player(max_overbid_player['player'])['name'], money(max_overbid_player['overbid']),
            max_overbid_player['overbidPercent']))
        print('################################################################')
        [print('%22s \t%11s \t%8s \t%6.2f%%' % (
            playerData['name'], money(playerData['price']), money(playerData['priceIncrement']),
            playerData['priceIncrementRelative'])) for playerData in players_data]
        print('################################################################')
        print('\tCaja: %s (Maxima puja: %s)  ' % ((money(cash)), money(max_bid)))
        print('\tValor de equipo: %s ' % (money(team_value)))
        print('\tIncremento diario: %s ' % (money(daily_total_increment)))
        print('\tTotal: %s           ' % (money(cash + team_value)))
        print('################################################################\n')


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

# full_board = bClient.full_board()
# league = bClient.league()

operation = sys.argv[1]

if operation == 'analyze_offers':
    analyze_offers()
elif operation == 'analyze_teams':
    analyze_teams(bClient.full_board(), bClient.league())
elif operation == 'analyze_my_players_value':
    analyze_my_players_value()
elif operation == 'players_ranking':
    players_ranking(bClient.full_board(), bClient.league())
else:
    players_ranking(bClient.full_board(), bClient.league())

# analyze_teams(full_board, league)
# analyze_offers()
# analyze_my_players_value()
# players_ranking(full_board, league)
