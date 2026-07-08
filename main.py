# main.py
import asyncio
from modules.bot import DraughtsBot

if __name__ == "__main__":
    bot = DraughtsBot()
    asyncio.run(bot.run())