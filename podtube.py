import sys
import logging
import requests

from tornado import web
from tornado import gen
from tornado import ioloop
from tornado import process

from pytube import YouTube

from feedgen.feed import FeedGenerator


class PlaylistHandler(web.RequestHandler):
    def get(self, playlist):
        logging.info('Playlist: %s', playlist)
        self.add_header('Content-type', 'application/rss+xml')
        playlist = playlist.split('/')
        if len(playlist) < 2:
            playlist.append('video')
        payload = {
            'part': 'snippet',
            'id': playlist[0],
            'key': sys.argv[2]
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
        fg.title(response['items'][0]['snippet']['title'])
        fg.subtitle(response['items'][0]['snippet']['title'])
        fg.id('http://' + self.request.host + self.request.uri)
        fg.author(name=response['items'][0]['snippet']['channelTitle'])
        fg.icon(response['items'][0]['snippet']['thumbnails']['default']['url'])
        fg.link(href='https://www.youtube.com/playlist?list=' + playlist[0])
        fg.author()
        payload = {
            'part': 'snippet',
            'maxResults': 25,
            'playlistId': playlist[0],
            'key': sys.argv[2]
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
        for item in response['items']:
            snippet = item['snippet']
            logging.debug('PlaylistVideo: %s %s', snippet['resourceId']['videoId'], snippet['title'])
            fe = fg.add_entry()
            fe.title(snippet['title'])
            fe.id(snippet['resourceId']['videoId'])
            fe.updated(snippet['publishedAt'])
            if playlist[1] == 'video':
                fe.enclosure(url='http://{url}/video/{vid}'.format(url=self.request.host,
                                                                   vid=snippet['resourceId']['videoId']),
                             type="video/mp4")
            elif playlist[1] == 'audio':
                fe.enclosure(url='http://{url}/audio/{vid}'.format(url=self.request.host,
                                                                   vid=snippet['resourceId']['videoId']),
                             type="audio/mpeg")
            fe.author(name=snippet['channelTitle'])
            fe.pubdate(snippet['publishedAt'])
            fe.link(href='http://www.youtube.com/watch?v=' + snippet['resourceId']['videoId'], title=snippet['title'])
            fe.summary(snippet['description'])
        self.write(fg.rss_str())
        self.finish()


class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info('Video: %s'.format(video))
        video = video.split('.')
        if len(video) < 2:
            video.append('mp4')
        yt = YouTube('http://www.youtube.com/watch?v=' + video[0])
        vid = sorted(yt.filter(video[1]), key=lambda video: int(video.resolution[:-1]), reverse=True)[0]
        self.redirect(vid.url)


class AudioHandler(web.RequestHandler):
    @web.asynchronous
    @gen.coroutine
    def get(self, audio):
        logging.info('Audio: %s'.format(audio))
        audio = audio.split('.')
        if len(audio) < 2:
            audio.append('mp3')
        yt = YouTube('http://www.youtube.com/watch?v=' + audio[0])
        vid = sorted(yt.filter("mp4"), key=lambda video: int(video.resolution[:-1]), reverse=True)[0]
        proc = process.Subprocess(
            ['ffmpeg',
             '-loglevel', 'panic',
             '-i', '{}'.format(vid.url),
             '-q:a', '0',
             '-map', 'a',
             '-f', audio[1], 'pipe:'],
            stdout=process.Subprocess.STREAM)
        proc.stdout.read_until_close(streaming_callback=self.on_chunk)
        yield proc.wait_for_exit()

    def on_chunk(self, chunk):
        if chunk:
            self.write(chunk)
            self.flush()
        else:
            self.finish()


def make_app():
    return web.Application([
        (r'/playlist/(.*)', PlaylistHandler),
        (r'/video/(.*)', VideoHandler),
        (r'/audio/(.*)', AudioHandler)
    ])

if __name__ == '__main__':
    app = make_app()
    app.listen(sys.argv[1])
    ioloop.IOLoop.current().start()
