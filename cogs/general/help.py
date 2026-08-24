import discord
from discord.ext import commands
import math

class HelpSelect(discord.ui.Select):
    def __init__(self, bot, cog_commands, ctx):
        options = []
        
        # Category Mapping with Emojis
        self.category_styles = {
            "Admin": "🛠️",
            "AI Assistant": "🤖",
            "Music": "🎵",
            "Utility": "⚙️",
            "Social": "📢",
            "Info": "📁",
            "General": "📦"
        }

        for cog_name in cog_commands:
            emoji = self.category_styles.get(cog_name, "🔹")
            options.append(discord.SelectOption(
                label=cog_name,
                description=f"View {cog_name} commands",
                emoji=emoji
            ))

        super().__init__(placeholder="📂 Select a category...", min_values=1, max_values=1, options=options)
        self.bot = bot
        self.cog_commands = cog_commands
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        cog_name = self.values[0]
        commands_list = self.cog_commands[cog_name]
        
        # Sort commands
        commands_list.sort()
        
        emoji = self.category_styles.get(cog_name, "🔹")
        
        text = f"### {emoji} {cog_name} Commands\n\n"
        
        for cmd_name in commands_list:
            cmd = self.bot.get_command(cmd_name)
            desc = cmd.help if cmd and cmd.help else "No description available."
            text += f"🔹 **{self.ctx.prefix}{cmd_name}**\n   └ *{desc}*\n"

        text += f"\n*Use `{self.ctx.prefix}help <command>` for more details on a specific command.*"
        
        await interaction.response.edit_message(content=text, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, bot, cog_commands, ctx):
        super().__init__(timeout=60)
        self.add_item(HelpSelect(bot, cog_commands, ctx))


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx, *, command_name: str = None):
        """Shows help for a category or command"""
        
        if command_name:
            # Search for specific command help
            cmd = self.bot.get_command(command_name)
            if not cmd:
                return await ctx.send(f"❌ Command `{command_name}` not found.")
            
            help_text = f"### 🔍 Help: {ctx.prefix}{cmd.name}\n"
            help_text += f"> **Description:** {cmd.help or 'No description'}\n"
            if cmd.aliases:
                help_text += f"> **Aliases:** {', '.join(cmd.aliases)}\n"
            usage = cmd.usage or f"{ctx.prefix}{cmd.name} {cmd.signature}"
            help_text += f"> **Usage:** `{usage}`\n"
            
            return await ctx.send(help_text)

        # Mapping Cogs to categories
        cog_mapping = {
            "Moderation": "Admin",
            "Maintenance": "Admin",
            "MusicPlayer": "Music",
            "AIDJ": "Music",
            "Utility": "Utility",
            "Reminder": "Utility",
            "AIChat": "AI Assistant",
            "AIInsights": "AI Assistant",
            "Economy": "Economy",
            "AdvancedEconomy": "Economy",
            "GiveawayCog": "Economy",
            "LeaderboardCommands": "Leaderboard",
            "LeaderboardTracker": "Leaderboard",
            "Confession": "Social",
            "Announcement": "General",
            "SetupGuide": "General",
            "Help": "General",
            "System": "Info",
            "Info": "Info",
            "Status": "Info",
            "General": "General"
        }

        cog_commands = {}

        for command in self.bot.commands:
            if command.hidden:
                continue

            cog_name = command.cog.qualified_name if command.cog else "General"
            category = cog_mapping.get(cog_name, cog_name)

            if category not in cog_commands:
                cog_commands[category] = []

            cog_commands[category].append(command.qualified_name)

            for subcommand in command.walk_commands():
                if not subcommand.hidden:
                    cog_commands[category].append(subcommand.qualified_name)

        view = HelpView(self.bot, cog_commands, ctx)

        welcome_text = (
            "## 📜 TaskForge Help Menu\n"
            "Welcome to the TaskForge help menu! Use the dropdown below to explore our features.\n\n"
            "🛠️ **Admin** - Commands for moderators\n"
            "🤖 **AI Assistant** - Chat normally ($chat/$talk) or get roasted ($roast)\n"
            "🎵 **Music** - Play tunes and manage queues\n"
            "💰 **Economy** - Manage profiles, items, and giveaways\n"
            "📊 **Leaderboard** - View server activity rankings\n"
            "⚙️ **Utility** - Reminders and helpful tools\n"
            "📢 **Social** - Confessions and fun\n"
            "📁 **Info** - Bot information and status\n\n"
            f"*Use `{ctx.prefix}help <command>` for more details on a specific command.*"
        )

        await ctx.send(welcome_text, view=view)


async def setup(bot):
    await bot.add_cog(Help(bot))
