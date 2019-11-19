import webbrowser
from time import time
from json import loads
from typing import List, Dict, Any
from base64 import b64encode
from certifi import where
from urllib3 import PoolManager
from urllib3.response import HTTPResponse
from urllib.parse import urlencode, quote

from . import Config, server, log


class Spotify:
    accounts_url = 'https://accounts.spotify.com'
    api_url = 'https://api.spotify.com/v1'
    redirect_uri = 'http://localhost:8888'

    def __init__(self):
        if not (Config.client and Config.secret):
            raise Exception('Missing Spotify client credentials')
        self.client = PoolManager(ca_certs=where())

    def response(self, response: HTTPResponse) -> Dict[str, Any]:
        if response.status != 200:
            raise ConnectionError(
                f'Failed with code {response.status}: {response.reason}')
        return loads(response.data)

    @property
    def token(self) -> str:
        if not Config.token:
            self.authorize()
        elif Config.validity < time():
            self.refresh()
        return Config.token

    def authorize(self) -> None:
        payload = {
            'client_id': Config.client,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': 'playlist-modify-public',
        }
        log.info('Opening browser for authorization')
        webbrowser.open(f"{self.accounts_url}/authorize?{urlencode(payload)}")
        code = server.listen()
        self.authenticate(code)

    def authenticate(self, code: str) -> None:
        payload = {
            'code': code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
            'client_id': Config.client,
            'client_secret': Config.secret,
        }
        log.info('Authenticating client')
        response = self.client.request_encode_body(
            'POST',
            self.accounts_url + '/api/token',
            fields=payload,
            encode_multipart=False)
        data = self.response(response)
        Config.update(
            token=data['access_token'],
            validity=time() + data['expires_in'],
            refresh=data['refresh_token'])

    def refresh(self):
        payload = {
            'refresh_token': self.token.refresh,
            'grant_type': 'refresh_token'
        }
        keys = f"{Config.client}:{Config.secret}"
        encoded_keys = b64encode(keys.encode("ascii")).decode("ascii")
        headers = {'Authorization': f'Basic {encoded_keys}'}
        log.info('Refreshing token')
        response = self.client.request_encode_body(
            'POST',
            self.accounts_url + '/api/token',
            fields=payload,
            headers=headers,
            encode_multipart=False)
        data = self.response(response)
        Config.update(
            token=data['access_token'], validity=time() + data['expires_in'])

    def search(self, artist: str, title: str):
        params = {
            'limit': 1,
            'type': 'track',
            'q': f'artist:{artist} track:{title}',
        }
        headers = {'Authorization': f"Bearer {self.token}"}
        query = urlencode(params, quote_via=quote).replace('%3A', ':')
        log.info(f"Searching for {artist} - {title}")
        response = self.client.request(
            'GET', f"{self.api_url}/search?{query}", headers=headers)
        data = self.response(response)
        if data['items']:
            # track = Track(**data['items'])
            log.debug(f"Track found")
            track = data['tracks']['items'][0]
            track_id = track['id']
            track_name = track['name']
            artist = track['artist'][0]['name']
        else:
            log.debug("Track not found")
        return self.get('/search', headers=headers)

    def add(self, tracks: List['Track']):
        self.client.request('POST', '')

    def reorder(self, number, range):
        self.client.request('PUT', '')

    def remove(self, tracks):
        self.client.request('DELETE', '')
