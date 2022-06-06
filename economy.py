import discord
from discord.ext import tasks, commands
from modules import Log
from configmanager import Config, LoadConfig
import threading
from datetime import date, datetime, timedelta
import os
import urllib, json

PRED_OPEN = 0
PRED_CLOSED = 1
PRED_ENDED = 2

def getEmote(index):
    if index == 1:
        return "<:one:981996226499207189>"
    elif index == 2:
        return "<:two:981996277086711858>"
    elif index == 3:
        return "<:three:981996283558502511>"
    elif index == 4:
        return "<:four:981996289325682758>"
    elif index == 5:
        return "<:five:981996299857567754>"
    else:
        return ""

class Cache:
    FILE_NAME = "economy.json"
    PREDICITON_CACHE_LIMIT = 10

    user_cache = {}
    prediction_cache = {}
    last_prediction_id = 0

    def save_cache():
        cache = {
            'user_cache' : Cache.user_cache,
            'prediction_cache' : Cache.prediction_cache,
            'last_prediction_id' : Cache.last_prediction_id
        }
        cache_json = json.dumps(cache)
        with open(Cache.FILE_NAME, "w") as jsonfile:
            jsonfile.write(cache_json)

    def load_cache():
        try:
            with open(Cache.FILE_NAME, "r") as jsonfile:
                cache = json.load(jsonfile)
                print("Config loaded.")
                if 'user_cache' in cache:
                    Cache.user_cache = cache['user_cache']
                if 'prediction_cache' in cache:
                    _pCache = cache['prediction_cache']
                    for _pKey in _pCache:
                        Cache.prediction_cache[int(_pKey)] = _pCache[_pKey]
                if 'last_prediction_id' in cache:
                    Cache.last_prediction_id = cache['last_prediction_id']
        except Exception as e:
            Log(f"Failed to load economy cache: {str(e)}")
    
    def get_user_balance(user_id):
        if user_id in Cache.user_cache:
            if 'balance' in Cache.user_cache[user_id]:
                return Cache.user_cache[user_id]['balance']
            else:
                Cache.user_cache[user_id]['balance'] = 1000
                Cache.save_cache()
        else:
            Cache.add_user(user_id)
            Cache.save_cache()
            return 1000

    def add_user(user_id):
        if user_id in Cache.user_cache:
            return
        else:
            Cache.user_cache[user_id] = {'balance':1000}
    
    def set_user_balance(user_id, value):
        if user_id in Cache.user_cache:
            Cache.user_cache[user_id]['balance'] = value
            Cache.save_cache()
        else:
            Cache.add_user(user_id)
            Cache.user_cache[user_id]['balance'] = value
            Cache.save_cache()
    
    def change_user_balance(user_id, value):
        if user_id in Cache.user_cache:
            if 'balance' in Cache.user_cache[user_id]:
                Cache.user_cache[user_id]['balance'] = Cache.get_user_balance(user_id) + value
                Cache.save_cache()
            else:
                Cache.user_cache[user_id]['balance'] = 1000 + value
                Cache.save_cache()
        else:
            Cache.add_user(user_id)
            Cache.user_cache[user_id]['balance'] = 1000 + value
            Cache.save_cache()

class Economy:
    initialized = False

    def init():
        try:
            Economy.initialized = True
            Cache.load_cache()
        except Exception as e:
            Log(f"Failed to load Economy: {str(e)}")
            return
    
    def getUserInfo(user_id, info):
        if info == "balance":
            return Cache.get_user_balance(user_id)
    
    def setUserBalance(user_id, value):
        Cache.set_user_balance(user_id, value)
    
    def changeUserBalance(user_id, value):
        Cache.change_user_balance(user_id, value)
    
    def checkPrediction():
        for _id in Cache.prediction_cache:
            prediction = Cache.prediction_cache[_id]
            if 'state' in prediction and (prediction['state'] == PRED_OPEN or prediction['state'] == PRED_CLOSED):
                return True
        return False

    def startPrediction(name, options):
        date = datetime.now().replace(microsecond = 0)
        curr_id = Cache.last_prediction_id + 1
        Cache.last_prediction_id += 1
        options_data = []
        for _opt in options:
            option_build = {'name': _opt, 'entries':[], 'total_users':0, 'total_money':0, 'percentage':0, 'rate':1.0}
            options_data.append(option_build)
        Cache.prediction_cache[curr_id] = {'name':name, 'started':str(date), 'options':options_data, 'state':PRED_OPEN, 'result':-1, 'channel_id':-1, 'message_id':-1, "author_n":"", "author_u":""}
        Cache.save_cache()
        return curr_id
    
    def closePrediction(prediction_id):
        prediction = Economy.getPrediction(prediction_id)
        if prediction == None:
            return 0 # prediction not found
        if prediction['state'] != PRED_OPEN:
            return 1 # prediction is already closed
        Cache.prediction_cache[prediction_id]['state'] = PRED_CLOSED
        Cache.save_cache()
        return -1
    
    async def endPrediction(client, ctx, prediction_id, result):
        prediction = Economy.getPrediction(prediction_id)
        if prediction == None:
            return 0 # prediction not found
        if prediction['state'] != PRED_CLOSED:
            return 1 # prediction must be closed
        result = int(result)
        Cache.prediction_cache[prediction_id]['state'] = PRED_ENDED
        Cache.prediction_cache[prediction_id]['result'] = result-1
        # pay out the winners
        winner_option = Cache.prediction_cache[prediction_id]['options'][result-1]
        ratio = float(winner_option['rate'])
        for entry in winner_option['entries']:
            Economy.changeUserBalance(str(entry['user_id']),int(round(entry['amount'] * ratio, 0)))
        
        total = 0
        for _opt in prediction['options']:
            total += _opt['total_money']

        # announce winners
        channel = client.get_channel(prediction['channel_id'])

        options_text = f"<:crown:982030519166443541> {getEmote(result)} {winner_option['name']}"
        options_text += f"\n\nA total of {total}$ has been paid out to {winner_option['total_users']} users <:partying_face:982031267610648627>"
        embed = discord.Embed(title=f"{prediction['name']}", description=f"{options_text}", color=discord.Color(3066993))
        embed.set_author(name=f"{ctx.author.name} ended a prediction", icon_url=f"{ctx.author.avatar_url}")
        embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")

        await channel.send(embed=embed)
        Cache.save_cache()
        return -1

    def getPrediction(_id):
        if _id == -1:
            if Cache.last_prediction_id in Cache.prediction_cache:
                return Cache.prediction_cache[Cache.last_prediction_id]
            else:
                return None
        if _id in Cache.prediction_cache:
            return Cache.prediction_cache[_id]
        else:
            return None
    
    def getLastPredictionId():
        return Cache.last_prediction_id
    
    def addPredictionEntry(user_id, prediction_id, option, amount):
        prediction = Economy.getPrediction(prediction_id)
        option = option - 1
        if prediction == None:
            return 0 # prediction not found
        if prediction['state'] != PRED_OPEN:
            return 1 # prediction is closed
        for _opt in prediction['options']:
            for entry in _opt['entries']:
                if entry['user_id'] == user_id:
                    return 2 # user already chose an option
        if option < 0 or option > len(prediction['options']) - 1:
            return 3 # option not found
        entry_build = {'user_id': user_id, 'amount': amount}
        Cache.prediction_cache[prediction_id]['options'][option]['entries'].append(entry_build)
        prediction = Cache.prediction_cache[prediction_id]
        # compute new prediction stats
        Cache.prediction_cache[prediction_id]['options'][option]['total_money'] += amount
        Cache.prediction_cache[prediction_id]['options'][option]['total_users'] += 1

        total = 0
        for _opt in prediction['options']:
            total += _opt['total_money']

        for _opt in prediction['options']:
            if _opt['total_money'] != 0:
                _opt['rate'] = str(round(total / _opt['total_money'], 2))
            else:
                _opt['rate'] = 0.0
            if total != 0:
                _opt['percentage'] = int(round(_opt['total_money'] / total, 0) * 100)
        Cache.save_cache()
        return -1

    async def displayPrediction(client, prediction_id, ctx=None):
        try:
            prediction = Economy.getPrediction(prediction_id)
            if prediction == None:
                return False
            if ctx == None and prediction['channel_id'] == -1:
                return False
            channel_id = prediction['channel_id']
            message_id = prediction['message_id']
            
            options_text = ""
            index = 1
            total_money = 0
            total_users = 0
            for _opt in prediction['options']:
                options_text += f"{str(getEmote(index))} "
                options_text += str(_opt['name']) + " - " + str(_opt['percentage']) + "% points, " + str(_opt['total_users']) + " entries, 1:" + str(_opt['rate']) + " winnings\n"
                total_money += _opt['total_money']
                total_users += _opt['total_users']
                index += 1
            color = 15844367
            if prediction['state'] == PRED_OPEN:
                options_text += "\nBet your money with '>predict (option number) (amount)'\n"
            elif prediction['state'] == PRED_CLOSED:
                color = 12745742
                options_text += "\n<:lock:982023436010401862> Prediction is closed, waiting for result..\n"
            if ctx != None and prediction['author_n'] == "":
                Cache.prediction_cache[prediction_id]['author_n'] = ctx.author.name
                Cache.prediction_cache[prediction_id]['author_u'] = str(ctx.author.avatar_url)
                Cache.save_cache()
            embed = discord.Embed(title=f"{prediction['name']}", description=f"{options_text}", color=discord.Color(color))
            embed.add_field(name=f"Total money", value=f"{total_money}$")
            embed.add_field(name=f"Total entries", value=f"{total_users}")
            embed.add_field(name=f"Started at", value=f"{prediction['started']}")
            embed.set_thumbnail(url=f"https://media.discordapp.net/attachments/961765313416941568/981999371782590474/unknown.png")
            embed.set_footer(text="Emikif ✨", icon_url="https://media.discordapp.net/attachments/949768918757691403/961715957338873887/darkice.png?width=679&height=609")
            if channel_id == -1:
                channel_id = ctx.channel.id
                embed.set_author(name=f"{ctx.author.name} started prediction", icon_url=f"{ctx.author.avatar_url}")
                msg = await ctx.reply(embed=embed)
                message_id = msg.id
                Cache.prediction_cache[prediction_id]['channel_id'] = channel_id
                Cache.prediction_cache[prediction_id]['message_id'] = message_id
                Cache.save_cache()
                return True
            elif channel_id != -1 and message_id != -1:
                channel = client.get_channel(channel_id)
                msg = await channel.fetch_message(message_id)

                embed.set_author(name=f"{Cache.prediction_cache[prediction_id]['author_n']} started prediction", icon_url=f"{Cache.prediction_cache[prediction_id]['author_u']}")
                await msg.edit(embed=embed)
            return False
        except Exception as e:
            Log(f"Error during displaying prediction: {e}")
            return False

        
        

