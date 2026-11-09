#!/usr/bin/env python3

import discord
import requests
import csv
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from discord import app_commands

# =========================
# CONFIG
# =========================
load_dotenv()

TOKEN = os.environ["TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

# Fallback hardcoded server ID; checks environment variable first
GUILD_ID = 00000000000000000000
if "GUILD_ID" in os.environ:
	GUILD_ID = int(os.environ["GUILD_ID"])

COMMAND_PREFIX = "!log" # can also use /commands now
CSV_FILE = "logs.csv"

def write_csv_log(user: str, data: dict):
	file_exists = os.path.isfile(CSV_FILE)

	with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
		writer = csv.writer(f)

		if not file_exists:
			writer.writerow([
				"timestamp",
				"user",
				"substance",
				"dose",
				"route",
				"note"
			])

		writer.writerow([
			datetime.utcnow().isoformat(),
			user,
			data.get("substance", ""),
			data.get("dose", ""),
			data.get("route", ""),
			data.get("note", "")
		])

# =========================
# DISCORD SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True

class MyClient(discord.Client):
	def __init__(self, *, intents: discord.Intents):
		super().__init__(intents=intents)
		self.tree = app_commands.CommandTree(self)

	async def setup_hook(self):
		# IF MORE THAN ONE /LOG COMMAND SHOWS UP UNCOMMENT THE LINE BELOW OTHERWISE IGNORE
		# await self.tree.sync() 
		if GUILD_ID:
			guild = discord.Object(id=GUILD_ID)
			self.tree.copy_global_to(guild=guild)
			await self.tree.sync(guild=guild)
			print(f"local slash commands synced to guild: {GUILD_ID}")

client = MyClient(intents=intents)
tree = client.tree

# =========================
# HELPERS
# =========================
def parse_log(message_content: str) -> dict:
	"""
	Parses messages using regex to handle key=value pairs seamlessly,
	even if notes or inputs contain spaces.
	Example: !log substance=Nicotine dose=~1mg note=vaped cigarette
	"""
	content = message_content[len(COMMAND_PREFIX):].strip()
	
	pattern = r'(\w+)\s*=\s*(.*?)(?=\s*\w+\s*=|\$)'
	matches = re.findall(pattern, content)
	
	data = {}
	for key, value in matches:
		clean_val = value.strip().rstrip(')')
		data[key.lower()] = clean_val
		
	return data


def format_log(user: str, data: dict) -> str:
	loguser = user

	if data.get("user", "") != "":
		loguser = data.get("user", "")

	substance_raw = data.get('substance', '')
	substance_path = substance_raw.replace(' ', '_')
	
	log = f"{loguser}: {data.get('dose', '')} [{substance_raw}](https://anodyne.wiki{substance_path})"

	if data.get("salt", "") != "":
		log += f" [{data.get('salt', '')}]"

	if data.get("route", "") != "":
		log += f" via {data.get('route', '')}"

	if data.get("site", "") != "":
		log += f" at {data.get('site', '')}"

	if data.get("note", "") != "":
		log += f"\n> {data.get('note', '')}"

	return log


def send_to_webhook(content: str):
	try:
		r = requests.post(WEBHOOK_URL, json={"content": content, "flags": 4})
		r.raise_for_status()
	except Exception as e:
		print(f"Webhook error: {e}")


# =========================
# EVENTS
# =========================
@client.event
async def on_ready():
	print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
	if message.author.bot:
		return

	if message.channel.id != CHANNEL_ID:
		return

	if not message.content.startswith(COMMAND_PREFIX):
		return

	try:
		log_data = parse_log(message.content)

		if not log_data or "substance" not in log_data:
			await message.channel.send(
				"⚠️ Invalid format. Missing substance parameter. Example:\n"
				"`!log substance=lsd dose=100ug route=oral`"
			)
			return

		formatted = format_log(message.author.name, log_data)
		write_csv_log(message.author.name, log_data)
		send_to_webhook(formatted)
		
		await message.delete()

	except Exception as e:
		print(f"Error processing text message: {e}")
		await message.channel.send("❌ Failed to process text log line.")


@tree.command(
	name="log",
	description="Record a log entry"
)
async def slash_log(
	interaction: discord.Interaction,
	substance: str,
	dose: str,
	route: str = "",
	salt: str = "",
	site: str = "",
	note: str = "",
	user: str = ""
):
	try:
		if interaction.channel_id != CHANNEL_ID:
			await interaction.response.send_message(
				"❌ Wrong channel.",
				ephemeral=True
			)
			return

		log_data = {
			"substance": substance,
			"dose": dose,
			"route": route,
			"salt": salt,
			"site": site,
			"note": note,
			"user": user
		}

		formatted = format_log(interaction.user.name, log_data)
		write_csv_log(interaction.user.name, log_data)
		send_to_webhook(formatted)

		await interaction.response.send_message(
			"✅ Logged successfully",
			ephemeral=True
		)

	except Exception as e:
		print(f"Slash command execution error: {e}")
		if not interaction.response.is_done():
			await interaction.response.send_message(
				"❌ Failed to process slash log entries.",
				ephemeral=True
			)

# =========================
# RUN
# =========================
if __name__ == "__main__":
	client.run(TOKEN)
