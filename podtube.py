#!/usr/bin/python3
import datetime
import glob
import logging
import os
from argparse import ArgumentParser
from pathlib import Path

import misaka
import psutil
import requests
from feedgen.feed import FeedGenerator
from pytube import YouTube
from tornado import gen, httputil, ioloop, iostream, process, web
from tornado.locks import Semaphore

__version__ = '1.0'

key = None
video_links = {}
playlist_feed = {}
channel_feed = {}
conversion_queue = {}
converting_lock = Semaphore(2)


def get_youtube_url(video):
    if video in video_links and video_links[video]['expire'] > datetime.datetime.now():
        return video_links[video]['url']
    yt = YouTube('http://www.youtube.com/watch?v=' + video)
    vid = yt.streams \
        .filter(progressive=True, file_extension='mp4') \
        .order_by('resolution') \
        .desc() \
        .first() \
        .url
    # try:  # Tries to find the video in 720p
    #     vid = yt.get('mp4', '720p').url
    # except Exception:  # Sorts videos by resolution and picks the highest quality video if a 720p video doesn't exist
    #     vid = sorted(yt.filter('mp4'), key=lambda video: int(video.resolution[:-1]), reverse=True)[0].url
    parts = {part.split('=')[0]: part.split('=')[1] for part in vid.split('?')[-1].split('&')}
    link = {'url': vid, 'expire': datetime.datetime.fromtimestamp(int(parts['expire']))}
    video_links[video] = link
    return link['url']


class ChannelHandler(web.RequestHandler):
    @gen.coroutine
    def get(self, channel):
        logging.info('Channel: %s (%s)', channel, self.request.remote_ip)
        channel = channel.split('/')
        if len(channel) < 2:
            channel.append('video')
        channel_name = ['/'.join(channel)]
        self.add_header('Content-type', 'application/rss+xml')
        if channel_name[0] in channel_feed and channel_feed[channel_name[0]]['expire'] > datetime.datetime.now():
            self.write(channel_feed[channel_name[0]]['feed'])
            self.finish()
            return
        fg = None
        video = None
        calls = 0
        response = {'nextPageToken': ''}
        while 'nextPageToken' in response.keys():
            next_page = response['nextPageToken']
            payload = {
                'part': 'snippet,contentDetails',
                'maxResults': 50,
                'channelId': channel[0],
                'key': key,
                'pageToken': next_page
            }
            request = requests.get('https://www.googleapis.com/youtube/v3/activities', params=payload)
            calls += 1
            if request.status_code != 200:
                payload = {
                    'part': 'snippet',
                    'maxResults': 1,
                    'forUsername': channel[0],
                    'key': key
                }
                request = requests.get('https://www.googleapis.com/youtube/v3/channels', params=payload)
                response = request.json()
                channel[0] = response['items'][0]['id']
                channel_name.append('/'.join(channel))
                payload = {
                    'part': 'snippet,contentDetails',
                    'maxResults': 50,
                    'channelId': channel[0],
                    'key': key,
                    'pageToken': next_page
                }
                request = requests.get('https://www.googleapis.com/youtube/v3/activities', params=payload)
                calls += 2
            response = request.json()
            if request.status_code == 200:
                logging.debug('Downloaded Playlist Information')
            else:
                logging.error('Error Downloading Playlist: %s', request.reason)
                self.send_error(reason='Error Downloading Playlist')
                return
            if not fg:
                fg = FeedGenerator()
                fg.load_extension('podcast')
                fg.generator('PodTube', __version__, 'https://github.com/aquacash5/PodTube')
                snippet = response['items'][0]['snippet']
                if 'Private' in snippet['title']:
                    continue
                icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
                fg.title(snippet['title'])
                fg.id('http://' + self.request.host + self.request.uri)
                fg.description(snippet['description'] or ' ')
                fg.author(name=snippet['channelTitle'])
                fg.image(snippet['thumbnails'][icon]['url'])
                fg.link(href='https://www.youtube.com/playlist?list=' + channel[0])
                fg.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
                fg.podcast.itunes_summary(snippet['description'])
                fg.podcast.itunes_category('Technology', 'Podcasting')
                fg.updated(str(datetime.datetime.utcnow()) + 'Z')
            for item in response['items']:
                snippet = item['snippet']
                if snippet['type'] != 'upload':
                    continue
                current_video = item['contentDetails']['upload']['videoId']
                logging.debug('PlaylistVideo: %s %s', current_video, snippet['title'])
                fe = fg.add_entry()
                fe.title(snippet['title'])
                fe.id(current_video)
                icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
                fe.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
                fe.updated(snippet['publishedAt'])
                if channel[1] == 'video':
                    fe.enclosure(url='http://{url}/video/{vid}'.format(url=self.request.host, vid=current_video),
                                 type="video/mp4")
                elif channel[1] == 'audio':
                    fe.enclosure(url='http://{url}/audio/{vid}'.format(url=self.request.host, vid=current_video),
                                 type="audio/mpeg")
                fe.author(name=snippet['channelTitle'])
                fe.podcast.itunes_author(snippet['channelTitle'])
                fe.podcast.itunes_author(snippet['channelTitle'])
                fe.pubdate(snippet['publishedAt'])
                fe.link(href='http://www.youtube.com/watch?v=' + current_video, title=snippet['title'])
                fe.podcast.itunes_summary(snippet['description'])
                fe.description(snippet['description'])
                if not video or video['expire'] < fe.pubdate():
                    video = {'video': fe.id(), 'expire': fe.pubdate()}
        feed = {'feed': fg.rss_str(), 'expire': datetime.datetime.now() + datetime.timedelta(hours=calls)}
        for chan in channel_name:
            channel_feed[chan] = feed
        self.write(feed['feed'])
        self.finish()
        video = video['video']
        mp3_file = 'audio/{}.mp3'.format(video)
        if channel[1] == 'audio' and not os.path.exists(mp3_file) and video not in conversion_queue.keys():
            conversion_queue[video] = {'status': False, 'added': datetime.datetime.now()}


class PlaylistHandler(web.RequestHandler):
    @gen.coroutine
    def get(self, playlist):
        logging.info('Playlist: %s (%s)', playlist, self.request.remote_ip)
        playlist = playlist.split('/')
        if len(playlist) < 2:
            playlist.append('video')
        playlist_name = '/'.join(playlist)
        self.add_header('Content-type', 'application/rss+xml')
        if playlist_name in playlist_feed and playlist_feed[playlist_name]['expire'] > datetime.datetime.now():
            self.write(playlist_feed[playlist_name]['feed'])
            self.finish()
            return
        calls = 0
        payload = {
            'part': 'snippet',
            'id': playlist[0],
            'key': key
        }
        request = requests.get('https://www.googleapis.com/youtube/v3/playlists', params=payload)
        calls += 1
        response = request.json()
        if request.status_code == 200:
            logging.debug('Downloaded Playlist Information')
        else:
            logging.error('Error Downloading Playlist: %s', request.reason)
            self.send_error(reason='Error Downloading Playlist')
            return
        fg = FeedGenerator()
        fg.load_extension('podcast')
        fg.generator('PodTube', __version__, 'https://github.com/aquacash5/PodTube')
        snippet = response['items'][0]['snippet']
        icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
        fg.title(snippet['title'])
        fg.id('http://' + self.request.host + self.request.uri)
        fg.description(snippet['description'] or ' ')
        fg.author(name=snippet['channelTitle'])
        fg.image(snippet['thumbnails'][icon]['url'])
        fg.link(href='https://www.youtube.com/playlist?list=' + playlist[0])
        fg.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
        fg.podcast.itunes_summary(snippet['description'])
        fg.podcast.itunes_category('Technology', 'Podcasting')
        fg.updated(str(datetime.datetime.utcnow()) + 'Z')
        video = None
        response = {'nextPageToken': ''}
        while 'nextPageToken' in response.keys():
            payload = {
                'part': 'snippet',
                'maxResults': 50,
                'playlistId': playlist[0],
                'key': key,
                'pageToken': response['nextPageToken']
            }
            request = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params=payload)
            calls += 1
            response = request.json()
            if request.status_code == 200:
                logging.debug('Downloaded Playlist Information')
            else:
                logging.error('Error Downloading Playlist: %s', request.reason)
                self.send_error(reason='Error Downloading Playlist Items')
                return
            for item in response['items']:
                snippet = item['snippet']
                current_video = snippet['resourceId']['videoId']
                if 'Private' in snippet['title']:
                    continue
                logging.debug('PlaylistVideo: %s %s', current_video, snippet['title'])
                fe = fg.add_entry()
                fe.title(snippet['title'])
                fe.id(current_video)
                icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
                fe.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
                fe.updated(snippet['publishedAt'])
                if playlist[1] == 'video':
                    fe.enclosure(url='http://{url}/video/{vid}'.format(url=self.request.host,
                                                                       vid=current_video),
                                 type="video/mp4")
                elif playlist[1] == 'audio':
                    fe.enclosure(url='http://{url}/audio/{vid}'.format(url=self.request.host,
                                                                       vid=current_video),
                                 type="audio/mpeg")
                fe.author(name=snippet['channelTitle'])
                fe.podcast.itunes_author(snippet['channelTitle'])
                fe.podcast.itunes_author(snippet['channelTitle'])
                fe.pubdate(snippet['publishedAt'])
                fe.link(href='http://www.youtube.com/watch?v=' + current_video, title=snippet['title'])
                fe.podcast.itunes_summary(snippet['description'])
                fe.description(snippet['description'])
                if not video or video['expire'] < fe.pubdate():
                    video = {'video': fe.id(), 'expire': fe.pubdate()}
        feed = {'feed': fg.rss_str(), 'expire': datetime.datetime.now() + datetime.timedelta(hours=calls)}
        playlist_feed[playlist_name] = feed
        self.write(feed['feed'])
        self.finish()
        video = video['video']
        mp3_file = 'audio/{}.mp3'.format(video)
        if playlist[1] == 'audio' and not os.path.exists(mp3_file) and video not in conversion_queue.keys():
            conversion_queue[video] = {'status': False, 'added': datetime.datetime.now()}


class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info('Video: %s', video)
        self.redirect(get_youtube_url(video))


class AudioHandler(web.RequestHandler):
    @gen.coroutine
    def get(self, audio):
        logging.info('Audio: %s (%s)', audio, self.request.remote_ip)
        mp3_file = './audio/{}.mp3'.format(audio)
        if not os.path.exists(mp3_file):
            if audio not in conversion_queue.keys():
                conversion_queue[audio] = {'status': False, 'added': datetime.datetime.now()}
            while audio in conversion_queue:
                yield gen.sleep(0.5)
        request_range = None
        range_header = self.request.headers.get("Range")
        if range_header:
            # As per RFC 2616 14.16, if an invalid Range header is specified,
            # the request will be treated as if the header didn't exist.
            request_range = httputil._parse_request_range(range_header)

        size = os.stat(mp3_file).st_size
        if request_range:
            start, end = request_range
            if (start is not None and start >= size) or end == 0:
                # As per RFC 2616 14.35.1, a range is not satisfiable only: if
                # the first requested byte is equal to or greater than the
                # content, or when a suffix with length 0 is specified
                self.set_status(416)  # Range Not Satisfiable
                self.set_header("Content-Type", "text/plain")
                self.set_header("Content-Range", "bytes */%s" % (size,))
                return
            if start is not None and start < 0:
                start += size
            if end is not None and end > size:
                # Clients sometimes blindly use a large range to limit their
                # download size; cap the endpoint at the actual file size.
                end = size
            # Note: only return HTTP 206 if less than the entire range has been
            # requested. Not only is this semantically correct, but Chrome
            # refuses to play audio if it gets an HTTP 206 in response to
            # ``Range: bytes=0-``.
            if size != (end or size) - (start or 0):
                self.set_status(206)  # Partial Content
                self.set_header("Content-Range", httputil._get_content_range(start, end, size))
        else:
            start = end = None
        if start is not None and end is not None:
            content_length = end - start
        elif end is not None:
            content_length = end
        elif start is not None:
            content_length = size - start
        else:
            content_length = size
        self.set_header("Accept-Ranges", "bytes")
        self.set_header("Content-Length", content_length)
        self.add_header('Content-Type', 'audio/mpeg')
        content = self.get_content(mp3_file, start, end)
        if isinstance(content, bytes):
            content = [content]
        for chunk in content:
            try:
                self.write(chunk)
                yield self.flush()
            except iostream.StreamClosedError:
                return

    @classmethod
    def get_content(cls, abspath, start=None, end=None):
        """Retrieve the content of the requested resource which is located
        at the given absolute path.

        This class method may be overridden by subclasses.  Note that its
        signature is different from other overridable class methods
        (no ``settings`` argument); this is deliberate to ensure that
        ``abspath`` is able to stand on its own as a cache key.

        This method should either return a byte string or an iterator
        of byte strings.  The latter is preferred for large files
        as it helps reduce memory fragmentation.

        .. versionadded:: 3.1
        """
        Path(abspath).touch(exist_ok=True)
        with open(abspath, "rb") as audio_file:
            if start is not None:
                audio_file.seek(start)
            if end is not None:
                remaining = end - (start or 0)
            else:
                remaining = None
            while True:
                chunk_size = 1024 ** 2
                if remaining is not None and remaining < chunk_size:
                    chunk_size = remaining
                chunk = audio_file.read(chunk_size)
                if chunk:
                    if remaining is not None:
                        remaining -= len(chunk)
                    yield chunk
                else:
                    if remaining is not None:
                        assert remaining == 0
                    return

    def on_connection_close(self):
        logging.info('Audio: User quit during transcoding (%s)', self.request.remote_ip)


class FileHandler(web.RequestHandler):
    def get(self):
        logging.info('ReadMe (%s)', self.request.remote_ip)
        self.write('''
<html>
    <head>
        <title>PodTube (v{}})</title>
        <link rel="shortcut icon" href="favicon.ico">
        <link rel="stylesheet" type="text/css" href="markdown.css">
    </head>
    <body>'''.format(__version__))
        with open('README.md') as text:
            self.write(misaka.html(text.read(), extensions=('tables', 'fenced-code')))
        self.write('''
    </body>
</html>''')


def cleanup():
    # Globals
    global video_links
    global playlist_feed
    global channel_feed
    current_time = datetime.datetime.now()
    # Video Links
    video_links_length = len(video_links)
    video_links = {video: info for video, info in video_links.items() if info['expire'] > current_time}
    video_links_length -= len(video_links)
    if video_links_length:
        logging.info('Cleaned %s items from video list', video_links_length)
    # Playlist Feeds
    playlist_feed_length = len(playlist_feed)
    playlist_feed = {playlist: info for playlist, info in playlist_feed.items() if info['expire'] > current_time}
    playlist_feed_length -= len(playlist_feed)
    if playlist_feed_length:
        logging.info('Cleaned %s items from playlist feeds', playlist_feed_length)
    # Channel Feeds
    channel_feed_length = len(channel_feed)
    channel_feed = {channel: info for channel, info in channel_feed.items() if info['expire'] > current_time}
    channel_feed_length -= len(channel_feed)
    if channel_feed_length:
        logging.info('Cleaned %s items from channel feeds', channel_feed_length)
    # Space Check
    size = psutil.disk_usage('./audio')
    if size.free < 536870912:
        for f in sorted(glob.glob('./audio/*mp3'), key=lambda audio_file: os.path.getctime(audio_file)):
            os.remove(f)
            logging.info('Deleted %s', f)
            size = psutil.disk_usage('./audio')
            if size.free > 16106127360:
                return


@gen.coroutine
def convert_videos():
    global conversion_queue
    global converting_lock
    try:
        remaining = [key for key in conversion_queue.keys() if not conversion_queue[key]['status']]
        video = sorted(remaining, key=lambda v: conversion_queue[v]['added'])[0]
        conversion_queue[video]['status'] = True
    except Exception:
        return
    with (yield converting_lock.acquire()):
        logging.info('Converting: %s', video)
        audio_file = './audio/{}.mp3'.format(video)
        ffmpeg_process = process.Subprocess(['ffmpeg',
                                             '-loglevel', 'panic',
                                             '-y',
                                             '-i', get_youtube_url(video),
                                             '-f', 'mp3', audio_file + '.temp'])
        try:
            yield ffmpeg_process.wait_for_exit()
            os.rename(audio_file + '.temp', audio_file)
        except Exception as ex:
            logging.error('Error converting file: %s', ex.reason)
            os.remove(audio_file + '.temp')
        finally:
            del conversion_queue[video]


def make_app():
    return web.Application([
        (r'/playlist/(.*)', PlaylistHandler),
        (r'/channel/(.*)', ChannelHandler),
        (r'/video/(.*)', VideoHandler),
        (r'/audio/(.*)', AudioHandler),
        (r'/', FileHandler),
        (r'/(.*)', web.StaticFileHandler, {'path': '.'})
    ])


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists('./audio'):
        os.mkdir('audio')
    parser = ArgumentParser(prog='PodTube')
    parser.add_argument('key',
                        help='Google\'s API Key')
    parser.add_argument('port',
                        type=int,
                        default=80,
                        nargs='?',
                        help='Port Number to listen on')
    parser.add_argument('--log-file',
                        type=str,
                        default='podtube.log',
                        metavar='FILE',
                        help='Location and name of log file')
    parser.add_argument('--log-format',
                        type=str,
                        default='%(asctime)-15s %(message)s',
                        metavar='FORMAT',
                        help='Logging format using syntax for python logging module')
    parser.add_argument('-v', '--version',
                        action='version',
                        version="%(prog)s " + __version__)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format=args.log_format, filename=args.log_file, filemode='a')
    key = args.key
    for file in glob.glob('audio/*.temp'):
        os.remove(file)
    app = make_app()
    app.listen(args.port)
    ioloop.PeriodicCallback(callback=cleanup, callback_time=1000).start()
    ioloop.PeriodicCallback(callback=convert_videos, callback_time=1000).start()
    ioloop.IOLoop.instance().start()
