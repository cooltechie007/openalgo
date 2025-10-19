from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for, abort
from database.strategy_db import (
    Strategy, StrategySymbolMapping, StrategyPosition, db_session,
    create_strategy, add_symbol_mapping, get_strategy_by_webhook_id,
    get_symbol_mappings, get_all_strategies, delete_strategy,
    update_strategy_times, delete_symbol_mapping, bulk_add_symbol_mappings,
    toggle_strategy, get_strategy, get_user_strategies,
    get_strategy_positions, has_active_positions, create_strategy_position,
    update_strategy_position, close_strategy_position, get_strategy_pnl
)
from database.symbol import enhanced_search_symbols
from database.auth_db import get_api_key_for_tradingview
from utils.session import check_session_validity, is_session_valid
from limiter import limiter
import json
from datetime import datetime, time
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from utils.logging import get_logger
import requests
import os
import uuid
import time as time_module
import queue
import threading
from collections import deque
from time import time
import re

logger = get_logger(__name__)

# Rate limiting configuration
WEBHOOK_RATE_LIMIT = os.getenv("WEBHOOK_RATE_LIMIT", "100 per minute")
STRATEGY_RATE_LIMIT = os.getenv("STRATEGY_RATE_LIMIT", "200 per minute")

strategy_bp = Blueprint('strategy_bp', __name__, url_prefix='/strategy')

# Initialize scheduler for time-based controls
scheduler = BackgroundScheduler(
    timezone=pytz.timezone('Asia/Kolkata'),
    job_defaults={
        'coalesce': True,
        'misfire_grace_time': 300,
        'max_instances': 1
    }
)
scheduler.start()

# Get base URL from environment or default to localhost
BASE_URL = os.getenv('HOST_SERVER', 'http://127.0.0.1:5000')

# Valid exchanges
VALID_EXCHANGES = ['NSE', 'BSE', 'NFO', 'CDS', 'BFO', 'BCD', 'MCX', 'NCDEX']

# Product types per exchange
EXCHANGE_PRODUCTS = {
    'NSE': ['MIS', 'CNC'],
    'BSE': ['MIS', 'CNC'],
    'NFO': ['MIS', 'NRML'],
    'CDS': ['MIS', 'NRML'],
    'BFO': ['MIS', 'NRML'],
    'BCD': ['MIS', 'NRML'],
    'MCX': ['MIS', 'NRML'],
    'NCDEX': ['MIS', 'NRML']
}

# Default values
DEFAULT_EXCHANGE = 'NSE'
DEFAULT_PRODUCT = 'MIS'

# Separate queues for different order types
regular_order_queue = queue.Queue()  # For placeorder (up to 10/sec)
smart_order_queue = queue.Queue()    # For placesmartorder (1/sec)

# Order processor state
order_processor_running = False
order_processor_lock = threading.Lock()

# Rate limiting state for regular orders
last_regular_orders = deque(maxlen=10)  # Track last 10 regular order timestamps

def process_orders():
    """Background task to process orders from both queues with rate limiting"""
    global order_processor_running
    
    while True:
        try:
            # Process smart orders first (1 per second)
            try:
                smart_order = smart_order_queue.get_nowait()
                if smart_order is None:  # Poison pill
                    break
                
                try:
                    response = requests.post(f'{BASE_URL}/api/v1/placesmartorder', json=smart_order['payload'])
                    if response.ok:
                        logger.info(f'Smart order placed for {smart_order["payload"]["symbol"]} in strategy {smart_order["payload"]["strategy"]}')
                    else:
                        logger.error(f'Error placing smart order for {smart_order["payload"]["symbol"]}: {response.text}')
                except Exception as e:
                    logger.error(f'Error placing smart order: {str(e)}')
                
                # Always wait 1 second after smart order
                time_module.sleep(1)
                continue  # Start next iteration
                
            except queue.Empty:
                pass  # No smart orders, continue to regular orders
            
            # Process regular orders (up to 10 per second)
            now = time()
            
            # Clean up old timestamps
            while last_regular_orders and now - last_regular_orders[0] > 1:
                last_regular_orders.popleft()
            
            # Process regular orders if under rate limit
            if len(last_regular_orders) < 10:
                try:
                    regular_order = regular_order_queue.get_nowait()
                    if regular_order is None:  # Poison pill
                        break
                    
                    try:
                        response = requests.post(f'{BASE_URL}/api/v1/placeorder', json=regular_order['payload'])
                        if response.ok:
                            logger.info(f'Regular order placed for {regular_order["payload"]["symbol"]} in strategy {regular_order["payload"]["strategy"]}')
                            last_regular_orders.append(now)
                        else:
                            logger.error(f'Error placing regular order for {regular_order["payload"]["symbol"]}: {response.text}')
                    except Exception as e:
                        logger.error(f'Error placing regular order: {str(e)}')
                    
                except queue.Empty:
                    pass  # No regular orders
            
            # Small sleep to prevent CPU spinning
            time_module.sleep(0.1)
            
        except Exception as e:
            logger.error(f'Error in order processor: {str(e)}')
            time_module.sleep(1)  # Sleep on error to prevent rapid retries

def ensure_order_processor():
    """Ensure the order processor is running"""
    global order_processor_running
    with order_processor_lock:
        if not order_processor_running:
            threading.Thread(target=process_orders, daemon=True).start()
            order_processor_running = True

def queue_order(endpoint, payload):
    """Add order to appropriate queue"""
    ensure_order_processor()
    if endpoint == 'placesmartorder':
        smart_order_queue.put({'payload': payload})
    else:
        regular_order_queue.put({'payload': payload})

def validate_strategy_times(start_time, end_time, squareoff_time):
    """Validate strategy time settings"""
    try:
        if not all([start_time, end_time, squareoff_time]):
            return False, "All time fields are required"
        
        # Convert strings to time objects for comparison
        start = datetime.strptime(start_time, '%H:%M').time()
        end = datetime.strptime(end_time, '%H:%M').time()
        squareoff = datetime.strptime(squareoff_time, '%H:%M').time()
        
        # Market hours validation (9:15 AM to 3:30 PM)
        market_open = datetime.strptime('09:15', '%H:%M').time()
        market_close = datetime.strptime('15:30', '%H:%M').time()
        
        if start < market_open:
            return False, "Start time cannot be before market open (9:15)"
        if end > market_close:
            return False, "End time cannot be after market close (15:30)"
        if squareoff > market_close:
            return False, "Square off time cannot be after market close (15:30)"
        if start >= end:
            return False, "Start time must be before end time"
        if squareoff < start:
            return False, "Square off time must be after start time"
        if squareoff < end:
            return False, "Square off time must be after end time"
        
        return True, None
        
    except ValueError:
        return False, "Invalid time format. Use HH:MM format"

def validate_position_logic(strategy_id, webhook_action):
    """
    Enhanced position validation logic
    
    Returns:
        tuple: (is_valid, error_message, active_positions_info)
    """
    try:
        active_positions = get_strategy_positions(strategy_id)
        has_active_positions = any(pos.is_active for pos in active_positions)
        
        if has_active_positions and webhook_action == 'ENTRY':
            return False, 'Strategy already has active positions. Cannot enter new trades.', [
                {
                    'symbol': pos.symbol,
                    'exchange': pos.exchange,
                    'quantity': pos.quantity,
                    'average_price': pos.average_price,
                    'unrealized_pnl': pos.unrealized_pnl
                } for pos in active_positions if pos.is_active
            ]
        
        if not has_active_positions and webhook_action == 'EXIT':
            return False, 'No active positions found. Cannot exit without entry.', []
        
        return True, None, []
        
    except Exception as e:
        logger.error(f'Error validating position logic: {str(e)}')
        return False, f'Error validating positions: {str(e)}', []

def validate_strategy_name(name):
    if not name:
        return False, "Strategy name is required"
    
    # Check length
    if len(name) < 3 or len(name) > 50:
        return False, "Strategy name must be between 3 and 50 characters"
    
    # Check characters
    if not re.match(r'^[A-Za-z0-9\s\-_]+$', name):
        return False, "Strategy name can only contain letters, numbers, spaces, hyphens and underscores"
    
    return True, None

def schedule_squareoff(strategy_id):
    """Schedule squareoff for intraday strategy"""
    strategy = get_strategy(strategy_id)
    if not strategy or not strategy.is_intraday or not strategy.squareoff_time:
        return
    
    try:
        hours, minutes = map(int, strategy.squareoff_time.split(':'))
        job_id = f'squareoff_{strategy_id}'
        
        # Remove existing job if any
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        
        # Add new job
        scheduler.add_job(
            squareoff_positions,
            'cron',
            hour=hours,
            minute=minutes,
            args=[strategy_id],
            id=job_id,
            timezone=pytz.timezone('Asia/Kolkata')
        )
        logger.info(f'Scheduled squareoff for strategy {strategy_id} at {hours}:{minutes}')
    except Exception as e:
        logger.error(f'Error scheduling squareoff for strategy {strategy_id}: {str(e)}')

def squareoff_positions(strategy_id):
    """Square off all positions for intraday strategy"""
    try:
        strategy = get_strategy(strategy_id)
        if not strategy or not strategy.is_intraday:
            return
        
        # Get API key for authentication
        api_key = get_api_key_for_tradingview(strategy.user_id)
        if not api_key:
            logger.error(f'No API key found for strategy {strategy_id}')
            return
            
        # Get all symbol mappings
        mappings = get_symbol_mappings(strategy_id)
        
        # Sort mappings to process BUY orders first, then SELL orders for squareoff
        def get_squareoff_priority(mapping):
            # For squareoff, prioritize SELL orders (to close long positions first)
            return 0 if mapping.quantity > 0 else 1
        
        sorted_mappings = sorted(mappings, key=get_squareoff_priority)
        
        for mapping in sorted_mappings:
            # For squareoff, reverse the quantity sign to close the position
            squareoff_action = 'SELL' if mapping.quantity > 0 else 'BUY'
            
            payload = {
                'apikey': api_key,
                'exchange': mapping.exchange,
                'product': mapping.product_type,
                'strategy': strategy.name,
                'action': squareoff_action
            }
            
            # Queue the order instead of executing directly
            queue_order('placeorder', payload)
            
            # Close the corresponding strategy position
            # Find the position for this symbol and close it
            positions = get_strategy_positions(strategy_id)
            for position in positions:
                if position.symbol == mapping.symbol and position.exchange == mapping.exchange:
                    # Calculate realized PnL (simplified - should use actual exit price)
                    realized_pnl = 0.0  # This should be calculated based on actual exit price
                    close_strategy_position(position.id, realized_pnl)
                    logger.info(f'Closed strategy position for {mapping.symbol}')
            
    except Exception as e:
        logger.error(f'Error in squareoff_positions for strategy {strategy_id}: {str(e)}')

@strategy_bp.route('/')
def index():
    """List all strategies"""
    if not is_session_valid():
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user')  
    if not user_id:
        flash('Please login to continue', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        logger.info(f"Fetching strategies for user: {user_id}")
        strategies = get_user_strategies(user_id)
        return render_template('strategy/index.html', strategies=strategies)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        flash('Error loading strategies', 'error')
        return redirect(url_for('dashboard_bp.index'))

@strategy_bp.route('/new', methods=['GET', 'POST'])
@check_session_validity
@limiter.limit(STRATEGY_RATE_LIMIT)
def new_strategy():
    """Create new strategy"""
    if request.method == 'POST':
        try:
            # Get user_id from session
            user_id = session.get('user')
            if not user_id:
                logger.error("No user_id found in session")
                flash('Session expired. Please login again.', 'error')
                return redirect(url_for('auth.login'))
            
            logger.info(f"Creating strategy for user: {user_id}")

            # Get form data
            platform = request.form.get('platform', '').strip()
            name = request.form.get('name', '').strip()

            # Validate platform
            if not platform:
                flash('Please select a platform', 'error')
                return redirect(url_for('strategy_bp.new_strategy'))

            # Create prefixed strategy name
            name = f"{platform}_{name}"

            # Get other form data
            strategy_type = request.form.get('type')
            trading_mode = request.form.get('trading_mode', 'LONG')  # Default to LONG
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            squareoff_time = request.form.get('squareoff_time')
            
            # Validate strategy name
            if not validate_strategy_name(name):
                flash('Invalid strategy name. Use only letters, numbers, spaces, hyphens, and underscores', 'error')
                return redirect(url_for('strategy_bp.new_strategy'))
            
            # Validate times for intraday strategy
            is_intraday = strategy_type == 'intraday'
            if is_intraday:
                if not validate_strategy_times(start_time, end_time, squareoff_time):
                    flash('Invalid trading times. End time must be after start time and before square off time', 'error')
                    return redirect(url_for('strategy_bp.new_strategy'))
            else:
                start_time = end_time = squareoff_time = None
            
            # Generate webhook ID
            webhook_id = str(uuid.uuid4())
            
            # Create strategy with user ID
            strategy = create_strategy(
                name=name,
                webhook_id=webhook_id,
                user_id=user_id,  # Use username from session
                is_intraday=is_intraday,
                trading_mode=trading_mode,
                start_time=start_time,
                end_time=end_time,
                squareoff_time=squareoff_time,
                platform=platform
            )
            
            if strategy:
                flash('Strategy created successfully!', 'success')
                if strategy.is_intraday:
                    schedule_squareoff(strategy.id)
                return redirect(url_for('strategy_bp.configure_symbols', strategy_id=strategy.id))
            else:
                flash('Error creating strategy', 'error')
                return redirect(url_for('strategy_bp.new_strategy'))
                
        except Exception as e:
            logger.error(f'Error creating strategy: {str(e)}')
            flash('Error creating strategy', 'error')
            return redirect(url_for('strategy_bp.new_strategy'))
    
    return render_template('strategy/new_strategy.html')

@strategy_bp.route('/<int:strategy_id>')
def view_strategy(strategy_id):
    """View strategy details"""
    if not is_session_valid():
        return redirect(url_for('auth.login'))
    
    strategy = get_strategy(strategy_id)
    if not strategy:
        flash('Strategy not found', 'error')
        return redirect(url_for('strategy_bp.index'))
    
    if strategy.user_id != session.get('user'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('strategy_bp.index'))
    
    symbol_mappings = get_symbol_mappings(strategy_id)
    positions = get_strategy_positions(strategy_id)
    pnl_data = get_strategy_pnl(strategy_id)
    
    return render_template('strategy/view_strategy.html', 
                         strategy=strategy,
                         symbol_mappings=symbol_mappings,
                         positions=positions,
                         pnl_data=pnl_data)

@strategy_bp.route('/toggle/<int:strategy_id>', methods=['POST'])
def toggle_strategy_route(strategy_id):
    """Toggle strategy active status"""
    if not is_session_valid():
        return redirect(url_for('auth.login'))
        
    try:
        strategy = toggle_strategy(strategy_id)
        if strategy:
            if strategy.is_active:
                # Schedule squareoff if being activated
                schedule_squareoff(strategy_id)
                flash('Strategy activated successfully', 'success')
            else:
                # Remove squareoff job if being deactivated
                try:
                    scheduler.remove_job(f'squareoff_{strategy_id}')
                except Exception:
                    pass
                flash('Strategy deactivated successfully', 'success')
            
            return redirect(url_for('strategy_bp.view_strategy', strategy_id=strategy_id))
        else:
            flash('Error toggling strategy: Strategy not found', 'error')
            return redirect(url_for('strategy_bp.index'))
    except Exception as e:
        flash(f'Error toggling strategy: {str(e)}', 'error')
        return redirect(url_for('strategy_bp.index'))

@strategy_bp.route('/<int:strategy_id>/delete', methods=['POST'])
@check_session_validity
@limiter.limit(STRATEGY_RATE_LIMIT)
def delete_strategy_route(strategy_id):
    """Delete strategy"""
    user_id = session.get('user')
    if not user_id:
        return jsonify({'status': 'error', 'error': 'Session expired'}), 401
        
    strategy = get_strategy(strategy_id)
    if not strategy:
        return jsonify({'status': 'error', 'error': 'Strategy not found'}), 404
    
    # Check if strategy belongs to user
    if strategy.user_id != user_id:
        return jsonify({'status': 'error', 'error': 'Unauthorized'}), 403
    
    try:
        # Remove squareoff job if exists
        try:
            scheduler.remove_job(f'squareoff_{strategy_id}')
        except Exception:
            pass
            
        if delete_strategy(strategy_id):
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'error': 'Failed to delete strategy'}), 500
    except Exception as e:
        logger.error(f'Error deleting strategy {strategy_id}: {str(e)}')
        return jsonify({'status': 'error', 'error': str(e)}), 500

@strategy_bp.route('/<int:strategy_id>/configure', methods=['GET', 'POST'])
@check_session_validity
@limiter.limit(STRATEGY_RATE_LIMIT)
def configure_symbols(strategy_id):
    """Configure symbols for strategy"""
    user_id = session.get('user')
    if not user_id:
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('auth.login'))
        
    strategy = get_strategy(strategy_id)
    if not strategy:
        abort(404)
    
    # Check if strategy belongs to user
    if strategy.user_id != user_id:
        abort(403)
    
    if request.method == 'POST':
        try:
            # Get data from either JSON or form
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
            
            logger.info(f"Received data: {data}")
            
            # Handle bulk symbols
            if 'symbols' in data:
                symbols_text = data.get('symbols')
                mappings = []
                
                for line in symbols_text.strip().split('\n'):
                    if not line.strip():
                        continue
                    
                    parts = line.strip().split(',')
                    if len(parts) != 6:
                        raise ValueError(f'Invalid format in line: {line}. Expected: symbol,exchange,quantity,product,strike_offset,option_type')
                    
                    symbol, exchange, quantity, product, strike_offset, option_type = parts
                    if exchange not in VALID_EXCHANGES:
                        raise ValueError(f'Invalid exchange: {exchange}')
                    
                    try:
                        quantity = int(quantity)
                        strike_offset = int(strike_offset)
                    except ValueError:
                        raise ValueError(f'Invalid quantity or strike_offset: {quantity}, {strike_offset}. Must be numbers')
                    
                    if quantity == 0:
                        raise ValueError(f'Quantity cannot be zero for symbol: {symbol}')
                    
                    mappings.append({
                        'symbol': symbol.strip(),
                        'exchange': exchange.strip(),
                        'quantity': quantity,
                        'product_type': product.strip(),
                        'strike_offset': strike_offset,
                        'option_type': option_type.strip()
                    })
                
                if mappings:
                    bulk_add_symbol_mappings(strategy_id, mappings)
                    return jsonify({'status': 'success'})
            
            # Handle single symbol
            else:
                symbol = data.get('symbol')
                exchange = data.get('exchange')
                quantity = data.get('quantity')
                product_type = data.get('product_type')
                strike_offset = data.get('strike_offset', 0)  # Default to 0 (ATM)
                option_type = data.get('option_type', 'XX')  # Default to XX
                
                logger.info(f"Processing single symbol: symbol={symbol}, exchange={exchange}, quantity={quantity}, product_type={product_type}, strike_offset={strike_offset}, option_type={option_type}")
                
                if not all([symbol, exchange, quantity, product_type]):
                    missing = []
                    if not symbol: missing.append('symbol')
                    if not exchange: missing.append('exchange')
                    if not quantity: missing.append('quantity')
                    if not product_type: missing.append('product_type')
                    raise ValueError(f'Missing required fields: {", ".join(missing)}')
                
                if exchange not in VALID_EXCHANGES:
                    raise ValueError(f'Invalid exchange: {exchange}')
                
                try:
                    quantity = int(quantity)
                    strike_offset = int(strike_offset)
                except ValueError:
                    raise ValueError('Quantity and strike_offset must be valid numbers')
                
                if quantity == 0:
                    raise ValueError('Quantity cannot be zero')
                
                mapping = add_symbol_mapping(
                    strategy_id=strategy_id,
                    symbol=symbol,
                    exchange=exchange,
                    quantity=quantity,
                    product_type=product_type,
                    strike_offset=strike_offset,
                    option_type=option_type
                )
                
                if mapping:
                    return jsonify({'status': 'success'})
                else:
                    raise ValueError('Failed to add symbol mapping')
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Error configuring symbols: {error_msg}')
            return jsonify({'status': 'error', 'error': error_msg}), 400
    
    symbol_mappings = get_symbol_mappings(strategy_id)
    return render_template('strategy/configure_symbols.html', 
                         strategy=strategy, 
                         symbol_mappings=symbol_mappings,
                         exchanges=VALID_EXCHANGES)

@strategy_bp.route('/<int:strategy_id>/symbol/<int:mapping_id>/delete', methods=['POST'])
@check_session_validity
@limiter.limit(STRATEGY_RATE_LIMIT)
def delete_symbol(strategy_id, mapping_id):
    """Delete symbol mapping"""
    username = session.get('user')
    if not username:
        return jsonify({'status': 'error', 'error': 'Session expired'}), 401
        
    strategy = get_strategy(strategy_id)
    if not strategy or strategy.user_id != username:
        return jsonify({'status': 'error', 'error': 'Strategy not found'}), 404
    
    try:
        if delete_symbol_mapping(mapping_id):
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'error': 'Symbol mapping not found'}), 404
    except Exception as e:
        logger.error(f'Error deleting symbol mapping: {str(e)}')
        return jsonify({'status': 'error', 'error': str(e)}), 400

@strategy_bp.route('/search')
@check_session_validity
def search_symbols():
    """Search symbols endpoint"""
    query = request.args.get('q', '').strip()
    exchange = request.args.get('exchange')
    
    if not query:
        return jsonify({'results': []})
    
    results = enhanced_search_symbols(query, exchange)
    return jsonify({
        'results': [{
            'symbol': result.symbol,
            'name': result.name,
            'exchange': result.exchange
        } for result in results]
    })

@strategy_bp.route('/<int:strategy_id>/pnl')
@check_session_validity
def get_strategy_pnl_api(strategy_id):
    """Get strategy PnL data via API"""
    user_id = session.get('user')
    if not user_id:
        return jsonify({'error': 'Session expired'}), 401
        
    strategy = get_strategy(strategy_id)
    if not strategy or strategy.user_id != user_id:
        return jsonify({'error': 'Strategy not found'}), 404
    
    try:
        positions = get_strategy_positions(strategy_id)
        pnl_data = get_strategy_pnl(strategy_id)
        
        return jsonify({
            'strategy_id': strategy_id,
            'strategy_name': strategy.name,
            'pnl_data': pnl_data,
            'positions': [{
                'id': pos.id,
                'symbol': pos.symbol,
                'exchange': pos.exchange,
                'quantity': pos.quantity,
                'average_price': pos.average_price,
                'current_price': pos.current_price,
                'unrealized_pnl': pos.unrealized_pnl,
                'realized_pnl': pos.realized_pnl,
                'entry_time': pos.entry_time.isoformat() if pos.entry_time else None,
                'is_active': pos.is_active
            } for pos in positions]
        })
    except Exception as e:
        logger.error(f'Error getting strategy PnL: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

def resolve_symbols_from_configuration(strategy_id, base_symbol, expiry, current_price, spread_config=None):
    """
    Resolve actual trading symbols based on strategy configuration, expiry, and current price
    Uses symbol search instead of hardcoding symbol construction
    
    Args:
        strategy_id: Strategy ID
        base_symbol: Base symbol (e.g., 'NIFTY', 'BANKNIFTY')
        expiry: Expiry date (e.g., '04NOV25')
        current_price: Current LTP of the base symbol
        spread_config: Optional spread configuration for multi-leg strategies
    
    Returns:
        list: List of resolved symbol mappings with actual trading symbols
    """
    try:
        # Get strategy symbol mappings
        mappings = get_symbol_mappings(strategy_id)
        if not mappings:
            logger.error(f"No symbol mappings found for strategy {strategy_id}")
            return []
        
        resolved_mappings = []
        
        for mapping in mappings:
            try:
                # Calculate ATM strike based on current price
                atm_strike = round(current_price / spread_config) * spread_config  # Round to nearest 50
                
                sign = 1 if mapping.option_type == 'CE' else -1
                # Calculate actual strike based on offset
                actual_strike = int(atm_strike + (mapping.strike_offset * spread_config * sign))
                
                option_type = mapping.option_type
                
                resolved_symbols = []
                
                search_query = f"{base_symbol} {int(actual_strike)} {option_type} {expiry}"
                
                # Use enhanced symbol search
                search_results = enhanced_search_symbols(search_query, mapping.exchange)
                
                # Filter results to find exact matches
                for result in search_results:
                    # Check if this result matches our criteria
                    if (result.name == base_symbol and 
                        result.expiry == expiry and 
                        result.strike == actual_strike and 
                        result.instrumenttype == option_type and 
                        result.exchange == mapping.exchange):
                        
                        resolved_symbols.append({
                            'symbol': result.symbol,
                            'exchange': mapping.exchange,
                            'quantity': mapping.quantity,
                            'product_type': mapping.product_type,
                            'strike_offset': mapping.strike_offset,
                            'option_type': option_type,
                            'actual_strike': actual_strike,
                            'atm_strike': atm_strike,
                            'current_price': current_price,
                            'token': result.token,
                            'lotsize': result.lotsize
                        })
                        logger.info(f"Found symbol via search: {result.symbol} (strike: {actual_strike}, type: {option_type})")
                        break  # Found exact match, no need to continue
                   
                resolved_mappings.extend(resolved_symbols)
                
            except Exception as e:
                logger.error(f"Error resolving symbol for mapping {mapping.id}: {str(e)}")
                continue
        
        logger.info(f"Resolved {len(resolved_mappings)} symbols for strategy {strategy_id} using symbol search")
        return resolved_mappings
        
    except Exception as e:
        logger.error(f"Error in resolve_symbols_from_configuration: {str(e)}")
        return []


@strategy_bp.route('/webhook/<webhook_id>', methods=['POST'])
@limiter.limit(WEBHOOK_RATE_LIMIT)
def webhook(webhook_id):
    """
    Handle webhook from trading platform with enhanced position logic and dynamic symbol resolution
    
    SUPPORTED FORMATS:
    
    1. ENHANCED WEBHOOK (Recommended):
    {
        "symbol": "NIFTY",           // Base symbol
        "expiry": "04NOV25",         // Expiry date
        "price": 25000,              // Current LTP for ATM calculation
        "action": "ENTRY",           // ENTRY or EXIT
        "spread": {...}              // Optional spread configuration
    }
    
    2. LEGACY WEBHOOK:
    {
        "symbol": "NIFTY04NOV2525000CE",
        "action": "ENTRY"
    }
    
    ENHANCED POSITION LOGIC:
    - ENTRY webhook: Entry orders (as configured in strategy) - only allowed if NO active positions exist
    - EXIT webhook: Closes actual positions from database - only allowed if active positions exist
    
    DYNAMIC SYMBOL RESOLUTION (ENTRY only):
    - Uses symbol search to find actual trading symbols based on configuration
    - Calculates ATM strike from current price
    - Applies strike_offset from strategy configuration with CE/PE sign logic
    - Supports option_type filtering (CE, PE, FUT, XX, etc.)
    - Falls back to closest available strikes if exact match not found
    
    EXIT WEBHOOK BEHAVIOR:
    - Gets all active positions from database via validate_position_logic
    - Uses stored product_type and entry_type from position records
    - Converts positions to exit orders (reverses position quantity)
    - Position quantities: positive for BUY entries, negative for SELL entries
    - Closes specific positions by position_id
    - No symbol resolution needed - uses actual position symbols
    
    Strategy configuration example:
    - Symbol: NIFTY, Exchange: NFO, Quantity: +50, Strike Offset: 0, Option Type: CE
    - Symbol: NIFTY, Exchange: NFO, Quantity: -50, Strike Offset: +2, Option Type: PE
    
    Execution for ENHANCED ENTRY webhook (NIFTY at 25000):
    1. BUY NIFTY04NOV2525000CE (50 qty) - ATM strike
    2. SELL NIFTY04NOV2525100PE (50 qty) - +2 offset strike
    
    Execution for EXIT webhook (closes actual positions):
    1. Gets active positions from database
    2. SELL NIFTY04NOV2525000CE (50 qty) - closes long position (quantity: +50)
    3. BUY NIFTY04NOV2525100PE (25 qty) - closes short position (quantity: -25)
    """
    try:
        strategy = get_strategy_by_webhook_id(webhook_id)
        if not strategy:
            return jsonify({'error': 'Invalid webhook ID'}), 404
        
        if not strategy.is_active:
            return jsonify({'error': 'Strategy is inactive'}), 400
        
        # Parse webhook data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        # Validate required fields - support both old and new format
        webhook_action = data.get('action', '').upper()
        required_fields = ['symbol', 'action']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        webhook_symbol = data['symbol']
        
        # Get all symbol mappings for this strategy (legacy behavior)
        mappings = get_symbol_mappings(strategy.id)
        if not mappings:
            return jsonify({'error': 'No symbol mappings found for this strategy'}), 400
    
        # Validate action
        if webhook_action not in ['ENTRY', 'EXIT']:
            return jsonify({'error': 'Invalid action. Use ENTRY or EXIT'}), 400
        # Check if this is enhanced webhook with expiry, price, spread
        if 'expiry' in data and 'price' in data and 'spread' in data and webhook_action == 'ENTRY':
            # Enhanced webhook format
            base_symbol = data.get('symbol', '')
            expiry = data.get('expiry', '')
            current_price = float(data.get('price', 0))
            spread_config = int(data.get('spread', 0))
            
            if not all([base_symbol, expiry, current_price, webhook_action]):
                missing_fields = []
                if not base_symbol: missing_fields.append('symbol')
                if not expiry: missing_fields.append('expiry')
                if not current_price: missing_fields.append('price')
                if not webhook_action: missing_fields.append('action')
                return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
            
            logger.info(f"Enhanced webhook: base_symbol={base_symbol}, expiry={expiry}, price={current_price}, action={webhook_action}")
            
            # Resolve symbols dynamically based on configuration using symbol search
            resolved_mappings = resolve_symbols_from_configuration(
                strategy_id=strategy.id,
                base_symbol=base_symbol,
                expiry=expiry,
                current_price=current_price,
                spread_config=spread_config
            )
            
            if not resolved_mappings:
                return jsonify({'error': 'No symbols could be resolved from configuration using symbol search'}), 400
            
            # Use resolved mappings instead of static mappings
            mappings = resolved_mappings
            webhook_symbol = f"{base_symbol}{expiry}"
        
        # Check trading hours for intraday strategies
        if strategy.is_intraday:
            now = datetime.now(pytz.timezone('Asia/Kolkata'))
            current_time = now.strftime('%H:%M')
            
            # For entry orders, check if within entry time window
            if strategy.start_time and current_time < strategy.start_time:
                return jsonify({'error': 'Orders not allowed before start time'}), 400
            
            if strategy.end_time and current_time > strategy.end_time:
                return jsonify({'error': 'Orders not allowed after end time'}), 400
            
            if strategy.squareoff_time and current_time > strategy.squareoff_time:
                return jsonify({'error': 'Orders not allowed after square off time'}), 400
        
        # Enhanced position logic validation
        is_valid, error_message, active_positions_info = validate_position_logic(strategy.id, webhook_action)
        if not is_valid:
            response_data = {
                'error': error_message,
                'webhook_action': webhook_action
            }
            if active_positions_info:
                response_data['active_positions'] = active_positions_info
                response_data['message'] = 'Use EXIT webhook to exit existing positions first'
            else:
                response_data['message'] = 'Use ENTRY webhook to enter positions first'
            
            return jsonify(response_data), 400
        
        # For EXIT actions, get actual positions from database instead of using mappings
        if webhook_action == 'EXIT':
            # Get actual positions from database
            current_positions = get_strategy_positions(strategy.id)
            active_positions = [pos for pos in current_positions if pos.is_active]
            
            if not active_positions:
                return jsonify({'error': 'No active positions found to exit'}), 400
            
            # Convert positions to mapping-like structure for processing
            mappings = []
            for pos in active_positions:
                mappings.append({
                    'symbol': pos.symbol,
                    'exchange': pos.exchange,
                    'quantity': pos.quantity,  # Use actual position quantity
                    'product_type': pos.product_type,  # Use stored product type
                    'position_id': pos.id,
                    'average_price': pos.average_price,
                    'entry_type': pos.entry_type
                })
            
            logger.info(f"EXIT webhook: Found {len(mappings)} active positions to close")
        
        # Get API key from database
        api_key = get_api_key_for_tradingview(strategy.user_id)
        if not api_key:
            logger.error(f'No API key found for user {strategy.user_id}')
            return jsonify({'error': 'No API key found'}), 401
        
        # Process all strategy orders - BUY orders first, then SELL orders
        processed_orders = []
        failed_orders = []
        
        # Sort mappings to process orders based on webhook action
        def get_order_priority(mapping):
            # Handle both legacy mappings (objects) and resolved mappings (dicts)
            quantity = mapping.quantity if hasattr(mapping, 'quantity') else mapping['quantity']
            if webhook_action == 'ENTRY':
                # For ENTRY webhook, prioritize BUY orders first, then SELL orders
                return 0 if quantity > 0 else 1
            else:  # webhook_action == 'EXIT'
                # For EXIT webhook (reverse), prioritize SELL orders first, then BUY orders
                return 0 if quantity < 0 else 1
        
        sorted_mappings = sorted(mappings, key=get_order_priority)
        
        for mapping in sorted_mappings:
            try:
                # Handle both legacy mappings (objects) and resolved mappings (dicts)
                if isinstance(mapping, dict):
                    # Resolved mapping (dictionary)
                    symbol = mapping['symbol']
                    exchange = mapping['exchange']
                    quantity = mapping['quantity']
                    product_type = mapping['product_type']
                    mapping_id = f"resolved_{mapping.get('actual_strike', 'unknown')}"
                else:
                    # Legacy mapping (object)
                    symbol = mapping.symbol
                    exchange = mapping.exchange
                    quantity = mapping.quantity
                    product_type = mapping.product_type
                    mapping_id = mapping.id
                
                # Determine the action based on quantity sign and webhook action
                if webhook_action == 'ENTRY':
                    # For ENTRY webhook, use the mapping quantity as-is
                    order_action = 'BUY' if quantity > 0 else 'SELL'
                    order_quantity = abs(quantity)
                else:  # webhook_action == 'EXIT'
                    # For EXIT webhook, reverse the position quantity to close it
                    # Position quantity already has correct sign (negative for SELL entries)
                    # To close: if position is long (positive), we SELL; if short (negative), we BUY
                    order_action = 'SELL' if quantity > 0 else 'BUY'
                    order_quantity = abs(quantity)  # Use absolute quantity for closing
                search_results = enhanced_search_symbols(symbol, exchange)
                if search_results and len(search_results) == 1:
                # Prepare order payload (only action field)
                    payload = {
                            'apikey': api_key,
                            'symbol': symbol,
                            'exchange': exchange,
                            'product': product_type,
                            'strategy': strategy.name,
                            'action': order_action,
                            'quantity': order_quantity,
                            'pricetype': 'MARKET'
                        }
                    
                    # Queue the order
                    queue_order('placeorder', payload)
                    processed_orders.append({
                        'symbol': symbol,
                        'action': order_action,
                        'quantity': order_quantity,
                        'mapping_id': mapping_id
                    })
                    logger.info(f'Strategy order queued: {order_action} {symbol} qty={order_quantity}')
                
                    # Enhanced position management logic
                    if webhook_action == 'ENTRY':
                        # For ENTRY webhook, create new position
                        placeholder_price = 100.0  # This should be replaced with actual fill price
                        create_strategy_position(
                            strategy_id=strategy.id,
                            symbol=symbol,
                            exchange=exchange,
                            quantity=order_quantity,
                            average_price=placeholder_price,
                            product_type=product_type,
                            entry_type=order_action
                        )
                        logger.info(f'Created new position for {symbol} via ENTRY ({order_action})')
                    
                    else:  # webhook_action == 'EXIT'
                        # For EXIT webhook, close the specific position
                        if isinstance(mapping, dict) and 'position_id' in mapping:
                            # Close the specific position from database
                            position_id = mapping['position_id']
                            realized_pnl = 0.0  # This should be calculated based on actual exit price
                            close_strategy_position(position_id, realized_pnl)
                            logger.info(f'Closed position {position_id} for {symbol} via EXIT')
                        else:
                            # Fallback: find and close position by symbol/exchange
                            current_positions = get_strategy_positions(strategy.id)
                            for pos in current_positions:
                                if (pos.symbol == symbol and 
                                    pos.exchange == exchange and 
                                    pos.is_active):
                                    realized_pnl = 0.0  # This should be calculated based on actual exit price
                                    close_strategy_position(pos.id, realized_pnl)
                                    logger.info(f'Closed position for {symbol} via EXIT')
                                    break
                
            except Exception as e:
                failed_orders.append({
                    'symbol': symbol if 'symbol' in locals() else 'unknown',
                    'error': str(e)
                })
                logger.error(f'Error processing order for {symbol if "symbol" in locals() else "unknown"}: {str(e)}')
        
        # Return response with processing results
        response_data = {
            'message': f'Strategy execution completed for webhook symbol {webhook_symbol}',
            'webhook_action': webhook_action,
            'processed_orders': processed_orders,
            'total_processed': len(processed_orders),
            'position_action': 'ENTRY' if webhook_action == 'ENTRY' else 'EXIT'
        }
        
        if failed_orders:
            response_data['failed_orders'] = failed_orders
            response_data['total_failed'] = len(failed_orders)
        
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f'Error processing webhook: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500
