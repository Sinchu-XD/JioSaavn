BASE_URL = "https://www.jiosaavn.com/api.php"

COMMON = "&_format=json&_marker=0&api_version=4&cc=in"

SEARCH = BASE_URL + "?__call=search.getResults" + COMMON + "&q="
SONG = BASE_URL + "?__call=song.getDetails" + COMMON + "&pids="
ALBUM = BASE_URL + "?__call=content.getAlbumDetails" + COMMON + "&albumid="
PLAYLIST = BASE_URL + "?__call=playlist.getDetails" + COMMON + "&listid="
LYRICS = BASE_URL + "?__call=lyrics.getLyrics" + COMMON + "&lyrics_id="
