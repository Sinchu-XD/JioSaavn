import asyncio

from JioSaavn import search
from JioSaavn.Core.Client import JioSaavnClient


async def main():
    query = input("Enter song name: ")

    async with JioSaavnClient() as client:
        results = await search(query, limit=10, client=client)

    if not results:
        print("\nNo results found")
        return

    print(f"\nFound {len(results)} results:\n")

    for i, song in enumerate(results, 1):
        print(f"{i}. {song.get('song')}")
        print(f"   Artist: {song.get('primary_artists')}")
        print(f"   Album: {song.get('album')}")
        print(f"   URL: {song.get('media_url')}")
        print(f"   Image: {song.get('image')}")
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
