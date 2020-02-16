#!/usr/bin/env python3
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from stat import S_IFDIR, S_IFREG

import requests
import slack
from fuse import FUSE, Operations

TOKEN = os.environ["SLACK_TOKEN"]


class SlackFS(Operations):
    def __init__(self):
        self.slack_client = slack.WebClient(token=TOKEN)
        self.channels = {channel["name_normalized"]: channel for channel in self.list_conversations()}
        self.files = defaultdict(dict)
        self.fd = 0

    def list_conversations(self):
        return self.slack_client.conversations_list(limit=200, types="public_channel,private_channel").data["channels"]

    def channel_files(self, channel_name):
        if channel_name not in self.files:
            channel_id = self.channels[channel_name]["id"]
            files = self.slack_client.files_list(channel=channel_id, limit=200).data["files"]

            for f in files:
                file_name = f"{f['id']}_{f['name']}"
                self.files[channel_name][file_name] = f

        return self.files[channel_name]

    def get_file(self, channel_name, file_name):
        self.channel_files(channel_name)
        return self.files[channel_name][file_name]

    def get_file_contents(self, channel_name, file_name):
        f = self.get_file(channel_name, file_name)
        if "contents" not in f:
            r = requests.request("GET", f["url_private_download"], headers={"Authorization": f"Bearer {TOKEN}"},)
            f["contents"] = r.content

        return f["contents"]

    def getattr(self, path, fh=None):
        p = Path(path)
        mode = 0
        size = 0

        if path == "/" or str(p.parent) == "/":
            mode = S_IFDIR | 0o700
        else:
            mode = S_IFREG | 0o600
            size = self.get_file(channel_name=str(p.parent.name), file_name=str(p.name))["size"]

        return {
            "st_atime": time.time(),
            "st_ctime": time.time(),
            "st_gid": os.getgid(),
            "st_mode": mode,
            "st_mtime": time.time(),
            "st_nlink": 2,
            "st_size": size,
            "st_uid": os.getuid(),
        }

    def readdir(self, path, fh):
        members = [".", ".."]

        if path == "/":
            members.extend(self.channels)
        else:
            channel_name = str(Path(path).name)
            members.extend(self.channel_files(channel_name))

        yield from iter(members)

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, length, offset, fh):
        p = Path(path)
        contents = self.get_file_contents(channel_name=str(p.parent.name), file_name=str(p.name))

        return contents[offset : offset + length]


def main(mountpoint):
    FUSE(SlackFS(), mountpoint, nothreads=True, foreground=True)


if __name__ == "__main__":
    main(sys.argv[1])
