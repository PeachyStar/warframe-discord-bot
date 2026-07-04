import discord
import os
import asyncio
import aiohttp
import time
from dotenv import load_dotenv

load_dotenv()

BOUNTY_URL = "https://oracle.browse.wf/bounty-cycle"
CRED_HEX_TEXT = "/Lotus/Types/Challenges/Vania/VaniaSafeCracker"

NOTIF_CHANNEL_ID = int(os.getenv('NOTIF_CHANNEL_ID'))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
CRED_HEX_ROLE_ID = int(os.getenv('CRED_HEX_ROLE_ID'))

intents = discord.Intents.default()
client = discord.Client(intents=intents)


async def fetch_bounty_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(BOUNTY_URL) as response:
            response.raise_for_status()
            return await response.json()


async def bounty_monitor():
    await client.wait_until_ready()

    notif_channel = client.get_channel(NOTIF_CHANNEL_ID)
    log_channel = client.get_channel(LOG_CHANNEL_ID)
    last_expiry = 0

    while not client.is_closed():
        try:
            data = await fetch_bounty_data()

            expiry_ms = data["expiry"]
            expiry_seconds = expiry_ms / 1000

            now = time.time()
            sleep_time = max(1, expiry_seconds - now)
            if expiry_ms != last_expiry:
                last_expiry = expiry_ms
                if log_channel:
                    await log_channel.send(
                        f"Current cycle expires: "
                        f"<t:{expiry_seconds:.0f}:R>"
                    )
                if any(CRED_HEX_TEXT in str(value) for value in data.values()):
                    if notif_channel:
                        embed = discord.Embed(
                            title="The credit farming bounty is available!",
                            description=
                            f"The bounty expires: "
                            f"<t:{expiry_seconds:.0f}:R>",
                            color=discord.Color.from_rgb(227, 195, 54))
                        await notif_channel.send(content=f"<@&{CRED_HEX_ROLE_ID}>\n", embed=embed)

            # Sleep until just after refresh
            if log_channel:
                await log_channel.send(
                    f"Waking up "
                    f"<t:{expiry_seconds+5:.0f}:R>"
                )
            await asyncio.sleep(sleep_time + 5)

            if log_channel:
                await log_channel.send("Bounty cycle refreshed.")

        except Exception as e:
            if log_channel:
                await log_channel.send(f"Monitor error: {e}")

            # Retry after a minute if something fails
            await asyncio.sleep(60)


@client.event
async def on_ready():
    print("Bot online!")
    log_channel = client.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(
            f"{client.user} is online!"
        )

    # Start monitor task once
    if not hasattr(client, "monitor_task"):
        client.monitor_task = asyncio.create_task(
            bounty_monitor()
        )


# get bot token from .env and run client
client.run(os.getenv('TOKEN'))
