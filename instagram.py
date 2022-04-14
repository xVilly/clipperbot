from pathlib import Path
from instagrapi import Client
from pydantic import HttpUrl
from configmanager import Config, LoadConfig
import threading
from datetime import date, datetime, timedelta
import os
from modules import Log, Clipper
from pystreamable import StreamableApi

class Instagram:
    ready = False
    cl = None
    stories_ready = []

    def init():
        Instagram.cl = Client()
        Instagram.cl.login(Config.ig_account, Config.ig_password)
        Instagram.ready = True
        

    def getStories(user_name, author):
        user_id = Instagram.cl.user_id_from_username(user_name)
        stories = Instagram.cl.user_stories(user_id)
        for story in stories:
            s = Story()
            s.author = author
            s.user_name = story.user.username
            s.user_pic = str(story.user.profile_pic_url)
            s.media_type = story.media_type
            s.taken_at = story.taken_at
            s.thumbnail_link = str(story.thumbnail_url)
            s.story_pk = story.pk

            if s.media_type == 1:
                Instagram.stories_ready.append(s)
            elif s.media_type == 2:
                s.download_video()


class Story:
    def __init__(self):
        self.author = None
        self.user_name = ""
        self.user_pic = ""
        self.taken_at = None
        self.media_type = 0
        self.streamable_link = ""
        self.thumbnail_link = ""
        self.story_pk = 0
    
    def download_video(self):
        if self.media_type != 2:
            return
        t1 = threading.Thread(target=self.download_video_work)
        t1.start()

    def download_video_work(self):
        try:
            Instagram.cl.story_download(self.story_pk, f"{self.story_pk}", f"{os.getcwd()}")
        except Exception as e:
            Log(f"Failed to download story 5 [{self.user_name}]")
            return
        predict_path = f"{os.getcwd()}/{self.story_pk}.mp4"
        if os.path.exists(predict_path):
            try:
                returned = Clipper.streamable_api.upload_video(predict_path, f"{self.user_name} - {str(self.taken_at)}")
            except Exception as e:
                Log(f"Exception during file 3 upload: {str(e)}")
                return
            try:
                os.remove(predict_path)
            except Exception as e:
                Log(f"Exception during file deleting: {str(e)}")
            if 'shortcode' not in returned:
                Log(f"Failed to upload story 2 [{self.user_name}]")
                return
            self.streamable_link = f"https://streamable.com/{returned['shortcode']}"
            Instagram.stories_ready.append(self)
            return
        else:
            Log(f"Failed to download story 1 [{self.user_name}]")
            return