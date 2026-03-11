import yt_dlp

ytdl_format_options = {
    'format': 'bestaudio/best',
    'default_search': 'auto',
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
data = ytdl.extract_info("music song", download=False)
if 'entries' in data:
    data = data['entries'][0]
print(data.keys())
