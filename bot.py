import discord
from secret import TOKEN
from discord.ext import commands
import psycopg2
from datetime import datetime
import praw
import random
import time
import typing

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
    global ice_emoji
    global anti_ice_emoji
    ice_emoji = discord.utils.get(bot.guilds[0].emojis, name="ice")
    anti_ice_emoji = discord.utils.get(bot.guilds[0].emojis, name="anti_ice")
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
  time_sums = {k: v for k, v in sorted(time_sums.items(), key=lambda item: item[1], reverse=True)} # does the sorting somehow

  stats = "```"
  for user_id in time_sums:
    time = str(time_sums[user_id]).split('.')[0] # last part removes microseconds
    stats += bot.get_user(user_id).name + ": " + time + "\n"
  stats+= "```"
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

@bot.command(name='kick', help='Vote kick iemand uit de discord! (@user)')
async def on_kick(ctx, user: discord.Member):
    vkmessage = await ctx.send("Kick Player: " + user.mention + "?")  # send a message that gets called back later
    emojies = ['👍', '👎']
    for emoji in emojies:
        await vkmessage.add_reaction(emoji)     # add the emojies to the vote kick message

    time.sleep(10)    # wait 10 sec before counting the emojies
    vkmessage = await ctx.fetch_message(vkmessage.id)

    pos, neg = 0, 0
    for emoji in vkmessage.reactions:   # Count reactions
        if str(emoji) == '👍':
            pos = emoji.count
        if str(emoji) == '👎':
            neg = emoji.count
    if pos-neg>=2:            # When kicked, get link send to join back
        link = await ctx.channel.create_invite(max_age = 300)
        await discord.Member.send(user, "Invite: " + link.url)
        await user.kick()
        await ctx.send("Kicking Player: " + user.mention + "...")
    else:
        await ctx.send(user.mention + " has not been kicked")

@bot.command(name="add_ice", help="Geef iemand een ice!")
async def add_ice(ctx, user: typing.Optional[discord.Member] = None, amount:int = 1):
  if amount < 1:
    await ctx.send("Goed geprobeerd, maar je moet een getal groter dan 0 geven")
    return
  if user and user != ctx.message.author: # in case you want to add ices to other you have to vote
    votemessage = await ctx.send("Moet " + user.mention + " " + str(amount) + " ice(s) trekken?")
    await votemessage.add_reaction(ice_emoji)
    await votemessage.add_reaction(anti_ice_emoji)
    time.sleep(10)
    votemessage = await ctx.fetch_message(votemessage.id)

    pos, neg = 0, 0
    for emoji in votemessage.reactions:   # Count reactions
        if emoji == ice_emoji:
            pos = emoji.count
        if emoji == anti_ice_emoji:
            neg = emoji.count
    if pos-neg < 2: # failed vote
      await ctx.send(user.mention + " hoeft geen extra ices te trekken.")
      return
  else:
    user = ctx.message.author
  cur.execute("SELECT * FROM ices WHERE user_id="+ str(user.id))
  current_ices = cur.fetchone()
  if not current_ices:
    cur.execute("INSERT INTO ices (user_id, ices) VALUES (%s,%s)", (user.id, max(amount,0)))
    await ctx.send(user.mention + " moet nog " + str(max(amount,0)) + " ice(s) trekken!")
  else:
    cur.execute("UPDATE ices SET ices="+ str(max(amount+current_ices[1],0)) + "WHERE user_id="+ str(user.id))
    await ctx.send(user.mention + " moet nog " + str(max(amount+current_ices[1],0)) + " ice(s) trekken!")

@bot.command(name="remove_ice", help="Iemand heeft een ice getrokken")
async def remove_ice(ctx, user: typing.Optional[discord.Member] = None, amount:int = 1):
  if amount < 1:
    await ctx.send("Goed geprobeerd, maar je moet een getal groter dan 0 geven")
    return
  if not user or user == ctx.message.author: # in case your deleting your own ices others need to vote
    user = ctx.message.author
    votemessage = await ctx.send("Heeft " + user.mention + " " + str(amount) + " ice(s) getrokken?")
    await votemessage.add_reaction(ice_emoji)
    await votemessage.add_reaction(anti_ice_emoji)
    time.sleep(10)
    votemessage = await ctx.fetch_message(votemessage.id)

    pos, neg = 0, 0
    for emoji in votemessage.reactions:   # Count reactions
        if emoji == ice_emoji:
            pos = emoji.count
        if emoji == anti_ice_emoji:
            neg = emoji.count
    if pos-neg < 2:
      await ctx.send(user.mention + " heeft geen " + str(amount) + " ice(s) getrokken.")
      return
  
  cur.execute("SELECT * FROM ices WHERE user_id=" + str(user.id))
  current_ices = cur.fetchone()
  if not current_ices:
    cur.execute("INSERT INTO ices (user_id, ices) VALUES (%s,%s)", (user.id, 0))
    await ctx.send(user.mention + " moet nog 0 ice(s) trekken!")
  else:
    cur.execute("UPDATE ices SET ices="+ str(max(current_ices[1] - amount,0)) + "WHERE user_id="+ str(user.id))
    await ctx.send(user.mention + " moet nog " + str(max(current_ices[1] - amount,0)) + " ice(s) trekken!")
  
@bot.command(name="ices", help="Laat lijst van nog te trekken ices zien")
async def ices(ctx):
  cur.execute('SELECT * FROM ices ORDER BY ices DESC')
  data = cur.fetchall()

  message = "```"
  for (user_id,ices) in data:
    message += bot.get_user(user_id).name + ": " + str(ices) + "\n"
  message+= "```"
  await ctx.send(message)

@add_ice.error
async def add_ice_error(ctx,error):
  print("error: ", error)
  await ctx.send("""Gebruik: \n'?add_ice' voegt 1 ice aan jezelf toe 
'?add_ice @user' start een vote om een ice aan user toe te voegen 
'?add_ice @user 5' start een vote om 5 ices aan user toe te voegen""")

@remove_ice.error
async def remove_ice_error(ctx,error):
  print("error: ", error)
  await ctx.send("""Gebruik: \n'?remove_ice' start een vote om 1 ice van jezelf weg te halen 
'?remove_ice @user' haalt een ice weg van user
'?remove_ice @user 5' haalt 5 ices weg van user""")

              
@on_kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('Please enter member using @')
    else:
        print("error: ", error)


bot.run(TOKEN)