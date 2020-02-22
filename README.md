# slackfs
Browse and upload slack files directly from your filesystem.

## How does it work?
This is a simple [FUSE](https://en.wikipedia.org/wiki/Filesystem_in_Userspace) application that
talks to Slack using API in the backend. Right now it runs in a single-threaded foreground mode.

## Usage
```
$ pip install -r requirements.txt
$ export SLACKFS_TOKEN=xoxp-your-token
$ ./slackfs.py /path/to/mountpoint
```
It was tested with legacy tokens that can be generated at https://api.slack.com/legacy/custom-integrations/legacy-tokens.

## Environment variables
- `SLACKFS_TOKEN` -- token for the underlying Slack client
- `SLACKFS_LOG_LEVEL`  -- the usual [Python logging level](https://docs.python.org/3/library/logging.html#levels),
  defaults to `ERROR`
