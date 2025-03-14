import json
import time
import threading
import sys
from dotenv import load_dotenv
from crypto_assistant import CryptoAssistant, check_ollama_running
import os

# Load environment variables from .env file
load_dotenv()

def display_tools():
    """Display the available cryptocurrency tools"""
    print("\n=== Available Cryptocurrency Tools ===")
    print("1. get_crypto_price - Get current price of a cryptocurrency")
    print("   Example: What's the price of Bitcoin? What's ETH trading at?")
    print("\n2. get_crypto_price_historical - Get historical price (past 30 days only)")
    print("   Example: What was BTC worth yesterday? ETH price 3 days ago?")
    print("\n3. get_gainers_losers - Get top gainers and losers")
    print("   Example: What are the top crypto gainers today?")
    print("\n4. get_fear_greed_latest - Get current fear and greed index")
    print("   Example: What's the crypto fear and greed index?")
    print("\n5. get_fear_greed_historical - Get historical fear and greed")
    print("   Example: What was the crypto fear and greed index last week?")
    print("\n=== Commands ===")
    print("/tools - Display this list of tools")
    print("/exit - Exit the assistant")
    print("===============================")

# Global variable to control animation thread
animation_running = False

def typing_animation():
    """Display a typing animation"""
    animation = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    global animation_running
    while animation_running:
        sys.stdout.write("\r\033[KAssistant: " + animation[i % len(animation)] + " ")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1

def main():
    """Main function to run the Crypto Assistant."""
    # Check if Ollama is running before proceeding
    if not check_ollama_running():
        exit(1)
    
    # Get API key
    api_key = os.getenv("COINMARKETCAP_API_KEY")
    print(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Initialize assistant
    assistant = CryptoAssistant(api_key, model_name="llama3.2")
    
    # Test simple generation first
    if not assistant.test_simple_generation():
        print("Simple generation test failed. Please check your Ollama setup.")
        exit(1)
    
    print("\n=== Cryptocurrency Assistant ===")
    print("Ask me anything about cryptocurrencies!")
    print("Type '/tools' to see available tools")
    print("Type '/exit' to quit.")
    print("===============================\n")
    
    # Initialize empty message history
    messages = []
    
    # Chat loop
    while True:
        user_input = input("\nYou: ")
        
        # Check for commands
        if user_input.lower() == "/exit" or user_input.lower() == "exit":
            break
            
        if user_input.lower() == "/tools" or user_input.lower() == "tools":
            display_tools()
            continue
        
        # Add user message
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Start typing animation in a separate thread
        global animation_running
        animation_running = True
        animation_thread = threading.Thread(target=typing_animation)
        animation_thread.daemon = True
        animation_thread.start()
        
        try:
            # Get response from Ollama
            response = assistant.chat(messages)
            
            # Stop typing animation
            animation_running = False
            time.sleep(0.2)  # Give thread time to exit
            
            # Clear the animation line
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            
            # Add assistant response to messages for context
            if "message" in response:
                assistant_message = response["message"]
                
                # Get the content and display it with a typing effect
                content = assistant_message.get("content", "")
                print("\nAssistant: ", end="", flush=True)
                
                # Simulate typing with a character-by-character display
                for char in content:
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    time.sleep(0.01)  # Base typing speed
                
                messages.append(assistant_message)
            elif "error" in response:
                print(f"\nAssistant: Error: {response['error']}")
        except Exception as e:
            # In case of error, make sure to stop animation
            animation_running = False
            time.sleep(0.2)  # Give thread time to exit
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            print(f"\nAssistant: An error occurred: {str(e)}")

if __name__ == "__main__":
    main()