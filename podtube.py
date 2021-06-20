#!/usr/bin/python3
import datetime
import glob
import logging
import os
from argparse import ArgumentParser
from pathlib import Path

import misaka
import youtube

from tornado import gen, httputil, ioloop, iostream, process, web
from tornado.locks import Semaphore

__version__ = '3.1'

conversion_queue = {}
converting_lock = Semaphore(2)

def make_app(key="test"):
    webapp = web.Application([
        (r'/channel/(.*)', youtube.ChannelHandler),
        (r'/playlist/(.*)', youtube.PlaylistHandler),
        (r'/video/(.*)', youtube.VideoHandler),
        (r'/audio/(.*)', youtube.AudioHandler),
        (r'/', youtube.FileHandler),
        (r'/(.*)', web.StaticFileHandler, {'path': '.'})
    ], compress_response=True)
    return webapp

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists('./audio'):
        os.mkdir('audio')
    parser = ArgumentParser(prog='PodTube')
    parser.add_argument(
        'key',
        help='Google\'s API Key'
    )
    parser.add_argument(
        'port',
        type=int,
        default=80,
        nargs='?',
        help='Port Number to listen on'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        default='podtube.log',
        metavar='FILE',
        help='Location and name of log file'
    )
    parser.add_argument(
        '--log-format',
        type=str,
        default='%(asctime)-15s %(message)s',
        metavar='FORMAT',
        help='Logging format using syntax for python logging module'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version="%(prog)s " + __version__
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format=args.log_format,
        filename=args.log_file,
        filemode='a'
    )
    key = args.key
    for file in glob.glob('audio/*.temp'):
        os.remove(file)
    app = make_app( key )
    app.listen(args.port)
    logging.info(f'Started listening on {args.port}')
    ioloop.PeriodicCallback(
        callback=youtube.cleanup,
        callback_time=1000
    ).start()
    ioloop.PeriodicCallback(
        callback=youtube.convert_videos,
        callback_time=1000
    ).start()
    ioloop.IOLoop.instance().start()
