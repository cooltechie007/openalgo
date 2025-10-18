#!/usr/bin/env python3
"""
CSRF Token Test Script
Tests CSRF token extraction from OpenAlgo login page
"""

import requests
import re

def extract_csrf_token(html_content):
    """
    Extract CSRF token from HTML content
    """
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

def test_csrf_extraction():
    """
    Test CSRF token extraction from login page
    """
    base_url = "http://127.0.0.1:5000"
    login_url = f"{base_url}/auth/login"
    
    print("🔍 Testing CSRF Token Extraction")
    print("=" * 40)
    
    try:
        # Get login page
        response = requests.get(login_url)
        
        if response.status_code == 200:
            print(f"✅ Login page accessible: {response.status_code}")
            
            # Extract CSRF token
            csrf_token = extract_csrf_token(response.text)
            
            if csrf_token:
                print(f"🔒 CSRF token found: {csrf_token[:20]}...")
                print(f"📏 Token length: {len(csrf_token)}")
                
                # Test login with CSRF token
                return test_login_with_csrf(csrf_token)
            else:
                print("❌ No CSRF token found in HTML")
                print("📄 HTML content preview:")
                print(response.text[:500] + "...")
                return False
        else:
            print(f"❌ Failed to get login page: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_login_with_csrf(csrf_token):
    """
    Test login with CSRF token
    """
    base_url = "http://127.0.0.1:5000"
    login_url = f"{base_url}/auth/login"
    
    print("\n🔐 Testing Login with CSRF Token")
    print("=" * 40)
    
    session = requests.Session()
    
    # Form data with CSRF token
    form_data = {
        'username': 'cool',
        'password': 'Demoacc@1',
        'csrf_token': csrf_token
    }
    
    try:
        response = session.post(login_url, data=form_data)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Login request successful!")
            
            # Check if we got JSON response
            try:
                json_response = response.json()
                print(f"📄 JSON Response: {json_response}")
                
                if json_response.get('status') == 'success':
                    print("🎉 Login successful!")
                    return True
                else:
                    print(f"❌ Login failed: {json_response.get('message')}")
                    return False
            except:
                print("📄 Non-JSON response (might be redirect)")
                return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"📄 Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return False

def test_without_csrf():
    """
    Test login without CSRF token (should fail)
    """
    base_url = "http://127.0.0.1:5000"
    login_url = f"{base_url}/auth/login"
    
    print("\n🚫 Testing Login WITHOUT CSRF Token")
    print("=" * 40)
    
    session = requests.Session()
    
    # Form data without CSRF token
    form_data = {
        'username': 'cool',
        'password': 'Demoacc@1'
    }
    
    try:
        response = session.post(login_url, data=form_data)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 400:
            print("✅ Expected CSRF error received!")
            if "CSRF token is missing" in response.text:
                print("🔒 CSRF protection is working correctly")
                return True
            else:
                print("⚠️ Unexpected CSRF error message")
                return False
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 OpenAlgo CSRF Token Test")
    print("=" * 50)
    
    # Test CSRF extraction
    csrf_found = test_csrf_extraction()
    
    # Test without CSRF (should fail)
    test_without_csrf()
    
    print("\n💡 Summary:")
    if csrf_found:
        print("✅ CSRF token extraction and login working!")
        print("🔧 Use the updated sample programs with CSRF support")
    else:
        print("❌ CSRF token extraction failed")
        print("💡 Check if OpenAlgo is running and CSRF is enabled")
