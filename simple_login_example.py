#!/usr/bin/env python3
"""
Simple programmatic login example for OpenAlgo
Demonstrates the exact form request that matches request.form['username'] and password
"""

import requests
import json
import re

def extract_csrf_token(html_content):
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

def simple_login_example():
    """
    Simple example showing how to login using form data
    This matches exactly what happens in the Flask route: request.form['username'] and request.form['password']
    """
    
    # OpenAlgo server URL
    base_url = "http://127.0.0.1:5000"
    login_url = f"{base_url}/auth/login"
    
    # Credentials (change these to your actual credentials)
    username = "cool"  # This will be request.form['username']
    password = "your_password_here"  # This will be request.form['password']
    
    print(f"🔐 Logging into OpenAlgo at: {login_url}")
    print(f"👤 Username: {username}")
    
    # Create session to maintain cookies
    session = requests.Session()
    
    # First, get the login page to extract CSRF token
    print("📡 Getting login page to extract CSRF token...")
    login_page_response = session.get(login_url)
    
    if login_page_response.status_code != 200:
        print(f"❌ Failed to get login page: {login_page_response.status_code}")
        return False
    
    # Extract CSRF token from HTML
    csrf_token = extract_csrf_token(login_page_response.text)
    
    if csrf_token:
        print(f"🔒 Found CSRF token: {csrf_token[:20]}...")
    else:
        print("⚠️ No CSRF token found, trying without it...")
    
    # Prepare form data (this is what Flask receives as request.form)
    form_data = {
        'username': username,    # request.form['username']
        'password': password     # request.form['password']
    }
    
    # Add CSRF token if found
    if csrf_token:
        form_data['csrf_token'] = csrf_token
    
    try:
        # Send POST request with form data
        print("📡 Sending POST request with form data...")
        response = session.post(login_url, data=form_data)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        # Check response
        if response.status_code == 200:
            try:
                # Try to parse JSON response
                json_response = response.json()
                print(f"📄 JSON Response: {json_response}")
                
                if json_response.get('status') == 'success':
                    print("✅ Login successful!")
                    
                    # Now try to access dashboard
                    dashboard_url = f"{base_url}/dashboard"
                    print(f"📊 Accessing dashboard: {dashboard_url}")
                    
                    dashboard_response = session.get(dashboard_url)
                    print(f"📊 Dashboard Status: {dashboard_response.status_code}")
                    
                    if dashboard_response.status_code == 200:
                        print("✅ Dashboard accessible!")
                        return True
                    else:
                        print("❌ Dashboard access failed")
                        return False
                        
                else:
                    print(f"❌ Login failed: {json_response.get('message', 'Unknown error')}")
                    return False
                    
            except json.JSONDecodeError:
                # Response might not be JSON (could be HTML redirect)
                print("📄 Non-JSON response received")
                print(f"📄 Response text: {response.text[:200]}...")
                
                # Check if it's a successful redirect
                if response.status_code == 200:
                    print("✅ Login may have succeeded (non-JSON response)")
                    return True
                else:
                    print("❌ Login failed")
                    return False
        else:
            print(f"❌ Login failed with status: {response.status_code}")
            print(f"📄 Response: {response.text[:500]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Could not connect to OpenAlgo server")
        print("💡 Make sure OpenAlgo is running on http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_form_data_structure():
    """
    Test to show exactly what form data structure is sent
    """
    print("\n🧪 Form Data Structure Test")
    print("=" * 40)
    
    # This is exactly what Flask receives
    form_data = {
        'username': 'cool',
        'password': 'test_password'
    }
    
    print("📋 Form data that will be sent:")
    for key, value in form_data.items():
        print(f"   {key}: {value}")
    
    print("\n📡 This matches Flask's request.form:")
    print("   request.form['username'] = 'cool'")
    print("   request.form['password'] = 'test_password'")

def interactive_login():
    """
    Interactive version where user can enter credentials
    """
    print("\n🔐 Interactive Login")
    print("=" * 30)
    
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()
    
    if not username or not password:
        print("❌ Username and password are required!")
        return False
    
    # Update the form data
    base_url = "http://127.0.0.1:5000"
    login_url = f"{base_url}/auth/login"
    
    form_data = {
        'username': username,
        'password': password
    }
    
    session = requests.Session()
    
    try:
        response = session.post(login_url, data=form_data)
        
        if response.status_code == 200:
            try:
                json_response = response.json()
                if json_response.get('status') == 'success':
                    print("✅ Login successful!")
                    return True
                else:
                    print(f"❌ Login failed: {json_response.get('message')}")
                    return False
            except json.JSONDecodeError:
                print("✅ Login successful (non-JSON response)")
                return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 OpenAlgo Form Login Example")
    print("=" * 50)
    
    # Show form data structure
    test_form_data_structure()
    
    # Run simple login example
    print("\n🔐 Running Simple Login Example")
    print("=" * 40)
    
    # Uncomment the line below and update password to test
    # simple_login_example()
    
    print("\n💡 To test:")
    print("1. Update the password in the script")
    print("2. Uncomment the simple_login_example() call")
    print("3. Run the script")
    print("\nOr run interactive mode:")
    
    # Uncomment to run interactive mode
    # interactive_login()
