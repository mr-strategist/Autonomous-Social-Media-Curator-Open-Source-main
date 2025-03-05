import unittest
from unittest.mock import patch, MagicMock
from social_media_bot.platforms.threads import Threads, ThreadsMediaError
import os

class TestThreadsMedia(unittest.TestCase):
    def setUp(self):
        self.threads = Threads()
        self.test_image = "tests/data/test_image.jpg"
        
    def test_media_validation(self):
        # Test valid image
        self.assertTrue(self.threads._validate_media(self.test_image))
        
        # Test invalid image
        with self.assertRaises(ThreadsMediaError):
            self.threads._validate_media("nonexistent.jpg") 