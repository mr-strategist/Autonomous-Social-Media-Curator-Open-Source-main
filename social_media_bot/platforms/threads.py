import os
import time
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from .base import SocialMediaPlatform
from ..config.platforms import Platform

class Threads(SocialMediaPlatform):
    """Threads platform implementation using Selenium"""
    
    def __init__(self):
        super().__init__(Platform.THREADS)
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        self.driver = None
        self.wait = None

    def _setup_driver(self):
        """Setup Selenium WebDriver"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def authenticate(self) -> bool:
        """Login to Threads via Instagram"""
        try:
            if not self.username or not self.password:
                return False

            if not self.driver:
                self._setup_driver()

            # Go to Instagram login
            self.driver.get('https://www.threads.net/login')
            
            # Wait for and fill username
            username_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_input.send_keys(self.username)

            # Fill password
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.send_keys(self.password)

            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()

            # Wait for successful login
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Create new thread']"))
                )
                self.is_authenticated = True
                return True
            except TimeoutException:
                return False

        except Exception as e:
            self.is_authenticated = False
            return False

    def post_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Post content to Threads"""
        if not self.is_authenticated:
            if not self.authenticate():
                return {"success": False, "error": "Authentication failed"}

        try:
            # Click create new thread button
            create_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='Create new thread']"))
            )
            create_button.click()

            # Wait for and fill content area
            content_area = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Post content']"))
            )
            content_area.send_keys(content)

            # Click post button
            post_button = self.driver.find_element(By.XPATH, "//button[text()='Post']")
            post_button.click()

            # Wait for post confirmation
            time.sleep(2)  # Brief wait for post to complete

            return {
                "success": True,
                "message": "Content posted successfully to Threads"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def check_status(self) -> bool:
        """Check Threads connection status"""
        try:
            if not self.driver:
                return self.authenticate()
            
            self.driver.get('https://www.threads.net')
            return 'threads.net' in self.driver.current_url
        except:
            return False

    def __del__(self):
        """Cleanup Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass 