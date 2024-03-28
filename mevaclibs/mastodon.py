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

    def _post_item(self, item_type, data, media_ids=None, visibility='private', in_reply_to_id='0', lang='',
                   sensitivity=0, dry_run=True):
        result = None
        for n in range(self._env.ratelimit_retries):
            try:
                if item_type == 'post':
                    endpoint = f'{self._endpoint}/api/v1/statuses'
                    payload = {'status': data, 'media_ids': media_ids, 'visibility': visibility, 'language': lang,
                               'sensitive': str(bool(sensitivity)).lower()}
                    if in_reply_to_id and in_reply_to_id != '0':
                        payload['in_reply_to_id'] = in_reply_to_id
                    if not dry_run:
                        result = requests.post(endpoint, headers=self._headers, json=payload)
                        self._update_rate_limits(result)
                        result.raise_for_status()
                elif item_type == 'media':
                    endpoint = f'{self._endpoint}/api/v2/media'
                    if not dry_run:
                        with open(data, 'rb') as file:
                            result = requests.post(endpoint, headers=self._headers, files={'file': file})
                            self._update_rate_limits(result)
                            result.raise_for_status()
                            if result.status_code == HTTPStatus.ACCEPTED:
                                self._wait_for_media(result.json().get('id', '0'))
                else:
                    raise Exception(f'Unknown post data type {item_type}')
                break
            except HTTPError as exc:
                code = exc.response.status_code
                if code == HTTPStatus.TOO_MANY_REQUESTS:
                    logging.warning(f'API rate-limit exceeded. Sleeping for: '
                                    f'{datetime.timedelta(seconds=self._env.ratelimit_reset)}')
                    time.sleep(self._env.ratelimit_reset)
                    continue
                elif code == HTTPStatus.UNPROCESSABLE_ENTITY:
                    logging.error(f'Client Error: Unprocessable Entity for {item_type}, {data}, {media_ids}. Skipping')
                    return '0'
                raise
        if dry_run:
            return '0'
        return result.json().get('id', '0')

    def post_fb_status(self, text: str, media_ids=None, visibility='private', dry_run=True):
        result = list()
        if media_ids and len(media_ids) > 4:
            media_ids = media_ids[:4]
            logging.warning(
                f'{len(media_ids)} media files attached but only 4 allowed. {len(media_ids) - 4} file(s) was dropped')
        if text:
            if len(text) <= self._env.text_size_limit:
                result.append(self._post_item('post', text, media_ids, visibility, dry_run=dry_run))
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
                        sub_result = self._post_item('post', text_to_post, media_ids, visibility, sub_result, dry_run)
                        result.append(sub_result)
                        text_to_post = word
                        text_prefix = '->'
                        # Attach media only to the first post
                        if post_number == 1:
                            media_ids = None
                        post_number += 1
                if text_to_post:
                    text_to_post = f'{post_number}. {text_prefix} {text_to_post}'
                    result.append(self._post_item('post', text_to_post, media_ids, visibility, sub_result, dry_run))

        elif media_ids:
            result.append(self._post_item('post', text, media_ids, visibility, dry_run=dry_run))
        else:
            raise Exception('Neither text nor media provided for post. Exiting')

        return result

    def post_mst_status(self, text: str, lang='en', media_ids=None, visibility='private', sensitivity=0,
                        in_reply_to_id='0', dry_run=True):
        return self._post_item('post', text, media_ids, visibility, in_reply_to_id, lang=lang,
                               sensitivity=sensitivity, dry_run=dry_run)

    def upload_media(self, media_file, dry_run=True):
        return self._post_item('media', media_file, dry_run=dry_run)

    def delete_entity(self, status_id):
        if status_id == '0':
            return status_id
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
                    logging.warning(f'API rate-limit exceeded. Sleeping for: '
                                    f'{datetime.timedelta(seconds=self._env.ratelimit_reset)}')
                    time.sleep(self._env.ratelimit_reset)
                    continue
                raise
        return result.json().get('id', '0')

    def _wait_for_media(self, media_id):
        if media_id != '0':
            endpoint = f'{self._endpoint}/api/v1/media'
            for i in range(self._env.media_retries):
                logging.info(f'Waiting for media {media_id} to be processed. Round {i}')
                result = requests.get(f'{endpoint}/{media_id}', headers=self._headers)
                if result.status_code == HTTPStatus.PARTIAL_CONTENT:
                    time.sleep(self._env.media_timeout)
                else:
                    break
