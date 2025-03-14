import requests
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

# Import our CryptoTool class
from crypto_tool import CryptoTool

class CryptoAssistant:
    """
    A class that integrates the CryptoTool with an Ollama LLM using MCP.
    """
    
    def __init__(self, api_key: str, model_name: str = "llama3", ollama_host: str = "http://localhost:11434"):
        self.crypto_tool = CryptoTool(api_key)
        self.model_name = model_name
        self.ollama_host = ollama_host
        
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Returns the tool definition in the format expected by Ollama.
        """
        manifest = self.crypto_tool.manifest()
        
        return {
            "name": manifest["name"],
            "description": manifest["description"],
            "input_schema": manifest["inputs"]
        }
    
    def chat(self, messages: List[Dict[str, Any]], stream: bool = False) -> Any:
        """Send a chat request to Ollama using the /api/chat endpoint."""
        # Add tool information as a system message if not present
        if not any(m.get("role") == "system" for m in messages):
            tool_info = {
                "role": "system",
                "content": """You are a helpful cryptocurrency assistant. You can engage in general conversation about cryptocurrencies, blockchain, and digital assets.

IMPORTANT: When users ask about cryptocurrency prices, you MUST first determine if they are asking about:
1. CURRENT price (no date mentioned)
2. HISTORICAL price (any date or time period mentioned)

For CURRENT prices (when NO date is mentioned):
1. Identify the cryptocurrency symbol (e.g., "Bitcoin" -> "BTC")
2. Use EXACTLY:
I need to use coinmarketcap_tool
Function: get_crypto_price
Arguments: {"symbol": "SYMBOL"}

For ANY price query that includes a DATE or TIME PERIOD:
1. ALWAYS use the historical price function
2. NEVER fallback to current prices when a date is mentioned
3. Use EXACTLY:
I need to use coinmarketcap_tool
Function: get_crypto_price_historical
Arguments: {"symbol": "SYMBOL", "date": "ACTUAL_DATE_OR_TERM"}

IMPORTANT ABOUT DATES:
- Pass RELATIVE dates like "yesterday", "2 days ago", "last week" DIRECTLY as strings
- Do NOT convert relative dates to specific dates
- For example: use "yesterday" NOT "YYYY-MM-DD"
- The tool can handle relative dates directly
- Historical prices are ONLY available for the past 30 days

Examples of queries that MUST use historical prices:
- "what's the price of BTC on March 10th" -> date="3/10/2025"
- "ETH price yesterday" -> date="yesterday"
- "how much was Bitcoin worth last week" -> date="last week"
- "what was the price of ETH on 3/10/2023" -> date="3/10/2023"
- "BTC price 2 days ago" -> date="2 days ago"

Remember:
- If a date is mentioned, ALWAYS use get_crypto_price_historical
- Historical data is only available for the past 30 days
- NEVER use current prices when a date is specified
- Always pass relative date terms directly (yesterday, 2 days ago, etc.)

IMPORTANT:
When users ask about top market movers, gainers, losers, best or worst performing assets (using words like "gainers", "losers", "top movers", "best performing", "worst performing", "moving the most", etc.) you MUST respond with EXACTLY:
I need to use coinmarketcap_tool
Function: get_gainers_losers
Arguments: {}

When users EXPLICITLY ask about the CRYPTOCURRENCY fear and greed index (they must EXPLICITLY mention "crypto" or "cryptocurrency" in their question about fear and greed), you MUST respond with EXACTLY:
I need to use coinmarketcap_tool
Function: get_fear_greed_latest
Arguments: {}

When users ask about historical CRYPTOCURRENCY fear and greed for a specific date (they must EXPLICITLY mention "crypto" or "cryptocurrency" AND a specific date), you MUST respond with EXACTLY:
I need to use coinmarketcap_tool
Function: get_fear_greed_historical
Arguments: {"date": "YYYY-MM-DD"}

For example:
- If user asks "what's the price of Bitcoin", respond with:
I need to use coinmarketcap_tool
Function: get_crypto_price
Arguments: {"symbol": "BTC"}

- If user asks "what was Bitcoin worth yesterday": Calculate yesterday's date and use get_crypto_price_historical
- If user asks "what was ETH's price 3 days ago": Calculate the date from 3 days ago and use get_crypto_price_historical

IMPORTANT: 
1. Historical prices are only available for the past 30 days.
2. Do NOT trigger fear and greed functions for general questions about market sentiment or any other context outside of cryptocurrency.
3. Only use these functions when the user EXPLICITLY asks about CRYPTO fear and greed or historical prices.

If you're not sure about a cryptocurrency's symbol, ask the user to provide it.
For all other questions, respond normally without using the tool."""
            }
            messages = [tool_info] + messages
        
        # Create the request payload
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": 0.1  # Lower temperature for more consistent tool usage
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/chat",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            if "message" in result:
                content = result["message"].get("content", "")
                # Check for tool usage
                if "I need to use coinmarketcap_tool" in content:
                    tool_response = self._handle_tool_call(content)
                    if tool_response and "message" in tool_response:
                        return tool_response
                return result
            
        except Exception as e:
            print(f"Error connecting to Ollama: {e}")
            return {"error": str(e)}
    
    def _handle_tool_call(self, response: str) -> Dict:
        """Handle tool call and execute the tool"""
        try:
            # Extract function name and arguments
            function_match = re.search(r"Function: (\w+)", response)
            args_match = re.search(r"Arguments: ({.*})", response, re.DOTALL)
            
            if not function_match or not args_match:
                return {
                    "message": {
                        "role": "assistant",
                        "content": response
                    }
                }
            
            function_name = function_match.group(1)
            args_str = args_match.group(1)
            
            try:
                arguments = json.loads(args_str)
                result = self.crypto_tool.execute({
                    "function": function_name,
                    "arguments": arguments
                })
                
                follow_up = self._generate_follow_up(function_name, result)
                if follow_up:
                    return {
                        "message": {
                            "role": "assistant",
                            "content": follow_up
                        }
                    }
                
                return {
                    "message": {
                        "role": "assistant",
                        "content": f"I encountered an error processing your request."
                    }
                }
                
            except json.JSONDecodeError:
                return {
                    "message": {
                        "role": "assistant",
                        "content": "I encountered an error parsing the arguments."
                    }
                }
            
        except Exception as e:
            print(f"Error handling tool call: {e}")
            return {
                "message": {
                    "role": "assistant",
                    "content": "I encountered an error processing your request."
                }
            }
    
    def _generate_follow_up(self, function_name: str, result: Dict[str, Any]) -> Optional[str]:
        """Generate a follow-up response based on the tool result"""
        try:
            if "error" in result:
                # Special handling for errors like future dates or invalid formats
                if "future date" in result["error"]:
                    return f"🔮 I can't predict the future! {result['error']}"
                elif "Invalid date format" in result["error"] or "Could not parse date format" in result["error"]:
                    return f"📅 {result['error']}"
                else:
                    return f"I encountered an error: {result['error']}"
            
            # Handle crypto price response
            if function_name == "get_crypto_price" and "results" in result:
                crypto_data = result["results"][0]
                symbol = result.get("symbol", "").upper()
                name = crypto_data.get("name", "")
                price = crypto_data.get("price")
                change_24h = crypto_data.get("percent_change_24h", 0)
                change_7d = crypto_data.get("percent_change_7d", 0)
                
                # Handle None price
                if price is None:
                    return f"I couldn't find current price data for {name} ({symbol})."
                
                formatted_price = f"${price:,.2f}" if price >= 1 else f"${price:.8f}"
                
                direction_24h = "up" if change_24h > 0 else "down"
                direction_7d = "up" if change_7d > 0 else "down"
                
                return (f"{name} ({symbol}) is currently trading at {formatted_price}, "
                       f"{direction_24h} {abs(change_24h):.2f}% in the last 24 hours and "
                       f"{direction_7d} {abs(change_7d):.2f}% in the last 7 days.")
            
            # Handle gainers and losers
            elif function_name == "get_gainers_losers":
                gainers = result.get("gainers", [])
                losers = result.get("losers", [])
                
                if not gainers and not losers:
                    return "I couldn't find gainers and losers data at the moment."
                
                response = "Here are the top gainers and losers from the top 100 cryptocurrencies in the last 24 hours:\n\n"
                
                if gainers:
                    response += "🚀 TOP GAINERS:\n"
                    for gainer in gainers:
                        price = gainer['price']
                        if price is not None:
                            price_str = f"${price:,.2f}" if price >= 1 else f"${price:.8f}"
                            response += f"   {gainer['name']} ({gainer['symbol']}) #{gainer['rank']}: "
                            response += f"{price_str} (+{gainer['percent_change_24h']:.2f}%)\n"
                        else:
                            response += f"   {gainer['name']} ({gainer['symbol']}) #{gainer['rank']}: "
                            response += f"Price unavailable (+{gainer['percent_change_24h']:.2f}%)\n"
                    response += "\n"
                
                if losers:
                    response += "📉 TOP LOSERS:\n"
                    for loser in losers:
                        price = loser['price']
                        if price is not None:
                            price_str = f"${price:,.2f}" if price >= 1 else f"${price:.8f}"
                            response += f"   {loser['name']} ({loser['symbol']}) #{loser['rank']}: "
                            response += f"{price_str} ({loser['percent_change_24h']:.2f}%)\n"
                        else:
                            response += f"   {loser['name']} ({loser['symbol']}) #{loser['rank']}: "
                            response += f"Price unavailable ({loser['percent_change_24h']:.2f}%)\n"
                
                return response.strip()
            
            # Handle fear and greed latest
            elif function_name == "get_fear_greed_latest":
                if "value" in result:
                    value = result["value"]
                    classification = result["classification"]
                    
                    return f"🎯 Current Crypto Fear & Greed Index: {value} - {classification}"
            
            # Handle fear and greed historical
            elif function_name == "get_fear_greed_historical":
                if "error" in result:
                    # Special handling for errors like future dates or invalid formats
                    if "future date" in result["error"]:
                        return f"🔮 I can't predict the future! {result['error']}"
                    elif "Invalid date format" in result["error"] or "Could not parse date format" in result["error"]:
                        return f"📅 {result['error']}"
                    else:
                        return f"I encountered an error: {result['error']}"
                
                if "value" in result:
                    value = result["value"]
                    classification = result["classification"]
                    requested_date = result.get("timestamp", "")
                    actual_date = result.get("actual_date", "")
                    
                    # Display note if actual date differs from requested date
                    date_info = requested_date
                    
                    return f"📅 Crypto Fear & Greed Index for {date_info}: {value} - {classification}"
            
            # Handle historical price response
            elif function_name == "get_crypto_price_historical":
                if "error_future_date" in result:
                    return result["error_future_date"]  # Return the friendly future date message directly
                elif "error" in result:
                    return f"I encountered an error: {result['error']}"
                
                if "results" in result:
                    crypto_data = result["results"][0]
                    symbol = result.get("symbol", "").upper()
                    name = crypto_data.get("name", "")
                    price = crypto_data.get("price")
                    requested_date = crypto_data.get("requested_date", "")
                    actual_date = crypto_data.get("actual_date", "")
                    
                    # Handle None price
                    if price is None:
                        return f"I couldn't find historical price data for {name} ({symbol}) on {requested_date}."
                    
                    formatted_price = f"${price:,.2f}" if price >= 1 else f"${price:.8f}"
                    
                    # Display note if actual date differs significantly from requested date
                    date_info = requested_date
                    if actual_date and actual_date != requested_date:
                        date_info = f"{requested_date} (data from {actual_date})"
                    
                    return f"💰 {name} ({symbol}) price on {date_info}: {formatted_price}"
            
            return "I couldn't process the requested information."
                
        except Exception as e:
            print(f"Error generating follow-up: {e}")
            return None
    
    def check_model_availability(self, model_name):
        """Check if the requested model is available in Ollama"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model.get('name') for model in models]
                
                if model_name in model_names:
                    return True
                else:
                    print(f"⚠️ Model '{model_name}' not found. Available models: {', '.join(model_names)}")
                    return False
            else:
                print(f"⚠️ Failed to get model list: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error checking model availability: {e}")
            return False

    def test_simple_generation(self):
        """Test a simple chat to check if the model is responding properly"""
        messages = [
            {
                "role": "user",
                "content": "Hello! Please respond with a simple greeting."
            }
        ]
        
        try:
            # this was for debugging if Ollama was connected, no need to print
            # print("\n=== Testing simple chat ===")
            response = requests.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.2
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            
            if "message" in result:
            # this was for debugging if Ollama was connected, no need to print
                # print(f"Response: {result['message'].get('content', '')}")
                return True
            return False
        except Exception as e:
            print(f"Error in test chat: {e}")
            return False

def check_ollama_running():
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get("http://localhost:11434/api/version")
        if response.status_code == 200:
            print("✅ Ollama is running!")
            return True
        else:
            print(f"⚠️ Ollama returned unexpected status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Ollama is not running. Please start Ollama first!")
        print("   Run 'ollama serve' in your terminal.")
        return False 