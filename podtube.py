import sys
import requests

from tornado import web
from tornado import ioloop

from pytube import YouTube

from feedgen.feed import FeedEntry
from feedgen.feed import FeedGenerator


class PlaylistHandler(web.RequestHandler):
    def get(self, playlist):
        print('Playlist: {}'.format(playlist))
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
        fg = FeedGenerator()

        fg.title(response['items'][0]['snippet']['title'])
        fg.subtitle(response['items'][0]['snippet']['title'])
        fg.id('http://' + self.request.host + self.request.uri)
        fg.author({'name': response['items'][0]['snippet']['channelTitle']})
        fg.icon(response['items'][0]['snippet']['thumbnails']['default']['url'])
        payload = {
            'part': 'snippet',
            'maxResults': 25,
            'playlistId': playlist[0],
            'key': sys.argv[1]
        }
        request = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params=payload)
        response = request.json()
        fg.updated(response['items'][0]['snippet']['publishedAt'])
        for item in response['items']:
            snippet = item['snippet']
            entry = FeedEntry()
            entry.title(snippet['title'])
            entry.updated(snippet['publishedAt'])
            entry.id('http://{url}/{type}/{vid}'.format(url=self.request.host,
                                                        type=playlist[1],
                                                        vid=snippet['resourceId']['videoId']))
            entry.author({'name': snippet['channelTitle']})
            entry.pubdate(snippet['publishedAt'])
            entry.link({'href': 'http://www.youtube.com/watch?v=' + snippet['resourceId']['videoId'],
                        'title': snippet['title']})
            entry.summary(snippet['description'])
            fg.add_entry(entry)
        self.write(fg.rss_str())
        self.finish()


class VideoHandler(web.RequestHandler):
    def get(self, video):
        print('Video: {}'.format(video))
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
    app.listen(sys.argv[1])
    ioloop.IOLoop.current().start()
