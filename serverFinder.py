import os
from pathlib import Path
import discord
from discord import app_commands
import json
import re
import asyncio
import pyperclip

TOKEN = ""
BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "servers.json"

# Bot setup
class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("Commands synced.")

client = MyClient()

# JSON file handling
def load_servers():
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_servers(servers):
    try:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(servers, f, indent=4, ensure_ascii=False)
        print(f"Saved {len(servers)} servers to {JSON_PATH}")
    except Exception as e:
        print(f"Failed to save: {e}")

# Processing data
def get_wave_number(game_mode_info):
    match = re.search(r"(\d+)[a-z]{2}\sWave", game_mode_info)
    if match: return int(match.group(1))
    match = re.search(r"(\d+)\sWaves", game_mode_info)
    return int(match.group(1)) if match else 0

def convert_to_discord_flag(region):
    flags = {
        "🇦🇺": ":flag_au:", "🇧🇷": ":flag_br:", "🇩🇪": ":flag_de:", "🇫🇷": ":flag_fr:",
        "🇬🇧": ":flag_gb:", "🇭🇰": ":flag_hk:", "🇮🇳": ":flag_in:", "🇯🇵": ":flag_jp:",
        "🇳🇱": ":flag_nl:", "🇵🇱": ":flag_pl:", "🇸🇬": ":flag_sg:", "🇺🇸": ":flag_us:",
    }
    return flags.get(region, region)

def process_copied_data(data):
    servers = []
    current = {}
    for line in data.strip().split("\n"):
        if line.strip() == "---":
            if current:
                servers.append(current)
                current = {}
        elif ": " in line:
            key, value = line.split(": ", 1)
            current[key] = value
    if current:
        servers.append(current)
    return servers

# Discord commands
REGION_CHOICES = [
    app_commands.Choice(name="Australia", value="Australia"),
    app_commands.Choice(name="Brazil", value="Brazil"),
    app_commands.Choice(name="France", value="France"),
    app_commands.Choice(name="Germany", value="Germany"),
    app_commands.Choice(name="Hong Kong", value="Hong Kong"),
    app_commands.Choice(name="India", value="India"),
    app_commands.Choice(name="Japan", value="Japan"),
    app_commands.Choice(name="Poland", value="Poland"),
    app_commands.Choice(name="Singapore", value="Singapore"),
    app_commands.Choice(name="The Netherlands", value="The Netherlands"),
    app_commands.Choice(name="United Kingdom", value="United Kingdom"),
    app_commands.Choice(name="US Central", value="US Central"),
    app_commands.Choice(name="US East", value="US East"),
    app_commands.Choice(name="US West", value="US West"),
]

MAP_CHOICES = [
    app_commands.Choice(name="Foggy Field", value="Foggy Field"),
    app_commands.Choice(name="Hougoumont", value="Hougoumont"),
    app_commands.Choice(name="La ferme d'En-Haut", value="La ferme d'En-Haut"),
    app_commands.Choice(name="La Haye Sainte", value="La Haye Sainte"),
    app_commands.Choice(name="Tyrolean Village", value="Tyrolean Village"),
]

@client.tree.command(name="findserver", description="Find top endless servers")
@app_commands.describe(region="Optional region filter", map="Optional map filter")
@app_commands.choices(region=REGION_CHOICES, map=MAP_CHOICES)
async def findserver(
    interaction: discord.Interaction,
    region: app_commands.Choice[str] = None,
    map: app_commands.Choice[str] = None,
):
    servers = load_servers()
    endless = [s for s in servers if "Endless" in s.get("GameModeInfo", "")]

    if region:
        region_value = region.value.casefold()
        endless = [
            s for s in endless
            if region_value in s.get("Region", "").casefold()
            or region_value in s.get("ServerInfo", "").casefold()
        ]

    if map:
        map_value = map.value.casefold()
        endless = [
            s for s in endless
            if map_value == s.get("MapInfo", "").casefold()
    ]

    endless.sort(key=lambda s: get_wave_number(s.get("GameModeInfo", "")), reverse=True)

    top = []
    seen = set()
    for s in endless:
        if len(top) >= 5:
            break
        job_id = s.get("JobId")
        if job_id in seen:
            continue
        top.append(s)
        seen.add(job_id)

    if not top:
        await interaction.response.send_message("No servers found matching your filter.", ephemeral=True)
        return

    lines = []
    for i, s in enumerate(top, 1):
        job = s.get("JobId", "Unknown")
        info = s.get("ServerInfo", "Unknown")
        map_ = s.get("MapInfo", "Unknown")
        wave = get_wave_number(s.get("GameModeInfo", ""))
        players = re.search(r"(\d+)/(\d+)", info)
        count = players.group(0) if players else "?"
        region_flag = convert_to_discord_flag(s.get("Region", ""))
        loc_match = re.match(r"([A-Za-z ]+)\s*\|", info)
        loc = loc_match.group(1).strip() if loc_match else "?"
        wave_text = f"w{wave}" if wave > 0 else "w?"
        lines.append(f"{i}. {job} | {count} | {wave_text} | {map_} | {region_flag} | {loc}")

    await interaction.response.send_message("**Top Endless Servers:**\n" + "\n".join(lines))

# Copying data
async def auto_process_loop():
    while True:
        for remaining in range(120, 0, -10):
            print(f"{remaining} seconds left")
            await asyncio.sleep(10)

        clipboard_data = pyperclip.paste().strip()
        if clipboard_data:
            processed_data = process_copied_data(clipboard_data)
            if processed_data:
                save_servers(processed_data)
                print("Data processed and saved.")
            else:
                print("Data was not in the expected format.")
        else:
            print("No data.")

# Update status
async def status_loop():
    statuses = [discord.Status.online, discord.Status.idle, discord.Status.dnd]
    current_status_index = 0
    status_update_interval = 120
    last_status_update = 0
    
    while True:
        servers = load_servers()
        endless = [s for s in servers if "Endless" in s.get("GameModeInfo", "")]
        endless.sort(key=lambda s: get_wave_number(s.get("GameModeInfo", "")), reverse=True)

        if endless:
            top = endless[0]
            wave = get_wave_number(top.get("GameModeInfo", ""))
            job_id = top.get("JobId", "Unknown")
            map_ = top.get("MapInfo", "Unknown")
            server_info = top.get("ServerInfo", "")
            region = server_info.split("|")[0].strip() if "|" in server_info else server_info.strip()

            presence_str = f"Wave {wave} {job_id} | {map_} | {region}"

            await client.change_presence(
                status=statuses[current_status_index],
                activity=discord.Game(name=presence_str)
            )

            current_time = asyncio.get_event_loop().time()
            if current_time - last_status_update >= status_update_interval:
                print(f"Status updated: {presence_str} | Status: {statuses[current_status_index]}")
                last_status_update = current_time

        current_status_index = (current_status_index + 1) % len(statuses)

        await asyncio.sleep(1)

# Bot startup
@client.event
async def on_ready():
    print(f"Logged in as {client.user} ({client.user.id})")
    asyncio.create_task(auto_process_loop())
    asyncio.create_task(status_loop())

if __name__ == "__main__":
    client.run(TOKEN)
