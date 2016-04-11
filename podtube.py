import sys
import requests
from tornado import web
from tornado import ioloop
from pytube import YouTube
from pyatom import AtomFeed
from pyatom import FeedEntry
from datetime import datetime


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
        feed = AtomFeed(title=response['items'][0]['snippet']['title'],
                        subtitle=response['items'][0]['snippet']['title'],
                        feed_url='http://' + self.request.host + self.request.uri,
                        url='https://www.youtube.com/playlist?list=' + playlist[0],
                        author=response['items'][0]['snippet']['channelTitle'],
                        icon=response['items'][0]['snippet']['thumbnails']['default']['url'])
        feed.title_type = 'text/plain'
        feed.subtitle_type = 'text/plain'
        payload = {
            'part': 'snippet',
            'maxResults': 25,
            'playlistId': playlist[0],
            'key': sys.argv[1]
        }
        request = requests.get('https://www.googleapis.com/youtube/v3/playlistItems', params=payload)
        response = request.json()
        feed.updated = datetime.strptime(response['items'][0]['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%S.%fZ')
        for item in response['items']:
            snippet = item['snippet']
            entry = FeedEntry(title=snippet['title'],
                              updated=datetime.strptime(snippet['publishedAt'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                              id='http://{url}/{type}/{vid}'.format(url=self.request.host,
                                                                    type=playlist[1],
                                                                    vid=snippet['resourceId']['videoId']))
            entry.author = [{'name': snippet['channelTitle']}]
            entry.published = datetime.strptime(snippet['publishedAt'], '%Y-%m-%dT%H:%M:%S.%fZ')
            entry.links.append({'href': 'http://www.youtube.com/watch?v=' + snippet['resourceId']['videoId'],
                                'title': snippet['title']})
            entry.summary = snippet['description']
            entry.summary_type = 'text/plain'
            entry.title_type = 'text/plain'
            feed.add(entry)
        for line in feed.generate():
            self.write(line)
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
