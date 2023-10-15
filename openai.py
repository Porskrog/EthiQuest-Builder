import openai
import json

openai.api_key = "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"

response = openai.Completion.create(
  engimodel="GPT-4",
  prompt="Translate the following English text to French: '{}'",
  max_tokens=60
)

print(json.dumps(response, indent=4))
