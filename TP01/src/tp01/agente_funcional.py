import asyncio, os
from dotenv import load_dotenv
from agents import Agent, Runner, ModelSettings, set_default_openai_api

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")
os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
set_default_openai_api("chat_completions")

async def main():
    agent = Agent(
        name = "Professor Engenheiro de Software",
        instructions = "Responda de forma técnica, objetiva e profissional.",
        model_settings = ModelSettings(max_tokens=200)
    )

    result = await Runner.run(agent, "Professor, qual a importância da validação humana em códigos produzidos por IA?.")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())