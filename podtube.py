import os
import logging
import requests
import datetime
from argparse import ArgumentParser

import misaka

from tornado import web
from tornado import gen
from tornado import ioloop
from tornado import process

from pytube import YouTube

from feedgen.feed import FeedGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(message)s')
key = None
video_links = {}
playlist_feed = {}
channel_feed = {}


def get_youtube_url(video):
    if video in video_links and video_links[video]['expire'] > datetime.datetime.now():
        return video_links[video]['url']
    yt = YouTube('http://www.youtube.com/watch?v=' + video)
    vid = sorted(yt.filter("mp4"), key=lambda video: int(video.resolution[:-1]), reverse=True)[0].url
    parts = {}
    for part in vid.split('?')[-1].split('&'):
        part = part.split('=')
        parts[part[0]] = part[1]
    link = {'url': vid, 'expire': datetime.datetime.fromtimestamp(int(parts['expire']))}
    video_links[video] = link
    return link['url']


def touch(fname, mode=0o666):
    flags = os.O_CREAT | os.O_APPEND
    with os.fdopen(os.open(fname, flags=flags, mode=mode)):
        pass


class ChannelHandler(web.RequestHandler):
    @gen.coroutine
    def get(self, channel):
        logging.info('Channel: %s', channel)
        channel = channel.split('/')
        if len(channel) < 2:
            channel.append('video')
        channel_name = ['/'.join(channel)]
        self.add_header('Content-type', 'application/rss+xml')
        if channel_name[0] in channel_feed and channel_feed[channel_name[0]]['expire'] > datetime.datetime.now():
            self.write(channel_feed[channel_name[0]]['feed'])
            self.finish()
            return
        payload = {
            'part': 'snippet,contentDetails',
            'maxResults': 25,
            'channelId': channel[0],
            'key': key
        }
        request = requests.get('https://www.googleapis.com/youtube/v3/activities', params=payload)
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
                'maxResults': 25,
                'channelId': channel[0],
                'key': key
            }
            request = requests.get('https://www.googleapis.com/youtube/v3/activities', params=payload)
        response = request.json()
        if request.status_code == 200:
            logging.debug('Downloaded Playlist Information')
        else:
            logging.error('Error Downloading Playlist: %s', request.reason)
            self.send_error(reason='Error Downloading Playlist')
            return
        fg = FeedGenerator()
        fg.load_extension('podcast')
        snippet = response['items'][0]['snippet']
        icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
        fg.title(snippet['title'])
        fg.id('http://' + self.request.host + self.request.uri)
        fg.description(snippet['description'] or ' ')
        fg.author(name=snippet['channelTitle'])
        fg.image(snippet['thumbnails'][icon]['url'])
        fg.link(href='https://www.youtube.com/playlist?list=' + channel[0])
        fg.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
        fg.podcast.itunes_summary(snippet['description'])
        fg.updated(response['items'][0]['snippet']['publishedAt'])
        video = None
        for item in response['items']:
            snippet = item['snippet']
            if snippet['type'] != 'upload':
                continue
            curvideo = item['contentDetails']['upload']['videoId']
            if not video:
                video = curvideo
            logging.debug('PlaylistVideo: %s %s', curvideo, snippet['title'])
            fe = fg.add_entry()
            fe.title(snippet['title'])
            fe.id(curvideo)
            icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
            fe.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
            fe.updated(snippet['publishedAt'])
            if channel[1] == 'video':
                fe.enclosure(url='http://{url}/video/{vid}'.format(url=self.request.host,
                                                                   vid=curvideo),
                             type="video/mp4")
            elif channel[1] == 'audio':
                fe.enclosure(url='http://{url}/audio/{vid}'.format(url=self.request.host,
                                                                   vid=curvideo),
                             type="audio/mpeg")
            fe.author(name=snippet['channelTitle'])
            fe.podcast.itunes_author(snippet['channelTitle'])
            fe.podcast.itunes_author(snippet['channelTitle'])
            fe.pubdate(snippet['publishedAt'])
            fe.link(href='http://www.youtube.com/watch?v=' + curvideo, title=snippet['title'])
            fe.podcast.itunes_summary(snippet['description'])
            fe.description(snippet['description'])
        feed = {'feed': fg.rss_str(), 'expire': datetime.datetime.now() + datetime.timedelta(minutes=120)}
        for chan in channel_name:
            channel_feed[chan] = feed
        self.write(feed['feed'])
        self.finish()
        if channel[1] == 'audio' and not os.path.exists(video + '.mp3') and not os.path.exists(video + '.mp3.temp'):
            touch(video + '.mp3.temp')
            proc = process.Subprocess(['ffmpeg',
                                       '-loglevel', 'panic',
                                       '-y',
                                       '-i', get_youtube_url(video),
                                       '-f', 'mp3', video + '.mp3.temp'])
            try:
                yield proc.wait_for_exit()
                os.rename(video + '.mp3.temp', video + '.mp3')
            except Exception:
                os.remove(video + '.mp3.temp')


class PlaylistHandler(web.RequestHandler):
    @gen.coroutine
    def get(self, playlist):
        logging.info('Playlist: %s', playlist)
        playlist = playlist.split('/')
        if len(playlist) < 2:
            playlist.append('video')
        playlist_name = '/'.join(playlist)
        self.add_header('Content-type', 'application/rss+xml')
        if playlist_name in playlist_feed and playlist_feed[playlist_name]['expire'] > datetime.datetime.now():
            self.write(playlist_feed[playlist_name]['feed'])
            self.finish()
            return
        payload = {
            'part': 'snippet',
            'id': playlist[0],
            'key': key
        }
        request = requests.get('https://www.googleapis.com/youtube/v3/playlists', params=payload)
        response = request.json()
        if request.status_code == 200:
            logging.debug('Downloaded Playlist Information')
        else:
            logging.error('Error Downloading Playlist: %s', request.reason)
            self.send_error(reason='Error Downloading Playlist')
            return
        fg = FeedGenerator()
        fg.load_extension('podcast')
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
        payload = {
            'part': 'snippet',
            'maxResults': 25,
            'playlistId': playlist[0],
            'key': key
        }
        request = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params=payload)
        response = request.json()
        if request.status_code == 200:
            logging.debug('Downloaded Playlist Information')
        else:
            logging.error('Error Downloading Playlist: %s', request.reason)
            self.send_error(reason='Error Downloading Playlist Items')
            return
        fg.updated(response['items'][0]['snippet']['publishedAt'])
        video = response['items'][0]['snippet']['resourceId']['videoId']
        for item in response['items']:
            snippet = item['snippet']
            curvideo = snippet['resourceId']['videoId']
            logging.debug('PlaylistVideo: %s %s', curvideo, snippet['title'])
            fe = fg.add_entry()
            fe.title(snippet['title'])
            fe.id(curvideo)
            icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
            fe.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
            fe.updated(snippet['publishedAt'])
            if playlist[1] == 'video':
                fe.enclosure(url='http://{url}/video/{vid}'.format(url=self.request.host,
                                                                   vid=curvideo),
                             type="video/mp4")
            elif playlist[1] == 'audio':
                fe.enclosure(url='http://{url}/audio/{vid}'.format(url=self.request.host,
                                                                   vid=curvideo),
                             type="audio/mpeg")
            fe.author(name=snippet['channelTitle'])
            fe.podcast.itunes_author(snippet['channelTitle'])
            fe.podcast.itunes_author(snippet['channelTitle'])
            fe.pubdate(snippet['publishedAt'])
            fe.link(href='http://www.youtube.com/watch?v=' + curvideo, title=snippet['title'])
            fe.podcast.itunes_summary(snippet['description'])
            fe.description(snippet['description'])
        feed = {'feed': fg.rss_str(), 'expire': datetime.datetime.now() + datetime.timedelta(minutes=120)}
        playlist_feed[playlist_name] = feed
        self.write(feed['feed'])
        self.finish()
        if playlist[1] == 'audio' and not os.path.exists(video + '.mp3') and not os.path.exists(video + '.mp3.temp'):
            touch(video + '.mp3.temp')
            proc = process.Subprocess(['ffmpeg',
                                       '-loglevel', 'panic',
                                       '-y',
                                       '-i', get_youtube_url(video),
                                       '-f', 'mp3', video + '.mp3.temp'])
            try:
                yield proc.wait_for_exit()
                os.rename(video + '.mp3.temp', video + '.mp3')
            except Exception:
                os.remove(video + '.mp3.temp')


class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info('Video: %s', video)
        self.redirect(get_youtube_url(video))


class AudioHandler(web.RequestHandler):
    @gen.coroutine
    def get(self, audio):
        self.closed = False
        logging.info('Audio: %s'.format(audio))
        file = '{}.mp3'.format(audio)
        if os.path.exists(file):
            self.send_file(file)
            return
        if not os.path.exists(file + '.temp'):
            touch(file + '.temp')
            proc = process.Subprocess(['ffmpeg',
                                       '-loglevel', 'panic',
                                       '-y',
                                       '-i', get_youtube_url(audio),
                                       '-f', 'mp3', file + '.temp'])
            try:
                yield proc.wait_for_exit()
                os.rename(file + '.temp', file)
            except Exception:
                os.remove(file + '.temp')
        else:
            while os.path.exists(file + '.temp') and not self.closed:
                yield gen.sleep(0.5)
        if self.closed or not os.path.exists(file):
            return
        self.send_file(file)

    def send_file(self, file):
        self.add_header('Content-Type', 'audio/mpeg')
        self.add_header('Content-Length', os.stat(file).st_size)
        with open(file, 'rb') as f:
            self.write(f.read())

    def on_connection_close(self):
        self.closed = True


class FileHandler(web.RequestHandler):
    def get(self):
        with open('README.md') as text:
            self.write(misaka.html(text.read(), extensions=['tables']))


def make_app():
    return web.Application([
        (r'/playlist/(.*)', PlaylistHandler),
        (r'/channel/(.*)', ChannelHandler),
        (r'/video/(.*)', VideoHandler),
        (r'/audio/(.*)', AudioHandler),
        (r'/', FileHandler)
    ])


def cleanup():
    global video_links
    global playlist_feed
    global channel_feed
    vid_len = len(video_links)
    play_len = len(playlist_feed)
    chan_len = len(channel_feed)
    video_links = {key: value for key, value in video_links.items() if value['expire'] > datetime.datetime.now()}
    playlist_feed = {key: value for key, value in playlist_feed.items() if value['expire'] > datetime.datetime.now()}
    channel_feed = {key: value for key, value in channel_feed.items() if value['expire'] > datetime.datetime.now()}
    vid_len -= len(video_links)
    play_len -= len(playlist_feed)
    chan_len -= len(channel_feed)
    if vid_len:
        logging.info('Cleaned %s items from video list', vid_len)
    if play_len:
        logging.info('Cleaned %s items from playlist feeds', play_len)
    if chan_len:
        logging.info('Cleaned %s items from channel feeds', chan_len)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('key',
                        help='Google\'s API Key')
    parser.add_argument('port',
                        help='Port Number to listen on',
                        type=int,
                        default=80,
                        nargs='?')
    args = parser.parse_args()
    key = args.key
    app = make_app()
    app.listen(args.port)
    ioloop.PeriodicCallback(callback=cleanup, callback_time=36 * 10 ** 5).start()
    ioloop.IOLoop.instance().start()
