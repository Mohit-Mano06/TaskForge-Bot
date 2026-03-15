import discord
import os
import asyncio
from discord.ext import commands
from mistralai.client import Mistral

TAMABOT_ID = 870295323401125948
MAX_CONVERSATION_TURNS = 5 # Change this to limit the turns

class BotChat(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.mistral = Mistral(api_key=os.getenv("MISTRAL_TOKEN"))

    async def get_tamabot_mention(self):
        """Helper to get Tamabot's mention string robustly"""
        user = self.bot.get_user(TAMABOT_ID)
        if not user:
            try:
                user = await self.bot.fetch_user(TAMABOT_ID)
            except discord.NotFound:
                return f"<@{TAMABOT_ID}>"
            except Exception:
                return f"<@{TAMABOT_ID}>"
        
        return user.mention

    @commands.command()
    async def talktamabot(self, ctx, *, message: str = "Heyyy Tamabot, Wasssup??"):
        """Start an interactive multi-turn conversation with Tamabot"""

        mention = await self.get_tamabot_mention()
        
        # Initialize conversation history
        history = [
            {"role": "system", "content": "You are Taskforge, a witty, productive, and slightly competitive Discord bot talking to another bot called Tamabot. Keep your replies short and funny."}
        ]

        current_message = message

        for turn in range(MAX_CONVERSATION_TURNS):
            # 1. Send Taskforge's message
            await ctx.send(f"{mention}: {current_message}")
            history.append({"role": "assistant", "content": current_message})

            # 2. Wait for Tamabot to reply
            def check(m):
                return m.author.id == TAMABOT_ID and m.channel == ctx.channel

            try:
                tamabot_reply = await self.bot.wait_for('message', check=check, timeout=10.0)
                history.append({"role": "user", "content": tamabot_reply.content})
            except asyncio.TimeoutError:
                return await ctx.send(f"Looks like Tamabot is ignoring me... 😔")

            # 3. Generate witty follow-up if not the last turn
            if turn < MAX_CONVERSATION_TURNS - 1:
                async with ctx.typing():
                    response = await self.mistral.chat.complete_async(
                        model="mistral-small-latest",
                        messages=history
                    )
                    current_message = response.choices[0].message.content
            else:
                async with ctx.typing():
                    history.append({"role": "system", "content": "The conversation is ending. Say goodbye to Tamabot in a witty or funny way. Keep it very short."})
                    response = await self.mistral.chat.complete_async(
                        model="mistral-small-latest",
                        messages=history
                    )
                    goodbye = response.choices[0].message.content
                await ctx.send(f"{mention}: {goodbye}")
                await ctx.send("*Conversation ended due to turn limit.*")

    @commands.command()
    async def roasttamabot(self, ctx):
        """Roast Tamabot using AI"""

        mention = await self.get_tamabot_mention()

        prompt = f"""
        You are Taskforge, a witty sarcastic savage Discord bot.

        Roast Tamabot brutally but in a funny way.

        Keep it short and funny.
        but do not repeat the same roast.
        """
        async with ctx.typing():
            response = await self.mistral.chat.complete_async(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}]
            )

            roast = response.choices[0].message.content

        await ctx.send(f"{mention}: {roast}")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from itself
        if message.author.id == self.bot.user.id:
            return

        # Check if Tamabot pinged Taskforge
        # We also check if it's NOT a reply to Taskforge's own message to avoid some loops
        is_tamabot = message.author.id == TAMABOT_ID
        mentions_me = self.bot.user.mentioned_in(message)

        if is_tamabot and mentions_me:
            # Short delay to look more natural and avoid instant spam
            await asyncio.sleep(2)
            
            async with message.channel.typing():
                history = [
                    {"role": "system", "content": "You are Taskforge, a witty, productive, and slightly competitive Discord bot. Tamabot just pinged you. Give a short, funny, and slightly sassy reply. Keep it under 2 sentences."},
                    {"role": "user", "content": message.content}
                ]
                try:
                    response = await self.mistral.chat.complete_async(
                        model="mistral-small-latest",
                        messages=history
                    )
                    reply = response.choices[0].message.content
                    await message.reply(reply)
                except Exception as e:
                    print(f"Error in Tamabot auto-reply: {e}")

async def setup(bot):
    await bot.add_cog(BotChat(bot))