import sys
import requests
from tornado import web
from tornado import ioloop
from pytube import YouTube


class PlaylistHandler(web.RequestHandler):
    def get(self, playlist):
        self.add_header('Content-type', 'application/rss+xml')
        playlist = playlist.split('/')
        if len(playlist) < 2:
            playlist.append('video')
        payload = {
            'part': 'snippet',
            'id': playlist[0],
            'key': sys.argv[1]
        }
        request = requests.get('https://www.googleapis.com/youtube/v3/playlists', params=payload)
        response = request.json()
        self.write('<?xml version="1.0" encoding="UTF-8"?>')
        self.write('<rss><channel>')
        self.write('<title>' + response['items'][0]['snippet']['title'] + '</title>')
        self.write('<link>https://www.youtube.com/playlist?list=' + playlist[0] + '</link>')
        self.write('<description>' + response['items'][0]['snippet']['description'] + '</description>')
        self.write('<itunes:image href="' + response['items'][0]['snippet']['thumbnails']['default']['url'] + '"/>')
        payload = {
            'part': 'snippet',
            'maxResults': 25,
            'playlistId': playlist[0],
            'key': sys.argv[1]
        }
        request = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params=payload)
        response = request.json()
        for item in response['items']:
            snippet = item['snippet']
            yt = YouTube('http://www.youtube.com/watch?v=' + snippet['resourceId']['videoId'])
            self.write('<item>')
            self.write('<title>' + snippet['title'] + '</title>')
            self.write('<link>' + yt.url + '</link>')
            self.write('<description>' + snippet['description'] + '</description>')
            self.write('<pubDate>' + snippet['publishedAt'] + '</pubDate>')
            self.write('<itunes:image>' + snippet['thumbnails']['default']['url'] + '</itunes:image>')
            self.write('<enclosure url="http://{url}/{type}/{vid}" length="{len}" type="{vtype}" />'.format(
                url=self.request.host,
                type=playlist[1],
                vid=yt.video_id,
                len=8,
                vtype='audio/mpeg' if playlist[1] == 'audio' else 'video/mp4'))
            self.write('</item>')
        self.finish('</channel></rss>')


class VideoHandler(web.RequestHandler):
    def get(self, video):
        print(video)
        yt = YouTube('http://www.youtube.com/watch?v=' + video)
        vid = sorted(yt.filter("mp4"), key=lambda video: int(video.resolution[:-1]), reverse=True)[0]
        self.redirect(vid.url)


def make_app():
    return web.Application([
        (r'/playlist/(.*)', PlaylistHandler),
        (r'/video/(.*)', VideoHandler)
    ])

if __name__ == '__main__':
    app = make_app()
    app.listen(8888)
    ioloop.IOLoop.current().start()
