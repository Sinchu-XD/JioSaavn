import asyncio

from JioSaavn import search, get_lyrics
from JioSaavn.Core.Client import JioSaavnClient


async def main():
    query = input("Enter song name: ")

    async with JioSaavnClient() as client:
        results = await search(query, limit=5, client=client)

        if not results:
            print("\nNo results found")
            return

        print(f"\nFound {len(results)} songs:\n")

        for i, song in enumerate(results, 1):
            print(f"{i}. {song.get('song')} - {song.get('primary_artists')}")

        try:
            choice = int(input("\nSelect song number for lyrics: "))
            selected = results[choice - 1]
        except:
            print("Invalid selection")
            return

        song_id = selected.get("id")

        if not song_id:
            print("Song ID not found")
            return

        print("\nFetching lyrics...\n")

        lyrics = await get_lyrics(song_id, client=client)

        if lyrics:
            print(lyrics[:500])
            print("\n... (truncated)")
        else:
            print("No lyrics available")


if __name__ == "__main__":
    asyncio.run(main())
