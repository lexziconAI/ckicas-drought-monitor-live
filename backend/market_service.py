import random
from datetime import datetime
from logger_config import logger

# Mock Portfolio Data
PORTFOLIO = {
    "total_value_nzd": 2384500.00,
    "cash_nzd": 180000.00,
    "daily_pnl_percent": 0.6,
    "win_rate": 0.65,
    "positions": [
        {"symbol": "AAPL", "market": "NASDAQ", "shares": 500, "current_price": 225.50, "currency": "USD", "sector": "Technology"},
        {"symbol": "MSFT", "market": "NASDAQ", "shares": 300, "current_price": 415.20, "currency": "USD", "sector": "Technology"},
        {"symbol": "TSLA", "market": "NASDAQ", "shares": 200, "current_price": 248.50, "currency": "USD", "sector": "Automotive"},
        {"symbol": "GOOGL", "market": "NASDAQ", "shares": 50, "current_price": 178.50, "currency": "USD", "sector": "Technology"},
        {"symbol": "BABA", "market": "NYSE", "shares": 1000, "current_price": 85.30, "currency": "USD", "sector": "Consumer Cyclical"},
    ]
}

# Mock Market State
MARKET_STATE = {
    "chaos_index": 0.45,
    "volatility": 0.32,
    "entropy": 0.28,
    "constitutional_score": 0.78
}

async def get_portfolio_summary():
    """Returns the current portfolio summary."""
    logger.debug("Fetching portfolio summary")
    return PORTFOLIO

async def get_position_details(symbol: str):
    """Returns details for a specific position."""
    symbol = symbol.upper()
    logger.debug(f"Fetching position details for {symbol}")
    for pos in PORTFOLIO["positions"]:
        if pos["symbol"] == symbol:
            return pos
    logger.warning(f"Position not found: {symbol}")
    return {"error": "Position not found"}

async def get_market_headlines():
    """Returns mock market headlines."""
    logger.debug("Fetching market headlines")
    return [
        {"title": "Fed signals potential rate pause as inflation cools", "source": "Bloomberg", "impact": 8},
        {"title": "Tech sector rallies on strong earnings reports", "source": "Reuters", "impact": 7},
        {"title": "Geopolitical tensions rise in Middle East, oil spikes", "source": "CNBC", "impact": 6},
        {"title": "China announces new stimulus package for property sector", "source": "Financial Times", "impact": 5},
        {"title": "Crypto markets volatile ahead of regulatory ruling", "source": "CoinDesk", "impact": 4}
    ]

async def get_constitutional_score():
    """Returns the current constitutional alignment score."""
    logger.debug("Fetching constitutional score")
    return {
        "score": MARKET_STATE["constitutional_score"],
        "alignment": {
            "ahimsa": "aligned",
            "satya": "aligned",
            "asteya": "aligned",
            "brahmacharya": "neutral",
            "aparigraha": "aligned"
        }
    }

async def get_chaos_state():
    """Returns the current market chaos metrics."""
    logger.debug("Fetching chaos state")
    return {
        "chaos_index": MARKET_STATE["chaos_index"],
        "volatility": MARKET_STATE["volatility"],
        "entropy": MARKET_STATE["entropy"]
    }

async def prepare_trade_order(action: str, symbol: str, quantity: int):
    """Prepares a trade order for review."""
    symbol = symbol.upper()
    logger.info(f"Preparing trade order: {action} {quantity} {symbol}")
    
    price = 0
    # Find price (mock)
    for pos in PORTFOLIO["positions"]:
        if pos["symbol"] == symbol:
            price = pos["current_price"]
            break
    if price == 0:
        price = 150.00 # Default mock price for new stocks

    total_value = price * quantity
    
    # Constitutional Check (Mock)
    constitutional_score = random.uniform(0.6, 0.95)
    
    logger.info(f"Trade prepared: {action} {symbol} @ {price} (Total: {total_value}), Score: {constitutional_score:.2f}")
    
    return {
        "action": action,
        "symbol": symbol,
        "quantity": quantity,
        "estimated_price": price,
        "total_value": total_value,
        "constitutional_score": constitutional_score,
        "status": "prepared_for_review"
    }
