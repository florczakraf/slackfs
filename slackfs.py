#!/usr/bin/env python3
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from stat import S_IFDIR, S_IFREG
from tempfile import NamedTemporaryFile

import requests
import slack
from fuse import FUSE, Operations, FuseOSError
from errno import ENOENT

TOKEN = os.environ["SLACK_TOKEN"]


class SlackFS(Operations):
    def __init__(self, root):
        self.slack_client = slack.WebClient(token=TOKEN, proxy=os.environ.get("https_proxy", None))
        self.channels = {channel["name_normalized"]: channel for channel in self.list_conversations()}
        self.files = defaultdict(dict)
        self.fd = 0
        self.root = Path(root)

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
            r = requests.request("GET", f["url_private_download"], headers={"Authorization": f"Bearer {TOKEN}"})
            f["contents"] = r.content

        return bytes(f["contents"])

    def getattr(self, path, fh=None):
        p = Path(path)
        mode = 0
        size = 0
        time_ = time.time()

        if path == "/" or str(p.parent) == "/":
            mode = S_IFDIR | 0o700
        else:
            try:
                mode = S_IFREG | 0o600
                size = self.get_file(channel_name=str(p.parent.name), file_name=str(p.name))["size"]
                time_ = self.get_file(channel_name=str(p.parent.name), file_name=str(p.name)).get("created", time.time())
            except KeyError:
                raise FuseOSError(ENOENT)

        return {
            "st_atime": time_,
            "st_ctime": time_,
            "st_gid": os.getgid(),
            "st_mode": mode,
            "st_mtime": time_,
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

    def create(self, path, mode):
        p = Path(path)
        self.fd += 1
        self.files[p.parent.name][p.name] = {"contents": bytearray(), "size": 0}

        return self.fd

    def write(self, path, data, offset, fh):
        p = Path(path)
        file_ = self.get_file(p.parent.name, p.name)
        contents = file_["contents"]

        if len(contents) < offset + len(data):
            contents += b"\0" * (offset + len(data) - len(contents))
            file_["size"] = len(contents)

        contents[offset : offset + len(data)] = data

        return len(data)

    def release(self, path, fh):
        p = Path(path)
        channel_name = p.parent.name
        channel_id = self.channels[channel_name]["id"]
        contents = self.get_file_contents(channel_name, p.name)

        with NamedTemporaryFile() as f:  # because slack doesn't want our in-memory bytes
            f.write(contents)
            f.flush()
            resp = self.slack_client.files_upload(file=f.name, channels=channel_id, filename=p.name).data['file']
            self.files[channel_name][f"{resp['id']}_{resp['name']}"] = {**self.files[channel_name][p.name], **resp}
            del self.files[channel_name][p.name]

        return 0


def main(mountpoint):
    FUSE(SlackFS(mountpoint), mountpoint, nothreads=True, foreground=True)


if __name__ == "__main__":
    main(sys.argv[1])
