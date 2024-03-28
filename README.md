# mEvac
Public GitHub Repository: [mEvac](https://github.com/mdefenders/mevac-public)

This is a simple script designed to migrate (import) social network post backups to Mastodon account.
Currently, the script supports the following networks:

- Facebook
- Mastodon

# Introduction

Mastodon does not offer a built-in content migration (import) tool. This is because developers want to avoid overloading
the
Fediverse with imported content traffic. While this decision is understandable, there are certain scenarios where
migration could be beneficial. For instance, one might want to transfer a historical archive of content from Facebook
and Twitter to dedicated accounts on a self-hosted Mastodon instance.

# Features

- Migration of Mastodon post archives
- Migration of Facebook post archives
- Timestamping and auto-threading of Facebook posts
- Provided as a docker image

# Requirements

- Docker installed
- Mastodon account and access token (can be created using Mastodon UI)
- Downloaded Facebook backup (archive)
- Downloaded Mastodon backup (archive)

# Configuration

The script's default behavior can be adjusted using environment variables. Variables without default values will be
prompted.

| Env var                      | Description                                        |        Default value |   
|:-----------------------------|----------------------------------------------------|---------------------:|
| LOGLEVEL                     | Logging level                                      |                 INFO |
| MASTODON_DOMAIN              | Mastodon server FQDN                               |                    - |
| MASTODON_RATELIMIT_RETRIES   | Retries on ratelimit                               |                    3 |
| MASTODON_CLIENT_ACCESS_TOKEN | Client access token                                |                    - |
| MASTODON_TEXT_SIZE_LIMIT     | Post text size limit                               |                  500 |
| FB_POSTS_DIR                 | Fb backup directory  (contains xxx_posts_nnn.json) |              ./posts |
| MST_POSTS_DIR                | Mastodon backup directory (contains outbox.json)   |           ./mstposts |
| MASTODON_VISIBILITY          | Fb posts visibility                                |              private |
| MASTODON_MEDIA_TIMEOUT       | Wait for media upload                              |                   10 |
| MASTODON_MEDIA_RETRIES       | Media upload retries                               |                    3 |
| MASTODON_DATE_TAGS           | Add date tags to the post                          |                 True |
| DB_FILE                      | SQLite DB path                                     | /app/db/evacuator.db |
| FILTER_OUT_AT                | Filter out post, started with @mentions            |                 True |

## Important notes

### General

The script uses SQLite as an internal database to store the imported posts. It allows re-running the push command in
case of errors or failures without duplicates. The database file is mounted into the /app/db folder inside the
container.

### Facebook import

Due to the variability of source data and different visibility models, the script uploads all Facebook posts with a
visibility setting configured by MASTODON_PUSH_VISIBILITY. The supported visibility settings are public, private, and
direct. The default setting is "private".

### Mastodon import

In some cases, responses may not contain any reply sign, except for starting
with an @mention. By default, these types of posts are excluded by the script. If you wish to include these in the
import, set the FILTER_OUT_AT variable to False.

## Docker container commands and options

Commands are required to load the archive into the internal database and push it to Mastodon. The internal database is
used to provide command reentrancy. You can run the command multiple times in case of errors or failures and avoid
duplicates. Removing the database file will reset the process.

For Facebook, the post timestamp is used as a unique key.
For Mastodian, the post ID is used as a unique key.

| Command         | Description                                   |   
|:----------------|:----------------------------------------------|
| load facebook   | loads FB archive into internal database       |
| push facebook   | pushes FB archive to Mastodon                 |
| load mastodon   | loads Mastodon archive into internal database |
| push mastodon   | pushes Mastodon archive to Mastodon           |
| report facebook | prints facebook report                        |
| report mastodon | prints mastodon report                        |

**IMPORTANT: Dry-run mode is default behaviour for all commands. To run the command in the real mode, add --no-dry-run
option**

# Large media processing notes

Processing large media files takes time from the Mastodon server, so they cannot be used immediately with the new post.
The script waits for MASTODON_MEDIA_TIMEOUT * MASTODON_MEDIA_RETRIES seconds for the media to be processed. If the media
isn't ready, the post can be skipped by the server. You can see in the post push report the count of "Partially pushed"
posts. You can run the push command again with the "--retry" option to re-push the skipped posts. As Mastodon doesn't
provide an option to push posts in the past, the script will push the post on top of your timeline.

# Limitations

## Facebook

The script imports only posts, contains text, media attachments or external links. Albums, internal Facebook reposts,
replays and other types of content are ignored.

## Mastodon

The script imports only posts, and own reply threads. Polls, boosts, stars, replies to other users are ignored.
Posts and replies, started with @mentions may be missed.

# Expected runtime

Due to the rate limits imposed on Mastodon API calls, the script may take a long time to complete. From practical
experience, importing an archive of 4k posts/1k media attachments takes about 3 days due to the rate-limit bottleneck.

# Usage

```shell
docker run --rm -ti -v <path to fb backup posts folder>/posts:/app/posts -v <path to local db folder>:/app/db mdefenders/mevac:latest command
```

**_Important:_** default backup sub-folders under the /app workdir are ./posts for the Facebook backup and ./mstposts
for the Mastodon backup.
You can change sub-folders name by setting FB_POSTS_DIR and MST_POSTS_DIR if needed. Root folder (/app) isn't
configurable so far.

## Examples

### Load posts to the internal database

```shell
docker run --rm -ti -v ./tests/testdata/posts:/app/posts -v ./db:/app/db mdefenders/mevac:latest load facebook
````

```
INFO:root:Facebook post file: your_posts_2421432.json
WARNING:root:Post from 07-09-2014 11:45:14 has more than 4 attachments, trimmed to 4
WARNING:root:Added link http://www.newsru.com/religy/12sep2014/auszeichnen.html to post from 12-09-2014 16:08:33
WARNING:root:Added link http://www.snob.ru/profile/26524/blog/81186 to post from 19-09-2014 08:57:11
INFO:root:Loaded 20 posts
 FB Posts   |   Count
------------+---------
 Imported   |      20
 Pushed     |       0
 Long posts |       2

 FB Media   |   Count
------------+---------
 Imported   |      10
 Pushed     |       0

```

### Print load report

```shell
docker run --rm -ti  -v ./db/:/app/db mdefenders/mevac:latest load report
````

```
 FB Posts   |   Count
------------+---------
 Imported   |      20
 Pushed     |       0
 Long posts |       2

 FB Media   |   Count
------------+---------
 Imported   |      10
 Pushed     |       0
```

### Push Facebook posts to Mastodon

```shell
docker run --rm -ti -v ./tests/testdata/posts:/app/posts -v ./db:/app/db mdefenders/mevac:latest push facebook
````

```
 FB Posts   |   Count
------------+---------
 Imported   |      20
 Pushed     |      19
 Long posts |       2

 FB Media   |   Count
------------+---------
 Imported   |      10
 Pushed     |      10
```

# Changelog

## 0.0.6

- Mastodon import added

## 0.0.5

- Pass 422 error on push
- Extended error handling and logging
- Some progress logging

## 0.0.4

hotfix release

## 0.0.3

hotfix release

## 0.0.2

- dry-run mode added as default

# Backlog

- Tests on CI
- import progress
- X migration