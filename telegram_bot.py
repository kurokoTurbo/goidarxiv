import logging
import os
import json
import pytz                                
from datetime import datetime, time, timedelta
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext, ContextTypes, MessageHandler, filters

from arxiv_api import fetch_arxiv_papers
from helpers import escape_html, chunk_html_message, paper_id_with_dot, format_papers

def authorized_only(func):
    """Decorator to check if user is authorized to use the bot."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config['authorized_users']:
            await update.message.reply_text('You are not authorized to use this bot.')
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration file
CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from JSON file"""
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "authorized_users": [],
            "topics": ["cs.CV", "cs.AI"],
            "notification_time": "09:00",
            "timezone": "UTC"
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Load configuration
config = load_config()

# Check if there's a token in the config that needs to be migrated
if 'token' in config:
    if not os.environ.get('TELEGRAM_BOT_TOKEN'):
        logger.warning("Token found in config.json. Please set it as TELEGRAM_BOT_TOKEN environment variable instead.")
        logger.warning(f"You can set it with: export TELEGRAM_BOT_TOKEN='{config['token']}'")
    # Remove token from config
    #del config['token']
    #save_config(config)

# Command handlers
@authorized_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'Hi! I am your ArXiv Paper Bot. I will send you daily updates of papers on your topics of interest.\n\n'
        'Use /help to see available commands.'
    )

@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        'Available commands:\n\n'
        '/topics - Show current topics\n'
        '/add_topic <topic> - Add a new topic (e.g., cs.CV, cs.AI)\n'
        '/remove_topic <topic> - Remove a topic\n'
        '/set_time HH:MM - Set notification time (24h format)\n'
        '/set_timezone <timezone> - Set timezone (e.g., UTC, US/Eastern)\n'
        '/today - Get today\'s papers now\n'
        '/abstract <paper_id> - Show full abstract of a paper by its arXiv ID\n'
        '/authorize <user_id> - Authorize a new user (admin only)\n'
        '/help - Show this help message'
    )

@authorized_only
async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current topics."""
    topics_text = "Current topics:\n\n" + "\n".join([f"- {topic}" for topic in config['topics']])
    await update.message.reply_text(topics_text)

@authorized_only
async def add_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new topic."""
    if not context.args:
        await update.message.reply_text('Please provide a topic to add (e.g., cs.CV).')
        return
    
    topic = context.args[0]
    if topic in config['topics']:
        await update.message.reply_text(f'Topic "{topic}" already exists.')
        return
    
    config['topics'].append(topic)
    save_config(config)
    await update.message.reply_text(f'Added topic: {topic}')

@authorized_only
async def remove_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a topic."""
    if not context.args:
        await update.message.reply_text('Please provide a topic to remove.')
        return
    
    topic = context.args[0]
    if topic not in config['topics']:
        await update.message.reply_text(f'Topic "{topic}" does not exist.')
        return
    
    config['topics'].remove(topic)
    save_config(config)
    await update.message.reply_text(f'Removed topic: {topic}')

@authorized_only
async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set notification time."""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text('Please provide time in HH:MM format.')
        return
    
    time_str = context.args[0]
    try:
        # Validate time format
        datetime.strptime(time_str, '%H:%M')
        config['notification_time'] = time_str
        save_config(config)
        await update.message.reply_text(f'Notification time set to {time_str}')
    except ValueError:
        await update.message.reply_text('Invalid time format. Please use HH:MM (24h format).')

@authorized_only
async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set timezone."""
    if not context.args:
        await update.message.reply_text('Please provide a timezone (e.g., UTC, US/Eastern).')
        return
    
    timezone = ' '.join(context.args)
    try:
        pytz.timezone(timezone)
        config['timezone'] = timezone
        save_config(config)
        await update.message.reply_text(f'Timezone set to {timezone}')
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text(f'Unknown timezone: {timezone}. Please provide a valid timezone.')

@authorized_only
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get today's papers."""
    await update.message.reply_text('Searching for today\'s papers, please wait...')
    
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    try:
        papers = fetch_arxiv_papers(config['topics'], yesterday, now)
    except Exception as e:
        logger.error(f"Error fetching papers: {e}")
        await update.message.reply_text(f"An error occurred: {str(e)}")
        return
    
    if not papers:
        await update.message.reply_text("No papers found today for your topics.")
        return

    message = format_papers(papers)

    # Split message if it's too long
    if len(message) <= 4096:
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        # Use the smart chunking function
        chunks = chunk_html_message(message)
        for chunk in chunks:
            try:
                await update.message.reply_text(chunk, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Error sending message chunk: {e}")
                # Try sending without HTML parsing as fallback
                try:
                    await update.message.reply_text(
                        f"Could not send formatted message due to an error. Here's the plain text:\n\n{chunk}",
                        parse_mode=None)
                except Exception as inner_e:
                    logger.error(f"Failed to send even plain text message: {inner_e}")

@authorized_only
async def authorize_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Authorize a new user (admin only)."""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text('Please provide a user ID to authorize.')
        return
    
    try:
        new_user_id = int(context.args[0])
        if new_user_id in config['authorized_users']:
            await update.message.reply_text(f'User {new_user_id} is already authorized.')
            return
        
        config['authorized_users'].append(str(new_user_id))
        save_config(config)
        await update.message.reply_text(f'User {new_user_id} has been authorized.')
    except ValueError:
        await update.message.reply_text('Invalid user ID. Please provide a numeric ID.')

@authorized_only
async def paper_abstract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get full abstract of a paper by its arXiv ID."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text('Please provide an arXiv paper ID (e.g., /abstract 2101.12345)')
        return
    
    paper_id = paper_id_with_dot(context.args[0])
    await update.message.reply_text(f'Searching for paper with ID: {paper_id}...')
    
    try:
        from arxiv_api import fetch_paper_by_id
        paper = fetch_paper_by_id(paper_id)
        
        if not paper:
            await update.message.reply_text(f'No paper found with ID: {paper_id}')
            return
        
        # Format the paper details
        title = escape_html(paper['title'])
        authors = ', '.join([escape_html(author) for author in paper['authors']])
        abstract = escape_html(paper['abstract'])
        categories = ', '.join(paper['categories']) if 'categories' in paper else 'N/A'
        published = paper['published']
        link = paper['link']
        
        message = (
            f"📄 <b>{title}</b>\n\n"
            f"👥 <b>Authors:</b> {authors}\n\n"
            f"📅 <b>Published:</b> {published}\n"
            f"🏷️ <b>Categories:</b> {categories}\n"
            f"🔗 <a href=\"{link}\">PDF Link</a>\n\n"
            f"📝 <b>Abstract:</b>\n{abstract}"
        )
        
        # Split message if it's too long
        if len(message) <= 4096:
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            chunks = chunk_html_message(message)
            for chunk in chunks:
                try:
                    await update.message.reply_text(chunk, parse_mode='HTML')
                except Exception as e:
                    logger.error(f"Error sending message chunk: {e}")
                    await update.message.reply_text(f"Error formatting message. Here's the plain text portion:\n\n{chunk[:3000]}")
    
    except Exception as e:
        logger.error(f"Error fetching paper with ID {paper_id}: {e}")
        await update.message.reply_text(f"An error occurred while fetching the paper: {str(e)}")


@authorized_only
async def abstract_no_space(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /abstractXXXXX commands where the ID is attached to the command."""
    # Extract paper ID from the command text
    command_text = update.message.text
    # Skip '/abstract' part and get the remaining text as paper_id
    paper_id = paper_id_with_dot(command_text[9:].strip())
    
    if not paper_id:
        await update.message.reply_text('Please provide an arXiv paper ID (e.g., /abstract 2101.12345)')
        return
    
    await update.message.reply_text(f'Searching for paper with ID: {paper_id}...')
    
    try:
        from arxiv_api import fetch_paper_by_id
        paper = fetch_paper_by_id(paper_id)
        
        if not paper:
            await update.message.reply_text(f'No paper found with ID: {paper_id}')
            return
        
        # Format the paper details
        title = escape_html(paper['title'])
        authors = ', '.join([escape_html(author) for author in paper['authors']])
        abstract = escape_html(paper['abstract'])
        categories = ', '.join(paper['categories']) if 'categories' in paper else 'N/A'
        published = paper['published']
        link = paper['link']
        
        message = (
            f"📄 <b>{title}</b>\n\n"
            f"👥 <b>Authors:</b> {authors}\n\n"
            f"📅 <b>Published:</b> {published}\n"
            f"🏷️ <b>Categories:</b> {categories}\n"
            f"🔗 <a href=\"{link}\">PDF Link</a>\n\n"
            f"📝 <b>Abstract:</b>\n{abstract}"
        )
        
        # Split message if it's too long
        if len(message) <= 4096:
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            chunks = chunk_html_message(message)
            for chunk in chunks:
                try:
                    await update.message.reply_text(chunk, parse_mode='HTML')
                except Exception as e:
                    logger.error(f"Error sending message chunk: {e}")
                    await update.message.reply_text(f"Error formatting message. Here's the plain text portion:\n\n{chunk[:3000]}")
    
    except Exception as e:
        logger.error(f"Error fetching paper with ID {paper_id}: {e}")
        await update.message.reply_text(f"An error occurred while fetching the paper: {str(e)}")


async def send_daily_papers(context: CallbackContext) -> None:
    """Send daily papers to all authorized users."""
    # Fetch all papers for all topics in one go
    now = datetime.now()
    yesterday = now - timedelta(days=1)

    try:
        papers = fetch_arxiv_papers(config['topics'], yesterday, now)
    except Exception as e:
        logger.error(f"Error fetching papers: {e}")
        message = f"An error occurred: {str(e)}"
        for user_id in config['authorized_users']:
            await send_message_to_user(context.bot, message, user_id)
        return 

    if not papers:
        message = "No papers found today for your topics."
        for user_id in config['authorized_users']:
            await send_message_to_user(context.bot, message, user_id)
        return

    message = format_papers(papers)   
    # Send to all authorized users
    for user_id in config['authorized_users']:
        await send_message_to_user(context.bot, message, user_id)

async def send_message_to_user(bot: Bot, message: str, user_id: str):
    try:
        if len(message) <= 4096:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
        else:
            # Use the smart chunking function
            chunks = chunk_html_message(message)
            for chunk in chunks:
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=chunk,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Error sending message chunk: {e}")
                    # Try sending without HTML parsing as fallback
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=f"Could not send formatted message due to an error. Here's the plain text:\n\n{chunk}",
                            parse_mode=None
                        )
                    except Exception as inner_e:
                        logger.error(f"Failed to send even plain text message: {inner_e}")
    except Exception as e:
        logger.error(f"Error sending message to user {user_id}: {e}")


def run_bot():
    """Run the bot."""
    # Get token from environment variable
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("No token provided. Please set the TELEGRAM_BOT_TOKEN environment variable.")
    
    # Create the Application with job_queue explicitly enabled
    application = Application.builder().token(config['token']).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("topics", topics_command))
    application.add_handler(CommandHandler("add_topic", add_topic))
    application.add_handler(CommandHandler("remove_topic", remove_topic))
    application.add_handler(CommandHandler("set_time", set_time))
    application.add_handler(CommandHandler("set_timezone", set_timezone))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("abstract", paper_abstract))
    application.add_handler(CommandHandler("authorize", authorize_user))
    application.add_handler(MessageHandler(filters.Regex(r'^/abstract[0-9v\.]+'), abstract_no_space))
    
    # Set up job queue for daily notifications
    job_queue = application.job_queue
    
    # Parse notification time
    hour, minute = map(int, config['notification_time'].split(':'))
    tz = pytz.timezone(config['timezone'])
    
    # Schedule daily paper updates
    job_queue.run_daily(
        send_daily_papers,
        time=time(hour=hour, minute=minute),
    )

    
    # Start the Bot
    application.run_polling()
    
    logger.info("Bot started!")
