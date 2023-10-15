import os
import openai

# Access the API key from environment variable
api_key = os.environ.get('OPENAI_API_KEY')

# Example API call to GPT-4
try:
    response = openai.Completion.create(
        engine="GPT-4",  # Replace with GPT-4 engine ID when available
        prompt="your-prompt-here",
        max_tokens=100,
        api_key=api_key  # Pass the API key here
    )
    generated_text = response.choices[0].text.strip()
    print(f"Generated text: {generated_text}")
except Exception as e:
    print(f"An error occurred: {e}")
