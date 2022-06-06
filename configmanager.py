import os
import urllib, json

class Config:
    # config.json (readonly)
    bot_token = ''
    owner_id = 0
    server_id = 0
    streamable_account = ''
    streamable_password = ''
    twitch_api_access = ''
    twitch_api_client = ''
    ig_account = ''
    ig_password = ''
    twitter_auth = ''

def LoadConfig():
    try:
        with open("config.json", "r") as jsonfile:
            data = json.load(jsonfile)
            print("Config loaded.")
            if 'bot_token' in data:
                Config.bot_token = data['bot_token']
            if 'owner_id' in data:
                Config.owner_id = data['owner_id']
            if 'server_id' in data:
                Config.server_id = data['server_id']
            if 'streamable_credentials' in data:
                if 'account_name' in data['streamable_credentials']:
                    Config.streamable_account = data['streamable_credentials']['account_name']
                if 'password' in data['streamable_credentials']:
                    Config.streamable_password = data['streamable_credentials']['password']
            if 'twitch_api_details' in data:
                if 'access_token' in data['twitch_api_details']:
                    Config.twitch_api_access = data['twitch_api_details']['access_token']
                if 'client_token' in data['twitch_api_details']:
                    Config.twitch_api_client = data['twitch_api_details']['client_token']
            if 'instagram' in data:
                if 'account' in data['instagram']:
                    Config.ig_account = data['instagram']['account']
                if 'password' in data['instagram']:
                    Config.ig_password = data['instagram']['password']
            if 'twitter_auth' in data:
                Config.twitter_auth = data['twitter_auth']
    except:
        print("Could not load config.json file.. Creating a new template..")
        GenerateConfig()

def GenerateConfig():
    config = {
        'bot_token' : 'discord_bot_token_here',
        'owner_id' : 0,
        'server_id' : 0,
        'streamable_credentials': {
            'account_name': '',
            'password': ''
        },
        'twitch_api_details' : {
            'access_token' : '',
            'client_token' : ''
        },
        'instagram' : {
            'account' : '',
            'password' : ''
        },
        'twitter_auth' : ''
    }
    json_settings = json.dumps(config)
    with open("config.json", "w") as jsonfile:
        jsonfile.write(json_settings)
        print('Config file generated at root path!')