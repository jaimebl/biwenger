from functools import reduce
from datetime import datetime, date, timedelta

import requests
import requests_cache

AUTH_TOKEN = 'YOUR_TOKEN_HERE'

def fetch_full_board():
    h = {'x-lang': 'es', 'x-league': '890435', 'x-user': '4095989', 'Authorization': AUTH_TOKEN}
    return \
        requests.get('https://biwenger.as.com/api/v2/league/890435/board?type=&limit=99999999999999', headers=h).json()[
            'data']


def fetch_team(teamId):
    h = {'x-lang': 'es', 'x-league': '890435', 'x-user': '4095989', 'Authorization': AUTH_TOKEN}
    return requests.get(
        'https://biwenger.as.com/api/v2/user/%i?fields=*,account(id),players(id,owner),lineups(round,points,count,position),league(id,name,competition,mode,scoreID),market,seasons,offers,lastPositions' % teamId,
        headers=h).json()['data']


def fetch_player(playerId):
    return requests.get(
        'https://cf.biwenger.com/api/v2/players/la-liga/%i?fields=*,team,fitness,reports(points,home,events,status(status,statusInfo),match(*,round,home,away),star),prices,competition,seasons,news,threads&score=5&lang=es' % playerId).json()[
        'data']


def fetch_league():
    h = {'x-lang': 'es', 'x-league': '890435', 'x-user': '4095989', 'Authorization': AUTH_TOKEN}

    return \
        requests.get('https://biwenger.as.com/api/v2/league?include=all&fields=*,standings,group,settings(description)',
                     headers=h).json()['data']


def get_sold_players_amount(team, fullBoard):
    soldAmounts = [content['amount'] for movement in fullBoard if movement['type'] == 'transfer' for content in
                   movement['content'] if content['from']['id'] == team['id']]

    return reduce(lambda x, y: x + y, soldAmounts, 0)


def get_sold_by_admin_players_amount(team, fullBoard):
    soldByAdminAmounts = [content['amount'] for movement in fullBoard if movement['type'] == 'adminTransfer' for content
                          in
                          movement['content'] if content['from']['id'] == team['id']]

    return reduce(lambda x, y: x + y, soldByAdminAmounts, 0)


def get_bought_players_amount(team, fullBoard):
    boughtAmounts = [content['amount'] for movement in fullBoard if movement['type'] == 'market' for content in
                     movement['content'] if content['to']['id'] == team['id']]

    return reduce(lambda x, y: x + y, boughtAmounts, 0)


def get_sold_initial_players(team, fullBoard):
    boughtPlayers = [content['player'] for movement in fullBoard if movement['type'] == 'market' for content in
                     movement['content'] if content['to']['id'] == team['id']]

    return [content['player'] for movement in fullBoard if movement['type'] == 'transfer' for content in
            movement['content'] if content['from']['id'] == team['id'] and content['player'] not in boughtPlayers]


def get_awards_amount(team, fullBoard):
    awardAmounts = [result['bonus'] for movement in fullBoard if movement['type'] == 'roundFinished' for result in
                    movement['content']['results'] if result['user']['id'] == team['id'] and 'bonus' in result]

    return reduce(lambda x, y: x + y, awardAmounts, 0)


def get_starting_players(team):
    return [player['id'] for player in team['players'] if player['owner']['price'] == 0]


def day_before(millisDate):
    date_before = datetime.fromtimestamp(millisDate) - timedelta(days=1)
    return int(date_before.strftime("%y%m%d"))


def get_maximum_overbid_player(team, fullBoard):
    bought_players = [{'player': content['player'], 'overbid': content['amount'] - price[1],
                       'overbidPercent': (content['amount'] - price[1]) / price[1] * 100} for movement in fullBoard
                      if
                      movement['type'] == 'market' for content in
                      movement['content'] if content['to']['id'] == team['id'] for price in
                      fetch_player(content['player'])['prices'] if
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


def team_value_by_date(team, date):
    teamPlayers = [player['id'] for player in team['players']]

    teamPlayerValues = [price[1] for player in teamPlayers for price in
                        fetch_player(player)['prices'] if
                        price[0] == int(date.strftime("%y%m%d"))]

    return reduce(lambda x, y: x + y, teamPlayerValues, 0)


requests_cache.install_cache('demo_cache')
# requests_cache.install_cache('test_cache', backend='sqlite', expire_after=300)

fullBoard = fetch_full_board()
league = fetch_league()

for standing in league['standings']:
    print('\n\t\t\t<< %s >>\n' % standing['name'])

    team = fetch_team(standing['id'])
    players = [fetch_player(player['id']) for player in team['players']]

    max_overbid_player = get_maximum_overbid_player(team, fullBoard)

    joinDate = millis_to_formatted_date(team['joinDate'])

    soldPlayersAmount = get_sold_players_amount(team, fullBoard)
    soldByAdminPlayersAmount = get_sold_by_admin_players_amount(team, fullBoard)
    boughtPlayersAmount = get_bought_players_amount(team, fullBoard)
    awardsAmount = get_awards_amount(team, fullBoard)

    startNotSoldPlayers = [price[1] for player in get_starting_players(team) for price in
                           fetch_player(player)['prices'] if
                           price[0] == joinDate]
    startNotSoldPlayersAmount = reduce(lambda x, y: x + y, startNotSoldPlayers, 0)

    startSoldPlayers = [price[1] for player in get_sold_initial_players(team, fullBoard) for price in
                        fetch_player(player)['prices'] if
                        price[0] == joinDate]
    startSoldPlayersAmount = reduce(lambda x, y: x + y, startSoldPlayers, 0)

    cash = (
                   40000000 - startNotSoldPlayersAmount - startSoldPlayersAmount) + soldPlayersAmount + soldByAdminPlayersAmount + awardsAmount - boughtPlayersAmount

    teamValue = [standing['teamValue'] for standing in league['standings'] if standing['id'] == team['id']][0]

    maxBid = cash + (teamValue / 4)

    # yesterday = date.today() - timedelta(days=1)
    # diffTeamValue = team_value_by_date(team, date.today()) - team_value_by_date(team, yesterday)
    dailyTotalIncrement = reduce(lambda x, y: x + y['priceIncrement'], players, 0)

    playersData = [{'name': player['name'], 'price': player['price'], 'priceIncrement': player['priceIncrement'],
                    'priceIncrementRelative': player['priceIncrement'] / player['price'] * 100} for player in players]
    playersData.sort(key=lambda x: x['priceIncrementRelative'], reverse=True)

    print('################################################################')
    print('\tValor equipo inicial: %s' % (money(startSoldPlayersAmount + startNotSoldPlayersAmount)))
    print('\tJugadores Vendidos: %s' % money(soldPlayersAmount + soldByAdminPlayersAmount))
    print('\tJugadores Comprados: %s' % money(boughtPlayersAmount))
    print('\tPremios: %s' % money(awardsAmount))
    print('\tMax Overbid: %s - %s (%i%%)' % (
        fetch_player(max_overbid_player['player'])['name'], money(max_overbid_player['overbid']), max_overbid_player['overbidPercent']))
    print('################################################################')
    [print('%22s \t%11s \t%8s \t%6.2f%%' % (
        playerData['name'], money(playerData['price']), money(playerData['priceIncrement']),
        playerData['priceIncrementRelative'])) for playerData in playersData]
    print('################################################################')
    print('\tCaja: %s (Maxima puja: %s)  ' % ((money(cash)), money(maxBid)))
    print('\tValor de equipo: %s ' % (money(teamValue)))
    print('\tIncremento diario: %s ' % (money(dailyTotalIncrement)))
    print('\tTotal: %s           ' % (money(cash + teamValue)))
    print('################################################################\n')

# print(fullBoard)
