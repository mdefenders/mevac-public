# mEvac
_This repo is a reference clone of the original private docker image repo, which uses self-hosted GitHub Actions runners, 
disabled for public repos._

Simple script to migrate social networks post dumps to Mastodon
Currentli supported networks:

- Facebook

# Introduction

Mastodon doesn't provide any content migration tool. The explanation is - developers wouldn't like to overload the
Fediverse with traffic of imported content. I appreciate this decision, it makes logical sense. However, the migration
may be useful for particular cases. For example, I would like to move a historical archive of my content from Facebook
and Twitter to my own, self-hosted Mastodon instance-based dedicated accounts.

# Features

- built as a docker image
- FB posts migration
- FB posts timestamping and auto-threading

# Backlog

- X migration
- Mastodon migration

# Requirements

- docker installed
- mastodon account and access token (may be created using Mastodon UI)
- Downloaded FB backup (archive)

# Variables/parameters

The default script behaviour may be configured using environment variables. Variables without default values are
prompted

| Env var                      |        Default value |   
|:-----------------------------|---------------------:|
| LOGLEVEL                     |                 INFO |
| MASTODON_DOMAIN              |                    - |
| MASTODON_RATELIMIT_RETRIES   |                    3 |
| MASTODON_CLIENT_ACCESS_TOKEN |                    - |
| MASTODON_TEXT_SIZE_LIMIT     |                  500 |
| MASTODON_WORK_DIR            |                   ./ |
| MASTODON_PUSH_PUBLIC         |                    0 |
| MASTODON_MEDIA_TIMEOUT       |                   10 |
| MASTODON_MEDIA_RETRIES       |                    3 |
| DB_FILE                      | /app/db/evacuator.db |

## Important notes

Because of uncertainty of source data, and different visibility models, the script uploads all posts with "Public" or "
Followers only" visibility. The default is "followers only". You can change this behaviour setting MASTODON_PUSH_PUBLIC
variable into '1'.

## Docker container commands and options

You need to run commands to load the archive into the internal db and push it to Mastodon
Internal db is used to provide the command reentrancy. You can run the command multiple times in case of errors or
failures and avoid duplicates. Removing the db file will reset the process.

For FB the post timestamp is used as a unique key.

| Command                  | Description                             |   
|:-------------------------|:----------------------------------------|
| load facebook            | loads FB archive into internal database |
| push facebook            | pushes FB archive to Mastodon           |
| load report, push report | prints the current process state        |

**IMPORTANT: Dry-run mode is default behaviour for all commands. To run the command in the real mode, add --no-dry-run
option**

# Large media processing notes

Processing large media files takes a time from Mastodon server, so they cannot be used immediately with the new post.
The scripts waits for MASTODON_MEDIA_TIMEOUT*MASTODON_MEDIA_RETRIES seconds for the media to be processed.
If the media isn't ready, post cam be skipped by the server. You can see in post push report the count of "Partially
pushed" posts. You can run the push command again with "--retry" option to re-push the skipped posts. As Mastodon
doesn't provide an option to push posts in the past, the script will push the post on top of your timeline.

# Limitations

## Facebook

The script imports only posts, contains text, media attachments or external links. Albums, internal Facebook reposts,
replays and other types of content are ignored.

# Expected runtime

As Mastodon API calls are restricted by sophisticated calculated and not configurable rate limits, the script may
take a long time to complete. From the practical experience, importing 4k posts/1k media attachments archive takes about
3 days because of the rate-limit bottleneck.

# Usage

```shell
docker run --rm -ti -v <path to fb backup posts folder>/posts:/app/posts -v <path to local db folder>:/app/db mdefenders/mevac:latest command
```

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

### Push posts to Mastodon

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
- Mastodon migration