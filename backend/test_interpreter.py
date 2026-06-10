import asyncio
from interpreter import interpreter

async def main():
    interpreter.auto_run = True
    interpreter.llm.model = "groq/llama3-8b-8192"
    interpreter.llm.api_key = "..." # Need to grab from env
    # Try a simple task
    print("Running interpreter...")
    messages = interpreter.chat("What is 10 + 10? Use python to calculate it.", display=False)
    print(messages)

if __name__ == "__main__":
    asyncio.run(main())
