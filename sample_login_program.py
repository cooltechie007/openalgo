#!/usr/bin/env python3
"""
Sample program to demonstrate programmatic login to OpenAlgo
This script shows how to login using form data with username and password
"""

import requests
import json
import os
import re
from urllib.parse import urljoin

class OpenAlgoLoginClient:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.logged_in = False
    
    def _extract_csrf_token(self, html_content):
        """
        Extract CSRF token from HTML content
        
        Args:
            html_content (str): HTML content of the login page
            
        Returns:
            str: CSRF token if found, None otherwise
        """
        # Look for CSRF token in various formats
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
        
    def login(self, username, password):
        """
        Login to OpenAlgo using form data with CSRF token
        
        Args:
            username (str): Username for login
            password (str): Password for login
            
        Returns:
            bool: True if login successful, False otherwise
        """
        login_url = urljoin(self.base_url, "/auth/login")
        
        try:
            print(f"🔐 Attempting to login as: {username}")
            print(f"📡 Getting login page first to extract CSRF token...")
            
            # First, get the login page to extract CSRF token
            login_page_response = self.session.get(login_url)
            
            if login_page_response.status_code != 200:
                print(f"❌ Failed to get login page: {login_page_response.status_code}")
                return False
            
            # Extract CSRF token from the HTML
            csrf_token = self._extract_csrf_token(login_page_response.text)
            
            if not csrf_token:
                print("⚠️ No CSRF token found, trying without it...")
            
            # Prepare form data with CSRF token
            form_data = {
                'username': username,
                'password': password
            }
            
            if csrf_token:
                form_data['csrf_token'] = csrf_token
                print(f"🔒 Using CSRF token: {csrf_token[:20]}...")
            
            print(f"📡 Sending POST request to: {login_url}")
            
            # Send POST request with form data
            response = self.session.post(login_url, data=form_data)
            
            print(f"📊 Response Status Code: {response.status_code}")
            print(f"📋 Response Headers: {dict(response.headers)}")
            
            # Check if login was successful
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get('status') == 'success':
                        print("✅ Login successful!")
                        self.logged_in = True
                        return True
                    else:
                        print(f"❌ Login failed: {response_data.get('message', 'Unknown error')}")
                        return False
                except json.JSONDecodeError:
                    # If response is not JSON, check if it's a redirect
                    if response.status_code == 200 and len(response.text) < 100:
                        print("✅ Login successful (redirect response)!")
                        self.logged_in = True
                        return True
                    else:
                        print(f"❌ Login failed: Invalid response format")
                        return False
            else:
                print(f"❌ Login failed with status code: {response.status_code}")
                print(f"📄 Response content: {response.text[:500]}...")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error: Could not connect to {self.base_url}")
            print("💡 Make sure OpenAlgo is running on the specified URL")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False
    
    def get_dashboard(self):
        """
        Access the dashboard after successful login
        
        Returns:
            bool: True if dashboard accessible, False otherwise
        """
        if not self.logged_in:
            print("❌ Must login first before accessing dashboard")
            return False
            
        dashboard_url = urljoin(self.base_url, "/dashboard")
        
        try:
            print(f"📊 Accessing dashboard: {dashboard_url}")
            response = self.session.get(dashboard_url)
            
            print(f"📊 Dashboard Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Dashboard accessible!")
                # Check if we got the actual dashboard or were redirected
                if "dashboard" in response.text.lower() or "margin" in response.text.lower():
                    print("📋 Dashboard content loaded successfully")
                    return True
                else:
                    print("⚠️ Dashboard response received but content may be unexpected")
                    return True
            else:
                print(f"❌ Dashboard access failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Dashboard access error: {e}")
            return False
    
    def logout(self):
        """
        Logout from OpenAlgo
        
        Returns:
            bool: True if logout successful, False otherwise
        """
        logout_url = urljoin(self.base_url, "/auth/logout")
        
        try:
            print(f"🚪 Logging out...")
            response = self.session.get(logout_url)
            
            if response.status_code in [200, 302]:  # 302 is redirect after logout
                print("✅ Logout successful!")
                self.logged_in = False
                return True
            else:
                print(f"❌ Logout failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Logout error: {e}")
            return False

def main():
    """
    Main function to demonstrate programmatic login
    """
    print("🚀 OpenAlgo Programmatic Login Demo")
    print("=" * 50)
    
    # Initialize client
    client = OpenAlgoLoginClient()
    
    # Get credentials from user input or environment
    username = os.getenv('OPENALGO_USERNAME', 'cool')  # Default username
    password = os.getenv('OPENALGO_PASSWORD', 'Demoacc@1')      # No default password
    
    if not password:
        print("🔑 Please enter your OpenAlgo credentials:")
        username = input("Username: ").strip() or username
        password = input("Password: ").strip()
    
    if not password:
        print("❌ Password is required!")
        return
    
    # Attempt login
    print(f"\n🔐 Logging in as: {username}")
    print("-" * 30)
    
    if client.login(username, password):
        print("\n📊 Testing dashboard access...")
        print("-" * 30)
        
        # Try to access dashboard
        if client.get_dashboard():
            print("\n🎉 Complete login flow successful!")
        else:
            print("\n⚠️ Login successful but dashboard access failed")
        
        # Optional: Logout
        print("\n🚪 Testing logout...")
        print("-" * 30)
        client.logout()
        
    else:
        print("\n❌ Login failed!")
        print("\n💡 Troubleshooting tips:")
        print("   • Check if OpenAlgo is running on http://127.0.0.1:5000")
        print("   • Verify username and password are correct")
        print("   • Check if auto-startup is disabled (AUTO_STARTUP_LOCALHOST=FALSE)")
        print("   • Try accessing http://127.0.0.1:5000/auth/login in browser first")

def test_with_different_methods():
    """
    Test different login methods and approaches
    """
    print("\n🧪 Testing Different Login Methods")
    print("=" * 50)
    
    client = OpenAlgoLoginClient()
    
    # Test 1: GET request to login page (should return HTML form)
    print("\n📋 Test 1: GET login page")
    try:
        response = client.session.get(urljoin(client.base_url, "/auth/login"))
        print(f"Status: {response.status_code}")
        if "login" in response.text.lower():
            print("✅ Login page accessible")
        else:
            print("⚠️ Unexpected response")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Test with invalid credentials
    print("\n🔐 Test 2: Invalid credentials")
    client.login("invalid_user", "invalid_pass")
    
    # Test 3: Test with empty credentials
    print("\n🔐 Test 3: Empty credentials")
    client.login("", "")

if __name__ == "__main__":
    # Run main demo
    main()
    
    # Uncomment to run additional tests
    # test_with_different_methods()
