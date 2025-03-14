import os
import json
import requests
from dotenv import load_dotenv
from crypto_assistant import CryptoAssistant
from test_prompts import CRYPTO_TEST_PROMPTS

# Load environment variables
load_dotenv()

def run_basic_llm(prompt: str, model: str = "llama3.2") -> str:
    """Run a prompt through the basic LLM without tools"""
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "temperature": 0.1
                }
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get("message", {}).get("content", "Error: No response content")
    except Exception as e:
        return f"Error: {str(e)}"

def run_comparison_tests():
    """Run comparison tests between basic LLM and tool-augmented responses"""
    
    # Initialize CryptoAssistant with API key
    api_key = os.getenv("COINMARKETCAP_API_KEY")
    if not api_key:
        print("Error: COINMARKETCAP_API_KEY not found in environment variables")
        return
    
    # Initialize assistant with same settings as main.py
    assistant = CryptoAssistant(api_key, model_name="llama3.2")
    
    # Test simple generation first
    if not assistant.test_simple_generation():
        print("Simple generation test failed. Please check your Ollama setup.")
        return
    
    # Create results directory if it doesn't exist
    if not os.path.exists("test_results"):
        os.makedirs("test_results")
    
    # Store results
    results = []
    
    # Run tests
    for i, prompt in enumerate(CRYPTO_TEST_PROMPTS, 1):
        print(f"\nTesting prompt {i}/{len(CRYPTO_TEST_PROMPTS)}")
        print(f"Prompt: {prompt}")
        
        # Get basic LLM response
        print("Getting basic LLM response...")
        basic_response = run_basic_llm(prompt)
        
        # Get tool-augmented response using message history like in main.py
        print("Getting tool-augmented response...")
        messages = []
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = assistant.chat(messages)
            if "message" in response:
                assistant_message = response["message"]
                augmented_content = assistant_message.get("content", "")
                messages.append(assistant_message)
            else:
                augmented_content = f"Error: {response.get('error', 'Unknown error')}"
        except Exception as e:
            augmented_content = f"Error: {str(e)}"
        
        result = {
            "prompt": prompt,
            "basic_response": basic_response,
            "augmented_response": augmented_content
        }
        results.append(result)
        
        print("\nBasic LLM Response:")
        print(basic_response)
        print("\nTool-Augmented Response:")
        print(augmented_content)
        print("\n" + "="*80)
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"test_results/comparison_results_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to test_results/comparison_results_{timestamp}.json")

if __name__ == "__main__":
    from datetime import datetime
    print("Starting comparison tests...")
    run_comparison_tests() 