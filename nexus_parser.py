import json
from loguru import logger as logging
import urllib3
from urllib.parse import urlparse


class NexusParser:
    pool_manager: urllib3.PoolManager
    API_URL_BASE = 'service/rest/v1/'
    DEFAULT_SCHEME = 'https'
    http_headers = {}
    docker_images = {}

    def __init__(self, server_name, repo_name, server_user='', server_pass=''):
        self.server_name = server_name
        self.server_user = server_user
        self.server_pass = server_pass
        self.repo_name = repo_name

    def init_pool_manager(self, retries) -> urllib3.poolmanager.PoolManager:
        self.pool_manager = urllib3.PoolManager(retries=urllib3.Retry(connect=retries))

    def __get_comp(self, continuation_token='') -> urllib3.request.RequestMethods:
        if continuation_token == '':
            try:
                return self.pool_manager.request('GET',
                                                 f'{self.__get_server_url().strip("/")}{self.__repo_comp_urn()}',
                                                 headers=self.http_headers)
            except urllib3.exceptions.HTTPError:
                # TODO: handle errors
                logging.error('HTTP ERROR')
        else:
            try:
                return self.pool_manager.request('GET',
                                                 f'{self.__get_server_url().strip("/")}'
                                                 f'{self.__repo_comp_urn(continuation_token)}',
                                                 headers=self.http_headers)
            except urllib3.exceptions.HTTPError:
                # TODO: handle errors
                logging.error('HTTP_ERROR')

    def setup_headers(self):
        if self.server_user == '' and self.server_pass == '':
            self.__set_headers([self.__set_accept_header()])
            logging.debug('No auth credentials provided. Switching to anonymous')
        else:
            self.__set_headers([self.__set_accept_header(), self.__set_auth_header()])
            logging.debug('Setting up auth headers')

    def __get_server_url(self) -> str:
        url = urlparse(self.server_name)
        if not url.scheme:
            return f'{self.DEFAULT_SCHEME}://{url.geturl()}'

        return str(url.geturl())

    def get_all_comps(self, continuation_token='', processed_items=0) -> dict:
        resp: urllib3.request.RequestMethods

        if continuation_token == '':
            resp = self.__get_comp()
        else:
            resp = self.__get_comp(continuation_token)

        if resp.status == 200:
            j = json.loads(resp.data.decode('utf-8'))
            if 'items' in j:
                for item in j['items']:
                    try:
                        if item['format'] == 'docker':
                            logging.debug(f"Adding image: {item['name']}:{item['version']}")
                            self.docker_images[item['id']] = {item['name']: item['version']}
                        else:
                            logging.error(f'wrong format for target component: {item["format"]}')
                            return self.docker_images
                    except KeyError:
                        logging.error("'format' key not found in server response.")
                        return self.docker_images

            if 'continuationToken' in j:
                if j['continuationToken'] is not None:
                    processed_items += len(j['items'])
                    logging.debug(f'Continue... Items processed: {processed_items}')
                    self.get_all_comps(j['continuationToken'], processed_items)
                else:
                    return self.docker_images
        else:
            logging.error(f'Wrong http server status: {resp.status}')
            logging.error(f'Server respond with answer: {resp.data}')

        return self.docker_images

    def __set_headers(self, headers: list):
        for h in headers:
            self.http_headers = self.http_headers | h

    def __set_auth_header(self) -> urllib3.util.request:
        return urllib3.make_headers(basic_auth=f'{self.server_user}:{self.server_pass}')

    def __set_accept_header(self) -> dict:
        return {'accept': 'application/json'}

    def __repo_comp_urn(self, continuation_token='') -> str:
        if not continuation_token:
            return f'/{self.API_URL_BASE}components?repository={self.repo_name}'
        return f'/{self.API_URL_BASE}components?repository={self.repo_name}&continuationToken={continuation_token}'
