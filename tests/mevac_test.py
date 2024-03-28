import os
import unittest
from mevaclibs.envs import PushEnv, LoadEnv
from mevaclibs.mastodon import Mastodon
from mevaclibs.importers import FbImporter, MstImporter
from mevaclibs.pusher import Pusher


class TestEnv(unittest.TestCase):
    env = PushEnv()

    def test_init(self):
        self.assertIsInstance(self.env, PushEnv)

    def test_props(self):
        self.assertIsInstance(self.env.token, str)
        self.assertIsNot(self.env.token, '')
        self.assertRegex(self.env.domain, '.*\\..*')


class TestMastodon(unittest.TestCase):
    env = PushEnv()
    mst = Mastodon(env)

    def test_verify(self):
        self.assertIsInstance(self.mst.verify_credentials(), str)
        self.assertIsNot(self.mst.verify_credentials(), '')

    def test_post_status(self):
        media_post_ids = list()
        for i in range(5):
            media_post_id = self.mst.upload_media('testdata/stephenxxx05.jpg', dry_run=False)
            self.assertIsInstance(int(media_post_id), int)
            media_post_ids.append(media_post_id)

        post_ids = self.mst.post_fb_status('Integration Private test', media_post_ids, dry_run=False)
        self.assertNotEqual(len(post_ids), 0)
        for post_id in post_ids:
            deleted_post_id = self.mst.delete_entity(post_id)
            self.assertEqual(post_id, deleted_post_id)

    def test_hidden_post(self):
        post_ids = self.mst.post_fb_status('Integration Private test', visibility='private', dry_run=False)
        for post_id in post_ids:
            deleted_post_id = self.mst.delete_entity(post_id)
            self.assertEqual(post_id, deleted_post_id)


class TestFbImporter(unittest.TestCase):
    load_env = LoadEnv()
    push_env = PushEnv()

    def prepare(self):
        if os.path.exists(self.load_env.db_file):
            os.remove(self.load_env.db_file)

    def run_importer(self):
        importer = FbImporter(self.load_env)
        self.assertIsInstance(importer._facebook_post_file, str)
        self.assertNotEqual(importer._facebook_post_file, '')
        importer.load_fb_posts(dry_run=False)
        self.assertIsNotNone(self.load_env.stat_fb_posts)
        importer.collect_stat()
        importer.print_stat()

    def run_pusher(self):
        pusher = Pusher(self.load_env, self.push_env)
        pushed_posts = pusher.push_fb_posts(dry_run=False)
        for pushed_post in pushed_posts:
            self.assertIsInstance(int(pushed_post), int)
            deleted_post_id = pusher._mst.delete_entity(pushed_post)
            self.assertEqual(pushed_post, deleted_post_id)

    def test_importer(self):
        self.prepare()
        self.run_importer()
        self.run_pusher()


class TestMstImporter(unittest.TestCase):
    load_env = LoadEnv()
    push_env = PushEnv()

    def run_importer(self):
        importer = MstImporter(self.load_env)
        self.assertIsInstance(importer._mst_post_file, str)
        self.assertNotEqual(importer._mst_post_file, '')
        importer.load_mst_posts(dry_run=False)
        self.assertIsNotNone(self.load_env.stat_mst_posts)
        importer.collect_stat()
        importer.print_stat()

    def run_pusher(self):
        pusher = Pusher(self.load_env, self.push_env)
        pushed_posts = pusher.push_mst_posts(dry_run=False)

        for pushed_post in pushed_posts:
            self.assertIsInstance(int(pushed_post), int)
            deleted_post_id = pusher._mst.delete_entity(pushed_post)
            self.assertEqual(pushed_post, deleted_post_id)

    def prepare(self):
        if os.path.exists(self.load_env.db_file):
            os.remove(self.load_env.db_file)

    def test_importer(self):
        self.prepare()
        self.run_importer()
        self.run_pusher()


if __name__ == '__main__':
    unittest.main()
