# /usr/bin/python3.6
import logging
import os
from asyncio import sleep
from asyncio.queues import LifoQueue
from contextlib import suppress
from datetime import datetime, timedelta
from glob import glob
from subprocess import Popen
from configparser import ConfigParser

import misaka
import ujson as json
from feedgen.feed import FeedGenerator
from sanic import Sanic
from sanic.exceptions import InvalidRangeType, HeaderNotFound
from sanic.handlers import ContentRangeHandler
from sanic.response import html, file, text, raw, HTTPResponse

from utils import get_youtube_url, get, metric_to_base, get_total_storage

__version__ = '2.0'

CONFIG = ConfigParser()
CONFIG.read('podtube.ini')
CONFIG = dict(CONFIG['PodTube'])
app = Sanic('PodTube')
log = logging.getLogger('sanic')
log.setLevel(logging._nameToLevel[CONFIG['log_level'].upper()])

playlist_feed = {}
channel_feed = {}
conversion_list = None
KEY = CONFIG['youtube_key']
AUDIO_DIRECTORY = CONFIG['audio_directory']


@app.get('/channel/<channel_id>')
@app.get('/channel/<channel_id>/<return_type>')
async def channel(request, channel_id, return_type='video'):
    log.info(f'Channel: {channel_id}')
    channel_name = [f'{channel_id}/{return_type}']
    if channel_name[0] in channel_feed and channel_feed[channel_name[0]]['expire'] > datetime.now():
        return raw(channel_feed[channel_name[0]]['feed'], content_type='application/rss+xml')
    fg = None
    calls = 0
    response = {'nextPageToken': ''}
    while 'nextPageToken' in response:
        next_page = response['nextPageToken']
        payload = {
            'part': 'snippet,contentDetails',
            'maxResults': 50,
            'channelId': channel_id,
            'key': KEY,
            'pageToken': next_page
        }
        response = json.loads(
            await get('https://www.googleapis.com/youtube/v3/activities', params=payload)
        )
        calls += 1
        if 'error' in response:
            payload = {
                'part': 'snippet',
                'maxResults': 1,
                'forUsername': channel_id,
                'key': KEY
            }
            response = json.loads(
                await get('https://www.googleapis.com/youtube/v3/channels', params=payload)
            )
            channel_id = response['items'][0]['id']
            channel_name.append(f'{channel_id}/{return_type}')
            payload = {
                'part': 'snippet,contentDetails',
                'maxResults': 50,
                'channelId': channel_id,
                'key': KEY,
                'pageToken': next_page
            }
            response = json.loads(
                await get('https://www.googleapis.com/youtube/v3/activities', params=payload)
            )
            calls += 2
        if not fg:
            fg = FeedGenerator()
            fg.load_extension('podcast')
            fg.generator('PodTube', __version__, 'https://github.com/aquacash5/PodTube')
            snippet = response['items'][0]['snippet']
            if 'Private' in snippet['title']:
                continue
            icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
            fg.title(snippet['title'])
            fg.id(f'http://{request.headers["host"]}{request.url}')
            fg.description(snippet['description'] or ' ')
            fg.author(name=snippet['channelTitle'])
            fg.image(snippet['thumbnails'][icon]['url'])
            fg.link(href=f'https://www.youtube.com/playlist?list={channel_id}')
            fg.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
            fg.podcast.itunes_summary(snippet['description'])
            fg.podcast.itunes_category('Technology', 'Podcasting')
            fg.updated(f'{str(datetime.utcnow())}Z')
        for item in response['items']:
            snippet = item['snippet']
            if snippet['type'] != 'upload':
                continue
            current_video = item['contentDetails']['upload']['videoId']
            log.debug(f'ChannelVideo: {current_video} {snippet["title"]}')
            fe = fg.add_entry()
            fe.title(snippet['title'])
            fe.id(current_video)
            icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
            fe.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
            fe.updated(snippet['publishedAt'])
            if return_type == 'audio':
                fe.enclosure(url=f'http://{request.headers["host"]}audio/{current_video}',
                             type="audio/mpeg")
            else:
                fe.enclosure(url=f'http://{request.headers["host"]}video/{current_video}',
                             type="video/mp4")
            fe.author(name=snippet['channelTitle'])
            fe.podcast.itunes_author(snippet['channelTitle'])
            fe.podcast.itunes_author(snippet['channelTitle'])
            fe.pubdate(snippet['publishedAt'])
            fe.link(href=f'http://www.youtube.com/watch?v={current_video}', title=snippet['title'])
            fe.podcast.itunes_summary(snippet['description'])
            fe.description(snippet['description'])
    feed = {
        'feed': fg.rss_str(),
        'expire': datetime.now() + timedelta(hours=calls)
    }
    for _name in channel_name:
        channel_feed[_name] = feed
    return raw(feed['feed'], content_type='application/rss+xml')


@app.get('/playlist/<playlist_id>')
@app.get('/playlist/<playlist_id>/<return_type>')
async def playlist(request, playlist_id, return_type='video'):
    log.info(f'Playlist: {playlist_id}')
    playlist_name = f'{playlist_id}/{return_type}'
    if playlist_name in playlist_feed and playlist_feed[playlist_name]['expire'] > datetime.now():
        return raw(playlist_feed[playlist_name]['feed'], content_type='application/rss+xml')
    calls = 0
    payload = {
        'part': 'snippet',
        'id': playlist_id,
        'key': KEY
    }
    log.debug('Downloaded Playlist Information')
    response = json.loads(
        await get('https://www.googleapis.com/youtube/v3/playlists', params=payload)
    )
    calls += 1
    fg = FeedGenerator()
    fg.load_extension('podcast')
    fg.generator('PodTube', __version__, 'https://github.com/aquacash5/PodTube')
    snippet = response['items'][0]['snippet']
    icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
    fg.title(snippet['title'])
    fg.id(f'http://{request.headers["host"]}{request.url}')
    fg.description(snippet['description'] or ' ')
    fg.author(name=snippet['channelTitle'])
    fg.image(snippet['thumbnails'][icon]['url'])
    fg.link(href=f'https://www.youtube.com/playlist?list={playlist_id}')
    fg.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
    fg.podcast.itunes_summary(snippet['description'])
    fg.podcast.itunes_category('Technology', 'Podcasting')
    fg.updated(f'{str(datetime.utcnow())}Z')
    response = {'nextPageToken': ''}
    while 'nextPageToken' in response.keys():
        payload = {
            'part': 'snippet',
            'maxResults': 50,
            'playlistId': playlist_id,
            'key': KEY,
            'pageToken': response['nextPageToken']
        }
        response = json.loads(
            await get('https://www.googleapis.com/youtube/v3/playlistItems', params=payload)
        )
        calls += 1
        for item in response['items']:
            snippet = item['snippet']
            current_video = snippet['resourceId']['videoId']
            if 'Private' in snippet['title']:
                continue
            log.debug(f'PlaylistVideo: {current_video} {snippet["title"]}')
            fe = fg.add_entry()
            fe.title(snippet['title'])
            fe.id(current_video)
            icon = max(snippet['thumbnails'], key=lambda x: snippet['thumbnails'][x]['width'])
            fe.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
            fe.updated(snippet['publishedAt'])
            if return_type == 'audio':
                fe.enclosure(url=f'http://{request.headers["host"]}audio/{current_video}',
                             type="audio/mpeg")
            else:
                fe.enclosure(url=f'http://{request.headers["host"]}video/{current_video}',
                             type="video/mp4")
            fe.author(name=snippet['channelTitle'])
            fe.podcast.itunes_author(snippet['channelTitle'])
            fe.podcast.itunes_author(snippet['channelTitle'])
            fe.pubdate(snippet['publishedAt'])
            fe.link(
                href='http://www.youtube.com/watch?v=' + current_video,
                title=snippet['title']
            )
            fe.podcast.itunes_summary(snippet['description'])
            fe.description(snippet['description'])
    feed = {
        'feed': fg.rss_str(),
        'expire': datetime.now() + timedelta(hours=calls)
    }
    playlist_feed[playlist_name] = feed
    return raw(feed['feed'], content_type='application/rss+xml')


@app.get('/video/<video_id>')
async def video(request, video_id):
    yt_url = get_youtube_url(video_id)
    return HTTPResponse(
        status=302,
        headers={'Location': yt_url},
        content_type=yt_url
    )


@app.head('/audio/<audio_id>')
async def audio(request, audio_id):
    global conversion_list
    global AUDIO_DIRECTORY
    log.info(f'Audio HEAD request {audio_id}')
    mp3_file = os.path.join(AUDIO_DIRECTORY, f'{audio_id}.mp3')
    headers = {'Accept-Ranges': 'bytes'}
    if not os.path.exists(mp3_file):
        conversion_list.put_nowait(audio_id)
    else:
        headers['Content-Length'] = os.stat(mp3_file).st_size
    return HTTPResponse(
        headers=headers,
        content_type='audio/mpeg')


@app.get('/audio/<audio_id>')
async def audio(request, audio_id):
    global conversion_list
    global AUDIO_DIRECTORY
    log.info(f'Audio GET request {audio_id}')
    mp3_file = os.path.join(AUDIO_DIRECTORY, f'{audio_id}.mp3')
    headers = {
        'Content-Type': 'audio/mpeg',
        'Content-Disposition': f'attachment; filename="{audio_id}.mp3"'
    }
    if not os.path.exists(mp3_file):
        conversion_list.put_nowait(audio_id)
        while not os.path.exists(mp3_file):
            await sleep(1)
    request_range = None
    with suppress(InvalidRangeType, HeaderNotFound):
        request_range = ContentRangeHandler(request, os.stat(mp3_file))
    return await file(mp3_file, _range=request_range, headers=headers)


@app.add_task
async def cleanup():
    global AUDIO_DIRECTORY
    max_size = metric_to_base(CONFIG['max_storage'])
    while True:
        size = await get_total_storage(AUDIO_DIRECTORY)
        log.debug(f'Size: {size}/{max_size}')
        if size > max_size:
            for removable_file in sorted(glob(f'{AUDIO_DIRECTORY}/*mp3'),
                                         key=lambda audio_file: os.path.getctime(audio_file)):
                size -= os.path.getsize(removable_file)
                os.remove(removable_file)
                log.info(f'Deleted {removable_file}')
                if size < max_size:
                    break
                await sleep(.01)
        await sleep(5)


@app.add_task
async def convert_youtube_video():
    global AUDIO_DIRECTORY
    global conversion_list
    conversion_list = LifoQueue()
    while True:
        try:
            video_id = await conversion_list.get()
            mp3_file = os.path.join(AUDIO_DIRECTORY, f'{video_id}.mp3')
            if any(glob(f'{mp3_file}*')):
                log.debug(f'{video_id} already exists or is being processed')
                break
            log.info(f'Processing {video_id}')
            ffmpeg_process = Popen(['ffmpeg',
                                    '-loglevel', 'panic',
                                    '-y',
                                    '-i', get_youtube_url(video_id),
                                    '-f', 'mp3', f'{mp3_file}.temp'])
            process_result = ffmpeg_process.poll()
            while process_result is None:
                await sleep(1)
                process_result = ffmpeg_process.poll()
            log.debug(f'{video_id} process result {process_result}')
            if process_result == 0:
                log.info(f'Converted {video_id}')
                os.rename(f'{mp3_file}.temp', mp3_file)
            else:
                raise Exception(f'{video_id} failed to convert')
        except Exception as ex:
            log.error(ex)
            os.remove(f'{mp3_file}.temp')
        finally:
            conversion_list.task_done()


@app.get('/')
async def readme(request):
    log.info('Read Me')
    head = [f'<title>PodTube ver.{__version__}</title>']
    with open('README.md') as readme_file:
        body = misaka.html(readme_file.read(),
                           extensions=('tables', 'fenced-code'))
    with open('markdown.css') as css:
        head.append(f'<style>{css.read()}</style>')
    head = '\n'.join(head)
    return html(f'<html><head>{head}</head><body>{body}</body></html>')


@app.get('/robots.txt')
async def robots_txt(request):
    log.info('ROBOTS!!!')
    return text('\n'.join([
        'User-agent: *',
        'Disallow: /playlist/',
        'Disallow: /channel/',
        'Disallow: /audio/',
        'Disallow: /video/'
    ]))


if __name__ == '__main__':
    os.makedirs(AUDIO_DIRECTORY, exist_ok=True)
    for temp_file in glob(os.path.join(AUDIO_DIRECTORY, '*temp')):
        os.remove(temp_file)
    app.run(host='0.0.0.0', port=CONFIG['port'])
