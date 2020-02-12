from config_parser import properties

import requests
import requests_cache
import sys


class BiwengerClient:

    def __init__(self):
        self._auth_token = properties['AUTH_TOKEN']
        self._x_league = properties['X_LEAGUE']
        self._x_user = properties['X_USER']
        self.num_requests = 0
        self.num_cached_requests = 0

        self._headers = {
            'x-lang': 'es',
            'x-league': self._x_league,
            'x-user': self._x_user,
            'Authorization': self._auth_token
        }

        requests_cache.install_cache('biwenger')
        # requests_cache.install_cache('test_cache', backend='sqlite', expire_after=300)

    def _make_request(self, url, method='GET', need_headers=True, query_params=None, body=None):

        headers = self._headers if need_headers else None


        # print(url)
        response = requests.request(method, url, headers=headers, params=query_params, json=body)

        if response.from_cache:
            self.num_cached_requests += 1

        self.num_requests += 1

        if response.status_code == 429:
            sys.exit(f'Too Many Requests {self.num_requests} ({self.num_cached_requests} cached)')
        elif response.status_code == 200:
            return response.json()['data']

    def full_board(self):
        return self._make_request(f'https://biwenger.as.com/api/v2/league/{self._x_league}/board?offset=0&limit=500') + \
               self._make_request(f'https://biwenger.as.com/api/v2/league/{self._x_league}/board?offset=500&limit=500')

    def team(self, teamId):
        return self._make_request(
            f'https://biwenger.as.com/api/v2/user/{teamId}?fields=*,account(id),players(id,owner),lineups(round,points,count,position),league(id,name,competition,mode,scoreID),market,seasons,offers,lastPositions')

    def player(self, player_id):
        # print(player_id)
        return self._make_request(
            f'https://cf.biwenger.com/api/v2/players/la-liga/{player_id}?fields=*,team,fitness,reports(points,home,events,status(status,statusInfo),match(*,round,home,away),star),prices,competition,seasons,news,threads&score=5&lang=es',
            need_headers=False)

    def players(self, player_ids):
        return [self.player(player_id) for player_id in player_ids]

    def market(self):
        return self._make_request('https://biwenger.as.com/api/v2/market')

    def league(self):
        return self._make_request(
            'https://biwenger.as.com/api/v2/league?include=all&fields=*,standings,group,settings(description)')
