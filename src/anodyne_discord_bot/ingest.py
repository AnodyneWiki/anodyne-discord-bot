#!/usr/bin/env python3

import csv
from datetime import datetime
import os
import discord
from dotenv import load_dotenv
import requests

# =========================
# CONFIG
# =========================
load_dotenv()

TOKEN = os.environ.get("TOKEN", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))

COMMAND_PREFIX = "!log"
CSV_FILE = "logs.csv"


def write_csv_log(user: str, data: dict):
	file_exists = os.path.isfile(CSV_FILE)

	with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
		writer = csv.writer(f)

		# write header only once
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

client = discord.Client(intents=intents)


# =========================
# HELPERS
# =========================
def parse_log(message_content: str) -> dict:
	"""
	Parses messages like:
	!log substance=lsd dose=100ug route=oral note=first_try
	"""
	parts = message_content.strip().split()
	data = {}

	for part in parts[1:]:
		if "=" in part:
			key, value = part.split("=", 1)
			data[key.lower()] = value

	return data


def format_log(user: str, data: dict) -> str:
	#timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

	loguser = user
	if data.get('user', '') != '':
		loguser = data.get('user', '')

	log = f"{loguser}: {data.get('dose', '')} [{data.get('substance', '')}](https://anodyne.wiki/substance/{data.get('substance', '').replace(' ', '_')})"
	if data.get('salt', '') != '':
		log += f" [{data.get('salt', '')}]"

	if data.get('route', '') != '':
		log += f" via {data.get('route', '')}"
	if data.get('site', '') != '':
		log += f" at {data.get('site', '')}"

	if data.get('note', '') != '':
		log += f"\n> {data.get('note', '')}"

	return (
		log
	)


def send_to_webhook(content: str):
	try:
		requests.post(WEBHOOK_URL, json={"content": content, "flags": 4})
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
	# Ignore bots
	if message.author.bot:
		return

	# Only listen in target channel
	if message.channel.id != CHANNEL_ID:
		return

	# Only process !log commands
	if not message.content.startswith(COMMAND_PREFIX):
		return

	try:
		log_data = parse_log(message.content)

		if not log_data:
			await message.channel.send(
				"⚠️ Invalid format. Example:\n"
				"`!log substance=lsd dose=100ug route=oral note=first_try`"
			)
			return

		formatted = format_log(message.author.name, log_data)

		write_csv_log(message.author.name, log_data)
		# Send to webhook
		send_to_webhook(formatted)

		# Optional: confirm in Discord
		#await message.add_reaction("✅")
		await message.delete()

	except Exception as e:
		print(f"Error: {e}")
		await message.channel.send("❌ Failed to process log.")


# =========================
# RUN
# =========================
def main():
	client.run(TOKEN)


if __name__ == "__main__":
	main()
