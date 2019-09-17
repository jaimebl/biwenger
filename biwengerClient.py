import requests
import requests_cache

class BiwengerClient:
    AUTH_TOKEN = 'Bearer XXX'
    X_LEAGUE = 'XXX'
    X_USER = 'XXX'

    HEADERS = {'x-lang': 'es', 'x-league': X_LEAGUE, 'x-user': X_USER, 'Authorization': AUTH_TOKEN}

    def __init__(cls):
        requests_cache.install_cache('biwenger')
        # requests_cache.install_cache('test_cache', backend='sqlite', expire_after=300)

    @classmethod
    def full_board(cls):
        return requests.get('https://biwenger.as.com/api/v2/league/890435/board?type=&limit=99999999999999',
                            headers=cls.HEADERS).json()['data']

    @classmethod
    def team(cls, teamId):
        return requests.get(
            'https://biwenger.as.com/api/v2/user/%i?fields=*,account(id),players(id,owner),lineups(round,points,count,position),league(id,name,competition,mode,scoreID),market,seasons,offers,lastPositions' % teamId,
            headers=cls.HEADERS).json()['data']

    @classmethod
    def player(cls, player_id):
        return requests.get(
            'https://cf.biwenger.com/api/v2/players/la-liga/%i?fields=*,team,fitness,reports(points,home,events,status(status,statusInfo),match(*,round,home,away),star),prices,competition,seasons,news,threads&score=5&lang=es' % player_id).json()[
            'data']

    @classmethod
    def players(cls, player_ids):
        return [cls.player(player_id) for player_id in player_ids]

    @classmethod
    def market(cls):
        return requests.get('https://biwenger.as.com/api/v2/market', headers=cls.HEADERS).json()['data']

    @classmethod
    def league(cls):
        return \
            requests.get('https://biwenger.as.com/api/v2/league?include=all&fields=*,standings,group,settings(description)',
                         headers=cls.HEADERS).json()['data']
