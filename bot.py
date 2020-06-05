# import discord
from secret import TOKEN
from discord.ext import commands
import psycopg2
from datetime import datetime
import praw
import random

description = '''LIT Bot v0.2'''
bot = commands.Bot(command_prefix='?', description=description)

# connect to database
db = psycopg2.connect('dbname=discord_data')
db.autocommit = True
cur = db.cursor()

current_voice_channel_members = {}

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.command()
async def hello(ctx):
    """Says world"""
    await ctx.send("world")

@bot.event
async def on_voice_state_update(member, before, after):
  print(hash(member))
  if before.channel == None and after.channel != None: # member joins voice channel
    current_voice_channel_members[member.id] = datetime.now()
    print(member.display_name + " joined " + after.channel.name)
  elif before.channel != None and after.channel == None:
    if member.id not in current_voice_channel_members:
      print("ERROR: " + member.display_name + " left a voice channel he never joined")
      return
    entry = (member.id, before.channel.id, current_voice_channel_members.pop(member.id), datetime.now())
    try:
      cur.execute("INSERT INTO voice_channel_data (user_id, channel_id, join_time, leave_time) VALUES (%s,%s,%s,%s)", entry)
    except:
      print("ERROR: probably the id was too big again... \nid:" , member.id)
    print(member.display_name + " left " + before.channel.name)

@bot.command()
async def stats(ctx):
  """Shows data on voice channel activity"""
  cur.execute('SELECT * FROM voice_channel_data')
  time_sums = {}
  for (user_id, channel, join_time, leave_time) in cur.fetchall():
    if user_id not in time_sums:
      time_sums[user_id] = leave_time - join_time
    else:
      time_sums[user_id] += leave_time - join_time

  stats = ""
  for user_id in time_sums:
    time = str(time_sums[user_id]).split('.')[0] # last part removes microseconds
    stats += bot.get_user(user_id).name + ": " + time + "\n"
  await ctx.send(stats)

@bot.command(name='meme', help='Pakt een epische meme van r/memes')
async def on_meme(ctx):
    memes = praw.Reddit(client_id="nILEhRzBOkWsUA",
                     client_secret="xCkBoPYyBULhvk1-wq9DjQ0Bw3k",
                     user_agent="TommieBoyRandomDiscord").subreddit('memes').hot()
    meme_to_pick = random.randint(1, 10)
    for i in range(0, meme_to_pick):
        submission = next(x for x in memes if not x.stickied)

    await ctx.channel.send(submission.url)

bot.run(TOKEN)