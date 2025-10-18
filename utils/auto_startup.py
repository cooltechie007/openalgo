#!/usr/bin/env python3
"""
OpenAlgo Auto-Startup Module
Automatically logs in user and authenticates broker on server startup
"""

import os
import time
import requests
import json
import threading
from datetime import datetime
import pytz
from utils.logging import get_logger

logger = get_logger(__name__)

class AutoStartupManager:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.logged_in = False
        self.broker_authenticated = False
        self.login_time = None
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # Clear any existing session to avoid conflicts
        self.session.cookies.clear()
        
    def extract_csrf_token(self, html_content):
        """Extract CSRF token from HTML content"""
        import re
        patterns = [
            r'name="csrf_token"\s+value="([^"]+)"',
            r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"',
            r'csrf_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def check_environment_variables(self):
        """Check if required environment variables are set"""
        required_vars = [
            'AUTO_STARTUP_USERNAME',
            'AUTO_STARTUP_PASSWORD',
            'BROKER_API_KEY',
            'BROKER_API_SECRET', 
            'BROKER_API_KEY_MARKET',
            'BROKER_API_SECRET_MARKET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"Auto-startup disabled - missing environment variables: {', '.join(missing_vars)}")
            return False
        
        logger.info("Auto-startup environment variables configured")
        return True
    
    def login_user(self, username, password):
        """Login to OpenAlgo"""
        logger.info(f"Auto-startup: Logging in user {username}")
        
        login_url = f"{self.base_url}/auth/login"
        
        try:
            # Get login page to extract CSRF token
            login_page_response = self.session.get(login_url)
            
            if login_page_response.status_code == 429:
                logger.warning(f"Auto-startup: Rate limited (429) - waiting before retry")
                return False
            elif login_page_response.status_code != 200:
                logger.error(f"Auto-startup: Failed to get login page: {login_page_response.status_code}")
                return False
            
            # Extract CSRF token
            csrf_token = self.extract_csrf_token(login_page_response.text)
            
            # Prepare form data
            form_data = {
                'username': username,
                'password': password
            }
            
            if csrf_token:
                form_data['csrf_token'] = csrf_token
            
            # Send login request
            response = self.session.post(login_url, data=form_data)
            
            logger.debug(f"Auto-startup: Login response status: {response.status_code}")
            logger.debug(f"Auto-startup: Login response content: {response.text[:200]}...")
            
            if response.status_code == 200:
                # Check if response is JSON
                try:
                    json_response = response.json()
                    if json_response.get('status') == 'success':
                        logger.info("Auto-startup: User login successful")
                        self.logged_in = True
                        # Set login time for session validation
                        now_utc = datetime.now(pytz.timezone('UTC'))
                        now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))
                        self.login_time = now_ist.isoformat()
                        return True
                    else:
                        logger.error(f"Auto-startup: Login failed: {json_response.get('message', 'Unknown error')}")
                        return False
                except json.JSONDecodeError as e:
                    # Response is not JSON, check if it's a successful HTML response
                    logger.debug(f"Auto-startup: Non-JSON response: {e}")
                    
                    # Check if we got redirected to dashboard or got a successful HTML response
                    if ("dashboard" in response.text.lower() or 
                        "success" in response.text.lower() or
                        response.url.endswith('/dashboard')):
                        logger.info("Auto-startup: User login successful (HTML response)")
                        self.logged_in = True
                        # Set login time for session validation
                        now_utc = datetime.now(pytz.timezone('UTC'))
                        now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))
                        self.login_time = now_ist.isoformat()
                        return True
                    else:
                        logger.error(f"Auto-startup: Login failed - unexpected response format")
                        logger.debug(f"Auto-startup: Response text: {response.text[:500]}")
                        return False
            elif response.status_code == 302:
                # Redirect response - check if redirected to dashboard
                redirect_location = response.headers.get('Location', '')
                if '/dashboard' in redirect_location:
                    logger.info("Auto-startup: User login successful (redirected to dashboard)")
                    self.logged_in = True
                    # Set login time for session validation
                    now_utc = datetime.now(pytz.timezone('UTC'))
                    now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))
                    self.login_time = now_ist.isoformat()
                    return True
                else:
                    logger.error(f"Auto-startup: Login failed - redirected to: {redirect_location}")
                    return False
            else:
                logger.error(f"Auto-startup: Login failed: {response.status_code}")
                logger.debug(f"Auto-startup: Response text: {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"Auto-startup: Login error: {e}")
            return False
    
    def authenticate_broker(self):
        """Authenticate with broker following the correct flow"""
        logger.info("Auto-startup: Authenticating with broker")
        
        try:
            # Step 1: Go to broker selection page (simulates user clicking "Connect Account")
            logger.info("Auto-startup: Step 1 - Going to broker selection page")
            broker_url = f"{self.base_url}/auth/broker"
            response = self.session.get(broker_url)
            
            logger.debug(f"Auto-startup: Broker page status: {response.status_code}")
            logger.debug(f"Auto-startup: Broker page URL: {response.url}")
            
            if response.status_code != 200:
                logger.error(f"Auto-startup: Failed to access broker page: {response.status_code}")
                return False
            
            # Step 2: Go to IIFL callback (this simulates clicking "Connect Account" for IIFL)
            logger.info("Auto-startup: Step 2 - Connecting to IIFL broker")
            broker_callback_url = f"{self.base_url}/iifl/callback"
            response = self.session.get(broker_callback_url)
            
            logger.debug(f"Auto-startup: IIFL callback status: {response.status_code}")
            logger.debug(f"Auto-startup: IIFL callback URL: {response.url}")
            
            if response.status_code in [200, 302]:
                # Check if we were redirected to dashboard (successful authentication)
                if "/dashboard" in response.url:
                    logger.info("Auto-startup: Broker authentication successful!")
                    self.broker_authenticated = True
                    return True
                else:
                    # Check if authentication succeeded by testing dashboard access
                    logger.debug("Auto-startup: Testing dashboard access after broker callback")
                    dashboard_response = self.session.get(f"{self.base_url}/dashboard")
                    
                    logger.debug(f"Auto-startup: Dashboard status: {dashboard_response.status_code}")
                    logger.debug(f"Auto-startup: Dashboard URL: {dashboard_response.url}")
                    
                    if dashboard_response.status_code == 200 and "dashboard" in dashboard_response.text.lower():
                        logger.info("Auto-startup: Broker authentication successful!")
                        self.broker_authenticated = True
                        return True
                    elif dashboard_response.status_code == 302 and "/dashboard" in dashboard_response.url:
                        logger.info("Auto-startup: Broker authentication successful!")
                        self.broker_authenticated = True
                        return True
                    else:
                        logger.error(f"Auto-startup: Broker authentication failed - dashboard not accessible")
                        logger.debug(f"Auto-startup: Dashboard response: {dashboard_response.text[:200]}")
                        return False
            else:
                logger.error(f"Auto-startup: Broker authentication failed: {response.status_code}")
                logger.debug(f"Auto-startup: Broker response: {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"Auto-startup: Broker authentication error: {e}")
            return False
    
    def verify_broker_in_database(self):
        """Verify that broker information is actually stored in the database"""
        logger.info("Auto-startup: Verifying broker information in database")
        
        try:
            # Test the master contract status endpoint which requires broker info
            status_url = f"{self.base_url}/api/master-contract/status"
            response = self.session.get(status_url)
            
            logger.debug(f"Auto-startup: Master contract status response: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.debug(f"Auto-startup: Master contract data: {data}")
                    
                    # Check if we got broker information
                    if 'broker' in data and data['broker']:
                        logger.info(f"Auto-startup: Broker verified in database: {data['broker']}")
                        return True
                    else:
                        logger.warning("Auto-startup: No broker information found in database")
                        return False
                except json.JSONDecodeError:
                    logger.warning("Auto-startup: Master contract status returned non-JSON response")
                    return False
            elif response.status_code == 401:
                logger.warning("Auto-startup: Master contract status requires authentication")
                return False
            else:
                logger.warning(f"Auto-startup: Master contract status failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Auto-startup: Broker verification error: {e}")
            return False
    
    def verify_system_ready(self):
        """Verify that the system is ready to accept API orders"""
        logger.info("Auto-startup: Verifying system readiness")
        
        # Test API endpoint
        api_url = f"{self.base_url}/api/v1/funds"
        
        try:
            response = self.session.get(api_url)
            
            if response.status_code in [200, 401]:  # 401 is expected for API key auth
                logger.info("Auto-startup: System ready for API orders")
                return True
            else:
                logger.warning(f"Auto-startup: API readiness check returned: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Auto-startup: System readiness check error: {e}")
            return False
    
    def run_auto_startup(self):
        """Run the complete auto-startup process"""
        logger.info("🚀 Starting OpenAlgo Auto-Startup Process")
        
        # Check if auto-startup is enabled
        if not self.check_environment_variables():
            logger.info("Auto-startup disabled - skipping automatic login")
            return False
        
        username = os.getenv('AUTO_STARTUP_USERNAME')
        password = os.getenv('AUTO_STARTUP_PASSWORD')
        
        # Check if we're already logged in by testing dashboard access
        logger.info("Auto-startup: Checking if already logged in...")
        dashboard_response = self.session.get(f"{self.base_url}/dashboard")
        
        # Check if we got redirected to login (not logged in)
        if dashboard_response.status_code == 302 and "/auth/login" in dashboard_response.url:
            logger.info("Auto-startup: Not logged in - proceeding with login")
        elif dashboard_response.status_code == 200 and "dashboard" in dashboard_response.text.lower():
            logger.info("Auto-startup: Already logged in - checking broker authentication")
            # Still need to check broker authentication
            if self.authenticate_broker():
                logger.info("🎉 Auto-startup completed successfully!")
                logger.info("✅ User already logged in")
                logger.info("✅ Broker authenticated")
                return True
            else:
                logger.warning("Auto-startup: User logged in but broker authentication failed")
        else:
            logger.info("Auto-startup: Login status unclear - proceeding with login")
        
        # Retry logic for login with longer delays to avoid rate limiting
        for attempt in range(self.max_retries):
            logger.info(f"Auto-startup attempt {attempt + 1}/{self.max_retries}")
            
            # Step 1: Login user
            if not self.login_user(username, password):
                logger.warning(f"Auto-startup: User login failed on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    # Use longer delay to avoid rate limiting
                    delay = self.retry_delay * (attempt + 2)  # 10, 15, 20 seconds
                    logger.info(f"Auto-startup: Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error("Auto-startup: User login failed after all retries")
                    return False
            
            # Step 2: Authenticate broker
            if not self.authenticate_broker():
                logger.warning(f"Auto-startup: Broker authentication failed on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 2)
                    logger.info(f"Auto-startup: Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error("Auto-startup: Broker authentication failed after all retries")
                    return False
            
            # Step 3: Verify system readiness
            if not self.verify_system_ready():
                logger.warning(f"Auto-startup: System readiness check failed on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 2)
                    logger.info(f"Auto-startup: Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    continue
                else:
                    logger.warning("Auto-startup: System readiness check failed, but continuing")
            
            # Success!
            logger.info("🎉 Auto-startup completed successfully!")
            logger.info("✅ User logged in")
            logger.info("✅ Broker authenticated")
            logger.info("✅ System ready for API orders")
            return True
        
        logger.error("Auto-startup: Failed after all retry attempts")
        return False

def start_auto_startup_async(base_url="http://127.0.0.1:5000", delay=15):
    """
    Start auto-startup process in a separate thread with delay
    This allows the server to fully initialize before attempting login
    """
    def auto_startup_worker():
        logger.info(f"Auto-startup: Waiting {delay} seconds for server to initialize...")
        time.sleep(delay)
        
        manager = AutoStartupManager(base_url)
        success = manager.run_auto_startup()
        
        if success:
            logger.info("Auto-startup: Process completed successfully")
        else:
            logger.warning("Auto-startup: Process failed - manual login may be required")
    
    # Start the auto-startup process in a separate thread
    thread = threading.Thread(target=auto_startup_worker, daemon=True)
    thread.start()
    logger.info("Auto-startup: Background process started")

def is_auto_startup_enabled():
    """Check if auto-startup is enabled via environment variables"""
    return (
        os.getenv('AUTO_STARTUP_USERNAME') and 
        os.getenv('AUTO_STARTUP_PASSWORD') and
        os.getenv('BROKER_API_KEY') and
        os.getenv('BROKER_API_SECRET')
    )

def init_auto_startup(app):
    """
    Initialize auto-startup for the Flask app
    This should be called during app initialization
    """
    if is_auto_startup_enabled():
        logger.info("Auto-startup: Enabled - will attempt automatic login after server startup")
        
        # Get configuration from environment
        base_url = os.getenv('HOST_SERVER', 'http://127.0.0.1:5000')
        delay = int(os.getenv('AUTO_STARTUP_DELAY', '10'))
        
        # Start auto-startup process
        start_auto_startup_async(base_url, delay)
    else:
        logger.info("Auto-startup: Disabled - manual login required")
