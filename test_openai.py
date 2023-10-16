import os
import openai
import json
import sys  # for sys.exit

api_key = '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'

# api_key = os.environ.get('OPENAI_API_KEY')

openai.api_key = api_key

# Example API call to GPT-4
try:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Who won the world series in 2020?"},
            {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
            {"role": "user", "content": "Where was it played?"}
        ]
    )
    generated_text = response['choices'][0]['message']['content']
except Exception as e:
    print(f"An error occurred: {e}")

print(f"Generated text: {generated_text}")


