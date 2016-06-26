# [PodTube](https://github.com/aquacash5/PodTube) (v1.0)

This is a python application for converting Youtube playlists and channels into podcast rss feeds.

## Requirements

#### Python

- [tornado](https://pypi.python.org/pypi/tornado/)
- [misaka](https://pypi.python.org/pypi/misaka/)
- [pytube](https://pypi.python.org/pypi/pytube/)
- [feedgen](https://pypi.python.org/pypi/feedgen/) (if you can't install lxml for feedgen, use the one on my [GitHub](https://github.com/aquacash5/python-feedgen))

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


## License

Copyright (c) 2016, Kyle Bloom

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
