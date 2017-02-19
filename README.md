# [PodTube](https://github.com/aquacash5/PodTube) (v2.0)

This is a python application for converting Youtube playlists and channels into podcast rss feeds.

### [LICENSE](https://github.com/aquacash5/podtube/blob/master/LICENSE)

## Requirements

#### Python

- [Sanic](https://pypi.python.org/pypi/sanic/)
- [misaka](https://pypi.python.org/pypi/misaka/)
- [pytube](https://pypi.python.org/pypi/pytube/)
- [feedgen](https://pypi.python.org/pypi/feedgen/)

#### System

- [ffmpeg](http://ffmpeg.org/)

## Starting Server

```
podtube.py [-h] key [port]
```

#### Positional Arguments:

| Key  | Description              | Default |
| ---- | ------------------------ | ------- |
| key  | Google's API Key         | None    |
| port | Port Number to listen on | 80      |

#### Optional Arguments:

| Key                 | Description                                           |
| ------------------- | ----------------------------------------------------- |
| -h, --help          | show this help message and exit                       |
| --log-file FILE     | Location and name of log file                         |
| --log-format FORMAT | Logging format using syntax for python logging module |
| -v, --version       | show program's version number and exit                |

## Usage

#### Playlists

Get the playlist id from the youtube url

```
https://www.youtube.com/playlist?list=<PlaylistID>
```

Add the url to your podcast client of choice

```
http://<host>:<port>/playlist/<PlaylistID>
```

If you want an audio podcast add a /audio to the url

```
http://<host>:<port>/playlist/<PlaylistID>/audio
```

#### Channels

Get the channel id or username from the youtube url

```
https://www.youtube.com/channel/<ChannelID>
```
or
```
https://www.youtube.com/user/<Username>
```

Add the url to your podcast client of choice

```
http://<host>:<port>/channel/<ChannelID>
```
or
```
http://<host>:<port>/channel/<Username>
```

If you want an audio podcast add a /audio to the url

```
http://<host>:<port>/channel/<Username>/audio
```

## Examples

#### Playlists

[http://podtube.aquacash5.com/playlist/PL662F41918C22319F](http://podtube.aquacash5.com/playlist/PL662F41918C22319F)

[http://podtube.aquacash5.com/playlist/PL662F41918C22319F/video](http://podtube.aquacash5.com/playlist/PL662F41918C22319F/video)

[http://podtube.aquacash5.com/playlist/PL662F41918C22319F/audio](http://podtube.aquacash5.com/playlist/PL662F41918C22319F/audio)


#### Channels

[http://podtube.aquacash5.com/channel/razethew0rld](http://podtube.aquacash5.com/channel/razethew0rld)

[http://podtube.aquacash5.com/channel/UCOWcZ6Wicl-1N34H0zZe38w](http://podtube.aquacash5.com/channel/UCOWcZ6Wicl-1N34H0zZe38w)

[http://podtube.aquacash5.com/channel/razethew0rld/video](http://podtube.aquacash5.com/channel/razethew0rld/video)

[http://podtube.aquacash5.com/channel/UCOWcZ6Wicl-1N34H0zZe38w/video](http://podtube.aquacash5.com/channel/UCOWcZ6Wicl-1N34H0zZe38w/video)

[http://podtube.aquacash5.com/channel/razethew0rld/audio](http://podtube.aquacash5.com/channel/razethew0rld/audio)

[http://podtube.aquacash5.com/channel/UCOWcZ6Wicl-1N34H0zZe38w/audio](http://podtube.aquacash5.com/channel/UCOWcZ6Wicl-1N34H0zZe38w/audio)
