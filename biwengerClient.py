import requests
import requests_cache
import sys


class BiwengerClient:
    AUTH_TOKEN = 'Bearer XXX'
    X_LEAGUE = 'XXX'
    X_USER = 'XXX'

    HEADERS = {'x-lang': 'es', 'x-league': X_LEAGUE, 'x-user': X_USER, 'Authorization': AUTH_TOKEN}

    def __init__(cls):
        requests_cache.install_cache('biwenger')
        # requests_cache.install_cache('test_cache', backend='sqlite', expire_after=300)

    @classmethod
    def make_request(cls, url, method='GET', headers=HEADERS, query_params=None, body=None):
        response = requests.request(method, url, headers=headers, params=query_params, json=body)
        if response.status_code == 429:
            sys.exit("Too Many Requests")
        elif response.status_code == 200:
            return response.json()['data']

    @classmethod
    def full_board(cls):
        return cls.make_request('https://biwenger.as.com/api/v2/league/890435/board?type=&limit=99999999999999')

    @classmethod
    def team(cls, teamId):
        return cls.make_request(f'https://biwenger.as.com/api/v2/user/{teamId}?fields=*,account(id),players(id,owner),lineups(round,points,count,position),league(id,name,competition,mode,scoreID),market,seasons,offers,lastPositions')

    @classmethod
    def player(cls, player_id):
        # print(player_id)
        return cls.make_request(f'https://cf.biwenger.com/api/v2/players/la-liga/{player_id}?fields=*,team,fitness,reports(points,home,events,status(status,statusInfo),match(*,round,home,away),star),prices,competition,seasons,news,threads&score=5&lang=es',
                                headers=None)

    @classmethod
    def players(cls, player_ids):
        return [cls.player(player_id) for player_id in player_ids]

    @classmethod
    def market(cls):
        return cls.make_request('https://biwenger.as.com/api/v2/market')

    @classmethod
    def league(cls):
        return cls.make_request('https://biwenger.as.com/api/v2/league?include=all&fields=*,standings,group,settings(description)')
