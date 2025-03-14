import logging
import os
from datetime import datetime, time, timedelta
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, ContextTypes, MessageHandler, filters
import json
from arxiv_api import fetch_arxiv_papers

def escape_html(text):
    """Escape HTML special characters
    
    Args:
        text: Text to escape
    """
    if not text:
        return ""
    
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def chunk_html_message(message, max_length=4000):
    """Split a long HTML message into chunks without breaking HTML tags.
    
    Args:
        message (str): The HTML message to split
        max_length (int): Maximum length of each chunk
        
    Returns:
        list: List of message chunks
    """
    if len(message) <= max_length:
        return [message]
    
    chunks = []
    current_chunk = ""
    
    # Simple approach: split on double newlines to keep paragraphs together
    paragraphs = message.split("\n\n")
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit, start a new chunk
        if len(current_chunk) + len(paragraph) + 2 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                # If a single paragraph is too long, we need to split it
                if len(paragraph) > max_length:
                    # Try to split at a safe position like a space
                    safe_length = max_length
                    while safe_length > 0 and paragraph[safe_length-1] != ' ':
                        safe_length -= 1
                    
                    if safe_length > 0:
                        chunks.append(paragraph[:safe_length])
                        current_chunk = paragraph[safe_length:]
                    else:
                        # Worst case: just split at max_length
                        chunks.append(paragraph[:max_length])
                        current_chunk = paragraph[max_length:]
                else:
                    current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

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
            "token": "",
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

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        logger.warning(f"Unauthorized access attempt by user {user_id}")
        return
    
    await update.message.reply_text(
        'Hi! I am your ArXiv Paper Bot. I will send you daily updates of papers on your topics of interest.\n\n'
        'Use /help to see available commands.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
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

async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current topics."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
    topics_text = "Current topics:\n\n" + "\n".join([f"- {topic}" for topic in config['topics']])
    await update.message.reply_text(topics_text)

async def add_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new topic."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
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

async def remove_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a topic."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
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

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set notification time."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
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

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set timezone."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
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

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get today's papers."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
    await update.message.reply_text('Searching for today\'s papers, please wait...')
    
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    all_results = []
    
    # Fetch papers for each topic separately
    for topic in config['topics']:
        try:
            results = fetch_arxiv_papers(topic, yesterday.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'))
            if results:
                all_results.append((topic, results))
        except Exception as e:
            logger.error(f"Error fetching papers for topic {topic}: {e}")
    
    if not all_results:
        await update.message.reply_text("No papers found today for your topics.")
        return
    
    # Format and send results
    for topic, results in all_results:
        message = f"📚 <b>{topic} Papers Today</b> 📚\n\n"
        
        for i, paper in enumerate(results, 1):
            title = escape_html(paper['title'])
            authors = ', '.join(paper['authors'][:3])
            if len(paper['authors']) > 3:
                authors += ' et al.'
            authors = escape_html(authors)
            
            message += f"{i}. <b>{title}</b>\n"
            message += f"   Authors: {authors}\n"
            
            paper_id = paper['id'].split('/')[-1]  # Extract just the ID part
            message += f"   Use /abstract{paper_id} to view details\n\n"
        
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
                        await update.message.reply_text(f"Could not send formatted message due to an error. Here's the plain text:\n\n{chunk}", parse_mode=None)
                    except Exception as inner_e:
                        logger.error(f"Failed to send even plain text message: {inner_e}")

async def authorize_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Authorize a new user (admin only)."""
    user_id = update.effective_user.id
    
    # Check if this is the first user (initialization)
    if not config['authorized_users']:
        config['authorized_users'].append(user_id)
        save_config(config)
        await update.message.reply_text(f'You are now authorized as the admin user.')
        return
    
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text('Please provide a user ID to authorize.')
        return
    
    try:
        new_user_id = int(context.args[0])
        if new_user_id in config['authorized_users']:
            await update.message.reply_text(f'User {new_user_id} is already authorized.')
            return
        
        config['authorized_users'].append(new_user_id)
        save_config(config)
        await update.message.reply_text(f'User {new_user_id} has been authorized.')
    except ValueError:
        await update.message.reply_text('Invalid user ID. Please provide a numeric ID.')

async def paper_abstract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get full abstract of a paper by its arXiv ID."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text('Please provide an arXiv paper ID (e.g., /abstract 2101.12345)')
        return
    
    paper_id = context.args[0]
    await update.message.reply_text(f'Searching for paper with ID: {paper_id}...')
    
    try:
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


async def abstract_no_space(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /abstractXXXXX commands where the ID is attached to the command."""
    user_id = update.effective_user.id
    if user_id not in config['authorized_users']:
        await update.message.reply_text('You are not authorized to use this bot.')
        return
    
    # Extract paper ID from the command text
    command_text = update.message.text
    # Skip '/abstract' part and get the remaining text as paper_id
    paper_id = command_text[9:].strip()
    
    if not paper_id:
        await update.message.reply_text('Please provide an arXiv paper ID (e.g., /abstract 2101.12345)')
        return
    
    await update.message.reply_text(f'Searching for paper with ID: {paper_id}...')
    
    try:
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
    today = datetime.now().strftime('%Y-%m-%d')
    
    for topic in config['topics']:
        try:
            results = fetch_arxiv_papers(topic, today, today, max_results=10)
            
            if not results:
                logger.info(f"No papers found today for topic {topic}")
                continue
            
            message = f"📚 <b>{topic} Papers Today</b> 📚\n\n"
            
            for i, paper in enumerate(results, 1):
                title = escape_html(paper['title'])
                authors = ', '.join(paper['authors'][:3])
                if len(paper['authors']) > 3:
                    authors += ' et al.'
                authors = escape_html(authors)
                
                message += f"{i}. <b>{title}</b>\n"
                message += f"   Authors: {authors}\n"
                
                paper_id = paper['id'].split('/')[-1]  # Extract just the ID part
                message += f"   Use /abstract{paper_id} to view details\n\n"
            
            # Send to all authorized users
            for user_id in config['authorized_users']:
                try:
                    if len(message) <= 4096:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='HTML'
                        )
                    else:
                        # Use the smart chunking function
                        chunks = chunk_html_message(message)
                        for chunk in chunks:
                            try:
                                await context.bot.send_message(
                                    chat_id=user_id,
                                    text=chunk,
                                    parse_mode='HTML'
                                )
                            except Exception as e:
                                logger.error(f"Error sending message chunk: {e}")
                                # Try sending without HTML parsing as fallback
                                try:
                                    await context.bot.send_message(
                                        chat_id=user_id,
                                        text=f"Could not send formatted message due to an error. Here's the plain text:\n\n{chunk}",
                                        parse_mode=None
                                    )
                                except Exception as inner_e:
                                    logger.error(f"Failed to send even plain text message: {inner_e}")
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing topic {topic}: {e}")

def run_bot():
    """Run the bot."""
    if not config['token']:
        logger.error("No token provided. Please add your bot token to the config.json file.")
        return
    
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
