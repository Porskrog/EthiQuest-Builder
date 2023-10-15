import os
import openai
import json
import sys  # for sys.exit

api_key = os.environ.get('OPENAI_API_KEY')
print(f"API Key: {api_key}")  # Debugging line to print API key

openai.api_key = api_key

try:
    response = openai.Completion.create(
        engine="GPT-4",
        prompt="your-prompt-here",
        max_tokens=100
    )
    generated_text = response.choices[0].text.strip()
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)  # Exit the script if an error occurs

response_json = json.dumps(response)
parsed_response = json.loads(response_json)

generated_text = parsed_response['choices'][0]['text']
print(f"Generated text: {generated_text}")

