import json
import logging

from loguru import logger as logging
import urllib3
from urllib.parse import urlparse
import urllib3.exceptions as http_ex


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

    def init_pool_manager(self, retries=3):
        self.pool_manager = urllib3.PoolManager(retries=urllib3.Retry(connect=retries))

    def __get_comp(self, continuation_token='') -> urllib3.request.RequestMethods:
        # Get server url
        srv_url = self.__get_server_url().strip("/")

        if continuation_token == '':
            http_request = f'{srv_url}{self.__repo_comp_urn()}'
        else:
            http_request = f'{srv_url}{self.__repo_comp_urn(continuation_token)}'

        try:
            return self.pool_manager.request('GET', http_request, headers=self.http_headers)
        except http_ex.MaxRetryError:
            logging.error(f'Max retries exceeded while connecting to server {srv_url}')
        except http_ex.ConnectTimeoutError:
            logging.error(f'Timeout is occurred while connecting to server {srv_url}')
        except http_ex.HTTPError:
            logging.error(f'HTTP error occurred while connecting to server {srv_url}')
        except Exception as e:
            logging.error(f'Non specific http request error: {e}')

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

    def get_results(self) -> dict:
        return self.docker_images

    def analyse_all_comps(self, continuation_token='', processed_items=0) -> None:
        if continuation_token == '':
            resp = self.__get_comp()
        else:
            resp = self.__get_comp(continuation_token)

        try:
            status = resp.status
        except AttributeError:
            logging.error(f"Server returns no status in the request. Stop processing.")
            return

        if status == 200:
            j = json.loads(resp.data.decode('utf-8'))
            if 'items' in j:
                for item in j['items']:
                    try:
                        if item['format'] == 'docker':
                            logging.debug(f"Adding image: {item['name']}:{item['version']}")
                            self.docker_images[item['id']] = {item['name']: item['version']}
                        else:
                            logging.error(f'wrong format for target component: {item["format"]}')
                            return
                    except KeyError:
                        logging.error("'format' key not found in server response.")
                        return

            if 'continuationToken' in j:
                if j['continuationToken'] is not None:
                    processed_items += len(j['items'])
                    logging.debug(f'Continue... Items processed: {processed_items}')
                    self.analyse_all_comps(j['continuationToken'], processed_items)
                else:
                    return
        else:
            logging.error(f'Wrong http server status: {resp.status}')
            # Print response body if exists
            data = resp.data.decode("utf-8")
            if len(data) > 0:
                logging.error(f'Server respond with answer: {data}')

        return

    def __set_headers(self, headers: list):
        for h in headers:
            self.http_headers = self.http_headers | h

    def __set_auth_header(self) -> urllib3.util.request:
        return urllib3.make_headers(basic_auth=f'{self.server_user}:{self.server_pass}')

    @staticmethod
    def __set_accept_header() -> dict:
        return {'accept': 'application/json'}

    def __repo_comp_urn(self, continuation_token='') -> str:
        if not continuation_token:
            return f'/{self.API_URL_BASE}components?repository={self.repo_name}'
        return f'/{self.API_URL_BASE}components?repository={self.repo_name}&continuationToken={continuation_token}'
