import queue
import discord
from discord.ext import tasks, commands
import asyncio
import time
from datetime import date, datetime, timedelta
import os
import threading
import math
import urllib, json
import requests
import dateutil.parser
import websocket
from pystreamable import StreamableApi
import subprocess
import os.path
from os import listdir
from os.path import isfile, join
from configmanager import Config

def parseTime(time="00:00:00"):
    parts = time.split(':')
    hour = "0"
    minute = "0"
    second = "0"
    if len(parts) < 2:
        second = time
    elif len(parts) == 2:
        minute = parts[0]
        second = parts[1]
    elif len(parts) == 3:
        hour = parts[0]
        minute = parts[1]
        second = parts[2]
    try:
        formatted = {
            'hour': int(hour),
            'minute': int(minute),
            'second': int(second)
        }
        return formatted
    except:
        return {'hour':0,'minute':0,'second':0}

def convertTime(time):
    if 'hour' in time and 'minute' in time and 'second' in time:
        return f"{time['hour']:02d}:{time['minute']:02d}:{time['second']:02d}"

def addTime(time, time2):
    hourOut = time['hour'] + time2['hour']
    minuteOut = time['minute'] + time2['minute']
    if minuteOut > 59:
        hourOut += math.floor(minuteOut / 60)
        minuteOut -= math.floor(minuteOut / 60) * 60
    secondOut = time['second'] + time2['second']
    if secondOut > 59:
        minuteOut += math.floor(secondOut / 60)
        secondOut -= math.floor(secondOut / 60) * 60
    if minuteOut > 59:
        hourOut += math.floor(minuteOut / 60)
        minuteOut -= math.floor(minuteOut / 60) * 60
    formatted = {
            'hour': hourOut,
            'minute': minuteOut,
            'second': secondOut
        }
    return formatted

def parseTwitchTime(time):
    hourOut = 0
    minuteOut = 0
    secondOut = 0
    cut_s = time[:-1]
    split_h = cut_s.split('h')
    try:
        if len(split_h) == 2:
            hourOut = int(split_h[0])
            split_m = split_h[1].split('m')
            if len(split_m) == 2:
                minuteOut = int(split_m[0])
                secondOut = int(split_m[1])
        else:
            split_m = cut_s.split('m')
            if len(split_m) == 2:
                minuteOut = int(split_m[0])
                secondOut = int(split_m[1])
            else:
                secondOut = int(cut_s)
        return {'hour':hourOut,'minute':minuteOut,'second':secondOut}
    except:
        return {'hour':0,'minute':0,'second':0}

def convertTwitchTime(time):
    output = ""
    if time['hour'] > 0:
        output += str(time['hour']) + 'h' + str(time['minute']) + 'm'
    elif time['minute'] > 0:
        output += str(time['minute']) + 'm'
    output += str(time['second']) + 's'
    return output


def substractTime(time, time2):
    format = '%H:%M:%S'
    startDateTime = datetime.strptime(time, format)
    endDateTime = datetime.strptime(time2, format)
    diff = endDateTime - startDateTime
    return str(diff)

def Log(msg):
    date = datetime.now().replace(microsecond = 0)
    print(f"[{str(date)}] {msg}")


class Clipper:
    ACTIVE_CLIPPERS_LIMIT = 10
    QUEUE_LIMIT = 8
    QUEUE_TIMEOUT = 10*60
    ready = False
    streamable_api = None
    active_clippers = []
    queue = []
    queue_system = True
    api_headers = {}

    _cache_pending = []

    def initialize(clipper_loop, streamable_login, streamable_password):
        Clipper.api_headers = {
            'Authorization': Config.twitch_api_access,
            'Client-Id': Config.twitch_api_client
        }
        Clipper.streamable_api = StreamableApi(streamable_login, streamable_password)
        clipper_loop.start()
        Clipper.ready = True

    async def Update():
        if not Clipper.ready:
            return
        for clipper in Clipper.active_clippers:
            if clipper.initialized and clipper.update_msg:
                if clipper.message != None:
                    try:
                        if clipper.cmd == "clip":
                            embed = discord.Embed(title=f"Clipping: {clipper.user_name}", description=f"{clipper.status}", color=discord.Color(clipper.color))
                            if clipper.errorcode > 0 and clipper.errorcode < 99:
                                embed.title = "Error"
                            else:
                                if clipper.user_image != "unknown":
                                    embed.set_thumbnail(url=f"{clipper.user_image}")
                                embed.set_author(name=f"{clipper.message_author.name}", icon_url=f"{clipper.message_author.avatar_url}")
                                embed.add_field(name="Title:", value=f"{clipper.title}")
                                embed.add_field(name="Clipper:", value=f"{clipper.message_author.name}")
                                embed.add_field(name="Timestamp:", value=f"{convertTime(clipper.start_time)}")
                                embed.add_field(name="Duration:", value=f"{convertTime(clipper.duration)}")
                            embed.set_footer(text="Clipperbot ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
                            await clipper.message.edit(embed = embed)
                            clipper.update_msg = False
                        elif clipper.cmd == "clip-vod":
                            embed = discord.Embed(title=f"VOD clipping: {clipper.vod_id}", description=f"{clipper.status}", color=discord.Color(clipper.color))
                            if clipper.errorcode > 0 and clipper.errorcode < 99:
                                embed.title = "Error"
                            else:
                                embed.set_author(name=f"{clipper.message_author.name}", icon_url=f"{clipper.message_author.avatar_url}")
                                embed.add_field(name="Title:", value=f"{clipper.title}")
                                embed.add_field(name="Clipper:", value=f"{clipper.message_author.name}")
                                embed.add_field(name="Timestamp:", value=f"{convertTime(clipper.start_time)}")
                                embed.add_field(name="Duration:", value=f"{convertTime(clipper.duration)}")
                            embed.set_footer(text="Clipperbot ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
                            await clipper.message.edit(embed = embed)
                            clipper.update_msg = False
                        elif clipper.cmd == "clip-live":
                            embed = discord.Embed(title=f"Live clipping: {clipper.user_name}", description=f"{clipper.status}", color=discord.Color(clipper.color))
                            if clipper.errorcode > 0 and clipper.errorcode < 99:
                                embed.title = "Error"
                            else:
                                if clipper.user_image != "unknown":
                                    embed.set_thumbnail(url=f"{clipper.user_image}")
                                embed.set_author(name=f"{clipper.message_author.name}", icon_url=f"{clipper.message_author.avatar_url}")
                                embed.add_field(name="Title:", value=f"{clipper.title}")
                                embed.add_field(name="Clipper:", value=f"{clipper.message_author.name}")
                                embed.add_field(name="Timestamp:", value=f"{convertTime(clipper.start_time)}")
                                embed.add_field(name="Duration:", value=f"{convertTime(clipper.duration)}")
                            embed.set_footer(text="Clipperbot ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
                            await clipper.message.edit(embed = embed)
                            clipper.update_msg = False
                    except Exception as e:
                        print(f"Exception during update: {str(e)}")
        await Clipper.Clean()
        await Clipper._cache_clean()
    
    async def Clean():
        for clipper in Clipper.active_clippers:
            if clipper.errorcode > 0 and not clipper.update_msg:
                Clipper.active_clippers.remove(clipper)

    async def _cache_clean():
        if len(Clipper.active_clippers) > 0:
            return
        try:
            predict_path = f"{os.getcwd()}"
            onlyfiles = [f for f in listdir(predict_path) if isfile(join(predict_path, f))]
            for f in onlyfiles:
                if f.endswith('.mkv'):
                    os.remove(f"{predict_path}/{f}")
                    #os.remove(f"{predict_path}\{f}")
        except Exception as e:
            Log(f"Error during cache cleaning! {str(e)}")

    def __init__(self):
        self.cmd = ""
        self.channel = None
        self.message_id = 0
        self.message = None
        self.message_author = None
        self.title = "unknown"
        self.vod_id = 0
        self.user_id = 0
        self.user_name = "unknown"
        self.user_image = "unknown"
        self.start_time = {'hour':0,'minute':0,'second':0}
        self.duration = {'hour':0,'minute':0,'second':0}
        self.current_duration = {'hour':0,'minute':0,'second':0}
        self.work_type = 0
        self.status = "unknown"
        self.errorcode = 0
        self.color = 3447003
        self.initialized = False
        self.update_msg = False
        self.queue_timeout = None
        
    
    def work_init(self):
        Clipper.active_clippers.append(self)
        t1 = threading.Thread(target=self.work)
        t1.start()

    def terminate(self):
        if self in Clipper.active_clippers:
            Clipper.active_clippers.remove(self)

    def work(self):
        if self.initialized:
            _skip_download = False
            if self.work_type == 2 or self.work_type == 3:
                try:
                    reqSession = requests.Session()
                    url = f"https://api.twitch.tv/helix/users?login={self.user_name}"
                    req = reqSession.get(url, headers=Clipper.api_headers)
                    req_json = req.json()
                    if 'data' in req_json and len(req_json['data']) > 0 and req_json['data'][0]['login'] == self.user_name:
                        self.user_id = req_json['data'][0]['id']
                        self.user_image = req_json['data'][0]['profile_image_url']
                    else:
                        Log(f"Clipping: User not found")
                        self.status = "User not found."
                        self.color = 10038562
                        self.errorcode = 5 # user not found
                        self.update_msg = True
                        return
                    url = f"https://api.twitch.tv/helix/videos?user_id={self.user_id}&first=1"
                    req2 = reqSession.get(url, headers=Clipper.api_headers)
                    req_json2 = req2.json()
                    if 'data' in req_json2 and len(req_json2['data']) > 0 and req_json2['data'][0]['user_id'] == self.user_id:
                        self.vod_id = req_json2['data'][0]['id']
                        self.current_duration = parseTwitchTime(str(req_json2['data'][0]['duration']))
                    else:
                        Log(f"Clipping: Vod not found")
                        self.status = "VOD not found."
                        self.color = 10038562
                        self.errorcode = 6 # vod not found
                        self.update_msg = True
                        return
                    if self.work_type == 3:
                        url = f"https://api.twitch.tv/helix/streams?user_id={self.user_id}"
                        req3 = reqSession.get(url, headers=Clipper.api_headers)
                        req_json3 = req3.json()
                        if 'data' not in req_json3 or len(req_json3['data']) < 1:
                            Log(f"Clipping: Vod not found")
                            self.status = "Channel is not live at the moment."
                            self.color = 10038562
                            self.errorcode = 6 # vod not found
                            self.update_msg = True
                            return
                        if self.current_duration['hour'] < 1 and self.current_duration['minute'] < 1 and self.current_duration['second'] < 1:
                            Log(f"Clipping: Failed to parse timestamp")
                            self.status = "Failed to parse timestamp from current VOD."
                            self.color = 10038562
                            self.errorcode = 7 # vod not found
                            self.update_msg = True
                            return
                        # attempt to download once
                        _skip_download = True
                        self.start_time = parseTime(substractTime(convertTime(self.duration),convertTime(self.current_duration)))
                        self.status = "Fetching VOD timestamp.."
                        self.update_msg = True
                        try:
                            subprocess.run(["twitch-dl", 'download', '-s', convertTime(self.start_time), '-e', convertTime(self.current_duration), '-q', 'source', '--overwrite', "--output", f"{str(self.message_id)}"+'.{format}', str(self.vod_id)])
                        except:
                            Log(f"Exception during file download: {str(e)}")
                            self.status = "Failed to download clip :("
                            self.color = 10038562
                            self.errorcode = 2 # failed to download file
                            self.update_msg = True
                            return
                        predict_path = f"{os.getcwd()}/{self.message_id}.mkv"
                        if not os.path.exists(predict_path):
                            if not Clipper.queue_system:
                                Log(f"Clipping: Queue disabled, clip abandoned")
                                self.status = "Queue system is disabled.\nTry clipping it again when VOD catches up."
                                self.color = 10038562
                                self.errorcode = 8 # queue system disabled, vod hasnt catched up
                                self.update_msg = True
                                return
                            elif len(Clipper.queue) >= Clipper.QUEUE_LIMIT:
                                Log(f"Clipping: Queue limit reached.")
                                self.status = "Too many clips are currently in a queue.\nTry using this command later."
                                self.color = 10038562
                                self.errorcode = 9 # queue limit reached
                                self.update_msg = True
                                return
                            Log(f"Added to the queue..")
                            self.status = "Clip has been added to the queue.\nIt will be uploaded as soon as VOD catches up."
                            self.color = 3426654
                            self.update_msg = True
                            self.queue_timeout = datetime.now()
                            Clipper.queue.append(self)
                            while self in Clipper.queue:
                                time.sleep(30)
                                try:
                                    subprocess.run(["twitch-dl", 'download', '-s', convertTime(self.start_time), '-e', convertTime(self.current_duration), '-q', 'source', '--overwrite', "--output", f"{str(self.message_id)}"+'.{format}', str(self.vod_id)])
                                except:
                                    Log(f"Exception during file download: {str(e)}")
                                    self.status = "Failed to download clip :("
                                    self.color = 10038562
                                    self.errorcode = 2 # failed to download file
                                    self.update_msg = True
                                    return
                                predict_path = f"{os.getcwd()}/{self.message_id}.mkv"
                                if os.path.exists(predict_path):
                                    Clipper.queue.remove(self)
                                    break
                                else:
                                    _timeout = datetime.now() - self.queue_timeout
                                    if _timeout.total_seconds() >= Clipper.QUEUE_TIMEOUT:
                                        Clipper.queue.remove(self)
                                        Log(f"Clipping: Queue timeout reached.")
                                        self.status = "Queue timeout has been reached.\nTry again later."
                                        self.color = 10038562
                                        self.errorcode = 10 # queue timeout
                                        self.update_msg = True
                                        return
                    self.work_type = 1
                except Exception as e:
                    Log(f"Exception during info gathering: {str(e)}")
                    self.status = "Could not find a VOD."
                    self.color = 10038562
                    self.errorcode = 4 # failed to find vod
                    self.update_msg = True
                    return
            if self.work_type == 1:
                self.status = "Downloading clip.."
                self.update_msg = True
                if not _skip_download:
                    try:
                        subprocess.run(["twitch-dl", 'download', '-s', convertTime(self.start_time), '-e', convertTime(addTime(self.start_time, self.duration)), '-q', 'source', '--overwrite', "--output", f"{str(self.message_id)}"+'.{format}', str(self.vod_id)])
                    except Exception as e:
                        Log(f"Exception during file download: {str(e)}")
                        self.status = "Failed to download clip :(\nVOD is probably not updated yet, try again later."
                        self.color = 10038562
                        self.errorcode = 2 # failed to download file
                        self.update_msg = True
                        return
                #predict_path = f"{os.getcwd()}\{self.message_id}.mkv"
                predict_path = f"{os.getcwd()}/{self.message_id}.mkv"
                if os.path.exists(predict_path):
                    self.status = "Uploading clip to streamable.."
                    self.update_msg = True
                    returned = None
                    try:
                        returned = Clipper.streamable_api.upload_video(predict_path, f"{self.title}")
                    except Exception as e:
                        Log(f"Exception during file upload: {str(e)}")
                        self.status = "Failed to upload clip :(\nTry again later."
                        self.color = 10038562
                        self.errorcode = 3 # failed to upload
                        self.update_msg = True
                        return
                    try:
                        os.remove(predict_path)
                    except Exception as e:
                        Log(f"Exception during file deleting: {str(e)}")
                    if 'shortcode' not in returned:
                        Log(f"Failed to upload clip [{self.user_name}]")
                        self.status = "Failed to upload clip :(\nTry again later."
                        self.color = 10038562
                        self.errorcode = 3 # failed to upload
                        self.update_msg = True
                        return
                    GlobalAccount.SaveClip(self.message_author.id, self.title, f"https://streamable.com/{returned['shortcode']}")
                    self.status = f"Clip uploaded!\nURL: https://streamable.com/{returned['shortcode']}"
                    self.color = 2067276
                    self.errorcode = 101 # success (uploaded)
                    self.update_msg = True
                    return
                else:
                    Log(f"Failed to download clip [{self.user_name}]")
                    self.status = "Failed to download clip :(\nVOD is probably not updated yet, try again later."
                    self.color = 10038562
                    self.errorcode = 2 # failed to download file
                    self.update_msg = True
                    return


class GlobalAccount:
    RECENT_CLIPS_LIMIT = 50
    RECENT_SYNCS_LIMIT = 50
    USER_OBJECT_LIMIT = 100
    # user model: {'total_clips':0, 'total_syncs':0, 'recent_clips':[], 'recent_syncs':[]}
    users = {}
    recent_clips = []
    recent_moments = []
    total_clips = 0
    total_syncs = 0

    def checkTemplate(user_id):
        if str(user_id) not in GlobalAccount.users:
            GlobalAccount.users[str(user_id)] = {'total_clips':0, 'total_syncs':0, 'recent_clips':[], 'recent_syncs':[]}

    def SaveClip(user_id, clip_title, clip_url):
        try:
            date = datetime.now().replace(microsecond = 0) - timedelta(hours = 7)
            GlobalAccount.checkTemplate(user_id)
            if len(GlobalAccount.recent_clips) >= GlobalAccount.RECENT_CLIPS_LIMIT:
                GlobalAccount.recent_clips.pop()
            GlobalAccount.recent_clips.insert(0, {'title':clip_title, 'url':clip_url, 'date':str(date), 'author':user_id})

            GlobalAccount.total_clips += 1
            GlobalAccount.users[str(user_id)]['total_clips'] += 1
            if len(GlobalAccount.users[str(user_id)]['recent_clips']) >= GlobalAccount.USER_OBJECT_LIMIT:
                GlobalAccount.users[str(user_id)]['recent_clips'].pop()
            GlobalAccount.users[str(user_id)]['recent_clips'].insert(0, {'title':clip_title, 'url':clip_url, 'date':str(date)})
        except Exception as e:
            Log(f"Error during saving clip {str(e)}")

class Twitter:
    api_headers = {
        'Authorization': ''
    }
    
    cache = {
        #Mizkif
        '4699719036' : {
            'alias':'Mizkif',
            'color':2067276,
            'liked_data':[],
            'tweets_data':[],
            'ignore_liked': True
        },
        #Emiru
        '1075578421139439616' : {
            'alias':'Emiru',
            'color':15277667,
            'liked_data':[],
            'tweets_data':[],
            'ignore_liked': True
        },
        #emiru alt
        '1495261736261365763' : {
            'alias':'Egglawl',
            'color':10181046,
            'liked_data':[],
            'tweets_data':[],
            'ignore_liked': True
        },
        #mizkif alt
        '1489490323382456321' : {
            'alias':'IsMizGoingLive',
            'color':2123412,
            'liked_data':[],
            'tweets_data':[],
            'ignore_liked': True
        },
        #villy
        '166808088688640000' : {
            'alias':'Villy',
            'color':2123412,
            'liked_data':[],
            'tweets_data':[],
            'ignore_liked': False
        }
    }

    display_new_likes = []
    display_new_tweets = []
    active = False

    def init():
        if Twitter.active:
            return
        Twitter.active = True
        Twitter.api_headers['Authorization'] = Config.twitter_auth
        t1 = threading.Thread(target=Twitter.check_liked)
        t1.start()
        t2 = threading.Thread(target=Twitter.check_tweets)
        t2.start()
        print(f'started with {Twitter.api_headers}')

    def check_liked():
        while True:
            try:
                if not Twitter.active:
                    return
                print("yo1")
                reqSession = requests.Session()
                user_count = 0
                for user in Twitter.cache:
                    if not Twitter.cache[user]['ignore_liked']:
                        user_count += 1
                for user in Twitter.cache:
                    if Twitter.cache[user]['ignore_liked']:
                        continue
                    req_liked = reqSession.get(f"https://api.twitter.com/2/users/{user}/liked_tweets?max_results=5&tweet.fields=created_at&user.fields=profile_image_url&expansions=author_id", headers=Twitter.api_headers)
                    print(f"{str(Twitter.cache[user]['alias'])} updated {str(req_liked.status_code)}")
                    if req_liked.status_code == 200:
                        req_liked_json = req_liked.json()
                        if user not in Twitter.cache:
                            Twitter.cache[user]['liked_data'] = req_liked_json['data']
                            continue
                        elif len(Twitter.cache[user]['liked_data']) == 0:
                            Twitter.cache[user]['liked_data'] = req_liked_json['data']
                            continue
                        else:
                            id_list = []
                            new_likes = []
                            for data in Twitter.cache[user]['liked_data']:
                                id_list.append(data['id'])
                            for curr_data in req_liked_json['data']:
                                if curr_data['id'] not in id_list:
                                    new_likes.append(curr_data)
                            if len(new_likes) > 0:
                                Twitter.processNewLikes(user, new_likes, req_liked_json['includes'], reqSession)
                            Twitter.cache[user]['liked_data'] = req_liked_json['data']
                reqSession.close()
                time.sleep((15 * user_count) + 2)
            except Exception as e:
                print("exception: " +str(e))
                time.sleep(10)

    def check_tweets():
        while True:
            try:
                if not Twitter.active:
                    return
                reqSession = requests.Session()
                for user in Twitter.cache:
                    req_tweets = reqSession.get(f"https://api.twitter.com/2/users/{user}/tweets?tweet.fields=source,created_at&user.fields=profile_image_url&expansions=in_reply_to_user_id,author_id", headers=Twitter.api_headers)
                    print(req_tweets.json())
                    if req_tweets.status_code == 200:
                        req_tweets_json = req_tweets.json()
                        if user not in Twitter.cache:
                            Twitter.cache[user]['tweets_data'] = req_tweets_json['data']
                            continue
                        elif len(Twitter.cache[user]['tweets_data']) == 0:
                            Twitter.cache[user]['tweets_data'] = req_tweets_json['data']
                            continue
                        else:
                            id_list = []
                            new_tweets = []
                            for data in Twitter.cache[user]['tweets_data']:
                                id_list.append(data['id'])
                            for curr_data in req_tweets_json['data']:
                                if curr_data['id'] not in id_list:
                                    new_tweets.append(curr_data)
                            if len(new_tweets) > 0:
                                Twitter.processNewTweets(user, new_tweets, req_tweets_json['includes'], reqSession)
                            Twitter.cache[user]['tweets_data'] = req_tweets_json['data']
                reqSession.close()
                time.sleep((1 * len(Twitter.cache)) + 1)
            except Exception as e:
                print("exception: " +str(e))
                time.sleep(10)
    
    def processNewLikes(user, new_likes, authors, reqSession):
        for like in new_likes:
            try:
                author_name = 'unknown'
                creation_date = 'unknown'
                author_pfp = 'unknown'
                user_pfp = 'unknown'
                if 'users' in authors and 'author_id' in like:
                    for u in authors['users']:
                        if u['id'] == like['author_id']:
                            author_name = u['username']
                            author_pfp = u['profile_image_url']
                user_details = reqSession.get(f"https://api.twitter.com/2/users/{user}?user.fields=profile_image_url", headers=Twitter.api_headers)
                user_details_json = user_details.json()
                if 'data' in user_details_json:
                    if 'profile_image_url' in user_details_json['data']:
                        user_pfp = user_details_json['data']['profile_image_url']
                if 'created_at' in like:
                    time = dateutil.parser.isoparse(like['created_at']).replace(tzinfo=None)
                    creation_date = str(time - timedelta(hours=5))
                like_id = like['id']
                date = datetime.now().replace(microsecond = 0) - timedelta(hours = 7)
                display_ready = {
                    'tweet_id': like_id,
                    'tweet_author': author_name,
                    'tweet_date': creation_date,
                    'tweet_author_pfp': author_pfp,
                    'tweet_text': like['text'],
                    'user_id': user,
                    'user_pfp': user_pfp,
                    'like_date': str(date)
                }
                Twitter.display_new_likes.append(display_ready)
            except Exception as e:
                print("exception: " +str(e))
    
    def processNewTweets(user, new_tweets, authors, reqSession):
        for tweet in new_tweets:
            try:
                author_name = 'unknown'
                creation_date = 'unknown'
                author_pfp = 'unknown'
                user_pfp = 'unknown'
                if 'users' in authors and 'author_id' in tweet:
                    author_id = tweet['author_id']
                    if 'in_reply_to_user_id' in tweet:
                        author_id = tweet['in_reply_to_user_id']
                    for u in authors['users']:
                        if u['id'] == author_id:
                            author_name = u['username']
                            author_pfp = u['profile_image_url']
                user_details = reqSession.get(f"https://api.twitter.com/2/users/{user}?user.fields=profile_image_url", headers=Twitter.api_headers)
                user_details_json = user_details.json()
                if 'data' in user_details_json:
                    if 'profile_image_url' in user_details_json['data']:
                        user_pfp = user_details_json['data']['profile_image_url']
                if 'created_at' in tweet:
                    time = dateutil.parser.isoparse(tweet['created_at']).replace(tzinfo=None)
                    creation_date = str(time - timedelta(hours=5))
                tweet_id = tweet['id']
                source = tweet['source']
                tweet_type = "tweet"
                if 'in_reply_to_user_id' in tweet:
                    tweet_type = "reply"
                elif tweet['text'].startswith('RT @'):
                    tweet_type = "retweet"
                date = datetime.now().replace(microsecond = 0) - timedelta(hours = 7)
                display_ready = {
                    'tweet_id': tweet_id,
                    'tweet_author': author_name,
                    'tweet_date': creation_date,
                    'tweet_author_pfp': author_pfp,
                    'tweet_text': tweet['text'],
                    'tweet_source': source,
                    'tweet_type': tweet_type,
                    'user_id': user,
                    'user_pfp': user_pfp,
                    'date': str(date)
                }
                Twitter.display_new_tweets.append(display_ready)
            except Exception as e:
                print("exception: " +str(e))