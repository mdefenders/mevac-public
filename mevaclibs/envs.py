import os


class LoadEnv(object):

    def __init__(self):
        self._env = dict()
        self._stat_fb_posts = list()
        self._stat_fb_media = list()
        self._stat_mst_posts = list()
        self._stat_mst_media = list()
        self._db_file = os.environ.get('DB_FILE', '/app/db/evacuator.db')
        self._env['fb_posts_dir'] = os.environ.get('FB_POSTS_DIR', '')
        self._env['mst_posts_dir'] = os.environ.get('MST_POSTS_DIR', '')
        self._env['filter_out_at'] = os.environ.get('FILTER_OUT_AT', 'True')
        if not self._env['fb_posts_dir']:
            if os.path.exists('./posts'):
                self._env['fb_posts_dir'] = './posts'
        if not self._env['mst_posts_dir']:
            if os.path.exists('./mstposts'):
                self._env['mst_posts_dir'] = './mstposts'
        for key, value in self._env.items():
            if not value:
                self._env[key] = input(f'Type {key.replace("_", " ")}: ').strip()
                if not self._env[key]:
                    raise Exception(f'No {key} provided')

    @property
    def fb_posts_dir(self):
        return self._env['fb_posts_dir']

    @property
    def mst_posts_dir(self):
        return self._env['mst_posts_dir']

    @property
    def stat_fb_posts(self):
        return self._stat_fb_posts

    @stat_fb_posts.setter
    def stat_fb_posts(self, value):
        self._stat_fb_posts = value

    @property
    def stat_fb_media(self):
        return self._stat_fb_media

    @stat_fb_media.setter
    def stat_fb_media(self, value):
        self._stat_fb_media = value

    @property
    def stat_mst_posts(self):
        return self._stat_mst_posts

    @stat_mst_posts.setter
    def stat_mst_posts(self, value):
        self._stat_mst_posts = value

    @property
    def stat_mst_media(self):
        return self._stat_mst_media

    @stat_mst_media.setter
    def stat_mst_media(self, value):
        self._stat_mst_media = value

    @property
    def db_file(self):
        return self._db_file

    @property
    def filter_out_at(self):
        return self._env['filter_out_at'].lower() == 'true'


class PushEnv(object):

    def __init__(self):
        self._env = dict()
        self._env['client_access_token'] = os.environ.get('MASTODON_CLIENT_ACCESS_TOKEN', '')
        self._env['domain'] = os.environ.get('MASTODON_DOMAIN', '')
        self._ratelimit_retries = int(os.environ.get('MASTODON_RATELIMIT_RETRIES', '3'))
        self._text_size_limit = int(os.environ.get('MASTODON_TEXT_SIZE_LIMIT', '500'))
        self._visibility = os.environ.get('MASTODON_VISIBILITY', 'private')
        self._media_timeout = os.environ.get('MASTODON_MEDIA_TIMEOUT', '10')
        self._media_retries = os.environ.get('MASTODON_MEDIA_RETRIES', '3')
        self._date_tags = os.environ.get('MASTODON_DATE_TAGS', 'True')
        if self._text_size_limit < 20:
            self._text_size_limit = 500
        self._ratelimit_limit = 0
        self._ratelimit_remaining = 0
        self._ratelimit_reset = 1000
        for key, value in self._env.items():
            if not value:
                self._env[key] = input(f'Type {key.replace("_", " ")}: ').strip()
                if not self._env[key]:
                    raise Exception(f'No {key} provided')

    @property
    def token(self):
        return self._env['client_access_token']

    @property
    def domain(self):
        return self._env['domain']

    @property
    def media_timeout(self):
        return int(self._media_timeout)

    @property
    def media_retries(self):
        return int(self._media_retries)

    @property
    def visibility(self):
        if self._visibility == 'public':
            return 'public'
        elif self._visibility == 'direct':
            return 'direct'
        else:
            return 'private'

    @property
    def ratelimit_limit(self):
        return self._ratelimit_limit

    @ratelimit_limit.setter
    def ratelimit_limit(self, value):
        self._ratelimit_limit = value

    @property
    def ratelimit_remaining(self):
        return self._ratelimit_remaining

    @ratelimit_remaining.setter
    def ratelimit_remaining(self, value):
        self._ratelimit_remaining = value

    @property
    def ratelimit_reset(self):
        return self._ratelimit_reset

    @ratelimit_reset.setter
    def ratelimit_reset(self, value):
        if value < 0:
            value = 0
        self._ratelimit_reset = value + 3

    @property
    def ratelimit_retries(self):
        return self._ratelimit_retries

    @ratelimit_retries.setter
    def ratelimit_retries(self, value):
        self._ratelimit_retries = value

    @property
    def text_size_limit(self):
        return self._text_size_limit

    @property
    def date_tags(self):
        return self._date_tags.lower() == 'true'
