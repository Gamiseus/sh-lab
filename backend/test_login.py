import steam
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

client = steam.Client()

@client.event
async def on_ready():
    print("EVENT: on_ready triggered!")

async def main():
    print("Calling login()...")
    try:
        await client.login()
        print("Login returned.")
    except Exception as e:
        print(f"Login failed: {e}")
    
    print("Waiting 10s...")
    await asyncio.sleep(10)
    print("Closing...")
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
