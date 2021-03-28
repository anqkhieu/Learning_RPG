import discord
from discord.ext import commands

import pymongo
from pymongo import MongoClient

import asyncio, csv, random

from creds import *
from authorize import *

# Testing Options
DEBUG = True

#################################################################

# Get Credentials
mongoConn = GetCredential('MongoDB')
discordToken = GetCredential('DiscordBot')

# MongoDB Setup
cluster = MongoClient(mongoConn)
db = cluster["LearningRPG-DiscordBot"]
profiles = db["lrpg"]

# Discord Bot
client = commands.Bot(command_prefix=';')
client.remove_command('help')

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    await client.change_presence(activity=discord.Game(name='a RPG for class! ⚔️'))
    authorizeSheets()

@client.event
async def on_message(message):
    if message.author == client.user: return

    userKey = {'_id': message.author.id}
    userExists = profiles.count_documents(userKey, limit = 1)

    if not userExists:
        values = {'level': 1, 'exp': 1, 'streak': 0, 'inventory':{}, 'gold': 0}
        profiles.update_one(userKey, {'$set': values}, upsert=True)
        if DEBUG: print('user does not exist, creating')
    else:
        profiles.update_one(userKey, {'$inc': {'exp':1}}, upsert=True)

    await client.process_commands(message)

@client.command(aliases=['q'])
async def question(ctx):
    num = random.randint(1,3)
    if num == 1: await qv(ctx)
    elif num == 2: await qm(ctx)
    elif num == 3: await qh(ctx)

async def sendEmbed(content, ctx, footer='None'):
    embed = discord.Embed(description=content, colour=discord.Colour.blue())
    if footer != 'None': embed.set_footer(text=footer)
    await ctx.send(embed=embed)

def randomQuestion(name):
    worksheet = openSheet(name)
    vals = worksheet.get_all_values()
    num = random.randint(7, len(vals))

    row = worksheet.row_values(num)
    time = int(worksheet.acell('E4').value)

    if name == 'Vocab':
        vocabTerm = row[1]
        row[1] = worksheet.acell('E3').value.replace('{Term}', vocabTerm)
    return row, time

async def showQuestion(type, row, duration, ctx):
    question = row[1]
    correctAns = row[2]
    shuffledAns = row[2:6]
    random.shuffle(shuffledAns)

    if type == 'History': type = '🌎' + ' - ' + type.upper()
    elif type == 'Math': type = '🧮' + ' - ' + type.upper()
    elif type == 'Vocab': type = '💬' + ' - ' + 'Vocabulary'.upper()

    embed = discord.Embed(description='**' + type + '**',
                          content= '**Q: ' + question + '**',
                          colour=discord.Colour.blue())

    content = '*React with the correct answer emoji!*\n\n'
    reactions = ['🔵', '🟥', '🔶', '💚']
    for i in range(len(shuffledAns)):
        content = content + reactions[i] + ' - ' + shuffledAns[i] + '\n'

    embed.add_field(name=question, value=content)
    embed.set_footer(text=f"*You have {duration} seconds to answer.*")
    sentQuestion = await ctx.send(embed=embed)
    for choiceReaction in reactions: await sentQuestion.add_reaction(choiceReaction)

    def checkUser(_, user):
        return (user == ctx.message.author)

    try:
        userReaction, user = await client.wait_for('reaction_add', timeout=duration, check=checkUser)
    except asyncio.TimeoutError:
        num = random.randint(1,3)
        if num == 1: await sendEmbed(f"🕓 *Oh no, out of time...*", ctx)
        elif num == 2: await sendEmbed(f"🕓 *Awhhh, too slow.*", ctx)
        elif num == 3: await sendEmbed(f"🕓 *You did not choose an answer in time!*", ctx)
        return

    # check if correct answer
    try:
        index = reactions.index(str(userReaction.emoji))
        chosenAns = shuffledAns[index]
    except:
        return

    if chosenAns == correctAns:
        userKey = user.id
        profiles.update_one({'_id': userKey}, {"$inc": {'streak': 1}})

        streak = profiles.find_one({'_id': userKey})['streak']
        exp = random.randint((streak * 2), (streak * 5))
        gold = random.randint(1, streak * 3) * 10

        profiles.update_one({'_id': userKey}, {"$inc": {'exp': exp}})
        profiles.update_one({'_id': userKey}, {"$inc": {'gold': gold}})

        num = random.randint(1,3)
        if num == 1: await sendEmbed(f"🎉 *Yesss, nice job!*", ctx, f"🏆 Streak: {streak}x | Exp: +{exp} | Gold: +{gold}g")
        elif num == 2: await sendEmbed(f"🎉 *Way to go!*", ctx, f"🏆 Streak: {streak}x | Exp: +{exp} | Gold: +{gold}g")
        elif num == 3: await sendEmbed(f"🎉 *That's right! Well done.*", ctx, f"🏆 Streak: {streak}x | Exp: +{exp} | Gold: +{gold}g")
    else:
        num = random.randint(1,3)
        if num == 1: await sendEmbed(f"😢 *Looks like you have some studying to do!*", ctx)
        elif num == 2: await sendEmbed(f"😢 *Not quite right, sadly...*", ctx)
        elif num == 3: await sendEmbed(f"😢 *Agh, try again next time?*", ctx)

        streakNum = profiles.find_one({'_id': user.id})['streak']
        if  streakNum > 0:
            profiles.update_one({'_id': user.id}, {'$set': {'streak': 0}}, upsert=True)
            await sendEmbed(f"😔 *Your streak ({streakNum}x) is broken...*", ctx)

@client.command(aliases=['vocab'])
async def qv(ctx):
    type = 'Vocab'
    row, time = randomQuestion(type)
    await showQuestion(type, row, time, ctx)

@client.command(aliases=['math'])
async def qm(ctx):
    type = 'Math'
    row, time = randomQuestion(type)
    await showQuestion(type, row, time, ctx)

@client.command(aliases=['history'])
async def qh(ctx):
    type = 'History'
    row, time = randomQuestion(type)
    await showQuestion(type, row, time, ctx)

@client.command()
async def profile(ctx):
    userKey = ctx.message.author.id
    content = f"🌟 **{ctx.message.author}** \n \
                **Streak:** {profiles.find_one({'_id': userKey})['streak']}x\n \
                **EXP:** {profiles.find_one({'_id': userKey})['exp']}\n \
                **Gold:** {profiles.find_one({'_id': userKey})['gold']}g"
    embed = discord.Embed(description=content, colour=discord.Colour.blue())
    await ctx.send(embed=embed)

@client.command()
async def showAll(ctx):
    await ctx.send("*Exporting all data from database!*")
    ids = profiles.distinct('_id')
    for userKey in ids:
        name = await client.fetch_user(userKey)
        content = f"🌟 **{name}**\n \
                    **Streak:** {profiles.find_one({'_id': userKey})['streak']}x\n \
                    **EXP:** {profiles.find_one({'_id': userKey})['exp']}\n \
                    **Gold:** {profiles.find_one({'_id': userKey})['gold']}g"
        embed = discord.Embed(description=content, colour=discord.Colour.blue())
        await ctx.send(embed=embed)

@client.command(aliases=['store'])
async def shop(ctx):
    await sendEmbed(f"🛍️ - **THE STORE** \n\n\
                    (1000g) one extra credit points on Homework\n\
                    (1500g) a custom Discord emoji on the class server\n\
                    (2500g) a custom Discord role and color on the class server\n\
                    (5000g) a 3-day extension on any assignment\n\n \
                    <:coins:825584898801926174> *You currently have {profiles.find_one({'_id': ctx.message.author.id})['gold']}g.*",
                    ctx, "📝 All purchases are subject to teacher approval, you must email them in order to redeem!")

@client.command()
async def help(ctx):
    embed = discord.Embed(description="👩‍🏫 **Welcome to Learning RPG** \
    \nLevel up your character by learning! Answer questions correctly in a row to start a streak, \
    and even earn special items and rewards on your journey. If you would like to see the full list \
    of game modes and features, type `;help` into chat anytime. \n\n**To get started playing now, type `;q` \
    into chat to bring up a question.**", colour=discord.Colour.blue())
    await ctx.send(embed=embed)

    embed = discord.Embed(description = ":star2: **ALL COMMANDS**\n\n", colour=discord.Colour.blue())
    embed.add_field(name='`;q` or `;question`',
                    value='Summon a random question of any subject.', inline=False)
    embed.add_field(name='`;qv` or `;vocab`',
                    value='Summon a random Vocabulary question.', inline=False)
    embed.add_field(name='`;qm` or `;math`',
                    value='Summon a random Math question.', inline=False)
    embed.add_field(name='`;qh` or `;history`',
                    value='Summon a random History question.', inline=False)
    embed.add_field(name='`;profile`',
                    value='Show your character stats, streak number, and gold.', inline=False)
    embed.add_field(name='`;showAll`',
                    value='Show all stats of users on the server.', inline=False)
    embed.add_field(name='`;shop`',
                    value='Bring up the shop menu.', inline=False)
    embed.add_field(name='`;help`',
                    value='Brings up this help info.', inline=False)
    await ctx.send(embed=embed)


client.run(discordToken)
