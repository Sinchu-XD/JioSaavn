import asyncio

from JioSaavn import search
from JioSaavn.Core.Client import JioSaavnClient


async def main():
    query = input("Enter song name: ")

    async with JioSaavnClient() as client:
        results = await search(query, limit=10, client=client)

    if not results:
        print("\n❌ No results found")
        return

    print(f"\n🎧 Found {len(results)} songs:\n")

    for i, song in enumerate(results, 1):
        print(f"{i}. {song.get('song')}")

        print(f"   🎤 Artist   : {song.get('primary_artists')}")
        print(f"   💿 Album    : {song.get('album')}")
        print(f"   ⏱️ Duration : {song.get('duration')}")
        print(f"   👁️ Views    : {song.get('views')}")
        print(f"   🔗 Stream   : {song.get('media_url')}")
        print(f"   🖼️ Image    : {song.get('image')}")

        print("-" * 50)

    
    try:
        choice = int(input("\nSelect song number to play URL: "))
        selected = results[choice - 1]

        print("\n🎵 Selected Song:")
        print(f"Title  : {selected.get('song')}")
        print(f"Stream : {selected.get('media_url')}")

    except:
        print("\n Invalid selection")


if __name__ == "__main__":
    asyncio.run(main())
