import discord
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'{client.user} is now online!')


# get bot token from .env and run client
client.run(os.getenv('TOKEN'))
