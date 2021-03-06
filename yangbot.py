import discord
import asyncio
import secretvalues
import traceback
import random
from datetime import datetime
from datetime import timedelta
import recordconvo
from secretvalues import *
from trigger import *
from discordsim import simulate, message_cache_ucsb, SIMULATION_INTERVAL
from trivia import trivia_question
from catfacts import cat_facts
import perspective

def prune(send_message):
	pos = send_message.find('>')
	return send_message[pos+1:]


def contains(text, choices):
	split_text = text.split()
	split_text = [s.lower() for s in split_text]
	for word in choices:
		if word in split_text:
			return True
	return False

do_not_reply = "I do not reply to private messages. If you have any questions, please message one of the mods, preferably Oppen_heimer."

on_invalid_intro = "Your message has been deleted for not following the introduction format that we have listed out. Please follow the format given.\n\n1) Discord handle (username#XXXX)\n2) School/Year/Major or the equivalent (UCSB/3rd/Underwater Basketweaving)\n3) Reason for joining the server (Make new friends)\n4) How you found us.\n5) [Optional] Anything you'd like to say"

on_join_message = "Hello, %s, and welcome to the UCSB Discord Server!\n \nWe ask that you introduce yourself so that the other members can get to know you better. Please post an introduction to our dedicated introductions channel with the following format:\n\n1) Discord handle (username#XXXX)\n2) School/Year/Major or the equivalent (UCSB/3rd/Underwater Basketweaving)\n3) Reason for joining the server (Make new friends)\n4) How you found us.\n5) [Optional] Anything you'd like to say\nIf you found us through another person, please list their name or their discord handle because we like to keep track of who invites other people.\n \nAlso, please read the rules. We don't want to have to ban you because you failed to read a short list of rules.\n \n \n(Disclaimer: This bot is NOT Chancellor Yang, and does not represent his opinions.)" 

on_toxic_message = "Message has been marked for toxicity:\nUser: {}\nChannel: {}\nTime: {}\nMessage: {}\nCertainty: {}"

recent_channel_messages = {}

client = discord.Client()


async def trigger(message):
	global last_trigger
	for option, words in trigger_words.items():
		if option not in gauchito_only:
			if contains(message.content, words):
				last_trigger = datetime.now()
				await client.send_message(message.channel, choiced_responses[option])
				break
		elif gauchito_id in [role.id for role in message.author.roles]:
			if contains(message.content, words):
				last_trigger = datetime.now()
				await client.send_message(message.channel, choiced_responses[option])
				break

async def yang_send(message):
	if message.author.server_permissions.manage_server:
		if len(message.channel_mentions) != 0:
			await client.send_message(message.channel_mentions[0], prune(message.content))
			if message.content[5] == 'h':
				await client.delete_message(message)
		else:
			await client.send_message(message.channel, 'Syntax is "$send [channel mention] text"')
	else:
		await client.send_message(message.channel, 'Invalid Permissions')

prev_cat_fact = "-1"
def get_random_catfact():
	global prev_cat_fact
	while(True):
		fact = random.choice(cat_facts)
		if id != prev_cat_fact:
			prev_cat_fact = fact
			return fact


@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('--------')

@client.event
async def on_message(message):
	#TODO stuff
	global recording, recent_channel_messages, last_discord_simulation
	
	if message.channel.is_private:
		try:
			await client.send_message(message.author, content=(do_not_reply))
			print('{}\n{}'.format(message.author, message.content))
			return
		except:
			print('This fucking error')
	elif message.content is not None and message.content != '':
		try:
			if message.server.id == server_id and not message.author.bot:
				toxic, toxic_score = perspective.is_toxic(message.clean_content)
				if toxic:
					await client.send_message(message.server.get_channel(admin_alerts), on_toxic_message.format(message.author.display_name, message.channel.mention, (message.timestamp-timedelta(hours=7)), message.clean_content, toxic_score*100))
				if message.channel.id == server_id:
					if message.content[0] not in '012345':
						try:
							await client.send_message(message.author, content=(on_invalid_intro))
						except:
							print('This fucking error')
						await client.delete_message(message)
				if message.channel.id in recent_channel_messages.keys():
					recent_channel_messages[message.channel.id].append(message)
					is_same = same_message_response(message.channel.id)
					if is_same:
						await client.send_message(message.channel, message.content)
						recent_channel_messages[message.channel.id].clear()
				if recording is not None and recording == message.channel:
					recordconvo.record_message(message)

				if message.content[0:5] == '$send':
					await yang_send(message)
				elif message.content[0:7] == '$record' and message.author.server_permissions.manage_server:
					if recording is None:
						recordconvo.record_init()
						recording = message.channel
					else:
						await client.send_message(message.channel, "Already recording in %s" % (recording.mention))
				elif message.content == '$trivia':
					await client.send_message(message.channel, "We do not have enough trivia questions. This feature will be available in the future")
					#await trivia_question(client, message.channel)
				elif message.content[0:11] == '$stoprecord' and message.author.server_permissions.manage_server:
					recordconvo.record_end()
					recording = None
				elif message.content[0:8] == '$catfact' or message.content.lower()[0:11] == 'unsubscribe':
					await client.send_message(message.channel, 'Thank you for subscribing to CatFacts™! Did you know:\n `%s`\n\nType "UNSUBSCRIBE" to stop getting cat facts' % get_random_catfact())
				elif message.timestamp - last_trigger > timedelta(minutes=10):
					await trigger(message)

				if len(message.content.split()) > 2 and message.channel.id not in no_simulate:
					with open(message_cache_ucsb, 'a') as file:
						file.write(message.clean_content + '\n')
				if message.timestamp - last_discord_simulation >= SIMULATION_INTERVAL:
					simulated_message = simulate(message_cache_ucsb)
					if simulated_message is not None:
						await client.send_message(message.server.get_channel(sim_channel_id), simulated_message)
						open(message_cache_ucsb, 'w').close()
						last_discord_simulation = message.timestamp
		except Exception as e:
			print('There was an error somewhere in on_message: ' +str(e))
			traceback.print_exc()
			print('Message Channel: ' + message.channel.name)
			print('Message Content: ' + message.content)
			print('Message Author: ' + message.author.name + '\n')


@client.event
async def on_message_edit(before, after):
	try:
		if after.server.id == server_id and after.author != client.user:
			if recording is not None and recording == after.channel:
				recordconvo.record_message_edit(after)
	except:
		print('There was an error somewhere in on_message_edit')
		traceback.print_exc()

@client.event
async def on_message_delete(message):
	try:
		if message.server.id == server_id and message.author != client.user:
			if recording is not None and recording == message.channel:
				recordconvo.record_message_delete(message)
	except:
		print('There was an error somewhere in on_message_delete')
		traceback.print_exc()


@client.event
async def on_reaction_add(reaction, user):
	try:
		if not reaction.me:
			await client.add_reaction(reaction.message, reaction.emoji)
	except:
		print('There was an error somewhere in on_reaction_add')
		traceback.print_exc()


@client.event
async def on_reaction_remove(reaction, user):
	try:
		if reaction.count == 1 and reaction.me:
			await client.remove_reaction(reaction.message, reaction.emoji, reaction.message.server.me)
	except Exception as e:
		print('There was an error somewhere in on_reaction_remove: ' + str(e))
		traceback.print_exc()

@client.event
async def on_member_join(member):
	try:
		await client.send_message(member, content=(on_join_message % (member.mention)))
	except:
		print('There was an error somewhere in on_member_join')
		traceback.print_exc()

def same_message_response(channel_id):
	if len(recent_channel_messages[channel_id]) > 3:
		recent_channel_messages[channel_id].pop(0)
	if len(recent_channel_messages[channel_id]) < 3:
		return False
	s = recent_channel_messages[channel_id][0].content.lower()
	if s == recent_channel_messages[channel_id][1].content.lower() and s == recent_channel_messages[channel_id][2].content.lower():
		if s.author.id != recent_channel_messages[channel_id][1].author.id and s.author.id != recent_channel_messages[channel_id][2].author.id:
			return True
	return False

recording = None
last_trigger = datetime.now() - timedelta(minutes=10)
last_discord_simulation = datetime.now() - timedelta(hours=1)

client.run(login_token)
