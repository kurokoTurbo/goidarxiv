import logging
from telegram_bot import run_bot

def main():
    """Entry point for the application"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    print("Starting ArXiv Telegram Bot...")
    # Run the Telegram bot
    run_bot()

if __name__ == "__main__":
    main()
