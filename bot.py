import os
import asyncio
import datetime as dt
from typing import Dict, List
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

from services.openstates import recent_bills_for_state

# -------- env --------
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
if not DISCORD_BOT_TOKEN:
    raise SystemExit("Missing DISCORD_BOT_TOKEN in environment (.env)")

# -------- bot setup --------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"✅ Logged in as {bot.user} (id={bot.user.id})")
    except Exception as e:
        print("Slash command sync error:", e)

# -------- state mapping --------
ABBR_TO_NAME = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut",
    "DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa",
    "KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan",
    "MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire",
    "NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
    "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee",
    "TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
    "DC":"District of Columbia"
}

def normalize_state(code: str) -> str:
    return ABBR_TO_NAME.get((code or "").strip().upper(), "")

# -------- simple per-user rate limit --------
_RATE_LIMIT = dt.timedelta(seconds=3)
_last_call: Dict[int, dt.datetime] = {}

def limited(user_id: int) -> bool:
    now = dt.datetime.utcnow()
    last = _last_call.get(user_id)
    if last and (now - last) < _RATE_LIMIT:
        return True
    _last_call[user_id] = now
    return False

# -------- slash commands --------
@bot.tree.command(
    name="bills",
    description="Show recent state bills by 2-letter code (e.g., WA, TX, NY)."
)
@app_commands.describe(
    state="Two-letter state code (e.g., WA, CA, TX)",
    limit="How many bills to show (1-20, default 10)"
)
async def bills(inter: discord.Interaction, state: str, limit: int = 10):
    if limited(inter.user.id):
        await inter.response.send_message("⏳ Easy there — try again in a moment.", ephemeral=True)
        return

    state_full = normalize_state(state)
    if not state_full:
        await inter.response.send_message(
            "Please provide a valid 2-letter state code (e.g., **WA**, **CA**, **TX**).",
            ephemeral=True
        )
        return

    limit = max(1, min(limit, 20))
    await inter.response.defer(thinking=True)

    try:
        data: List[dict] = await asyncio.to_thread(
            recent_bills_for_state, state_full, 14, limit
        )
    except Exception as e:
        await inter.edit_original_response(content=f"⚠️ Error fetching bills for **{state_full}**:\n`{e}`")
        return

    if not data:
        await inter.edit_original_response(content=f"No recent bills found for **{state_full}** in the last 14 days.")
        return

    embed = discord.Embed(
        title=f"Recent Bills in {state_full}",
        description=f"Source: OpenStates • showing {len(data)}",
        color=0x4F46E5
    )

    for b in data:
        name = b.get("identifier") or "Bill"
        parts = []
        if b.get("title"):
            parts.append(b["title"])
        la = b.get("status") or b.get("latest_action")
        lad = b.get("latest_action_date")
        if la:
            parts.append(f"*Last action:* {la}" + (f" ({lad})" if lad else ""))
        if b.get("link"):
            parts.append(f"[OpenStates link]({b['link']})")
        value = "\n".join(parts)[:1024]
        embed.add_field(name=name, value=value, inline=False)

    embed.set_footer(text="Try: /bills WA")
    await inter.edit_original_response(embed=embed)

@bot.tree.command(name="help_civics", description="What can I ask this bot?")
async def help_civics(inter: discord.Interaction):
    embed = discord.Embed(
        title="Civics Bot — Commands",
        color=0x14B8A6,
        description=(
            "Privacy-first: **state codes only** (no addresses).\n\n"
            "**/bills <STATE> [limit]** — recent bills for a state\n"
            "Examples: `/bills WA`, `/bills TX 5`"
        ),
    )
    await inter.response.send_message(embed=embed, ephemeral=True)

# -------- run --------
if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
