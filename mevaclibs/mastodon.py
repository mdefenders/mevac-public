import requests
import datetime
import time
import logging
from http import HTTPStatus
from requests.exceptions import HTTPError

from mevaclibs.envs import PushEnv
from mevaclibs.common import Utils


class Mastodon:

    def __init__(self, env: PushEnv):
        self._env = env

        self._headers = {'Authorization': f'Bearer {self._env.token}'}
        self._endpoint = f'https://{self._env.domain}'

    def _update_rate_limits(self, result):
        self._env.ratelimit_limit = int(result.headers.get('x-ratelimit-limit'))
        self._env.ratelimit_remaining = int(result.headers.get('x-ratelimit-remaining'))
        self._env.ratelimit_reset = Utils.mastodon_timestamp_to_epoch(
            result.headers.get('x-ratelimit-reset')) - int(datetime.datetime.now().timestamp())

    def verify_credentials(self):
        endpoint = f'{self._endpoint}/api/v1/apps/verify_credentials'
        result = requests.get(endpoint, headers=self._headers)
        self._update_rate_limits(result)
        result.raise_for_status()

        return result.json().get('name', '')

    def _post_item(self, item_type, data, media_ids=None, private=False, in_reply_to_id=''):
        result = None
        for n in range(self._env.ratelimit_retries):
            try:
                if item_type == 'post':
                    endpoint = f'{self._endpoint}/api/v1/statuses'
                    payload = {'status': data, 'media_ids': media_ids}
                    if private:
                        payload['visibility'] = 'private'
                    if in_reply_to_id:
                        payload['in_reply_to_id'] = in_reply_to_id
                    result = requests.post(endpoint, headers=self._headers, json=payload)
                elif item_type == 'media':
                    endpoint = f'{self._endpoint}/api/v2/media'
                    with open(data, 'rb') as file:
                        result = requests.post(endpoint, headers=self._headers, files={'file': file})
                else:
                    raise Exception(f'Unknown post data type {item_type}')
                self._update_rate_limits(result)
                result.raise_for_status()
                break
            except HTTPError as exc:
                code = exc.response.status_code
                if code == HTTPStatus.TOO_MANY_REQUESTS:
                    logging.warning(f'API rate-limit exceeded. Sleeping for: {self._env.ratelimit_reset} sec')
                    time.sleep(self._env.ratelimit_reset)
                    continue
                raise
        return result.json().get('id', '0')

    def post_status(self, text: str, media_ids=None, private=False):
        result = list()
        if media_ids:
            media_count = len(media_ids)
            if media_count > 4:
                media_ids = media_ids[:4]
                logging.warning(
                    f'{media_count} media files attached but only 4 allowed. {media_count - 4} file(s) was dropped')
        if text:
            if len(text) <= self._env.text_size_limit:
                result.append(self._post_item('post', text, media_ids, private))
            else:
                post_number = 1
                text_prefix = ''
                words = text.split(' ')
                text_to_post = ''
                sub_result = ''
                for word in words:
                    if len(str(post_number)) + 2 + len(text_prefix) + 1 + len(text_to_post) + 1 + len(
                            word) < self._env.text_size_limit:
                        text_to_post = text_to_post + ' ' + word
                    else:
                        text_to_post = f'{post_number}. {text_prefix} {text_to_post}'
                        sub_result = self._post_item('post', text_to_post, media_ids, private, sub_result)
                        result.append(sub_result)
                        text_to_post = word
                        text_prefix = '->'
                        # Attach media only to the first post
                        if post_number == 1:
                            media_ids = None
                        post_number += 1
                if text_to_post:
                    text_to_post = f'{post_number}. {text_prefix} {text_to_post}'
                    result.append(self._post_item('post', text_to_post, media_ids, private, sub_result))

        elif media_ids:
            result.append(self._post_item('post', text, media_ids, private))
        else:
            raise Exception('Neither text nor media provided for post. Exiting')

        return result

    def upload_media(self, media_file):
        return self._post_item('media', media_file)

    def delete_entity(self, status_id):
        result = None
        endpoint = f'{self._endpoint}/api/v1/statuses/{status_id}'
        for n in range(self._env.ratelimit_retries):
            try:
                result = requests.delete(endpoint, headers=self._headers)
                self._update_rate_limits(result)
                result.raise_for_status()
                break
            except HTTPError as exc:
                code = exc.response.status_code
                if code == HTTPStatus.TOO_MANY_REQUESTS:
                    logging.warning(f'API rate-limit exceeded. Sleeping for: {self._env.ratelimit_reset} sec')
                    time.sleep(self._env.ratelimit_reset)
                    continue
                raise
        return result.json().get('id', '0')
