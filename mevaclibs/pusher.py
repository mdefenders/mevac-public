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

        c.execute('SELECT * FROM fb_posts WHERE posted = ?', (post_condition,))
        fb_post_posted = 1
        fb_posts = c.fetchall()
        fb_posts_count = len(fb_posts)
        result = list()
        for fb_post in fb_posts:
            formatted_timestamp = strftime("%d-%m-%Y %H:%M:%S", localtime(fb_post[0]))
            media_post_ids = self._push_post_media(fb_post[0], media_condition, 'fb',
                                                   self._load_env.fb_posts_dir, dry_run)
            logging.info(f'Dry-run {dry_run}. {fb_post_posted}/{fb_posts_count} '
                         f'Posting toot from {formatted_timestamp}: {fb_post[1][:20]}')
            if fb_post[1] != '' or media_post_ids:
                post_ids = self._mst.post_fb_status(f'{formatted_timestamp}\r{fb_post[1]}', media_post_ids,
                                                    visibility=self._push_env.visibility, dry_run=dry_run)
                result_post_id = post_ids[0]
                for post_id in post_ids:
                    if post_id == '0':
                        # to mark the post as partially posted if one of the parts failed
                        result_post_id = '2'
                        break
                if not dry_run:
                    c.execute('UPDATE fb_posts SET posted = ? WHERE id = ?', (result_post_id, fb_post[0],))
                    self._conn.commit()
                result = result + post_ids
                fb_post_posted += 1
        return result

    def push_mst_posts(self, parent_id='0', in_reply_to='0', dry_run=True, retry=False):
        if parent_id != '0':
            logging.info(f'Pushing reply for parent_id {parent_id}')
        c = self._conn.cursor()
        if retry:
            post_condition = '2'
            media_condition = 'AND posted != 0'
        else:
            post_condition = '0'
            media_condition = 'AND posted = 0'

        c.execute('SELECT * FROM mst_posts WHERE posted = ? and parent_id = ?',
                  (post_condition, parent_id))
        mst_posts = c.fetchall()
        mst_post_posted = 1
        mst_posts_count = len(mst_posts)
        result = list()
        for mst_post in mst_posts:
            media_post_ids = self._push_post_media(mst_post[0], media_condition, 'mst',
                                                   self._load_env.mst_posts_dir, dry_run)
            post_date = localtime(mst_post[2])

            logging.info(f'Dry-run {dry_run}. {mst_post_posted}/{mst_posts_count} '
                         f'Posting toot from {strftime("%d-%m-%Y %H:%M:%S", post_date)}: {mst_post[5][:20]}')
            post_id = self._mst.post_mst_status(mst_post[5], mst_post[4], media_post_ids, mst_post[3], mst_post[6],
                                                in_reply_to, dry_run)
            if post_id == '0':
                post_id = '2'
            if not dry_run:
                c.execute('UPDATE mst_posts SET posted = ? WHERE id = ?', (post_id, mst_post[0],))
                self._conn.commit()
            result.append(post_id)
            mst_post_posted += 1
            # Thread processing
            if parent_id == '0' and self._push_env.date_tags and post_id != '2':
                tagged_ext = (
                    f'{" ".join(mst_post[5].split()[:8])}...\n Posted #{strftime("day%d%b%Y", post_date)} '
                    f'#{strftime("%b%Y", post_date)} #{strftime("year%Y", post_date)}')
                self._mst.post_mst_status(tagged_ext, mst_post[4], None, mst_post[3], mst_post[6], post_id, dry_run)
            result = result + self.push_mst_posts(str(mst_post[0]), post_id, dry_run, retry)
        return result

    def _push_post_media(self, post_id, media_condition, media_source, media_root, dry_run=True):
        media_post_ids = list()
        c = self._conn.cursor()
        c.execute(f'SELECT * FROM {media_source}_media WHERE post_id = ? {media_condition}', (post_id,))
        post_medias = c.fetchall()
        for post_media in post_medias:
            media_file = f'{media_root}/{post_media[2]}'
            if post_media[3] == 0:
                logging.info(f'Dry-run {dry_run}. Posting media {media_file}')
                media_post_id = self._mst.upload_media(media_file, dry_run)
            else:
                media_post_id = post_media[3]
            media_post_ids.append(media_post_id)
            c.execute(f'UPDATE {media_source}_media SET posted = ? WHERE id = ?', (media_post_id, post_media[0],))
            self._conn.commit()
        return media_post_ids
