
# CSE473 R2 (Winter 2025)
#### Name: Charles An

This is an implementation of an MCP that works Llama 3.2 3b model (though can be modified to support other Ollama models, if you wish to modify). It uses the CoinMarketCap API to provide real-time and historical information about cryptocurrencies through natural prompting on the CLI. 

Before running, please get an API key from https://coinmarketcap.com/api/ and label it COINMARKETCAP_API_KEY in .env

Then, run `python main.py` to begin chatting.


There is a test suite provided with [test_comparison.py](https://github.com/devcharlesan/coinmarketcap-mcp/blob/main/test_comparison.py) handles prompts from [test_prompts.py](https://github.com/devcharlesan/coinmarketcap-mcp/blob/main/test_prompts.py). The output is in [test_results](https://github.com/devcharlesan/coinmarketcap-mcp/blob/main/test_results/comparison_results_20250314_180718.json). Run `python test_comparison.py` to initiate testing.

## Available Tools for Llama

1. `get_crypto_price`
   - Get current cryptocurrency prices
   - Real-time market data

2. `get_crypto_price_historical`
   - Historical price data (30-day limit)
   - Supports relative (5 days ago, 17 days ago, etc.) and absolute dates (YYYY-MM-DD)

3. `get_gainers_losers`
   - Top 5 best performing and worst performing coins for the day
   - 24-hour performance metrics (% price change)

4. `get_fear_greed_latest`
   - Current market sentiment
   - Fear & Greed Index value

5. `get_fear_greed_historical`
   - Historical market sentiment (last 500 days, absolute dates)
   - Past Fear & Greed Index values

