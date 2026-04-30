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

## Start bot
To start the bot, navtiagte via `cd src` and  run bot via ` nohup python kleinanzeigen_bot.py > bot.log 2>&1 &`.
This will load the environment variables and start the bot in the background.
