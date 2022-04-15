import discord
from discord.ext import tasks, commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option, create_permission
from hikari import OptionType
from modules import Clipper, parseTime, convertTime, addTime, Log, GlobalAccount, parseTwitchTime, convertTwitchTime
import urllib, json
import requests
import dateutil.parser
import websocket
from datetime import date, datetime, timedelta
import os
from configmanager import Config, LoadConfig
from instagram import Instagram, Story

client = commands.Bot(command_prefix=">")
slash = SlashCommand(client, sync_commands=True)
client.remove_command('help')

LoadConfig()
active_guilds = [Config.server_id]


class Settings:
    # settings.json
    active = False
    bot_manager_role = 0
    general_channel = 0
    bot_channel = 0
    allowed_commands=[]

async def SaveSettings():
    if Config.server_id == 0:
        print("Failed to load settings: server ID not configured.")
    settings = {
        Config.server_id : {
            'bot_manager_role' : Settings.bot_manager_role,
            'general_channel' : Settings.general_channel,
            'bot_channel' : Settings.bot_channel,
            'global_info' : {
                'total_clips' : GlobalAccount.total_clips,
                'total_syncs' : GlobalAccount.total_syncs,
                'users' : GlobalAccount.users,
                'recent_clips' : GlobalAccount.recent_clips
            }
        }
    }
    json_settings = json.dumps(settings)
    with open("settings.json", "w") as jsonfile:
        jsonfile.write(json_settings)

async def LoadSettings():
    try:
        with open("settings.json", "r") as jsonfile:
            data = json.load(jsonfile)
            print("Settings Loaded.")
            if str(Config.server_id) in data:
                server_data = data[str(Config.server_id)]
                if 'bot_manager_role' in server_data:
                    Settings.bot_manager_role = server_data['bot_manager_role']
                if 'general_channel' in server_data:
                    Settings.general_channel = server_data['general_channel']
                if 'bot_channel' in server_data:
                    Settings.bot_channel = server_data['bot_channel']
                if 'global_info' in server_data:
                    if 'total_clips' in server_data['global_info']:
                        GlobalAccount.total_clips = server_data['global_info']['total_clips']
                    if 'total_syncs' in server_data['global_info']:
                        GlobalAccount.total_syncs = server_data['global_info']['total_syncs']
                    if 'users' in server_data['global_info']:
                        GlobalAccount.users = server_data['global_info']['users']
                    if 'recent_clips' in server_data['global_info']:
                        GlobalAccount.recent_clips = server_data['global_info']['recent_clips']
    except:
        print("Could not load settings")

@client.event
async def on_ready():
    if Config.server_id == 0:
        print("Server ID is not configured. Data will not be saved.")
        return
    print(f"Running on server {Config.server_id} ..")
    await LoadSettings()
    global_save.start()
    instagram_loop.start()


#                                #
#  MOD/FUN COMMANDS (NON-SLASH)  #
#                                #

@client.command(name="initialize", aliases=['init'])
async def _initialize(ctx):
    if ctx.guild.id != Config.server_id:
        return
    if (not (ctx.guild.get_role(Settings.bot_manager_role) in ctx.author.roles)) and ctx.author.id != Config.owner_id:
        embed = discord.Embed(description="This command requires manager role.", color=discord.Color(15158332))
        await ctx.reply(embed = embed)
        return
    if Clipper.ready:
        embed = discord.Embed(description="Bot is already initialized.", color=discord.Color(15158332))
        await ctx.reply(embed = embed)
        return
    Clipper.initialize(clipper_loop, Config.streamable_account, Config.streamable_password)
    Instagram.init()
    Log("Bot started!")
    embed = discord.Embed(description=f"Clipping module initialized", color=discord.Color(3066993))
    await ctx.reply(embed = embed)
    return

@client.command(name="shutdown", aliases=['stop'])
async def _shutdown(ctx):
    if ctx.guild.id != Config.server_id:
        return
    if (not (ctx.guild.get_role(Settings.bot_manager_role) in ctx.author.roles)) and ctx.author.id != Config.owner_id:
        embed = discord.Embed(description="This command requires manager role.", color=discord.Color(15158332))
        await ctx.reply(embed = embed)
        return
    if not Clipper.ready:
        embed = discord.Embed(description="Bot is already stopped.", color=discord.Color(15158332))
        await ctx.reply(embed = embed)
        return
    Clipper.ready = False
    Clipper.active_clippers.clear()
    clipper_loop.stop()
    Log("Bot stopped.")
    embed = discord.Embed(description=f"Clipping module stopped", color=discord.Color(15158332))
    await ctx.reply(embed = embed)
    return

@client.command(name="setup-channel")
async def _setup_channel(ctx, arg="", arg2=""):
    if ctx.guild.id != Config.server_id:
        return
    if (not (ctx.guild.get_role(Settings.bot_manager_role) in ctx.author.roles)) and ctx.author.id != Config.owner_id:
        embed = discord.Embed(description="This command requires manager role.", color=discord.Color(15158332))
        await ctx.reply(embed = embed)
        return
    Log(f"{ctx.author.name} used setup-channel with {arg} {arg2}")
    if arg=="" or arg2=="":
        embed = discord.Embed(description="Usage:\n>setup-channel <general/bot> <channel_id>", color=discord.Color(15158332))
        await ctx.reply(embed = embed)
        return
    else:
        try:
            if arg == "general":
                Settings.general_channel = int(arg2)
                embed = discord.Embed(description=f"General channel changed to {arg2}", color=discord.Color(3066993))
                await ctx.reply(embed = embed)
                return
            elif arg == "bot":
                Settings.bot_channel = int(arg2)
                embed = discord.Embed(description=f"Bot channel changed to {arg2}", color=discord.Color(3066993))
                await ctx.reply(embed = embed)
                return
        except Exception as e:
            Log(f"Exception: {str(e)}")
            embed = discord.Embed(description="Channel id has to be an integer", color=discord.Color(15158332))
            await ctx.reply(embed = embed)
            return

@client.command(name="help")
async def _help(ctx):
    if ctx.guild.id != Config.server_id:
        return
    if (not (ctx.guild.get_role(Settings.bot_manager_role) in ctx.author.roles)) and ctx.author.id != Config.owner_id:
        embed = discord.Embed(description="This command requires manager role.", color=discord.Color(15158332))
        await ctx.reply(embed = embed)
        return
    Log(f"{ctx.author.name} used help")
    embed = discord.Embed(title="Commands for bot manager:", description=">init - start up a clipper bot\n>shutdown - stop most bot functions\n>setup-channel <general/bot> <channel_id> - sets up config field (general used for /sync-live)", color=discord.Color(3066993))
    await ctx.reply(embed = embed)
    return

@client.command(name="commands")
async def _commands(ctx):
    if ctx.guild.id != Config.server_id:
        return
    if (not (ctx.guild.get_role(Settings.bot_manager_role) in ctx.author.roles)) and ctx.author.id != Config.owner_id:
        embed = discord.Embed(description="This command requires manager role.", color=discord.Color(15158332))
        await ctx.reply(embed = embed)
        return
    await ctx.reply(f"https://media.discordapp.net/attachments/949768918757691403/963530017604796476/unknown.png?width=993&height=609")
    return

@client.command(name="myclips", aliases=['mc'])
async def _myclips(ctx, arg=""):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    if str(ctx.author.id) not in GlobalAccount.users:
        embed=discord.Embed(description=f"You have no clips saved yet.", color=10038562)
        await ctx.reply(embed=embed)
        return
    if arg=="":
        embed=discord.Embed(title=f"Stats for {ctx.author.name}:", description=f"Clips saved: {GlobalAccount.users[str(ctx.author.id)]['total_clips']}\nUse 'myclips recent' to view your recent clips.", color=15844367)
        embed.set_thumbnail(url=f"{ctx.author.avatar_url}")
        embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
        await ctx.reply(embed=embed)
        return
    elif arg=="recent":
        desc = ""
        curr = 0
        for rc in GlobalAccount.users[str(ctx.author.id)]['recent_clips']:
            curr += 1
            desc += f"[{rc['date']} - {rc['title']}]({rc['url']})\n"
            if curr >= 10:
                break
        embed=discord.Embed(title=f"Recent clips for {ctx.author.name}:", description=desc, color=15844367)
        embed.set_thumbnail(url=f"{ctx.author.avatar_url}")
        embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
        await ctx.reply(embed=embed)
    return

@client.command(name="recent")
async def _recap(ctx, arg=""):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    page = 1
    if arg=="":
        page = 1
    else:
        try:
            page = int(arg)
        except:
            page = 1
    desc = ""
    curr = 0
    for rc in GlobalAccount.recent_clips:
        curr += 1
        if curr >= (page-1)*10:
            _usrname = "unknown"
            try:
                __usr = await client.fetch_user(rc['author'])
                _usrname = __usr.name
            except:
                _usrname = "unknown"
            desc += f"[{rc['date']} - {rc['title']} - by {_usrname}]({rc['url']})\n"
            if curr >= 10 * page:
                break
    embed=discord.Embed(title=f"Recent clips (Page {page})", description=desc, color=15844367)
    embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
    await ctx.reply(embed=embed)
    return

#                  #
#  SLASH COMMANDS  #
#                  #

# *  /clip <channel_name> <timestamp> <?duration> <?title>
@slash.slash(
    name="clip",
    description="Makes a clip from specified live channel and uploads it to streamable (timestamp required)",
    guild_ids=active_guilds,
    options=[
        create_option(
            name="channel",
            description="Channel that is currently live",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="timestamp",
            description="Timestamp string formatted HH:MM:SS for example: '01:15:05'",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="duration",
            description="Duration of the clip in seconds (default 30), example: '40', '1:30'",
            required=False,
            option_type=OptionType.STRING
        ),
        create_option(
            name="title",
            description="Title of the clip, has your name included already",
            required=False,
            option_type=OptionType.STRING
        )
    ]
)
async def _clip(ctx:SlashContext, channel: str, timestamp: str, duration: str ="30", title: str ="default"):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    if not Clipper.ready:
        embed=discord.Embed(description="Clipping module is disabled.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip (failed: module disabled)")
        return
    if len(Clipper.active_clippers) >= Clipper.ACTIVE_CLIPPERS_LIMIT:
        embed=discord.Embed(description=f"Current clipping limit is {Clipper.ACTIVE_CLIPPERS_LIMIT} at a time.\nTry again later.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip (failed: workers limit)")
        return
    time = parseTime(timestamp)
    time2 = parseTime(duration)
    if time2['hour'] > 0 or time2['minute'] > 5:
        embed=discord.Embed(description=f"Current clip length limit is 5 minutes.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip (failed: length limit)")
        return
    if len(title) < 1 or len(title) > 100:
        title = "default"
    clipper = Clipper()
    clipper.message_author = ctx.author
    clipper.channel = ctx.channel
    clipper.user_name = channel
    clipper.title = title
    clipper.work_type = 2
    clipper.start_time = time
    clipper.duration = time2
    embed = discord.Embed(title="Running command", description="...", color=discord.Color(16776960))
    rep = await ctx.send(embed = embed)
    clipper.message_id = rep.id
    clipper.message = rep
    clipper.cmd = "clip"
    clipper.initialized = True
    clipper.work_init()
    Log(f"{ctx.author.name} used command /clip")

# *  /clip-vod <vod_id> <timestamp> <?duration> <?title>
@slash.slash(
    name="clip-vod",
    description="Makes a clip from specified VOD and uploads it to streamable",
    guild_ids=active_guilds,
    options=[
        create_option(
            name="vod_id",
            description="VOD id that u can find at the end of vod link",
            required=True,
            option_type=OptionType.INTEGER
        ),
        create_option(
            name="timestamp",
            description="Timestamp string formatted HH:MM:SS for example: '01:15:05'",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="duration",
            description="Duration of the clip in seconds (default 30), example: '40', '1:30'",
            required=False,
            option_type=OptionType.STRING
        ),
        create_option(
            name="title",
            description="Title of the clip, has your name included already",
            required=False,
            option_type=OptionType.STRING
        )
    ]
)
async def _clip_vod(ctx:SlashContext, vod_id: int, timestamp: str, duration: str ="30", title: str ="default"):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    if not Clipper.ready:
        embed=discord.Embed(description="Clipping module is disabled.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip-vod (failed: module disabled)")
        return
    if len(Clipper.active_clippers) >= Clipper.ACTIVE_CLIPPERS_LIMIT:
        embed=discord.Embed(description=f"Current clipping limit is {Clipper.ACTIVE_CLIPPERS_LIMIT} at a time.\nTry again later.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip-vod (failed: workers limit)")
        return
    time = parseTime(timestamp)
    time2 = parseTime(duration)
    if time2['hour'] > 0 or time2['minute'] > 5:
        embed=discord.Embed(description=f"Current clip length limit is 5 minutes.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip-vod (failed: length limit)")
        return
    if len(title) < 1 or len(title) > 100:
        title = "default"
    clipper = Clipper()
    clipper.message_author = ctx.author
    clipper.channel = ctx.channel
    clipper.vod_id = vod_id
    clipper.title = title
    clipper.work_type = 1
    clipper.start_time = time
    clipper.duration = time2
    embed = discord.Embed(title="Running command", description="...", color=discord.Color(16776960))
    rep = await ctx.send(embed = embed)
    clipper.message_id = rep.id
    clipper.message = rep
    clipper.cmd = "clip-vod"
    clipper.initialized = True
    clipper.work_init()
    Log(f"{ctx.author.name} used command /clip-vod")

# *  /clip-save <streamable_id>
@slash.slash(
    name="clip-save",
    description="Generates URL for downloading streamable clip",
    guild_ids=active_guilds,
    options=[
        create_option(
            name="streamable_id",
            description="Letters at the end of streamable link (NOT THE LINK ITSELF)",
            required=True,
            option_type=OptionType.STRING
        )
    ]
)
async def _clip_save(ctx:SlashContext, streamable_id: str):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    if not Clipper.ready:
        embed=discord.Embed(description="Clipping module is disabled.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip-save (failed: module disabled)")
        return
    response = {}
    try:
        response = Clipper.streamable_api.get_info(streamable_id)
    except Exception as e:
        embed=discord.Embed(description=f"Streamable clip not found ({streamable_id})", color=10038562)
        await ctx.send(embed=embed)
        return
    if 'status' in response and response['status'] == 2 and 'title' in response and 'files' in response and 'mp4' in response['files'] and 'url' in response['files']['mp4']:
        mp4_file = response['files']['mp4']
        embed=discord.Embed(title=f"{response['title']}",description=f"[Click here to download]({mp4_file['url']})", color=7419530)
        if 'framerate' in mp4_file:
            embed.add_field(name="FPS:", value=f"{mp4_file['framerate']}")
        if 'size' in mp4_file:
            embed.add_field(name="Size:", value=f"{round(mp4_file['size']/1024/1024, 2)}MB")
        if 'duration' in mp4_file:
            embed.add_field(name="Duration:", value=f"{mp4_file['duration']}s")
        embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
        await ctx.send(embed=embed)
        return
    else:
        embed=discord.Embed(description=f"Streamable clip not found or is private ({streamable_id})", color=10038562)
        await ctx.send(embed=embed)
        return

# *  /timestamp-live <channel> <?title>
@slash.slash(
    name="timestamp-live",
    description="Generates a VOD url with current timestamp",
    guild_ids=active_guilds,
    options=[
        create_option(
            name="channel",
            description="Channel name to grab last vod from",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="title",
            description="Title for this timestamp",
            required=False,
            option_type=OptionType.STRING
        )
    ]
)
async def _timestamp_live(ctx:SlashContext, channel: str, title: str = "none"):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    try:
        if len(title) < 1 or len(title) > 100:
            title = "none"
        Log(f"{ctx.author.name} used command /timestamp-live")
        user_id = 0
        user_pic = ""
        vod_id = ""
        vod_url = ""
        vod_duration = ""
        reqSession = requests.Session()
        url = f"https://api.twitch.tv/helix/users?login={channel}"
        req = reqSession.get(url, headers=Clipper.api_headers)
        req_json = req.json()
        if 'data' in req_json and len(req_json['data']) > 0 and req_json['data'][0]['login'] == channel:
            user_id = req_json['data'][0]['id']
            user_pic = req_json['data'][0]['profile_image_url']
        else:
            Log(f"Timestamp-live: User not found")
            embed=discord.Embed(description=f"Channel not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        url = f"https://api.twitch.tv/helix/videos?user_id={user_id}&first=1"
        req2 = reqSession.get(url, headers=Clipper.api_headers)
        req_json2 = req2.json()
        if 'data' in req_json2 and len(req_json2['data']) > 0 and req_json2['data'][0]['user_id'] == user_id:
            vod_id = req_json2['data'][0]['id']
            vod_url = req_json2['data'][0]['url']
            vod_duration = req_json2['data'][0]['duration']
        else:
            Log(f"Timestamp-live: Vod not found")
            embed=discord.Embed(description=f"VOD not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        if vod_id != "" and vod_url != "" and vod_duration != "":
            embed=discord.Embed(title=f"Timestamp for {channel}",description=f"VOD id: {vod_id}\nTimestamp: {vod_url}?t={vod_duration}", color=10038562)
            if title != "none" and len(title) > 0 and len(title) < 40:
                embed.title = title
            if user_pic != "":
                embed.set_thumbnail(url=user_pic)
            embed.set_author(name=f"{ctx.author.name}", icon_url=f"{ctx.author.avatar_url}")
            embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
            await ctx.send(embed=embed)
            return
    except Exception as e:
        Log(f"(Timestamp-live) Exception during info gathering: {e}")
        embed=discord.Embed(description=f"Error occured while gathering channel info.\nTry again later.", color=10038562)
        await ctx.send(embed=embed)
        return

# *  /timestamp <channel> <timestamp> <?title>
@slash.slash(
    name="timestamp",
    description="Generates a VOD url with given timestamp",
    guild_ids=active_guilds,
    options=[
        create_option(
            name="channel",
            description="Channel name to grab last vod from",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="timestamp",
            description="Timestamp string formatted HH:MM:SS for example: '01:15:05'",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="title",
            description="Title for this timestamp",
            required=False,
            option_type=OptionType.STRING
        )
    ]
)
async def _timestamp(ctx:SlashContext, channel: str, timestamp: str, title: str = "none"):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    try:
        if len(title) < 1 or len(title) > 100:
            title = "none"
        Log(f"{ctx.author.name} used command /timestamp")
        user_id = 0
        user_pic = ""
        vod_id = ""
        vod_url = ""
        reqSession = requests.Session()
        url = f"https://api.twitch.tv/helix/users?login={channel}"
        req = reqSession.get(url, headers=Clipper.api_headers)
        req_json = req.json()
        if 'data' in req_json and len(req_json['data']) > 0 and req_json['data'][0]['login'] == channel:
            user_id = req_json['data'][0]['id']
            user_pic = req_json['data'][0]['profile_image_url']
        else:
            Log(f"Timestamp-live: User not found")
            embed=discord.Embed(description=f"Channel not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        url = f"https://api.twitch.tv/helix/videos?user_id={user_id}&first=1"
        req2 = reqSession.get(url, headers=Clipper.api_headers)
        req_json2 = req2.json()
        if 'data' in req_json2 and len(req_json2['data']) > 0 and req_json2['data'][0]['user_id'] == user_id:
            vod_id = req_json2['data'][0]['id']
            vod_url = req_json2['data'][0]['url']
        else:
            Log(f"Timestamp-live: Vod not found")
            embed=discord.Embed(description=f"VOD not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        if vod_id != "" and vod_url != "":
            embed=discord.Embed(title=f"Timestamp for {channel}",description=f"VOD id: {vod_id}\nTimestamp: {vod_url}?t={parseTime(timestamp)['hour']}h{parseTime(timestamp)['minute']}m{parseTime(timestamp)['second']}s", color=10181046)
            if title != "none" and len(title) > 0 and len(title) < 40:
                embed.title = title
            if user_pic != "":
                embed.set_thumbnail(url=user_pic)
            embed.set_author(name=f"{ctx.author.name}", icon_url=f"{ctx.author.avatar_url}")
            embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
            await ctx.send(embed=embed)
            return
    except Exception as e:
        Log(f"(Timestamp) Exception during info gathering: {e}")
        embed=discord.Embed(description=f"Error occured while gathering channel info.\nTry again later.", color=10038562)
        await ctx.send(embed=embed)
        return

# *  /sync-live <channel> <?title>
@slash.slash(
    name="sync-live",
    description="Send a bot message in #general with current timestamp and links it here",
    guild_ids=active_guilds,
    options=[
        create_option(
            name="channel",
            description="Channel name for grabbing the timestamp",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="title",
            description="Optional title for sync message",
            required=False,
            option_type=OptionType.STRING
        )
    ]
)
async def _sync_live(ctx:SlashContext, channel: str, title: str = "none"):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    try:
        if len(title) < 1 or len(title) > 100:
            title = "none"
        Log(f"{ctx.author.name} used command /sync")
        user_id = 0
        user_pic = ""
        vod_id = ""
        vod_url = ""
        vod_duration = ""
        reqSession = requests.Session()
        url = f"https://api.twitch.tv/helix/users?login={channel}"
        req = reqSession.get(url, headers=Clipper.api_headers)
        req_json = req.json()
        if 'data' in req_json and len(req_json['data']) > 0 and req_json['data'][0]['login'] == channel:
            user_id = req_json['data'][0]['id']
            user_pic = req_json['data'][0]['profile_image_url']
        else:
            Log(f"Timestamp-live: User not found")
            embed=discord.Embed(description=f"Channel not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        url = f"https://api.twitch.tv/helix/videos?user_id={user_id}&first=1"
        req2 = reqSession.get(url, headers=Clipper.api_headers)
        req_json2 = req2.json()
        if 'data' in req_json2 and len(req_json2['data']) > 0 and req_json2['data'][0]['user_id'] == user_id:
            vod_id = req_json2['data'][0]['id']
            vod_url = req_json2['data'][0]['url']
            vod_duration = req_json2['data'][0]['duration']
        else:
            Log(f"Timestamp-live: Vod not found")
            embed=discord.Embed(description=f"VOD not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        if vod_id != "" and vod_url != "":
            date = datetime.now().replace(microsecond = 0) - timedelta(hours = 7)
            _sync_msg=discord.Embed(title=f"Sync generated message",description=f"Timestamp: {vod_url}?t={vod_duration}\nAustin time: {str(date)}", color=11027200)
            if title != "none" and len(title) > 0 and len(title) < 40:
                _sync_msg.title = title
            _sync_msg.set_author(name=f"{ctx.author.name} made a sync link:", icon_url=f"{ctx.author.avatar_url}")
            general_channel = client.get_channel(Settings.general_channel)
            sync_msg = await general_channel.send(embed=_sync_msg)
            embed=discord.Embed(title=f"Synced with generated message",description=f"Message link: [#{general_channel.name}]({sync_msg.jump_url})", color=12745742)
            if title != "none" and len(title) > 0 and len(title) < 40:
                embed.title = title
            if user_pic != "":
                embed.set_thumbnail(url=user_pic)
            embed.set_author(name=f"{ctx.author.name}", icon_url=f"{ctx.author.avatar_url}")
            embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
            await ctx.send(embed=embed)
            return
    except Exception as e:
        Log(f"(Timestamp) Exception during info gathering: {e}")
        embed=discord.Embed(description=f"Error occured while gathering channel info.\nTry again later.", color=10038562)
        await ctx.send(embed=embed)
        return

# *  /sync <channel> <message_id> <?title>
@slash.slash(
    name="sync",
    description="Sync specified message with channel vod",
    guild_ids=active_guilds,
    options=[
        create_option(
            name="channel",
            description="Channel name for grabbing the timestamp",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="message_id",
            description="Message id which will be linked (has to be in general)",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="title",
            description="Optional title",
            required=False,
            option_type=OptionType.STRING
        )
    ]
)
async def _sync(ctx:SlashContext, channel: str, message_id:str, title: str = "none"):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    try:
        if len(title) < 1 or len(title) > 100:
            title = "none"
        Log(f"{ctx.author.name} used command /sync")
        user_id = 0
        user_pic = ""
        vod_id = ""
        vod_url = ""
        vod_duration = ""
        reqSession = requests.Session()
        url = f"https://api.twitch.tv/helix/users?login={channel}"
        req = reqSession.get(url, headers=Clipper.api_headers)
        req_json = req.json()
        if 'data' in req_json and len(req_json['data']) > 0 and req_json['data'][0]['login'] == channel:
            user_id = req_json['data'][0]['id']
            user_pic = req_json['data'][0]['profile_image_url']
        else:
            Log(f"Sync: User not found")
            embed=discord.Embed(description=f"Channel not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        if '/' in message_id:
            _split = message_id.split('/')
            if len(_split) > 2:
                message_id = _split[len(_split)-1]
        source_message = None
        try:
            source_message = await client.get_channel(Settings.general_channel).fetch_message(message_id)
        except:
            Log(f"Message not found during sync")
            embed=discord.Embed(description=f"Message not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        if source_message == None:
            Log(f"Message not found during sync")
            embed=discord.Embed(description=f"Message not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        url = f"https://api.twitch.tv/helix/videos?user_id={user_id}"
        req2 = reqSession.get(url, headers=Clipper.api_headers)
        req_json2 = req2.json()
        if 'data' in req_json2 and len(req_json2['data']) > 0 and req_json2['data'][0]['user_id'] == user_id:
            for vod in req_json2['data']:
                _vod_start_raw = vod['created_at']
                _vod_duration_raw = vod['duration']
                _vod_start = datetime.strptime(_vod_start_raw, "%Y-%m-%dT%H:%M:%SZ")
                _vod_duration = parseTwitchTime(_vod_duration_raw)
                _vod_end = _vod_start + timedelta(hours=_vod_duration['hour'], minutes=_vod_duration['minute'], seconds=_vod_duration['second'])
                if _vod_start < source_message.created_at and source_message.created_at < _vod_end:
                    vod_url = vod['url']
                    vod_id = vod['id']
                    _vod_current_time = str(source_message.created_at - _vod_start)
                    if '.' in _vod_current_time:
                        _vod_current_time_split = _vod_current_time.split('.')
                        _vod_current_time = _vod_current_time_split[0]
                    vod_duration = convertTwitchTime(parseTime(_vod_current_time))
        else:
            Log(f"Sync: Vod not found")
            embed=discord.Embed(description=f"VOD not found.", color=10038562)
            await ctx.send(embed=embed)
            return
        if vod_id != "" and vod_url != "" and vod_duration != "":
            austin_time = source_message.created_at.replace(microsecond = 0) - timedelta(hours = 5)
            embed=discord.Embed(title=f"Synced with message",description=f"Timestamp: {vod_url}?t={vod_duration}\nAustin time: {str(austin_time)}\nMessage link: [{source_message.author.name} in #{client.get_channel(Settings.general_channel).name}]({source_message.jump_url})", color=12745742)
            if title != "none" and len(title) > 0 and len(title) < 40:
                embed.title = title
            if user_pic != "":
                embed.set_thumbnail(url=user_pic)
            embed.set_author(name=f"{ctx.author.name}", icon_url=f"{ctx.author.avatar_url}")
            embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
            await ctx.send(embed=embed)
            return
        else:
            Log(f"Sync: Vod not found")
            embed=discord.Embed(description=f"VOD not found.", color=10038562)
            await ctx.send(embed=embed)
            return
    except Exception as e:
        Log(f"(Timestamp) Exception during info gathering: {e}")
        embed=discord.Embed(description=f"Error occured while gathering channel info.\nTry again later.", color=10038562)
        await ctx.send(embed=embed)
        return

# *  /clip-live <channel_name> <?duration> <?title>
@slash.slash(
    name="clip-live",
    description="Makes a clip with current live timestamp and queues it up for download.",
    guild_ids=active_guilds,
    options=[
        create_option(
            name="channel",
            description="Channel that is currently live",
            required=True,
            option_type=OptionType.STRING
        ),
        create_option(
            name="duration",
            description="Duration of the clip in seconds (default 30), example: '40', '1:30'",
            required=False,
            option_type=OptionType.STRING
        ),
        create_option(
            name="title",
            description="Title of the clip, has your name included already",
            required=False,
            option_type=OptionType.STRING
        )
    ]
)
async def _clip_live(ctx:SlashContext, channel: str, duration: str ="30", title: str ="default"):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    if not Clipper.ready:
        embed=discord.Embed(description="Clipping module is disabled.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip-live (failed: module disabled)")
        return
    if len(Clipper.active_clippers) >= Clipper.ACTIVE_CLIPPERS_LIMIT:
        embed=discord.Embed(description=f"Current clipping limit is {Clipper.ACTIVE_CLIPPERS_LIMIT} at a time.\nTry again later.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip-live (failed: workers limit)")
        return
    time2 = parseTime(duration)
    if time2['hour'] > 0 or time2['minute'] > 5:
        embed=discord.Embed(description=f"Current clip length limit is 5 minutes.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /clip (failed: length limit)")
        return
    if len(title) < 1 or len(title) > 100:
        title = "default"
    clipper = Clipper()
    clipper.message_author = ctx.author
    clipper.channel = ctx.channel
    clipper.user_name = channel
    clipper.title = title
    clipper.work_type = 3
    clipper.duration = time2
    embed = discord.Embed(title="Running command", description="...", color=discord.Color(16776960))
    rep = await ctx.send(embed = embed)
    clipper.message_id = rep.id
    clipper.message = rep
    clipper.cmd = "clip-live"
    clipper.initialized = True
    clipper.work_init()
    Log(f"{ctx.author.name} used command /clip-live")

# *  /save-story <ig_name>
@slash.slash(
    name="save-story",
    description="Grabs stories posted on instagram",
    guild_ids=active_guilds,
    options=[
        create_option(
            name="user",
            description="Username",
            required=True,
            option_type=OptionType.STRING
        )
    ]
)
async def _save_story(ctx:SlashContext, user: str):
    if ctx.guild.id != Config.server_id:
        return
    if ctx.channel.id != Settings.bot_channel:
        return
    if ctx.author.id != Config.owner_id:
        return
    if not Clipper.ready:
        embed=discord.Embed(description="Clipping module is disabled.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /save-story (failed: module disabled)")
        return
    if Instagram.ready:
        Instagram.getStories(user, ctx.author)
    else:
        embed=discord.Embed(description="Instagram module is disabled.", color=10038562)
        await ctx.send(embed=embed)
        Log(f"{ctx.author.name} used command /save-story (failed: ig not initialized)")
        return
    Log(f"{ctx.author.name} used command /save-story")

######################

@tasks.loop(seconds=1)
async def clipper_loop():
    await Clipper.Update()

@tasks.loop(seconds=10)
async def global_save():
    await SaveSettings()

@tasks.loop(seconds=3)
async def instagram_loop():
    if len(Instagram.stories_ready) > 0:
        try:
            bot_channel = client.get_channel(Settings.bot_channel)
            for story in Instagram.stories_ready:
                desc = f"No video attached."
                if story.media_type == 2:
                    desc = f"[Video reupload (streamable.com)]({story.streamable_link})"
                embed = discord.Embed(title=f"Story from {story.user_name}", description=f"{desc}", color=discord.Color(15277667))
                if story.author != None:
                    embed.set_author(name=f"{story.author.name}", icon_url=f"{story.author.avatar_url}")
                if story.user_pic != "":
                    embed.set_thumbnail(url=f"{story.user_pic}")
                if story.thumbnail_link != "":
                    embed.set_image(url=f"{story.thumbnail_link}")
                embed.add_field(name="Posted at:", value=f"{str(story.taken_at)}")
                embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
                await bot_channel.send(embed=embed)
                Instagram.stories_ready.remove(story)
        except Exception as e:
            Log(f"Exception during instagram loop: {str(e)}")

client.run(Config.bot_token)