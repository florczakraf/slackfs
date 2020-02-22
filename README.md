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

## Filesystem layout
In the root of the filesystem there are directories that represent channels you are a member of.
Inside a channel you can find files that have been shared to it. There is a following naming
convention for files: `SLACK-FILE-ID_ORIGNAL-FILE-NAME` to avoid name overlapping. `stat` on a file
reports its real creation time so it is possible to list files by it (e.g. `ls -lat | head`).

```
$ tree
.
├── some-channel
│   ├── FU0BQXXXX_Screenshot_2020-02-21_21-21-29.png
│   ├── FUCKUXXXX_somefile
│   └── FUCL2XXXX_Screenshot_2020-02-21_21-23-41.png
├── empty-channel
├── other-channel
│   ├── FJPC5XXXX_dh.png
│   ├── FJS36XXXX_gh.png
...
```

## Current limitations
Only some of the FUSE callbacks are implemented to provide the basic functionality. More sophisticated
are provided by the `fusepy` library and most likely return unconditional success or some garbage.
There is hardly any error handling in slackfs which in turn cause syscalls to return errors to applications.

New directory creation is UB. Creating files in root of the filesystem is UB, as is modifying existing ones.

There is absolutely no slack api rate limit respecting implemented on slackfs side. Unless official slack
python api library handles that itself, your key or even account might be temporarily blocked.
