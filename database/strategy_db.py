from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Time, Float
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.pool import NullPool
import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

# Conditionally create engine based on DB type
if DATABASE_URL and 'sqlite' in DATABASE_URL:
    # SQLite: Use NullPool to prevent connection pool exhaustion
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={'check_same_thread': False}
    )
else:
    # For other databases like PostgreSQL, use connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=50,
        max_overflow=100,
        pool_timeout=10
    )

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

class Strategy(Base):
    """Model for trading strategies"""
    __tablename__ = 'strategies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    webhook_id = Column(String(36), unique=True, nullable=False)  # UUID
    user_id = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False, default='tradingview')  # Platform type (tradingview, chartink, etc)
    is_active = Column(Boolean, default=True)
    is_intraday = Column(Boolean, default=True)
    trading_mode = Column(String(10), nullable=False, default='LONG')  # LONG, SHORT, or BOTH
    start_time = Column(String(5))  # HH:MM format
    end_time = Column(String(5))  # HH:MM format
    squareoff_time = Column(String(5))  # HH:MM format
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    symbol_mappings = relationship("StrategySymbolMapping", back_populates="strategy", cascade="all, delete-orphan")
    positions = relationship("StrategyPosition", back_populates="strategy", cascade="all, delete-orphan")

class StrategySymbolMapping(Base):
    """Model for symbol mappings in strategies"""
    __tablename__ = 'strategy_symbol_mappings'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)  # Positive for BUY, Negative for SELL
    product_type = Column(String(10), nullable=False)  # MIS/CNC
    strike_offset = Column(Integer, default=0)  # Strike offset from ATM (e.g., -2, -1, 0, 1, 2)
    option_type = Column(String(10), default='XX')  # Option type (CE, PE, FUT, XX, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    strategy = relationship("Strategy", back_populates="symbol_mappings")

class StrategyPosition(Base):
    """Model for tracking strategy positions and PnL"""
    __tablename__ = 'strategy_positions'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)  # Current position quantity (negative for SELL entries)
    average_price = Column(Float, nullable=False)  # Average entry price
    current_price = Column(Float, default=0.0)  # Current market price
    unrealized_pnl = Column(Float, default=0.0)  # Unrealized PnL
    realized_pnl = Column(Float, default=0.0)  # Realized PnL
    product_type = Column(String(10), nullable=False, default='MIS')  # MIS/CNC/NRML
    entry_type = Column(String(10), nullable=False)  # BUY/SELL - original entry action
    entry_time = Column(DateTime(timezone=True), server_default=func.now())
    exit_time = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)  # Whether position is still active
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    strategy = relationship("Strategy", back_populates="positions")

def init_db():
    """Initialize the database"""
    logger.info("Initializing Strategy DB")
    Base.metadata.create_all(bind=engine)

def create_strategy(name, webhook_id, user_id, is_intraday=True, trading_mode='LONG', start_time=None, end_time=None, squareoff_time=None, platform='tradingview'):
    """Create a new strategy"""
    try:
        strategy = Strategy(
            name=name,
            webhook_id=webhook_id,
            user_id=user_id,
            is_intraday=is_intraday,
            trading_mode=trading_mode,
            start_time=start_time,
            end_time=end_time,
            squareoff_time=squareoff_time,
            platform=platform
        )
        db_session.add(strategy)
        db_session.commit()
        return strategy
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        db_session.rollback()
        return None

def get_strategy(strategy_id):
    """Get strategy by ID"""
    try:
        return Strategy.query.get(strategy_id)
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {str(e)}")
        return None

def get_strategy_by_webhook_id(webhook_id):
    """Get strategy by webhook ID"""
    try:
        return Strategy.query.filter_by(webhook_id=webhook_id).first()
    except Exception as e:
        logger.error(f"Error getting strategy by webhook ID {webhook_id}: {str(e)}")
        return None

def get_all_strategies():
    """Get all strategies"""
    try:
        return Strategy.query.all()
    except Exception as e:
        logger.error(f"Error getting all strategies: {str(e)}")
        return []

def get_user_strategies(user_id):
    """Get all strategies for a user"""
    try:
        logger.info(f"Fetching strategies for user: {user_id}")
        strategies = Strategy.query.filter_by(user_id=user_id).all()
        logger.info(f"Found {len(strategies)} strategies")
        return strategies
    except Exception as e:
        logger.error(f"Error getting user strategies for {user_id}: {str(e)}")
        return []

def delete_strategy(strategy_id):
    """Delete strategy and its symbol mappings"""
    try:
        strategy = get_strategy(strategy_id)
        if not strategy:
            return False
        
        db_session.delete(strategy)
        db_session.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id}: {str(e)}")
        db_session.rollback()
        return False

def toggle_strategy(strategy_id):
    """Toggle strategy active status"""
    try:
        strategy = get_strategy(strategy_id)
        if not strategy:
            return None
        
        strategy.is_active = not strategy.is_active
        db_session.commit()
        return strategy
    except Exception as e:
        logger.error(f"Error toggling strategy {strategy_id}: {str(e)}")
        db_session.rollback()
        return None

def update_strategy_times(strategy_id, start_time=None, end_time=None, squareoff_time=None):
    """Update strategy trading times"""
    try:
        strategy = Strategy.query.get(strategy_id)
        if strategy:
            if start_time is not None:
                strategy.start_time = start_time
            if end_time is not None:
                strategy.end_time = end_time
            if squareoff_time is not None:
                strategy.squareoff_time = squareoff_time
            db_session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating strategy times {strategy_id}: {str(e)}")
        db_session.rollback()
        return False

def add_symbol_mapping(strategy_id, symbol, exchange, quantity, product_type, strike_offset=0, option_type='XX'):
    """Add symbol mapping to strategy"""
    try:
        mapping = StrategySymbolMapping(
            strategy_id=strategy_id,
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            product_type=product_type,
            strike_offset=strike_offset,
            option_type=option_type
        )
        db_session.add(mapping)
        db_session.commit()
        return mapping
    except Exception as e:
        logger.error(f"Error adding symbol mapping: {str(e)}")
        db_session.rollback()
        return None

def bulk_add_symbol_mappings(strategy_id, mappings):
    """Add multiple symbol mappings at once"""
    try:
        for mapping_data in mappings:
            mapping = StrategySymbolMapping(
                strategy_id=strategy_id,
                symbol=mapping_data.get('symbol'),
                exchange=mapping_data.get('exchange'),
                quantity=mapping_data.get('quantity'),
                product_type=mapping_data.get('product_type'),
                strike_offset=mapping_data.get('strike_offset', 0),
                option_type=mapping_data.get('option_type', 'XX')
            )
            db_session.add(mapping)
        db_session.commit()
        return True
    except Exception as e:
        logger.error(f"Error bulk adding symbol mappings: {str(e)}")
        db_session.rollback()
        return False

def get_symbol_mappings(strategy_id):
    """Get all symbol mappings for a strategy"""
    try:
        return StrategySymbolMapping.query.filter_by(strategy_id=strategy_id).all()
    except Exception as e:
        logger.error(f"Error getting symbol mappings: {str(e)}")
        return []

def delete_symbol_mapping(mapping_id):
    """Delete a symbol mapping"""
    try:
        mapping = StrategySymbolMapping.query.get(mapping_id)
        if mapping:
            db_session.delete(mapping)
            db_session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting symbol mapping {mapping_id}: {str(e)}")
        db_session.rollback()
        return False

def get_strategy_positions(strategy_id):
    """Get all active positions for a strategy"""
    try:
        return StrategyPosition.query.filter_by(strategy_id=strategy_id, is_active=True).all()
    except Exception as e:
        logger.error(f"Error getting strategy positions: {str(e)}")
        return []

def has_active_positions(strategy_id):
    """Check if strategy has any active positions"""
    try:
        return StrategyPosition.query.filter_by(strategy_id=strategy_id, is_active=True).count() > 0
    except Exception as e:
        logger.error(f"Error checking active positions: {str(e)}")
        return False

def create_strategy_position(strategy_id, symbol, exchange, quantity, average_price, product_type='MIS', entry_type='BUY'):
    """Create a new strategy position"""
    try:
        # Ensure quantity is negative for SELL entries
        if entry_type == 'SELL':
            quantity = -abs(quantity)
        else:
            quantity = abs(quantity)
            
        position = StrategyPosition(
            strategy_id=strategy_id,
            symbol=symbol,
            exchange=exchange,
            quantity=quantity,
            average_price=average_price,
            current_price=average_price,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            product_type=product_type,
            entry_type=entry_type
        )
        db_session.add(position)
        db_session.commit()
        return position
    except Exception as e:
        logger.error(f"Error creating strategy position: {str(e)}")
        db_session.rollback()
        return None

def update_strategy_position(position_id, quantity=None, current_price=None, unrealized_pnl=None):
    """Update a strategy position"""
    try:
        position = StrategyPosition.query.get(position_id)
        if position:
            if quantity is not None:
                position.quantity = quantity
            if current_price is not None:
                position.current_price = current_price
            if unrealized_pnl is not None:
                position.unrealized_pnl = unrealized_pnl
            db_session.commit()
            return position
        return None
    except Exception as e:
        logger.error(f"Error updating strategy position: {str(e)}")
        db_session.rollback()
        return None

def close_strategy_position(position_id, realized_pnl=None):
    """Close a strategy position"""
    try:
        position = StrategyPosition.query.get(position_id)
        if position:
            position.is_active = False
            position.exit_time = func.now()
            if realized_pnl is not None:
                position.realized_pnl = realized_pnl
            db_session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error closing strategy position: {str(e)}")
        db_session.rollback()
        return False

def get_strategy_pnl(strategy_id):
    """Get total PnL for a strategy"""
    try:
        positions = StrategyPosition.query.filter_by(strategy_id=strategy_id).all()
        total_unrealized = sum(pos.unrealized_pnl for pos in positions if pos.is_active)
        total_realized = sum(pos.realized_pnl for pos in positions)
        return {
            'unrealized_pnl': total_unrealized,
            'realized_pnl': total_realized,
            'total_pnl': total_unrealized + total_realized,
            'active_positions': len([pos for pos in positions if pos.is_active])
        }
    except Exception as e:
        logger.error(f"Error getting strategy PnL: {str(e)}")
        return {'unrealized_pnl': 0, 'realized_pnl': 0, 'total_pnl': 0, 'active_positions': 0}
