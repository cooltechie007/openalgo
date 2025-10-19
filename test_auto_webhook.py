#!/usr/bin/env python3
"""
Test script for Auto-Webhook Endpoint

This script demonstrates the new auto-webhook endpoint that automatically
selects expiry and strike based on the symbol provided.
"""

import requests
import json

def test_auto_webhook():
    """Test the auto-webhook endpoint"""
    
    # Replace with your actual webhook ID
    webhook_id = "YOUR_WEBHOOK_ID_HERE"
    base_url = "http://127.0.0.1:5000"
    
    # Test cases
    test_cases = [
        {
            "name": "NIFTY Call Entry (ATM)",
            "payload": {
                "symbol": "NIFTY",
                "action": "ENTRY",
                "instrument_type": "CE",
                "strike_offset": 0
            }
        },
        {
            "name": "NIFTY Put Entry (ATM-100)",
            "payload": {
                "symbol": "NIFTY", 
                "action": "ENTRY",
                "instrument_type": "PE",
                "strike_offset": -100
            }
        },
        {
            "name": "BANKNIFTY Call Entry (ATM+200)",
            "payload": {
                "symbol": "BANKNIFTY",
                "action": "ENTRY", 
                "instrument_type": "CE",
                "strike_offset": 200
            }
        },
        {
            "name": "NIFTY Call Entry with Specific Expiry",
            "payload": {
                "symbol": "NIFTY",
                "action": "ENTRY",
                "instrument_type": "CE",
                "strike_offset": 0,
                "expiry": "20-OCT-25"
            }
        },
        {
            "name": "NIFTY Exit",
            "payload": {
                "symbol": "NIFTY",
                "action": "EXIT",
                "instrument_type": "CE",
                "strike_offset": 0
            }
        }
    ]
    
    print("🚀 Auto-Webhook Endpoint Test")
    print("=" * 50)
    
    for test_case in test_cases:
        print(f"\n📋 Test: {test_case['name']}")
        print(f"Payload: {json.dumps(test_case['payload'], indent=2)}")
        
        try:
            # Make request to auto-webhook endpoint
            url = f"{base_url}/strategy/auto-webhook/{webhook_id}"
            response = requests.post(url, json=test_case['payload'])
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Success!")
                print(f"Message: {result.get('message', 'N/A')}")
                print(f"Webhook Action: {result.get('webhook_action', 'N/A')}")
                print(f"Position Action: {result.get('position_action', 'N/A')}")
                
                # Show auto-selection details
                auto_selection = result.get('auto_selection', {})
                if auto_selection:
                    print(f"Base Symbol: {auto_selection.get('base_symbol', 'N/A')}")
                    print(f"Instrument Type: {auto_selection.get('instrument_type', 'N/A')}")
                    print(f"Strike Offset: {auto_selection.get('strike_offset', 'N/A')}")
                
                # Show processed orders
                processed_orders = result.get('processed_orders', [])
                if processed_orders:
                    print(f"Processed Orders ({len(processed_orders)}):")
                    for i, order in enumerate(processed_orders, 1):
                        print(f"  {i}. {order['action']} {order['symbol']} ({order['exchange']})")
                        print(f"     Quantity: {order['quantity']}")
                        print(f"     Expiry: {order.get('expiry', 'N/A')}")
                        print(f"     Strike: {order.get('strike', 'N/A')}")
                        print(f"     Type: {order.get('instrument_type', 'N/A')}")
                
            else:
                print("❌ Error!")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data.get('error', 'Unknown error')}")
                    if 'message' in error_data:
                        print(f"Message: {error_data['message']}")
                except:
                    print(f"Response: {response.text}")
                    
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
        
        print("-" * 30)

def show_usage_examples():
    """Show usage examples for the auto-webhook endpoint"""
    
    print("\n📖 Auto-Webhook Usage Examples")
    print("=" * 50)
    
    examples = [
        {
            "title": "Basic NIFTY Call Entry (ATM)",
            "curl": '''curl -X POST http://127.0.0.1:5000/strategy/auto-webhook/YOUR_WEBHOOK_ID \\
  -H "Content-Type: application/json" \\
  -d '{
    "symbol": "NIFTY",
    "action": "ENTRY",
    "instrument_type": "CE",
    "strike_offset": 0
  }' ''',
            "description": "Enters NIFTY Call option at ATM strike with nearest expiry"
        },
        {
            "title": "NIFTY Call Entry with Specific Expiry",
            "curl": '''curl -X POST http://127.0.0.1:5000/strategy/auto-webhook/YOUR_WEBHOOK_ID \\
  -H "Content-Type: application/json" \\
  -d '{
    "symbol": "NIFTY",
    "action": "ENTRY",
    "instrument_type": "CE",
    "strike_offset": 0,
    "expiry": "20-OCT-25"
  }' ''',
            "description": "Enters NIFTY Call option at ATM strike with specific expiry"
        },
        {
            "title": "NIFTY Put Entry (ATM-100)",
            "curl": '''curl -X POST http://127.0.0.1:5000/strategy/auto-webhook/YOUR_WEBHOOK_ID \\
  -H "Content-Type: application/json" \\
  -d '{
    "symbol": "NIFTY",
    "action": "ENTRY", 
    "instrument_type": "PE",
    "strike_offset": -100
  }' ''',
            "description": "Enters NIFTY Put option 100 points below ATM"
        },
        {
            "title": "BANKNIFTY Call Entry (ATM+200)",
            "curl": '''curl -X POST http://127.0.0.1:5000/strategy/auto-webhook/YOUR_WEBHOOK_ID \\
  -H "Content-Type: application/json" \\
  -d '{
    "symbol": "BANKNIFTY",
    "action": "ENTRY",
    "instrument_type": "CE", 
    "strike_offset": 200
  }' ''',
            "description": "Enters BANKNIFTY Call option 200 points above ATM"
        },
        {
            "title": "Exit All Positions",
            "curl": '''curl -X POST http://127.0.0.1:5000/strategy/auto-webhook/YOUR_WEBHOOK_ID \\
  -H "Content-Type: application/json" \\
  -d '{
    "symbol": "NIFTY",
    "action": "EXIT",
    "instrument_type": "CE",
    "strike_offset": 0
  }' ''',
            "description": "Exits all NIFTY Call positions"
        }
    ]
    
    for example in examples:
        print(f"\n🔹 {example['title']}")
        print(f"Description: {example['description']}")
        print("Command:")
        print(example['curl'])
        print()

def main():
    """Main function"""
    print("⚠️  IMPORTANT: Replace 'YOUR_WEBHOOK_ID_HERE' with your actual webhook ID")
    print("⚠️  Make sure your OpenAlgo server is running on http://127.0.0.1:5000")
    print()
    
    # Show usage examples
    show_usage_examples()
    
    # Ask if user wants to run tests
    print("\n" + "="*50)
    print("To run actual tests, update the webhook_id in the script and uncomment the line below:")
    print("# test_auto_webhook()")
    
    # Uncomment the line below to run actual tests
    # test_auto_webhook()

if __name__ == "__main__":
    main()
