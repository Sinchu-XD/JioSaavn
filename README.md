# 🎧 SaavnAPI

> ⚡ Fast, Async JioSaavn API Wrapper for Python

A powerful and fully asynchronous wrapper for JioSaavn, built for speed and scalability.

---

## 🚀 Features

- ⚡ Fully Async (aiohttp based)
- 🔍 Search Songs
- 🎵 Get Stream URLs (320kbps)
- 📝 Fetch Lyrics
- 💿 Album Support
- 📻 Playlist Support
- 🧠 Clean & Modular Design

---

## 📦 Installation

```bash
pip install SaavnAPI
```

---

## ⚡ Quick Example

```python
import asyncio
from JioSaavn import search

async def main():
    songs = await search("Arijit Singh")

    for s in songs:
        print(s["song"], "-", s["primary_artists"])

asyncio.run(main())
```

---

## 🔍 Search Songs

```python
from JioSaavn import search

songs = await search("Hawa Hawa", limit=5)

print(songs[0])
```

---

## 🎵 Get Song Details

```python
from JioSaavn import get_song

song = await get_song("4ZSL1xJk")

print(song["song"])
print(song["media_url"])
```

---

## 📝 Get Lyrics

```python
from JioSaavn import get_lyrics

lyrics = await get_lyrics("4ZSL1xJk")
print(lyrics)
```

---

## 💿 Get Album

```python
from JioSaavn import get_album

album = await get_album("123456")

print(album["title"])
print(album["songs"])
```

---

## 📻 Get Playlist

```python
from JioSaavn import get_playlist

playlist = await get_playlist("123456")

print(playlist["listname"])
print(len(playlist["songs"]))
```

---

## 📊 Example Response

```json
{
  "id": "4ZSL1xJk",
  "song": "Hawa Hawa",
  "primary_artists": "Mika Singh",
  "album": "Mubarakan",
  "duration": "3:45",
  "views": "12000000",
  "image": "https://...",
  "media_url": "https://..."
}
```

---

## ⚠️ Disclaimer

This is an unofficial API wrapper.  
JioSaavn may change their API anytime.

---

## 🧠 Use Cases

- 🤖 Telegram Music Bots  
- 🎧 Discord Music Bots  
- 💻 CLI Music Tools  
- 📱 Streaming Apps  

---

## 📜 License

MIT License

---

## 👑 Author

Made with ❤️ by **Abhi Singh**
