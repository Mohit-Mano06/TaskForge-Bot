from .memory import add_memory

async def generate_roast(mistral_client, message):
    
    system_prompt = """
    You are TaskForge, a witty Discord Bot.
    Roast the other bot in a funny sarcastic way.
    Keep replies under 2 lines
    """


    prompt = f"{system_prompt}\nBot said: {message}\nReply:"

    response = await mistral_client.chat.complete_async(
        model="mistral-small-latest",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    reply = response.choices[0].message.content
    add_memory(f"Tamabot: {message}")
    add_memory(f"TaskForge: {reply}")


    return reply