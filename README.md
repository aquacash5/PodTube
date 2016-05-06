# PodTube

## Requirements

#### Python
- [tornado](https://pypi.python.org/pypi/tornado/)
- [misaka](https://pypi.python.org/pypi/misaka/)
- [pytube](https://pypi.python.org/pypi/pytube/)
- [feedgen](https://pypi.python.org/pypi/feedgen/)
(if you can't install lxml for feedgen, use the one on my
[GitHub](https://github.com/aquacash5/python-feedgen))

#### System
- [ffmpeg](http://ffmpeg.org/)

## Starting Server

```
podtube.py [-h] key [port]
```

#### Positional Arguments:

Key  | Description | Default
---- | ----------- | -------
key  | Google's API Key | None
port | Port Number to listen on | 80

#### Optional Arguments:

Key  | Description
---- | ----
-h, --help | show this help message and exit

## Usage

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

#### Examples
```
http://example.com/playlist/PL662F41918C22319F/audio
```