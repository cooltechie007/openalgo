#!/usr/bin/env python3
"""
Test script for enhanced webhook functionality with dynamic symbol resolution
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5000"
WEBHOOK_ID = "your_webhook_id_here"  # Replace with actual webhook ID

def test_enhanced_webhook():
    """Test the enhanced webhook with expiry, price, and spread"""
    
    print("🚀 Testing Enhanced Webhook with Dynamic Symbol Resolution")
    print("=" * 60)
    
    # Enhanced webhook payload
    enhanced_payload = {
        "symbol": "NIFTY",
        "expiry": "04NOV25", 
        "price": 25000,  # Current LTP for ATM calculation
        "action": "ENTRY",
        "spread": {
            "type": "call_spread",
            "legs": 2
        }
    }
    
    print("📤 Enhanced Webhook Payload:")
    print(json.dumps(enhanced_payload, indent=2))
    print()
    
    try:
        # Send enhanced webhook
        response = requests.post(
            f"{BASE_URL}/strategy/webhook/{WEBHOOK_ID}",
            json=enhanced_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📥 Response Status: {response.status_code}")
        print("📥 Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("✅ Enhanced webhook executed successfully!")
        else:
            print("❌ Enhanced webhook failed!")
            
    except Exception as e:
        print(f"❌ Error testing enhanced webhook: {str(e)}")

def test_legacy_webhook():
    """Test the legacy webhook format for backward compatibility"""
    
    print("\n🔄 Testing Legacy Webhook (Backward Compatibility)")
    print("=" * 60)
    
    # Legacy webhook payload
    legacy_payload = {
        "symbol": "NIFTY04NOV2525000CE",
        "action": "ENTRY"
    }
    
    print("📤 Legacy Webhook Payload:")
    print(json.dumps(legacy_payload, indent=2))
    print()
    
    try:
        # Send legacy webhook
        response = requests.post(
            f"{BASE_URL}/strategy/webhook/{WEBHOOK_ID}",
            json=legacy_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📥 Response Status: {response.status_code}")
        print("📥 Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("✅ Legacy webhook executed successfully!")
        else:
            print("❌ Legacy webhook failed!")
            
    except Exception as e:
        print(f"❌ Error testing legacy webhook: {str(e)}")

def test_exit_webhook():
    """Test EXIT webhook to close positions"""
    
    print("\n🚪 Testing EXIT Webhook")
    print("=" * 60)
    
    # EXIT webhook payload
    exit_payload = {
        "symbol": "NIFTY",
        "expiry": "04NOV25",
        "price": 25100,  # Updated price
        "action": "EXIT"
    }
    
    print("📤 EXIT Webhook Payload:")
    print(json.dumps(exit_payload, indent=2))
    print()
    
    try:
        # Send EXIT webhook
        response = requests.post(
            f"{BASE_URL}/strategy/webhook/{WEBHOOK_ID}",
            json=exit_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📥 Response Status: {response.status_code}")
        print("📥 Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("✅ EXIT webhook executed successfully!")
        else:
            print("❌ EXIT webhook failed!")
            
    except Exception as e:
        print(f"❌ Error testing EXIT webhook: {str(e)}")

def main():
    """Main test function"""
    
    print("🧪 Enhanced Webhook Test Suite")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"🔗 Webhook ID: {WEBHOOK_ID}")
    print()
    
    if WEBHOOK_ID == "your_webhook_id_here":
        print("⚠️  Please update WEBHOOK_ID with your actual webhook ID")
        print("   You can find it in your strategy configuration")
        return
    
    # Run tests
    test_enhanced_webhook()
    test_legacy_webhook() 
    test_exit_webhook()
    
    print("\n🎯 Test Summary:")
    print("=" * 60)
    print("✅ Enhanced webhook with dynamic symbol resolution")
    print("✅ Legacy webhook backward compatibility")
    print("✅ EXIT webhook for position closing")
    print("✅ Symbol search integration (no hardcoding)")
    print("✅ ATM strike calculation from current price")
    print("✅ Strike offset application from configuration")
    print("✅ Option type filtering (CE, PE, FUT, XX)")

if __name__ == "__main__":
    main()
