#!/usr/bin/env python3
"""
Expiry Date Sorting and Filtering Utility

This script sorts expiry dates and finds the first expiry after today's date.
"""

from datetime import datetime, timedelta
import pytz

def parse_expiry_date(expiry_str):
    """Parse expiry date string to datetime object"""
    try:
        # Parse format like "20-OCT-25"
        return datetime.strptime(expiry_str, '%d-%b-%y')
    except ValueError:
        try:
            # Try alternative format
            return datetime.strptime(expiry_str, '%d-%m-%Y')
        except ValueError:
            print(f"Error parsing date: {expiry_str}")
            return None

def get_next_expiry(expiry_list, current_date=None):
    """Get the first expiry date after today"""
    # Get current IST date
    if not current_date:
        ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
        current_date = ist_now.date()
    else:
        current_date = current_date.date()
    
    # Parse and filter expiry dates
    valid_expiries = []
    for expiry_str in expiry_list:
        expiry_date = parse_expiry_date(expiry_str)
        if expiry_date:
            valid_expiries.append({
                'date_str': expiry_str,
                'date_obj': expiry_date.date(),
                'days_from_today': (expiry_date.date() - current_date).days
            })
    
    # Sort by date
    valid_expiries.sort(key=lambda x: x['date_obj'])
    
    # Find first expiry after today
    next_expiries = [exp for exp in valid_expiries if exp['days_from_today'] > 0]
    
    if next_expiries:
        return next_expiries[0]['date_str']
    else:
        return None

def main():
    """Main function"""
    # Your expiry data
    expiry_data = {
        'data': ['20-OCT-25', '28-OCT-25', '04-NOV-25', '11-NOV-25', '18-NOV-25', '25-NOV-25', 
                '30-DEC-25', '31-MAR-26', '30-JUN-26', '29-SEP-26', '29-DEC-26', '29-JUN-27', 
                '28-DEC-27', '27-JUN-28', '26-DEC-28', '26-JUN-29', '24-DEC-29', '25-JUN-30'],
        'message': 'Found 18 expiry dates for NIFTY options in NFO',
        'status': 'success'
    }
    
    # Get next expiry
    next_expiry = get_next_expiry(expiry_data['data'])
    
    if next_expiry:
        print(next_expiry)
    else:
        print("No valid expiry found")

if __name__ == "__main__":
    main()
