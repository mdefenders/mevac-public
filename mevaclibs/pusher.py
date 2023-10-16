from mevaclibs.envs import PushEnv, LoadEnv
from mevaclibs.mastodon import Mastodon
import sqlite3
from os import path
import logging
from time import strftime, localtime


class Pusher:

    def __init__(self, load_env: LoadEnv, push_env: PushEnv):
        self._mst = Mastodon(push_env)
        self._conn = sqlite3.connect(load_env.db_file)
        self._load_env = load_env
        self._push_env = push_env
        if not path.exists(self._load_env.fb_posts_dir):
            raise Exception(f'Facebook posts dir {self._load_env.fb_posts_dir} does not exist')

    def push_fb_posts(self, dry_run=True, retry=False):
        c = self._conn.cursor()
        if retry:
            post_condition = '2'
            media_condition = 'AND posted != 0'
        else:
            post_condition = '0'
            media_condition = 'AND posted = 0'
        c.execute('SELECT count(*) FROM fb_posts WHERE posted = ?', (post_condition,))
        fb_posts_count = c.fetchone()[0]
        fb_post_posted = 1
        c.execute('SELECT * FROM fb_posts WHERE posted = ?', (post_condition,))
        fb_posts = c.fetchall()
        result = list()
        for fb_post in fb_posts:
            media_post_ids = list()
            formatted_timestamp = strftime("%d-%m-%Y %H:%M:%S", localtime(fb_post[0]))
            c.execute(f'SELECT * FROM fb_media WHERE post_id = ? {media_condition}', (fb_post[0],))
            fb_medias = c.fetchall()
            for fb_media in fb_medias:
                media_file = f'{self._load_env.fb_posts_dir}/{fb_media[2]}'
                if fb_media[3] == 0:
                    logging.info(f'Dry-run {dry_run}. Posting media {media_file}')
                    media_post_id = self._mst.upload_media(media_file, dry_run)
                else:
                    media_post_id = fb_media[3]
                media_post_ids.append(media_post_id)
                c.execute('UPDATE fb_media SET posted = ? WHERE id = ?', (media_post_id, fb_media[0],))
                self._conn.commit()
            logging.info(f'Dry-run {dry_run}. {fb_post_posted}/{fb_posts_count} '
                         f'Posting toot from {formatted_timestamp}: {fb_post[1][:20]}')
            if fb_post[1] != '' or media_post_ids:
                post_ids = self._mst.post_status(f'{formatted_timestamp}\r{fb_post[1]}', media_post_ids,
                                                 private=self._push_env.push_private, dry_run=dry_run)
                result_post_id = post_ids[0]
                for post_id in post_ids:
                    if post_id == '0':
                        # to mark the post as partially posted if one of the parts failed
                        result_post_id = '2'
                        break
                c.execute('UPDATE fb_posts SET posted = ? WHERE id = ?', (result_post_id, fb_post[0],))
                self._conn.commit()
                result = result + post_ids
                fb_post_posted += 1
        return result
