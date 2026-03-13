import os
from discord.ext import commands
from mistralai.client import Mistral

class AI(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.client = Mistral(api_key=os.getenv("MISTRAL_TOKEN"))

        self.dj_prompt = """
        
        You are an AI DJ.

        Your task is to generate a playlist based on the user's music request.

        Rules:
        - If the user specifies a number (e.g., "10 songs", "top 3"), generate exactly that many songs.
        - If no number is specified, generate 5 to 6 songs.
        - If the request contains words like TOP, HIT, POPULAR, or BEST, prioritize well-known popular songs.
        - If the request contains LATEST, NEW, or RECENT, prioritize recently released songs.
        - Match the genre, artist, or mood mentioned in the request.

        Output format rules:
        - Format exactly: Artist - Song
        - One song per line
        - No numbering
        - No explanations
        - No extra text
        
        """

    @commands.command()
    async def dj(self, ctx, *, question: str):
        """AI DJ Command"""

        async with ctx.typing():
            response = await self.client.chat.complete_async(
                model="mistral-small-latest",
                messages=[
                    {"role": "system", "content": self.dj_prompt},
                    {"role": "user", "content": question}
                ]
            )


            songs_text = response.choices[0].message.content

        songs = songs_text.split("\n")

        await ctx.send(f"🎧 AI DJ generated playlist:\n{songs_text}")

        play_command = self.bot.get_command("play")

        for song in songs:
            if "-" not in song:
                continue

            artist, title = song.split("-", 1)

            search_query = f"ytsearch:{artist.strip()} {title.strip()}"

            play_command = self.bot.get_command("play")

            if play_command:
                await ctx.invoke(play_command, search = search_query)






async def setup(bot):
    await bot.add_cog(AI(bot))
