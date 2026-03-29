"""Stock query agent using Strands and Yahoo Finance."""

import logging
import json
from typing import Any, Dict, List
from pathlib import Path
import yfinance as yf
from datetime import datetime, timedelta


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)


PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(
    filename: str
) -> str:
    """Load prompt from prompts directory.

    Args:
        filename: Name of the prompt file

    Returns:
        Prompt text content
    """
    prompt_path = PROMPTS_DIR / filename

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text()


def _get_stock_price(
    ticker: str
) -> Dict[str, Any]:
    """Get current stock price for a ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')

    Returns:
        Dictionary with stock price information
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        previous_close = info.get('previousClose')

        if current_price is None:
            return {
                "error": f"Could not retrieve price for {ticker}",
                "ticker": ticker.upper()
            }

        change = None
        change_percent = None
        if previous_close:
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100

        return {
            "ticker": ticker.upper(),
            "name": info.get('longName', ticker.upper()),
            "current_price": round(current_price, 2),
            "previous_close": round(previous_close, 2) if previous_close else None,
            "change": round(change, 2) if change else None,
            "change_percent": round(change_percent, 2) if change_percent else None,
            "currency": info.get('currency', 'USD'),
            "market_state": info.get('marketState', 'UNKNOWN'),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching stock data for {ticker}: {e}")
        return {
            "error": str(e),
            "ticker": ticker.upper()
        }


def _format_market_cap_display(
    market_cap: Any
) -> str:
    """Format raw market cap number as a short human-readable string (e.g. 2.8T)."""
    if market_cap is None:
        return "N/A"
    try:
        value = float(market_cap)
    except (TypeError, ValueError):
        return str(market_cap)
    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"{value / 1e12:.1f}T"
    if abs_v >= 1e9:
        return f"{value / 1e9:.1f}B"
    if abs_v >= 1e6:
        return f"{value / 1e6:.1f}M"
    return f"{value:,.0f}"


def _compare_stocks(
    symbol1: str,
    symbol2: str
) -> Dict[str, Any]:
    """Compare two stocks side-by-side.

    Args:
        symbol1: First stock symbol (e.g., 'AAPL')
        symbol2: Second stock symbol (e.g., 'MSFT')

    Returns:
        Dictionary with comparison data for both stocks
    """
    try:
        s1 = symbol1.upper().strip()
        s2 = symbol2.upper().strip()

        price1 = _get_stock_price(s1)
        price2 = _get_stock_price(s2)

        if price1.get("error"):
            return {
                "error": price1["error"],
                "ticker": s1,
            }
        if price2.get("error"):
            return {
                "error": price2["error"],
                "ticker": s2,
            }

        info1 = _get_company_info(s1)
        info2 = _get_company_info(s2)

        name1 = price1.get("name") or info1.get("name") or s1
        name2 = price2.get("name") or info2.get("name") or s2

        return {
            "comparison": {
                "symbol1": s1,
                "symbol2": s2,
                "stock1": {
                    "symbol": s1,
                    "current_price": price1["current_price"],
                    "company_name": name1,
                    "market_cap": _format_market_cap_display(info1.get("market_cap")),
                },
                "stock2": {
                    "symbol": s2,
                    "current_price": price2["current_price"],
                    "company_name": name2,
                    "market_cap": _format_market_cap_display(info2.get("market_cap")),
                },
            }
        }

    except Exception as e:
        logger.error(f"Error comparing {symbol1} and {symbol2}: {e}")
        return {
            "error": str(e),
            "symbol1": symbol1.upper().strip(),
            "symbol2": symbol2.upper().strip(),
        }


def _get_stock_history(
    ticker: str,
    days: int = 30
) -> Dict[str, Any]:
    """Get historical stock prices.

    Args:
        ticker: Stock ticker symbol
        days: Number of days of history to retrieve (default: 30)

    Returns:
        Dictionary with historical price data
    """
    try:
        stock = yf.Ticker(ticker.upper())
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            return {
                "error": f"No historical data available for {ticker}",
                "ticker": ticker.upper()
            }

        # Get latest and earliest prices for period summary
        latest = hist.iloc[-1]
        earliest = hist.iloc[0]

        period_change = latest['Close'] - earliest['Close']
        period_change_percent = (period_change / earliest['Close']) * 100

        return {
            "ticker": ticker.upper(),
            "period_days": days,
            "start_date": hist.index[0].strftime('%Y-%m-%d'),
            "end_date": hist.index[-1].strftime('%Y-%m-%d'),
            "start_price": round(earliest['Close'], 2),
            "end_price": round(latest['Close'], 2),
            "period_change": round(period_change, 2),
            "period_change_percent": round(period_change_percent, 2),
            "high": round(hist['High'].max(), 2),
            "low": round(hist['Low'].min(), 2),
            "average_volume": int(hist['Volume'].mean()),
            "data_points": len(hist)
        }

    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}")
        return {
            "error": str(e),
            "ticker": ticker.upper()
        }


def _get_company_info(
    ticker: str
) -> Dict[str, Any]:
    """Get company information for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with company details
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        return {
            "ticker": ticker.upper(),
            "name": info.get('longName'),
            "sector": info.get('sector'),
            "industry": info.get('industry'),
            "description": info.get('longBusinessSummary'),
            "website": info.get('website'),
            "market_cap": info.get('marketCap'),
            "employees": info.get('fullTimeEmployees'),
            "country": info.get('country'),
            "exchange": info.get('exchange')
        }

    except Exception as e:
        logger.error(f"Error fetching company info for {ticker}: {e}")
        return {
            "error": str(e),
            "ticker": ticker.upper()
        }


# Tool definitions for Strands agent
STOCK_TOOLS = [
    {
        "name": "get_stock_price",
        "description": "Get the current stock price and basic information for a ticker symbol. Use this when the user asks about current price, real-time price, or latest price.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, TSLA, MSFT)"
                }
            },
            "required": ["ticker"]
        },
        "function": _get_stock_price
    },
    {
        "name": "get_stock_history",
        "description": "Get historical stock price data over a period. Use this when the user asks about price changes, trends, or historical performance.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, TSLA, MSFT)"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to retrieve (default: 30)",
                    "default": 30
                }
            },
            "required": ["ticker"]
        },
        "function": _get_stock_history
    },
    {
        "name": "get_company_info",
        "description": "Get detailed company information including sector, industry, and description. Use this when the user asks about the company itself, not just the stock price.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, TSLA, MSFT)"
                }
            },
            "required": ["ticker"]
        },
        "function": _get_company_info
    },
    {
        "name": "compare_stocks",
        "description": (
            "Compare two stocks side-by-side using current price, company name, and market cap. "
            "Use when the user asks to compare two tickers, which stock is better, or to contrast "
            "two companies (e.g. 'Compare AAPL and MSFT', 'Tesla vs Ford')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol1": {
                    "type": "string",
                    "description": "First stock symbol to compare (e.g. AAPL)",
                },
                "symbol2": {
                    "type": "string",
                    "description": "Second stock symbol to compare (e.g. MSFT)",
                },
            },
            "required": ["symbol1", "symbol2"],
        },
        "function": _compare_stocks,
    },
]


def get_system_prompt() -> str:
    """Get the system prompt for the stock agent."""
    return _load_prompt("system_prompt.txt")


def get_tool_by_name(
    tool_name: str
) -> Any:
    """Get tool function by name."""
    for tool in STOCK_TOOLS:
        if tool["name"] == tool_name:
            return tool["function"]
    return None


def execute_tool_call(
    tool_name: str,
    parameters: Dict[str, Any]
) -> str:
    """Execute a tool call and return JSON result."""
    tool_func = get_tool_by_name(tool_name)

    if not tool_func:
        return json.dumps({"error": f"Tool {tool_name} not found"})

    try:
        result = tool_func(**parameters)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return json.dumps({"error": str(e)})
