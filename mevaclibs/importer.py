from mevaclibs.envs import LoadEnv
from os import walk
from os import path
import logging
import json
import sqlite3
from time import strftime, localtime
from tabulate import tabulate


class Importer:
    def __init__(self, load_env: LoadEnv):
        self._conn = sqlite3.connect(load_env.db_file)
        self._env = load_env
        if not path.exists(self._env.fb_posts_dir):
            raise Exception(f'Facebook posts dir {self._env.fb_posts_dir} does not exist')
        self._facebook_post_file = None
        self._posts = dict()
        for (_, dir_names, filenames) in walk(f'{self._env.fb_posts_dir}'):
            for filename in filenames:
                if filename.startswith('your_posts'):
                    if self._facebook_post_file is not None:
                        raise Exception(
                            f'More then one facebook backup dir. {filenames} found when {self._facebook_post_file} '
                            f'exists')
                    self._facebook_post_file = filename
                    logging.info(f'Facebook post file: {self._facebook_post_file}')
            break
        if self._facebook_post_file is None:
            logging.warning(f'Facebook post file not detected in {self._env.fb_posts_dir}')
        self._prepare_db()

    def load_fb_posts(self, dry_run=True):
        c = self._conn.cursor()
        if self._facebook_post_file is None:
            raise Exception(f'Facebook post file not detected in {self._env.fb_posts_dir}')
        with open(f'{self._env.fb_posts_dir}/{self._facebook_post_file}') as fb_posts:
            self._posts = json.load(fb_posts)
        posts_count = 0
        media_count = 0
        for post in self._posts:
            text = ''
            data = post.get('data')
            timestamp = post.get('timestamp')
            formatted_timestamp = strftime("%d-%m-%Y %H:%M:%S", localtime(timestamp))
            if data and data[0].get('post', '') != '':
                text = data[0].get('post').encode('latin1').decode('utf8')
            attachments = post.get('attachments')
            if text != '' or attachments:
                posts_count += 1
                try:
                    # process attachments
                    if attachments:
                        post_media_count = 0
                        for attachment in attachments[0].get('data', []):
                            media = attachment.get('media')
                            link = attachment.get('external_context', {}).get('url', '')
                            # process photos and videos
                            if media:
                                if post_media_count > 3:
                                    logging.warning(
                                        f'Post from {formatted_timestamp} '
                                        f'has more then 4 attachments, trimmed to 4')
                                    break
                                uri = media.get('uri').partition('posts/')[2]
                                if uri:
                                    try:
                                        logging.info(f'Dry-run {dry_run}. '
                                                     f'Adding attachment {uri} to post from {formatted_timestamp}')
                                        if not dry_run:
                                            c.execute('INSERT INTO fb_media (post_id, uri) VALUES (?, ?)',
                                                      (timestamp, uri))
                                        media_count += 1
                                        post_media_count += 1
                                    except sqlite3.IntegrityError:
                                        logging.warning(
                                            f'Attachment {uri} already exists')
                            # process links
                            if link != '' and text.find(link) == -1:
                                text += f'\n{link}'
                                logging.warning(f'Added link {link} to post from {formatted_timestamp}')
                    # process post
                    logging.info(f'Dry-run {dry_run}. Inserting post from {formatted_timestamp}')
                    if not dry_run:
                        c.execute('INSERT INTO fb_posts (id, text) VALUES (?, ?)',
                                  (timestamp, text))
                    self._conn.commit()
                except sqlite3.IntegrityError:
                    logging.warning(
                        f'Post from {formatted_timestamp} already exists')

        logging.info(f'Loaded {posts_count} posts, {media_count} media files')

    def collect_stat(self):
        c = self._conn.cursor()
        result = c.execute('SELECT COUNT (*) FROM fb_posts').fetchone()
        self._env.stat_fb_posts.append(['Imported', result[0]])
        result = c.execute('SELECT COUNT (*) FROM fb_posts WHERE posted != 0').fetchone()
        self._env.stat_fb_posts.append(['Pushed', result[0]])
        result = c.execute('SELECT COUNT (*) FROM fb_posts WHERE posted = 2').fetchone()
        self._env.stat_fb_posts.append(['Partially pushed', result[0]])
        result = c.execute('SELECT COUNT (*) FROM fb_posts WHERE length(text) > 500').fetchone()
        self._env.stat_fb_posts.append(['Long posts', result[0]])
        result = c.execute('SELECT COUNT (*) FROM fb_media').fetchone()
        self._env.stat_fb_media.append(['Imported', result[0]])
        result = c.execute('SELECT COUNT (*) FROM fb_media WHERE posted != 0').fetchone()
        self._env.stat_fb_media.append(['Pushed', result[0]])

    def _prepare_db(self):
        c = self._conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS fb_posts (id INTEGER PRIMARY KEY, text TEXT, posted INTEGER default 0)')
        c.execute(
            'CREATE TABLE IF NOT EXISTS fb_media (id INTEGER PRIMARY KEY, post_id INTEGER, uri TEXT, '
            'posted INTEGER default 0)')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS fb_media_post_id_uri ON fb_media (post_id, uri)')
        self._conn.commit()

    def print_stat(self):
        print(tabulate(self._env.stat_fb_posts, headers=['FB Posts', 'Count'], tablefmt='presto'))
        print('')
        print(tabulate(self._env.stat_fb_media, headers=['FB Media', 'Count'], tablefmt='presto'))
