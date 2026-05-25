#!/usr/bin/env python3
import discord
from discord.ext import commands
import os
import sys

print("Starting bot...", flush=True)

BOT_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

if not BOT_TOKEN:
    print("ERROR: DISCORD_TOKEN not set", file=sys.stderr, flush=True)
    sys.exit(1)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}", flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands", flush=True)
    except Exception as e:
        print(f"Error syncing: {e}", flush=True)

@bot.tree.command(name="ping", description="Pong!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)

if __name__ == "__main__":
    try:
        print("Connecting to Discord...", flush=True)
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
