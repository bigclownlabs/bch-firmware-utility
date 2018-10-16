#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import serial
import click
import requests
import platform
import hashlib
import appdirs
from distutils.version import LooseVersion

user_cache_dir = appdirs.user_cache_dir('bcf')
user_config_dir = appdirs.user_config_dir('bcf')

pyserial_34 = LooseVersion(serial.VERSION) >= LooseVersion("3.4.0")


def get_devices(include_links=False):
    if os.name == 'nt' or sys.platform == 'win32':
        from serial.tools.list_ports_windows import comports
    elif os.name == 'posix':
        from serial.tools.list_ports_posix import comports

    if pyserial_34:
        ports = comports(include_links=include_links)
    else:
        ports = comports()

    return sorted(ports)


def select_device(device):
    if device is None:
        ports = get_devices()
        if not ports:
            raise Exception("No device")

        for i, port in enumerate(ports):
            click.echo("%i %s" % (i, port[0]), err=True)
        d = click.prompt('Please enter device')
        for port in ports:
            if port[0] == d:
                device = port[0]
                break
        else:
            try:
                device = ports[int(d)][0]
            except Exception as e:
                raise Exception("Unknown device")
    return device


def download_url_reporthook(count, blockSize, totalSize):
    print_progress_bar('Download', count * blockSize, totalSize)


def download_url(url, use_cache=True):
    if url.startswith("https://github.com/bigclownlabs/bcf-"):
        filename = url.rsplit('/', 1)[1]
    else:
        filename = hashlib.sha256(url.encode()).hexdigest()
    filename_bin = os.path.join(user_cache_dir, filename)

    if use_cache and os.path.exists(filename_bin):
        return filename_bin

    click.echo('Download firmware from ' + url)
    click.echo('Save as' + filename_bin)

    try:
        response = requests.get(url, stream=True, allow_redirects=True)
        total_length = response.headers.get('content-length')
        with open(filename_bin, "wb") as f:
            if total_length is None:  # no content length header
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    download_url_reporthook(1, dl, total_length)
    except Exception as e:
        click.echo("Firmware download problem: " + e.args[0])
        sys.exit(1)
    return filename_bin


def print_table(labels, rows):
    if not labels and not rows:
        return

    max_lengths = [0] * (len(rows[0]) if rows else len(labels))
    for i, label in enumerate(labels):
        max_lengths[i] = len(label)

    for row in rows:
        for i, v in enumerate(row):
            if len(v) > max_lengths[i]:
                max_lengths[i] = len(v)

    row_format = "{:<" + "}  {:<".join(map(str, max_lengths)) + "}"

    if labels:
        click.echo(row_format.format(*labels))
        click.echo("=" * (sum(max_lengths) + len(labels) * 2))

    for row in rows:
        click.echo(row_format.format(*row))


def print_progress_bar(title, progress, total, length=20):
    filled_length = int(length * progress // total)
    if filled_length < 0:
        filled_length = 0
    bar = '#' * filled_length
    bar += '-' * (length - filled_length)
    percent = 100 * (progress / float(total))
    if percent > 100:
        percent = 100
    elif percent < 0:
        percent = 0
    sys.stdout.write('\r\r')
    sys.stdout.write(title + ' [' + bar + '] ' + "{:5.1f}%".format(percent))
    sys.stdout.flush()
    if percent == 100:
        sys.stdout.write('\n')
        sys.stdout.flush()
