import discord
import os
import asyncio
import aiohttp
import time
from dotenv import load_dotenv

load_dotenv()

BOUNTY_URL = "https://oracle.browse.wf/bounty-cycle"
WORLD_STATE_URL = "https://oracle.browse.wf/worldState.min.json"
CRED_HEX_TEXT = "/Lotus/Types/Challenges/Vania/VaniaSafeCracker"

NOTIF_CHANNEL_ID = int(os.getenv('NOTIF_CHANNEL_ID'))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
CRED_HEX_ROLE_ID = int(os.getenv('CRED_HEX_ROLE_ID'))
VOID_CASCADE_ROLE_ID = int(os.getenv('VOID_CASCADE_ROLE_ID'))

intents = discord.Intents.default()
client = discord.Client(intents=intents)


def get_omnia_info(ws_data):
    now_ms = int(time.time() * 1000)

    has_void_cascade = False
    earliest_expiry = None
    cascade_id = None
    cascade_expiry = None

    for mission in ws_data.get("ActiveMissions", []):
        if mission.get("Modifier") != "VoidT6":
            continue

        if mission.get("Hard") is not True:
            continue

        expiry_ms = int(mission["Expiry"]["$date"]["$numberLong"])

        if expiry_ms <= now_ms:
            continue

        if mission.get("MissionType") == "MT_VOID_CASCADE":
            print("void cascade")
            has_void_cascade = True
            cascade_id = mission["_id"]["$oid"]
            cascade_expiry = expiry_ms

        if earliest_expiry is None or expiry_ms < earliest_expiry:
            earliest_expiry = expiry_ms

    return has_void_cascade, earliest_expiry, cascade_id, cascade_expiry


async def fetch_bounty_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(BOUNTY_URL) as response:
            response.raise_for_status()
            return await response.json()


async def fetch_ws_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(WORLD_STATE_URL) as response:
            response.raise_for_status()
            return await response.json()


async def monitor():
    await client.wait_until_ready()

    notif_channel = client.get_channel(NOTIF_CHANNEL_ID)
    log_channel = client.get_channel(LOG_CHANNEL_ID)

    last_bounty_notified = None
    last_void_cascade_id_notified = None

    while not client.is_closed():
        try:
            # Fetch data
            bounty_data = await fetch_bounty_data()
            ws_data = await fetch_ws_data()

            # Process Steel Path Omnia missions
            has_void_cascade, earliest_voidt6_expiry_ms, cascade_id, cascade_expiry = get_omnia_info(ws_data)
            if earliest_voidt6_expiry_ms is not None and log_channel:
                await log_channel.send(f"Next SP Omnia mission expiry: <t:{earliest_voidt6_expiry_ms / 1000:.0f}:R>")

            if has_void_cascade and log_channel:
                await log_channel.send("There is a Steel Path void cascade!")

            if (
                    has_void_cascade
                    and cascade_id != last_void_cascade_id_notified
                    and notif_channel
            ):
                last_void_cascade_id_notified = cascade_id

                embed = discord.Embed(
                    title="There is a Steel Path void cascade!",
                    description=f"The rift expires: <t:{cascade_expiry / 1000:.0f}:R>",
                    color=discord.Color.from_rgb(227, 195, 54),
                )

                await notif_channel.send(
                    content=f"<@&{VOID_CASCADE_ROLE_ID}>",
                    embed=embed,
                )

            # Process bounty cycle
            bounty_expiry_ms = bounty_data["expiry"]

            if log_channel:
                await log_channel.send(f"Current bounty cycle expires: <t:{bounty_expiry_ms / 1000:.0f}:R>")

            has_credit_bounty = any(
                CRED_HEX_TEXT in str(value)
                for value in bounty_data.values()
            )

            if (
                    has_credit_bounty
                    and bounty_expiry_ms != last_bounty_notified
                    and notif_channel
            ):
                last_bounty_notified = bounty_expiry_ms

                embed = discord.Embed(
                    title="The credit farming bounty is available!",
                    description=f"The bounty expires: <t:{bounty_expiry_ms / 1000:.0f}:R>",
                    color=discord.Color.from_rgb(227, 195, 54),
                )

                await notif_channel.send(
                    content=f"<@&{CRED_HEX_ROLE_ID}>",
                    embed=embed,
                )

            # Determine next wake-up time
            next_expiry_ms = min(
                bounty_expiry_ms,
                earliest_voidt6_expiry_ms or float("inf")
            )

            sleep_time = (
                    max(1, next_expiry_ms / 1000 - time.time())
                    + 5
            )

            if log_channel:
                await log_channel.send(
                    f"Waking up in {sleep_time:.0f} seconds"
                )

            # Sleep until next refresh
            await asyncio.sleep(sleep_time)

            if log_channel:
                await log_channel.send("Cycle refreshed.")

        except Exception as e:
            if log_channel:
                await log_channel.send(f"Monitor error: {e}")

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
            monitor()
        )


# get bot token from .env and run client
client.run(os.getenv('TOKEN'))
