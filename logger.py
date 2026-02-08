
async def send_log(bot, message):
    LOG_CHANNEL_ID = 1470000358960136287

    channel = bot.get_channel(LOG_CHANNEL_ID)

    if channel is None:
        return
    
    await channel.send(message)
