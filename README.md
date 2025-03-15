# GoidArXiv Bot

A Telegram bot that delivers daily updates of arXiv papers based on your topics of interest.

## Features

- **Daily Paper Updates**: Receive notifications about new papers in your selected research areas
- **Topic Management**: Add or remove research topics (e.g., cs.CV, cs.AI)
- **Customizable Schedule**: Set your preferred notification time and timezone
- **Paper Details**: View full abstracts and metadata for any paper
- **User Authorization**: Control who can access your bot

## Setup

### Prerequisites

- Python 3.11+
- Telegram Bot Token

### Installation

#### Using Docker (Recommended)

```bash
# Build the Docker image
docker build -t goidarxiv-bot .

# Run the container
docker run -d --name goidarxiv-bot goidarxiv-bot
```

#### Manual Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/goidarxiv.git
cd goidarxiv
```

2. Install dependencies using uv
```bash
pip install uv
uv sync
```

3. Configure the bot (see Configuration section)

4. Run the bot
```bash
uv run main.py
```

## Configuration

Create a `config.json` file with the following structure:

```json
{
  "token": "YOUR_TELEGRAM_BOT_TOKEN",
  "authorized_users": [123456789],
  "topics": ["cs.CV", "cs.AI"],
  "notification_time": "09:00",
  "timezone": "UTC"
}
```

- `token`: Your Telegram bot token (get it from [@BotFather](https://t.me/botfather))
- `authorized_users`: List of Telegram user IDs allowed to use the bot
- `topics`: List of arXiv categories to monitor
- `notification_time`: Daily notification time (24-hour format)
- `timezone`: Your timezone (e.g., "UTC", "US/Eastern", "Europe/London")

## Usage

### Bot Commands

- `/start` - Start the bot
- `/help` - Show available commands
- `/topics` - Show current topics
- `/add_topic <topic>` - Add a new topic (e.g., cs.CV, cs.AI)
- `/remove_topic <topic>` - Remove a topic
- `/set_time HH:MM` - Set notification time (24h format)
- `/set_timezone <timezone>` - Set timezone
- `/today` - Get today's papers now
- `/abstract <paper_id>` - Show full abstract of a paper by its arXiv ID
- `/authorize <user_id>` - Authorize a new user (admin only)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
