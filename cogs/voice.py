from discord.ext import commands

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # Track bot's voice clients per guild

    @commands.command(help="Connect to the voice channel you're in")
    async def connect(self, ctx):
        # Check if user is in a voice channel
        if not ctx.author.voice:
            await ctx.send("❌ You need to be in a voice channel to use this command!")
            return

        # Get the voice channel
        channel = ctx.author.voice.channel
        
        # Check if bot is already in a voice channel in this guild
        if ctx.guild.id in self.voice_clients:
            vc = self.voice_clients[ctx.guild.id]
            if vc.is_connected():
                if vc.channel.id == channel.id:
                    await ctx.send("❌ I'm already in your voice channel!")
                    return
                else:
                    await vc.move_to(channel)
                    await ctx.send(f"🔊 Moved to {channel.name}")
                    return

        # Connect to the voice channel
        try:
            vc = await channel.connect()
            self.voice_clients[ctx.guild.id] = vc
            await ctx.send(f"✅ Joined {channel.name}")
        except Exception as e:
            await ctx.send(f"❌ Failed to join voice channel: {str(e)}")

    @commands.command(help="Disconnect from the current voice channel")
    async def old_disconnect(self, ctx):
        if ctx.guild.id not in self.voice_clients:
            await ctx.send("❌ I'm not in any voice channel!")
            return

        vc = self.voice_clients[ctx.guild.id]
        if vc.is_connected():
            await vc.disconnect()
            del self.voice_clients[ctx.guild.id]
            await ctx.send("✅ Left the voice channel")
        else:
            await ctx.send("❌ I'm not connected to a voice channel!")

    @commands.command(help="Play a sound file in voice channel")
    async def old_play(self, ctx, sound_name: str = None):
        # Check if bot is in a voice channel
        if ctx.guild.id not in self.voice_clients:
            await ctx.send("❌ I'm not in a voice channel! Use `$connect` first.")
            return

        vc = self.voice_clients[ctx.guild.id]
        if not vc.is_connected():
            await ctx.send("❌ I'm not connected to a voice channel!")
            return

        # You can add sound file handling here
        # For now, just a placeholder
        if sound_name:
            await ctx.send(f"🎵 Playing '{sound_name}' (WIP)")
        else:
            await ctx.send("🎵 Playing sound (WIP)")

    @commands.command(help="Show current voice channel status")
    async def vcstat(self, ctx):
        # Prepare status message
        status_lines = []
        
        # Add ping information
        websocket_ping = self.bot.latency * 1000
        if websocket_ping > 250:
            ping_status = "🔴 High"
        elif websocket_ping > 150:
            ping_status = "🟡 Medium" 
        else:
            ping_status = "🟢 Low"
            
        status_lines.append(f"📡 WebSocket Ping: {websocket_ping:.2f}ms ({ping_status})")
        
        # Add voice channel information
        if ctx.guild.id in self.voice_clients:
            vc = self.voice_clients[ctx.guild.id]
            if vc.is_connected():
                channel = vc.channel
                members = [member.display_name for member in channel.members if not member.bot]
                member_count = len([m for m in channel.members if not m.bot])
                
                status_lines.append(f"🔊 Currently in: {channel.name}")
                status_lines.append(f"👥 Members: {member_count}")
                if members:
                    status_lines.append(f"📋 Members: {', '.join(members)}")
            else:
                status_lines.append("🔇 Not currently in a voice channel")
        else:
            status_lines.append("🔇 Not currently in a voice channel")
        
        await ctx.send("\n".join(status_lines))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates (optional feature)"""
        # Optional: Auto-disconnect when channel is empty
        # Or track when users join/leave
        
        # Example: If bot is alone in a channel, optionally disconnect
        if member == self.bot.user and after.channel is None:
            # Bot was disconnected
            if member.guild.id in self.voice_clients:
                del self.voice_clients[member.guild.id]
        
        # You can add more logic here for monitoring voice activity

async def setup(bot):
    await bot.add_cog(Voice(bot))
