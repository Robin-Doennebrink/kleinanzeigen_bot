# Kleinanzeigenbot
This bot queries the kleinanzeigen API frequently to find new ads for your search queries.
If he finds a new ad, he will send you a message to your telegram chat.

## Set-up
Create an environment file  `environment.env` and add your telegram bot token, chat id and search queries.

```env
# Telegram bot credentials
TELEGRAM_TOKEN=yourbot token
CHAT_ID=42
SEARCH_QUERIES=["https://www.kleinanzeigen.de/s-44139/zentrierst%C3%A4nder/k0l1112r100"]
```

## Start the Bot

Navigate to the `src` directory:

```bash
cd src
```

Start the bot in the background using `nohup`:

```bash
nohup python kleinanzeigen_bot.py > /dev/null 2> nohup.err &
```

This command:
- Runs the bot in the background, allowing it to continue running after the terminal session is closed.
- Automatically loads environment variables from `environment.env`.
- Writes application logs to `bot.log` using Python's logging configuration.
- Redirects unexpected stderr output to `nohup.err` while discarding stdout.

### Monitor the Bot

Check whether the bot is running:

```bash
pgrep -af kleinanzeigen_bot.py
```

Monitor application logs in real time:

```bash
tail -F bot.log
```

### Stop the Bot

Find the process ID (PID) using `pgrep`, then stop it gracefully:

```bash
kill <PID>
```

**Note:** The bot requires a valid `environment.env` file in the working directory. Ensure it is configured before starting the bot.
