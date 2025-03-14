import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

class CryptoTool:
    """
    A tool that integrates with CoinMarketCap API to fetch cryptocurrency data.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.headers = {
            'X-CMC_PRO_API_KEY': api_key,
            'Accept': 'application/json'
        }
    
    def get_crypto_price(self, symbol: str) -> Dict[str, Any]:
        """Get the latest price for a cryptocurrency"""
        try:
            endpoint = f"{self.base_url}/cryptocurrency/quotes/latest"
            params = {
                'symbol': symbol
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "data" in data and symbol in data["data"]:
                crypto_data = data["data"][symbol]
                quote = crypto_data.get("quote", {}).get("USD", {})
                
                return {
                    "symbol": symbol,
                    "results": [{
                        "name": crypto_data.get("name", ""),
                        "price": quote.get("price", 0),
                        "market_cap": quote.get("market_cap", 0),
                        "volume_24h": quote.get("volume_24h", 0),
                        "percent_change_24h": quote.get("percent_change_24h", 0),
                        "percent_change_7d": quote.get("percent_change_7d", 0),
                        "last_updated": quote.get("last_updated", "")
                    }]
                }
            
            return {"error": f"No data available for {symbol}"}
            
        except Exception as e:
            print(f"Error in get_crypto_price: {e}")
            return {"error": f"Failed to fetch crypto price: {e}"}
    
    def get_gainers_losers(self) -> Dict[str, Any]:
        """Get the biggest gainers and losers in the last 24 hours from top 100 coins"""
        try:
            # First get top 100 coins by market cap
            listing_endpoint = f"{self.base_url}/cryptocurrency/listings/latest"
            listing_params = {
                'limit': 100,
                'sort': 'market_cap',
                'sort_dir': 'desc',
                'convert': 'USD'
            }
            
            response = requests.get(listing_endpoint, headers=self.headers, params=listing_params)
            response.raise_for_status()
            data = response.json()
            
            result = {"gainers": [], "losers": []}
            
            if "data" in data:
                cryptos = data["data"]
                
                # Process each cryptocurrency
                for crypto in cryptos:
                    quote = crypto.get("quote", {}).get("USD", {})
                    percent_change = quote.get("percent_change_24h", 0)
                    market_cap = quote.get("market_cap", 0)
                    
                    if market_cap > 0:  # Only include coins with valid market cap
                        entry = {
                            "name": crypto.get("name", ""),
                            "symbol": crypto.get("symbol", ""),
                            "price": quote.get("price"),
                            "percent_change_24h": percent_change,
                            "market_cap": market_cap,
                            "rank": crypto.get("cmc_rank", 0)
                        }
                        
                        # Add to gainers if positive change, losers if negative
                        if percent_change > 0:
                            result["gainers"].append(entry)
                        elif percent_change < 0:
                            result["losers"].append(entry)
                
                # Sort and limit each list
                result["gainers"] = sorted(
                    result["gainers"], 
                    key=lambda x: x["percent_change_24h"], 
                    reverse=True
                )[:5]
                
                result["losers"] = sorted(
                    result["losers"], 
                    key=lambda x: x["percent_change_24h"]
                )[:5]
            
            return result
            
        except Exception as e:
            print(f"Error in get_gainers_losers: {e}")
            return {"error": f"Failed to fetch gainers-losers data: {e}"}

    def get_fear_greed_latest(self) -> Dict[str, Any]:
        """Get the latest crypto fear and greed index"""
        try:
            endpoint = "https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest"
            
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            # Debug print only visible to developers, not users
            # print(f"Fear and greed response: {data}")
            
            if "data" in data:
                # The data object can be directly accessed
                latest_data = data["data"]
                
                return {
                    "value": latest_data.get("value", 0),
                    "classification": latest_data.get("value_classification", "Unknown"),
                    "timestamp": latest_data.get("update_time", "")
                }
            
            return {"error": "No fear and greed data available"}
            
        except Exception as e:
            print(f"Error in get_fear_greed_latest: {e}")
            return {"error": f"Failed to fetch fear and greed data: {e}"}

    def get_fear_greed_historical(self, date: str) -> Dict[str, Any]:
        """Get historical crypto fear and greed index for a specific date"""
        try:
            # Validate and standardize the date format
            try:
                # Parse various date formats
                parsed_date = None
                
                # Handle MM/DD/YYYY format
                if '/' in date:
                    parts = date.split('/')
                    if len(parts) == 3:
                        month, day, year = parts
                        parsed_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                
                # Handle already formatted YYYY-MM-DD
                elif '-' in date and len(date.split('-')) == 3:
                    parsed_date = date
                    
                # Handle text dates like "November 11 2024"
                else:
                    try:
                        dt = datetime.strptime(date, "%B %d %Y")
                        parsed_date = dt.strftime("%Y-%m-%d")
                    except ValueError:
                        try:
                            dt = datetime.strptime(date, "%b %d %Y")
                            parsed_date = dt.strftime("%Y-%m-%d")
                        except ValueError:
                            pass
                
                if not parsed_date:
                    return {"error": f"Could not parse date format: {date}. Please use YYYY-MM-DD or MM/DD/YYYY format."}
                
                # Check if date is in the future
                current_date = datetime.now().date()
                requested_date = datetime.strptime(parsed_date, "%Y-%m-%d").date()
                
                if requested_date > current_date:
                    return {"error": f"Cannot get fear and greed data for future date: {parsed_date}. The Fear & Greed index is only available for past dates."}
                
                # Check if date is too far in the past (more than 500 days)
                days_difference = (current_date - requested_date).days
                if days_difference > 500:
                    return {"error": f"Cannot get fear and greed data for {parsed_date}. Data is only available for the past 500 days."}
                
                # Set the standardized date for the API request
                date = parsed_date
                    
            except Exception as e:
                return {"error": f"Invalid date format: {date}. Please use YYYY-MM-DD or MM/DD/YYYY format. Details: {e}"}
            
            # Convert the requested date to a UTC timestamp at midnight
            requested_date_obj = datetime.strptime(date, "%Y-%m-%d")
            requested_timestamp = int(requested_date_obj.replace(hour=0, minute=0, second=0).timestamp())
            
            # Get historical data
            endpoint = "https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical"
            params = {
                'limit': 500  # Get maximum number of records
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "data" in data and data["data"] and len(data["data"]) > 0:
                # Loop through all records to find the matching date
                matching_data = None
                for item in data["data"]:
                    timestamp = item.get("timestamp", "")
                    if timestamp and str(timestamp).isdigit():
                        item_timestamp = int(timestamp)
                        # Check if this timestamp matches our requested date
                        if item_timestamp == requested_timestamp:
                            matching_data = item
                            break
                
                # If no exact match, find the closest date
                if not matching_data:
                    closest_diff = float('inf')
                    for item in data["data"]:
                        timestamp = item.get("timestamp", "")
                        if timestamp and str(timestamp).isdigit():
                            item_timestamp = int(timestamp)
                            diff = abs(item_timestamp - requested_timestamp)
                            if diff < closest_diff:
                                closest_diff = diff
                                matching_data = item
                
                if matching_data:
                    # Format the readable date from the matched timestamp
                    timestamp = matching_data.get("timestamp", "")
                    if timestamp and str(timestamp).isdigit():
                        date_from_timestamp = datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d")
                    else:
                        date_from_timestamp = date
                    
                    return {
                        "value": matching_data.get("value", 0),
                        "classification": matching_data.get("value_classification", "Unknown"),
                        "timestamp": date,  # Use the requested date for display
                        "actual_date": date_from_timestamp  # Include the actual date from the timestamp
                    }
            
            return {"error": f"No fear and greed data available for {date}"}
            
        except Exception as e:
            print(f"Error in get_fear_greed_historical: {e}")
            return {"error": f"Failed to fetch historical fear and greed data: {e}"}


    def get_crypto_price_historical(self, symbol: str, date: str) -> Dict[str, Any]:
        """Get historical price for a cryptocurrency at a specific date"""
        try:
            # Debug input
            # print(f"Input: symbol={symbol}, date={date}")

            # Convert symbol to uppercase
            symbol = symbol.upper()
            
            # Get current date and time in UTC
            current_datetime = datetime.now(timezone.utc)
            
            # Store original date input for error messages
            original_date_input = date
            
            # Determine the target date
            target_date = None
            
            # CASE 1: Handle relative dates
            if isinstance(date, str) and date.lower() == "yesterday":
                target_date = current_datetime - timedelta(days=1)
                
            elif isinstance(date, str) and (date.lower() == "last week" or date.lower() == "a week ago"):
                target_date = current_datetime - timedelta(days=7)
                
            elif isinstance(date, str) and "days ago" in date.lower():
                try:
                    # Extract number
                    days_text = date.lower().split("days ago")[0].strip()
                    if not days_text:  # Handle "days ago" without a number
                        days = 1
                    else:
                        days = int(days_text)
                    
                    target_date = current_datetime - timedelta(days=days)
                except ValueError:
                    print(f"Could not parse days in: {date}")
                    return {"error": f"Could not understand the date format: {date}"}
            
            # CASE 2: Handle specific date formats
            elif isinstance(date, str) and '/' in date:
                try:
                    # MM/DD/YYYY format
                    parts = date.split('/')
                    if len(parts) != 3:
                        print(f"Invalid date format with slashes: {date}")
                        return {"error": f"Invalid date format: {date}. Use MM/DD/YYYY."}
                    
                    month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                    # Handle 2-digit years
                    if len(str(year)) == 2:
                        year = 2000 + year
                    
                    # Create date object
                    target_date = datetime(year, month, day, 
                                          hour=current_datetime.hour,
                                          minute=current_datetime.minute,
                                          tzinfo=timezone.utc)
                    print(f"Parsed date MM/DD/YYYY: {target_date.strftime('%Y-%m-%d')}")
                except ValueError as e:
                    print(f"Date parsing error: {e}")
                    return {"error": f"Invalid date values in: {date}"}
                
            # CASE 3: Handle YYYY-MM-DD format
            elif isinstance(date, str) and len(date) == 10 and '-' in date:
                try:
                    year, month, day = map(int, date.split('-'))
                    target_date = datetime(year, month, day, 
                                          hour=current_datetime.hour,
                                          minute=current_datetime.minute,
                                          tzinfo=timezone.utc)
                    print(f"Parsed date YYYY-MM-DD: {target_date.strftime('%Y-%m-%d')}")
                except ValueError as e:
                    print(f"Date parsing error: {e}")
                    return {"error": f"Invalid date format: {date}. Use YYYY-MM-DD."}
            
            # CASE 4: Unknown format
            else:
                print(f"Unrecognized date format: {date}")
                return {"error": f"Unrecognized date format: {date}. Use YYYY-MM-DD or MM/DD/YYYY."}
            
            # Ensure we have a valid date
            if target_date is None:
                print("Failed to determine target date")
                return {"error": f"Could not determine date from: {date}"}
            
            # Format date string for display
            formatted_date = target_date.strftime("%Y-%m-%d")
            
            # Check if date is in the future
            if target_date.date() > current_datetime.date():
                return {"error_future_date": f"🔮 I can't predict future prices! The date {formatted_date} is in the future."}
            
            # Check if date is too far in the past
            days_diff = (current_datetime.date() - target_date.date()).days
            
            if days_diff > 30:
                print(f"Date too far in past: {formatted_date}")
                return {"error": f"Historical price data is only available for the past 30 days. Cannot fetch data for {formatted_date}."}
            
            # Format API parameters - Use a WIDER time window (2 hours) to increase chances of finding data
            # Start 1 hour before the target time
            time_start = (target_date - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:00Z")
            # End 1 hour after the target time
            time_end = (target_date + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:00Z")
            
            
            # Request data from API
            endpoint = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical"
            params = {
                'symbol': symbol,
                'time_start': time_start,
                'time_end': time_end,
                'interval': '5m',  # Keep 5m interval for granularity
                'convert': 'USD',
                'aux': 'price'
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if "data" in data and symbol in data["data"]:
                    crypto_data = data["data"][symbol]
                    if crypto_data and len(crypto_data) > 0:
                        crypto_data = crypto_data[0]  # Take first entry for main token
                        if crypto_data.get("quotes") and len(crypto_data["quotes"]) > 0:
                            # Find the quote closest to our target time
                            quotes = crypto_data["quotes"]
                            closest_quote = quotes[0]
                            
                            # Get the quote data
                            quote_data = closest_quote.get("quote", {}).get("USD", {})
                            timestamp = closest_quote.get("timestamp", "")
                            
                            if timestamp and quote_data.get("price") is not None:
                                quote_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                actual_date = quote_time.strftime("%Y-%m-%d %H:%M UTC")
                                
                                return {
                                    "symbol": symbol,
                                    "results": [{
                                        "name": crypto_data.get("name", ""),
                                        "price": quote_data.get("price", 0),
                                        "requested_date": formatted_date,
                                        "actual_date": actual_date
                                    }]
                                }
                
                print(f"No price data found for {symbol} on {formatted_date}")
                return {"error": f"No price data available for {symbol} on {formatted_date}"}
            
            return {"error": f"No historical price data available for {symbol}"}
        except Exception as e:
            return {"error": f"Failed to fetch historical crypto price: {str(e)}"}

    # MCP specification methods
    def manifest(self) -> Dict[str, Any]:
        """Return the tool manifest for MCP"""
        return {
            "name": "coinmarketcap_tool",
            "description": "A tool for getting cryptocurrency data from CoinMarketCap",
            "inputs": {
                "type": "object",
                "properties": {
                    "function": {
                        "type": "string",
                        "enum": [
                            "get_crypto_price", 
                            "get_gainers_losers",
                            "get_fear_greed_latest",
                            "get_fear_greed_historical",
                            "get_crypto_price_historical"
                        ],
                        "description": "The function to call"
                    },
                    "arguments": {
                        "type": "object",
                        "description": "The arguments for the function"
                    }
                },
                "required": ["function", "arguments"]
            }
        }
        
    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the requested function with the given arguments"""
        function = request.get("function")
        arguments = request.get("arguments", {})
        
        if function == "get_crypto_price":
            symbol = arguments.get("symbol")
            if symbol:
                return self.get_crypto_price(symbol)
        elif function == "get_gainers_losers":
            return self.get_gainers_losers()
        elif function == "get_fear_greed_latest":
            return self.get_fear_greed_latest()
        elif function == "get_fear_greed_historical":
            date = arguments.get("date")
            if date:
                return self.get_fear_greed_historical(date)
        elif function == "get_crypto_price_historical":
            symbol = arguments.get("symbol")
            date = arguments.get("date")
            if symbol and date:
                return self.get_crypto_price_historical(symbol, date)
        
        return {"error": f"Unknown function: {function}"} 