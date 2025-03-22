import unittest
import asyncio
import json
import os
from datetime import datetime, time
import pytz
from unittest.mock import patch, MagicMock
from telegram.ext import Application, JobQueue
import telegram_bot
from telegram_bot import run_bot, config, load_config, chunk_html_message, paper_id_without_dot, send_daily_papers

class TestJobQueue(unittest.TestCase):
    
    def setUp(self):
        # Create a mock config for testing
        self.mock_config = {
            "authorized_users": ["123456", "789012"],
            "topics": ["cs.CV", "cs.AI"],
            "notification_time": "09:00",
            "timezone": "UTC"
        }
        
        # Set up environment variable for token
        os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
        
        # Sample paper data for testing
        self.sample_papers = [
            {
                'id': 'http://arxiv.org/abs/2401.12345',
                'title': 'Test Paper 1',
                'authors': ['Author One', 'Author Two', 'Author Three', 'Author Four'],
                'categories': ['cs.CV', 'cs.LG'],
                'published': '2023-01-01',
                'link': 'http://arxiv.org/pdf/2401.12345'
            },
            {
                'id': 'http://arxiv.org/abs/2401.67890',
                'title': 'Test Paper 2',
                'authors': ['Author Five', 'Author Six'],
                'categories': ['cs.AI'],
                'published': '2023-01-01',
                'link': 'http://arxiv.org/pdf/2401.67890'
            }
        ]
    
    def tearDown(self):
        # Clean up environment
        if "TELEGRAM_BOT_TOKEN" in os.environ:
            del os.environ["TELEGRAM_BOT_TOKEN"]
    
    @patch('telegram_bot.fetch_arxiv_papers')
    def test_job_queue_setup(self, mock_fetch_papers):
        # Mock the paper fetching to return our sample data
        mock_fetch_papers.return_value = self.sample_papers
        
        # Create a real Application instance with a test token
        # Note: We're not actually connecting to Telegram API
        application = Application.builder().token("test_token").build()
        
        # Get the job queue from the application
        job_queue = application.job_queue
        
        # Schedule the daily job with our actual function
        notification_time = time(hour=9, minute=0)
        job = job_queue.run_daily(
            send_daily_papers,
            time=notification_time,
        )
        
        # Verify the job was scheduled correctly
        self.assertIsNotNone(job)
        # In python-telegram-bot v20+, we need to check the trigger's fields
        self.assertEqual(job.trigger.fields[5].expressions[0].first, 9)  # hour is at index 5
        self.assertEqual(job.trigger.fields[4].expressions[0].first, 0)  # minute is at index 4
        
        # Clean up
        application.shutdown()
    
    @patch('telegram_bot.fetch_arxiv_papers')
    def test_job_queue_with_different_time(self, mock_fetch_papers):
        # Mock the paper fetching to return our sample data
        mock_fetch_papers.return_value = self.sample_papers
        
        # Create a real Application instance with a test token
        application = Application.builder().token("test_token").build()
        
        # Get the job queue from the application
        job_queue = application.job_queue
        
        # Schedule the daily job with a different time
        notification_time = time(hour=15, minute=30)
        job = job_queue.run_daily(
            send_daily_papers,
            time=notification_time,
        )
        
        # Verify the job was scheduled correctly
        self.assertIsNotNone(job)
        # In python-telegram-bot v20+, we need to check the trigger's fields
        self.assertEqual(job.trigger.fields[5].expressions[0].first, 15)  # hour is at index 5
        self.assertEqual(job.trigger.fields[4].expressions[0].first, 30)  # minute is at index 4
        
        # Clean up
        application.shutdown()
    
    def test_load_config_new_file(self):
        # Use a temporary config file for testing
        temp_config_file = 'test_config.json'
        original_config_file = telegram_bot.CONFIG_FILE
        
        try:
            # Temporarily change the config file path
            telegram_bot.CONFIG_FILE = temp_config_file
            
            # Make sure the test file doesn't exist
            if os.path.exists(temp_config_file):
                os.remove(temp_config_file)
            
            # Call the function
            result = load_config()
            
            # Verify a default config was created
            self.assertIn("authorized_users", result)
            self.assertIn("topics", result)
            self.assertIn("notification_time", result)
            self.assertIn("timezone", result)
            
            # Verify the file was created
            self.assertTrue(os.path.exists(temp_config_file))
            
            # Read the file to verify its contents
            with open(temp_config_file, 'r') as f:
                saved_config = json.load(f)
            
            self.assertEqual(result, saved_config)
            
        finally:
            # Clean up and restore original config file path
            if os.path.exists(temp_config_file):
                os.remove(temp_config_file)
            telegram_bot.CONFIG_FILE = original_config_file
    
    def test_load_config_existing_file(self):
        # Use a temporary config file for testing
        temp_config_file = 'test_config.json'
        original_config_file = telegram_bot.CONFIG_FILE
        
        try:
            # Temporarily change the config file path
            telegram_bot.CONFIG_FILE = temp_config_file
            
            # Create a test config file
            with open(temp_config_file, 'w') as f:
                json.dump(self.mock_config, f)
            
            # Call the function
            result = load_config()
            
            # Verify the result matches our mock config
            self.assertEqual(result, self.mock_config)
            
        finally:
            # Clean up and restore original config file path
            if os.path.exists(temp_config_file):
                os.remove(temp_config_file)
            telegram_bot.CONFIG_FILE = original_config_file
    
    def test_chunk_html_message(self):
        # Test normal message (under limit)
        short_message = "This is a short message"
        chunks = chunk_html_message(short_message, max_length=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], short_message)
        
        # Test message that needs to be split
        long_message = "Paragraph 1\n\nParagraph 2\n\n" + "X" * 100 + "\n\nParagraph 4"
        chunks = chunk_html_message(long_message, max_length=50)
        self.assertGreater(len(chunks), 1)
        
        # Ensure all content is preserved across chunks
        combined = "\n\n".join(chunks)
        self.assertEqual(combined.replace("\n\n\n\n", "\n\n"), long_message)
    
    def test_paper_id_without_dot(self):
        # Test ID with dot
        self.assertEqual(paper_id_without_dot("2401.12345"), "240112345")
        
        # Test ID without dot
        self.assertEqual(paper_id_without_dot("240112345"), "240112345")
    
    @patch('telegram_bot.fetch_arxiv_papers')
    async def test_send_daily_papers_async(self, mock_fetch_papers):
        # This test requires an async test runner
        # Mock the paper fetching to return our sample data
        mock_fetch_papers.return_value = self.sample_papers
        
        # Create a real Application instance with a test token
        application = Application.builder().token("test_token").build()
        
        # Create a context with the application
        context = MagicMock()
        context.bot = application.bot
        
        # Call the function
        try:
            # We're not actually sending messages, just testing the function runs
            await send_daily_papers(context)
            # If we get here without errors, the test passes
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"send_daily_papers raised exception {e}")
        finally:
            # Clean up
            await application.shutdown()

if __name__ == '__main__':
    unittest.main()
