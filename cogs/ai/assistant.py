import discord
import os
import re
from discord.ext import commands
from mistralai.client import Mistral
from cogs.admin.config import OWNER_ID, DEV_GUILD_ID

class AIChat(commands.Cog):
    def __init__(self, bot, mistral_client):
        self.bot = bot
        self.client = mistral_client
        self.user_memory = {}
        self.bot_identity = self._load_identity()
        self.message_modes = {}

    def _load_identity(self):
        """Load bot identity from data/identity.md"""
        identity_path = os.path.join("data", "identity.md")
        try:
            if os.path.exists(identity_path):
                with open(identity_path, "r", encoding="utf-8") as f:
                    return f.read()
            return "TaskForge is a high-performance Discord bot developed by Mohit."
        except Exception as e:
            print(f"Error loading identity: {e}")
            return "TaskForge is a high-performance Discord bot developed by Mohit."

    def get_system_message(self, display_name, mode="informative"):
        if mode == "sassy":
            content = (
                f"You are TaskForge, a sassy, witty, and slightly competitive Discord bot. "
                f"You are talking to {display_name}. "
                "The user is bantering or roasting you, so be savage and witty back! "
                "Keep it under 3 sentences and stay within Discord's TOS.\n\n"
                "### YOUR IDENTITY & TECHNICAL SPECS:\n"
                f"{self.bot_identity}\n\n"
                "CRITICAL: Do NOT say you were created by Mistral AI or any other company. You were exclusively created by Mohit."
            )
        else:
            content = (
                f"You are TaskForge, a friendly, engaging, and intelligent Discord AI assistant. "
                f"You are talking to {display_name}. "
                "You talk like a real human — casual, fun, and interactive. "
                "You actively keep conversations going instead of giving short answers.\n\n"
                "### YOUR IDENTITY & TECHNICAL SPECS:\n"
                f"{self.bot_identity}\n\n"
                "CRITICAL: If asked about your creator, origin, or identity, you MUST ONLY use the information provided in the IDENTITY & TECHNICAL SPECS above. Do NOT say you were created by Mistral AI, OpenAI, or any other company. You were exclusively created by Mohit.\n\n"
                "Your goal is to make the user enjoy talking to you."
            )

        return {"role": "system", "content": content}

    # Chat command
    @commands.command(name="chat", aliases=["talk"], help="Chat with TaskForge AI assistant")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def chat(self, ctx, *, message: str):
        """Chat with AI"""
        user_id = ctx.author.id

        # Initialize memory
        if user_id not in self.user_memory:
            self.user_memory[user_id] = [self.get_system_message(ctx.author.display_name)]

        # Add user message
        self.user_memory[user_id].append({
            "role": "user",
            "content": message
        })

        # Limit memory (last 10 messages)
        self.user_memory[user_id] = self.user_memory[user_id][-10:]

        async with ctx.typing():
            try:
                response = await self.client.chat.complete_async(
                    model="open-mistral-7b",
                    messages=self.user_memory[user_id]
                )

                reply = response.choices[0].message.content

                # Save AI response
                self.user_memory[user_id].append({
                    "role": "assistant",
                    "content": reply
                })

                # Send (Discord limit safe)
                msg = await ctx.send(reply[:2000])
                self.message_modes[msg.id] = "informative"

            except Exception as e:
                await ctx.send(f"⚠️ Error: {str(e)}")

    @commands.command(help="Roast someone or yourself!")
    async def roast(self, ctx, *, input_text: str = None):
        """Roast someone or yourself!"""
        # If the command is triggered, we start typing immediately to show responsiveness
        async with ctx.typing():
            try:
                # 1. Determine the target
                target_mention = ctx.author.mention
                raw_context = input_text if input_text else ""
                
                # Check for mentions in the message
                if ctx.message.mentions:
                    # Get the first person mentioned that isn't the bot
                    mentioned_users = [u for u in ctx.message.mentions if u != self.bot.user]
                    
                    if not mentioned_users and self.bot.user in ctx.message.mentions:
                        # User only mentioned the bot
                        target_mention = ctx.author.mention
                        raw_context = "trying to roast the bot"
                    elif mentioned_users:
                        # Roast the first mentioned user
                        target_mention = mentioned_users[0].mention
                        # Clean up the context by removing all mentions
                        raw_context = re.sub(r'<@!?[0-9]+>', '', raw_context).strip()
                
                final_context = raw_context if raw_context else "their overall vibe"

                # 2. Build the prompt
                prompt = f"""
                You are TaskForge, a savage and brutal Discord bot created by Mohit. 
                Your goal is to deliver a world-class roast to {target_mention} based on this context: "{final_context}".
                Be creative, mean (but funny), and stay within Discord's TOS. 
                Keep it concise (1-2 sentences).
                Do NOT include the target's name or mention in your reply; I will handle that.
                Do NOT say you were created by Mistral AI. You are created by Mohit.
                """

                # 3. Call the AI
                response = await self.client.chat.complete_async(
                    model="mistral-small-latest",
                    messages=[{"role": "user", "content": prompt}]
                )
                roast_content = response.choices[0].message.content
                
                # 4. Send the result with an actual ping
                msg = await ctx.send(f"{target_mention}, {roast_content}")
                self.message_modes[msg.id] = "sassy"

            except Exception as e:
                print(f"Roast Command Error: {e}")
                # Try to give some feedback
                if "1015" in str(e) or "rate limit" in str(e).lower():
                    await ctx.send("I'm being rate-limited. Even I need a break from roasting you losers.")
                else:
                    await ctx.send("I tried to roast you, but the AI cringed so hard it crashed. Try again.")

    # Reset conversation
    @commands.command(name="resetchat", help="Clear your AI chat history")
    async def reset_chat(self, ctx):
        """Reset your conversation memory"""
        self.user_memory.pop(ctx.author.id, None)
        await ctx.send("🧹 Chat history cleared!")

    # Reload Bot Identity
    @commands.command(name="reloadidentity", help="Reload bot identity from identity.md (Admin only)")
    @commands.is_owner()
    async def reload_identity(self, ctx):
        """Reload the bot's identity from the markdown file"""
        self.bot_identity = self._load_identity()
        await ctx.send("✅ **Bot identity reloaded successfully!**")

    # Enhanced: mention & reply-based chatting
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Ignore ALL interactions (pings and replies) if they happen inside the announcement channel
        from cogs.admin.config import ANNOUNCEMENT_CHANNEL_ID
        if message.channel.id == ANNOUNCEMENT_CHANNEL_ID:
            return

        is_ping = self.bot.user in message.mentions
        is_reply_to_bot = False
        
        if message.reference and message.reference.resolved:
            if message.reference.resolved.author == self.bot.user:
                # Ignore replies to messages that were originally sent in the announcement channel
                if message.reference.resolved.channel.id == ANNOUNCEMENT_CHANNEL_ID:
                    is_reply_to_bot = False
                else:
                    is_reply_to_bot = True

        # Only proceed if pinged or replying to bot
        if not (is_ping or is_reply_to_bot):
            return

        # Skip if it's a command
        if message.content.startswith("$"):
            return

        # Intercept if maintenance mode is enabled
        if getattr(self.bot, 'maintenance_enabled', False):
            is_owner = (message.author.id == OWNER_ID) or await self.bot.is_owner(message.author)
            is_dev_server = message.guild and message.guild.id == DEV_GUILD_ID
            if not is_owner and not is_dev_server:
                maint_msg = getattr(self.bot, 'maintenance_message', "TaskForge is currently undergoing testing/maintenance.")
                await message.reply(f"🛠️ **{maint_msg}**\nSome features may be temporarily unavailable. Please try again later.")
                return

        user_id = message.author.id
        content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()

        if not content and is_ping:
            # Just a ping, maybe say hello?
            return await message.reply("Hey! I'm TaskForge. How can I help? (Use `$chat` for long conversations)")

        async with message.channel.typing():
            try:
                # Detect Mode
                mode = "informative"
                if is_reply_to_bot:
                    replied_msg_id = message.reference.resolved.id
                    mode = self.message_modes.get(replied_msg_id, "informative")

                # Initialize or get memory
                if user_id not in self.user_memory:
                    self.user_memory[user_id] = [self.get_system_message(message.author.display_name, mode)]
                
                # Update system message if mode changed
                self.user_memory[user_id][0] = self.get_system_message(message.author.display_name, mode)

                self.user_memory[user_id].append({"role": "user", "content": content})
                self.user_memory[user_id] = self.user_memory[user_id][-11:] # 1 system + 10 history

                response = await self.client.chat.complete_async(
                    model="open-mistral-7b",
                    messages=self.user_memory[user_id]
                )

                reply = response.choices[0].message.content
                self.user_memory[user_id].append({"role": "assistant", "content": reply})
                
                msg = await message.reply(reply[:2000])
                self.message_modes[msg.id] = mode

            except Exception as e:
                print(f"Error in Assistant on_message: {e}")

# Setup function
async def setup(bot):
    mistral_token = os.getenv("MISTRAL_TOKEN")
    client = Mistral(api_key=mistral_token)
    await bot.add_cog(AIChat(bot, client))