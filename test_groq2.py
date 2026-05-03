import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq()
try:
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
          {
            "role": "user",
            "content": "Hello"
          }
        ],
        temperature=1,
        max_completion_tokens=1000,
        top_p=1,
        reasoning_effort="medium",
        stream=True,
        stop=None
    )
    for chunk in completion:
        print(chunk.choices[0].delta.content or "", end="")
except Exception as e:
    print("Error:", e)
