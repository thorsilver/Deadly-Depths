import libtcodpy as libtcod
import math
import textwrap
import shelve
import random
import time
 
#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

#graphical mode switch - default colourful mode
SET_CONSOLE_MODE = False

#size of the map
MAP_WIDTH = 80
MAP_HEIGHT = 43

#tile assignments for custom font for TILES VERSION
wall_tile = 256
floor_tile = 257
player_tile = 728 #258
orc_tile = 259
troll_tile = 260
scroll_tile = 261
healingpotion_tile = 262
sword_tile = 263
shield_tile = 264
stairsdown_tile = 265
dagger_tile = 266
corpse_tile = 267

#special chars for certain objects
web_char = chr(176)

#dungeon generation parameters
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

#BSP dungeon parameters
DEPTH = 8
MIN_SIZE = 7
FULL_ROOMS = False

#item parameters
HEAL_AMOUNT = 40

#spell parameters
LIGHTNING_RANGE = 5
LIGHTNING_DAMAGE = 40
CONFUSE_NUM_TURNS = 10
CONFUSE_RANGE = 8
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 25

#experience and level-ups
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150
LEVEL_SCREEN_WIDTH = 40
CHARACTER_SCREEN_WIDTH = 30

#FOV algorithm constants
FOV_ALGO = 0 #default algorithm
FOV_LIGHT_WALLS = True #light walls in player's FOV
TORCH_RADIUS = 10

#sizes and coordinates for GUI
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
INVENTORY_WIDTH = 50

#message bar size and position
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

#tile colours
color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)
 
LIMIT_FPS = 120  #120 frames-per-second maximum

# class Diceroll:
	# #defining dice rolls for damage calculations
	# def __init__(self, sides, number):
		# self.sides = sides
		# self.number = number
	
def roll(sides, number):
		return sum(random.randint(1, sides) for times in range(number))
		
def damageRoll(dice):
		number, sides = dice.split('d', 1)
		number = int(number)
		sides = int(sides)
		return roll(sides, number)
		
def update_kills(name):
		if name in kill_count:
			kill_count[name] += 1
		else:
			kill_count[name] = 1
		

class Tile:
	#a tile of the map and its properties
	def __init__(self, blocked, block_sight = None):
		self.blocked = blocked

		#by default, tiles start unexplored
		#self.explored = True
		self.explored = False

		#by default, if a tile is blocked, it also blocks sight
		if block_sight is None: block_sight = blocked
		self.block_sight = block_sight

class Rect:
	#a rectangle on the map.  used to generate a room.
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h
	
	def center(self):
		center_x = (self.x1 + self.x2) / 2
		center_y = (self.y1 + self.y2) / 2
		return (center_x, center_y)

	def intersect(self, other):
		#returns true if this rectangle intersects with another one
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)
		
class Ticker:
	#this is the timer object
	#allows for scheduling of turns for monsters, effects, etc.
	def __init__(self):
		self.ticks = 0
		self.schedule = {}
		self.last_turn = 'monster'
		
	def schedule_turn(self, interval, obj_index):
		self.schedule.setdefault(self.ticks + interval, []).append(obj_index)
		
	def check_player_turn(self):
		things_to_do = self.schedule.pop(self.ticks, [])
		for obj in things_to_do:
			if obj == player:
				return 'player'
		
	def next_turn(self):
		global key, mouse
		things_to_do = self.schedule.pop(self.ticks, [])
		#print(self.ticks)
		#print(things_to_do)
		for obj in things_to_do:
			if objects[obj] == player:# and self.last_turn != 'player':
				#libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
				key = libtcod.console_wait_for_keypress(True)
				#if key.vk == libtcod.KEY_ENTER and key.lalt:
					#Alt+Enter: toggle fullscreen
				#	libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
				player_action = handle_keys()
				# # turn_over = False
				# # while turn_over == False:
				# while True:
					# #player_action = handle_keys()
					# if player_action == 'exit':
						# return 'exit'
					# if player_action == 'acted':
						# self.last_turn = 'player'
						# break
				#self.schedule_turn(player.fighter.speed, objects.index(player))
				if player_action == 'exit':
					return 'exit'
				self.schedule_turn(player.fighter.speed, objects.index(player))
				# print(player_action)
			if objects[obj] != player and objects[obj].ai and objects[obj].ai is not None:
				#print(obj.name + ' takes a turn!')
				objects[obj].ai.take_turn(clock)
				self.last_turn = 'monster'

class Object:
	#this is a generic object
	#it's always represented by an ASCII character
	def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None, arrows=None, wand=None, food=None):
		self.x = x
		self.y = y
		self.char = char
		self.name = name
		self.color = color
		#self.inventory = inventory
		self.blocks = blocks
		self.always_visible = always_visible
		self.fighter = fighter
		if self.fighter:
			self.fighter.owner = self
		self.ai = ai
		if self.ai:
			self.ai.owner = self
		self.item = item
		if self.item:
			self.item.owner = self
		self.equipment = equipment
		if self.equipment:
			self.equipment.owner = self
			self.item = Item()
			self.item.owner = self
		self.arrows = arrows
		if self.arrows:
			self.arrows.owner = self
			self.item = Item()
			self.item.owner = self
		self.wand = wand
		if self.wand:
			self.wand.owner = self
			self.item = Item()
			self.item.owner = self
		self.food = food
		if self.food:
			self.food.owner = self
			self.item = Item()
			self.item.owner = self
			
	def monster_mutator(self, mut_strength):
		last_mut = 0
		for mutation in range(mut_strength):
			mut_choice = damageRoll('1d6')
			if mut_choice == 6 and 'naga' in self.name:
				mut_choice -= 1
			if mut_choice == last_mut and mut_choice != 1:
				mut_choice -= 1
			elif mut_choice == last_mut and mut_choice == 1:
				mut_choice += 1
			if mut_choice == 6:
				self.fighter.base_ranged += 4
				self.fighter.xp += 35
				self.ai = PoisonSpitterAI()
				self.ai.owner = self
				self.color += libtcod.violet
				self.name = 'venomous ' + self.name
				last_mut = 6
			elif mut_choice == 5:
				self.fighter.max_hp += 20
				self.fighter.hp += 20
				self.fighter.xp += 30
				self.color += libtcod.gold
				self.name = 'golden ' + self.name
				last_mut = 5
			elif mut_choice == 4:
				self.fighter.max_hp += 10
				self.fighter.hp += 10
				self.fighter.defense += 2
				self.color += libtcod.dark_sepia
				self.name = 'cave ' + self.name
				last_mut = 4
			elif mut_choice == 3:
				self.fighter.base_power += 4
				self.fighter.base_ranged += 4
				self.fighter.xp += 25
				self.color += libtcod.orange
				self.name = 'hellfire ' + self.name
				last_mut = 3
			elif mut_choice == 2:
				self.fighter.base_defense += 4
				self.fighter.xp += 15
				self.color += libtcod.dark_grey
				self.name = 'armored ' + self.name
				last_mut = 2
			elif mut_choice == 1:
				self.fighter.power += 2
				self.fighter.defense += 2
				self.fighter.xp += 15
				self.color += libtcod.dark_yellow
				self.name = 'dire ' + self.name
				last_mut = 1
			else:
				print "Bad mutation!"

	def move(self, dx, dy):
		if not is_blocked(self.x + dx, self.y + dy):
			#move by the given amount if not blocked
			self.x += dx
			self.y += dy
			self.fighter.x = self.x
			self.fighter.y = self.y
			
	def wander(self):
		#move a random square
		self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))

	def move_towards(self, target_x, target_y):
		#vector from this object to the target, and distance
		dx = target_x - self.x
		dy = target_y - self.y
		distance = math.sqrt(dx ** 2 + dy ** 2)

		#normalise to length 1, preserving direction
		#then round and convert to integer so movement stays on grid
		dx = int(round(dx / distance))
		dy = int(round(dy / distance))
		self.move(dx, dy)
	
	def move_astar(self, target):
		#create an FOV map that has the dimensions of the map
		fov = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)

		#scan the current map each turn and set walls as unwalkable
		for y1 in range(MAP_HEIGHT):
			for x1 in range(MAP_WIDTH):
				libtcod.map_set_properties(fov, x1, y1, not map[x1][y1].block_sight, not map[x1][y1].blocked)

		#scan all objects to see if any must be navigated around
		#check also that the object isn't self or the target
		#the AI class handles things if self is next to target and won't use A* then
		for obj in objects:
			if obj.blocks and obj != self and obj!= target:
				#set the tile as a wall so it must be navigated around
				libtcod.map_set_properties(fov, obj.x, obj.y, True, False)

		#allocate an A* path
		#1.41 is the normal diagonal cost of moving
		my_path = libtcod.path_new_using_map(fov, 1.41)

		#compute the path between self's coordinates and the target's coordinates
		libtcod.path_compute(my_path, self.x, self.y, target.x, target.y)

		#check if the path exists and is less than 25 tiles
		#path size matters if you want monsters to sneak round the back from far away!
		#generally keep it low to prevent circuitous routes
		if not libtcod.path_is_empty(my_path) and libtcod.path_size(my_path) < 25:
			#find the next coordinates in the computed full path
			x, y = libtcod.path_walk(my_path, True)
			if x or y:
				#set coordinates to the next path tile
				self.x = x
				self.y = y
				self.fighter.x = self.x
				self.fighter.y = self.y
		else:
			#keep the old move function as a backup
			#if there arent any paths it will still try to advance toward player
			self.move_towards(target.x, target.y)
		#delete path to free memory
		libtcod.path_delete(my_path)
		
	def move_dijk(self, target):
		
		#create an FOV map that has the dimensions of the map
		fov = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)

		#scan the current map each turn and set walls as unwalkable
		for y1 in range(MAP_HEIGHT):
			for x1 in range(MAP_WIDTH):
				libtcod.map_set_properties(fov, x1, y1, not map[x1][y1].block_sight, not map[x1][y1].blocked)

		#scan all objects to see if any must be navigated around
		#check also that the object isn't self or the target
		#the AI class handles things if self is next to target and won't use A* then
		for obj in objects:
			if obj.blocks and obj != self and obj!= target:
				#set the tile as a wall so it must be navigated around
				libtcod.map_set_properties(fov, obj.x, obj.y, True, False)

		#allocate an A* path
		#1.41 is the normal diagonal cost of moving
		path_dijk = libtcod.dijkstra_new(fov)

		#compute the path between self's coordinates and the target's coordinates
		libtcod.dijkstra_compute(path_dijk, target.x, target.y)

		#check if the path exists, then walk down it and move the monster
		if not libtcod.dijkstra_is_empty(path_dijk):
			path_px, path_py = libtcod.dijkstra_path_walk(path_dijk)
			self.x = path_px
			self.y = path_py
			self.fighter.x = self.x
			self.fighter.x = self.y
			
		#if the path doesn't exist, go try move_astar instead
		else:
			#keep the old move function as a backup
			#if there arent any paths it will still try to advance toward player
			self.move_astar(target)

	def distance_to(self, other):
		#return the distance to another object
		dx = other.x - self.x
		dy = other.y - self.y
		return math.sqrt(dx ** 2 + dy ** 2)

	def distance(self, x, y):
		#return the distance to a specified tile
		return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
		
	def draw(self):
		#only draw if visible to player
		# if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or
			# (self.always_visible) and map[self.x][self.y].explored):
			# #set the color and then draw the character
			# libtcod.console_set_default_foreground(con, self.color)
			# libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)
		if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or
			(self.always_visible) and map[self.x][self.y].explored):
			#set the color and then draw the character
			libtcod.console_set_default_foreground(con, self.color)
			libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)
		elif (not self.always_visible and map[self.x][self.y].explored):
			libtcod.console_set_default_foreground(con, libtcod.grey)
			#libtcod.console_set_char_background(con, self.x, self.y, color_dark_ground, libtcod.BKGND_NONE)
			libtcod.console_put_char_ex(con, self.x, self.y, '.', libtcod.darker_grey, libtcod.black)
		else:
			libtcod.console_set_default_foreground(con, libtcod.black)
			
	#TILES VERSION
	def draw_tiles(self): #unexplored tiles with objects appear black, explored but out of fov shows floor tile
		#only draw if visible to player
		if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or
			(self.always_visible) and map[self.x][self.y].explored):
			#set the color and then draw the character
			libtcod.console_set_default_foreground(con, self.color)
			libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)
		elif (not self.always_visible and map[self.x][self.y].explored):
			libtcod.console_set_default_foreground(con, libtcod.grey)
			libtcod.console_put_char(con, self.x, self.y, floor_tile, libtcod.BKGND_NONE)
		else:
			libtcod.console_set_default_foreground(con, libtcod.black)
			
	def send_to_back(self):
		#make object get drawn first, so others appear above it on same tile
		global objects, items
		if self in objects:
			objects.remove(self)
			objects.insert(0, self)
		elif self in items:
			items.remove(self)
			items.insert(0, self)
	def clear(self):
		#erase the character that represents this object
		libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

class Fighter:
	#combat-related properties and methods (monsters, players, and NPCs)
	def __init__(self, x, y, speed, hp, defense, power, ranged, quiver, xp, damage_type, damage_dice, hunger=0, max_hunger=0, turn_count=0, poison_tick=0, inventory = [], resistances=[], 
		immunities=[], weaknesses=[], enraged=False, poisoned=False, death_function=None, role=None):
		self.x = x
		self.y = y
		self.speed = speed
		self.base_max_hp = hp
		self.hp = hp
		self.base_defense = defense
		self.base_power = power
		self.base_ranged = ranged
		self.quiver = quiver
		self.xp = xp
		self.hunger = hunger
		self.max_hunger = max_hunger
		self.damage_type = damage_type
		self.damage_dice = damage_dice
		self.turn_count = turn_count
		self.poison_tick = poison_tick
		self.inventory = inventory
		self.resistances = resistances
		self.immunities = immunities
		self.weaknesses = weaknesses
		self.enraged = enraged
		self.poisoned = poisoned
		self.death_function = death_function
		self.role=role
	
	@property
	def power(self):
		bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
		return self.base_power + bonus

	@property
	def defense(self):
		bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
		return self.base_defense + bonus

	@property
	def max_hp(self):
		bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
		return self.base_max_hp + bonus
		
	@property
	def ranged(self):
		bonus = sum(equipment.ranged_bonus for equipment in get_all_equipped(self.owner))
		return self.base_ranged + bonus

	def check_hunger(self):
		#deduct a point of hunger for every action
		self.hunger -= 1
		#check hunger, reduce power and defense if starving
		if self.hunger == 100:
			message(self.owner.name.title() + ' is getting hungry!', libtcod.red)
		elif self.hunger == 50:
			message(self.owner.name.title() + ' is weak from hunger!', libtcod.red)
			self.hp -= 1
		elif self.hunger < 50 and self.hunger % 2 == 0:
			self.hp -= 2
			message(self.owner.name.title() + ' is slowly starving!', libtcod.red)
		if self.hp <= 0:
			self.check_death()
		
	def take_damage(self, damage, type):
		#apply damage if possible
		
		if damage > 0 and type not in self.resistances and type not in self.immunities and type not in self.weaknesses:
			self.hp -= damage
			return damage
		#apply damage to resistant monsters
		elif damage > 0 and type in self.resistances and type not in self.immunities:
			reduced_damage = int(damage / 2) + 1
			self.hp -= reduced_damage
			return reduced_damage
		#apply double damage to weak monsters
		elif damage > 0 and type in self.weaknesses:
			enhanced_damage = damage * 2
			self.hp -= enhanced_damage
			return enhanced_damage
		#reject damage to immune monsters
		elif damage > 0 and type in self.immunities:
			return 'immune'
		
					
	def distance_to(self, other):
		#return the distance to another object
		dx = other.x - self.x
		dy = other.y - self.y
		return math.sqrt(dx ** 2 + dy ** 2)
		
	def direct_magic_attack(self, target, damage_dice, type):
		#for direct magic attacks (magic missile, fireball, lightning, etc.)
		#try to apply damage, check resistances, etc., and check for death
		damage = damageRoll(damage_dice)
		attack = target.take_damage(damage, type)
		
	def check_death(self):
		if self.hp <= 0:
			if self.owner != player:  #give experience
				player.fighter.xp += self.xp
				update_kills(self.owner.name)
			function = self.death_function
			if function is not None:
				function(self.owner)
	
	def attack(self, target, damage_type, damage_dice):
		#make a damage roll
		attacker = self.owner
		#print(attacker.x, attacker.y, attacker.name, attacker.char, attacker.fighter.hp, damage_dice)
		damage = damageRoll(damage_dice)
		attack = self.AttackRoll(target.fighter)
		
		if attack == 'hit':
			#make target take damage if possible
			result = target.fighter.take_damage(damage, damage_type)
			#report half damage for resistant targets
			if result < damage or result == 1:
				message(self.owner.name.title() + ' attacks ' + target.name.title() + ' for ' + str(result) + 
					' damage, but ' + target.name.title() + ' seems relatively unfazed.', libtcod.yellow)
			#report no damage for immune targets
			elif result == 'immune':
				message(self.owner.name.title() + ' attacks ' + target.name.title() + ' but ' + target.name.title() + ' shrugs it off completely!', libtcod.red)
			#report double damage for weak targets
			elif result > damage:
				message(self.owner.name.title() + ' attacks ' + target.name.title() + ' for ' + str(result) + ' damage, and ' + 
					target.name.title() + ' screams in pain!', libtcod.orange)
			else:
				#report normal damage otherwise
				message(self.owner.name.title() + ' attacks ' + target.name.title() + ' for ' + str(result) + ' damage.', libtcod.white)
			#check for death
			if target.fighter.hp <= 0:
				if target != player:  #give experience
					player.fighter.xp += target.fighter.xp
					update_kills(target.name)
				function = target.fighter.death_function
				if function is not None:
					function(target)	
		elif attack == 'crit':
			#make target take crit damage if possible
			critDamage = damage * 2
			result = target.fighter.take_damage(critDamage, damage_type)
			#report half damage for resistant targets
			if result < damage or result == 1:
				message(self.owner.name.title() + ' smashes ' + target.name.title() + ' for ' + str(result) + 
					' damage, but ' + target.name.title() + ' seems relatively unfazed.', libtcod.yellow)
			#report no damage for immune targets
			elif result == 'immune':
				message(self.owner.name.title() + ' smashes ' + target.name.title() + ' but ' + target.name.title() + ' shrugs it off completely!', libtcod.red)
			#report double damage for weak targets
			elif result > critDamage:
				message(self.owner.name.title() + ' brutally smashes ' + target.name.title() + ' for ' + str(result) + ' damage, and ' + 
					target.name.title() + ' screams in pain!', libtcod.orange)
			else:
				#report normal damage otherwise
				message(self.owner.name.title() + ' brutally attacks ' + target.name.title() + ' for ' + str(result) + ' damage.', libtcod.white)
			#check for death
			if target.fighter.hp <= 0:
				if target != player:  #give experience
					player.fighter.xp += target.fighter.xp
					update_kills(target.name)
				function = target.fighter.death_function
				if function is not None:
					function(target)			
		elif attack == 'miss':
			message(self.owner.name.title() + ' attacks ' + target.name.title() + ' but misses.', libtcod.white)
			
	def ranged_attack(self, target, damage_type, damage_dice):
		#simple formula for ranged damage -- to change later
		if self.quiver > 0: 
			roll = self.ranged_attack_roll(target.fighter)
			damage = damageRoll(damage_dice)
			if roll == 'hit':
				#make target take damage
				result = target.fighter.take_damage(damage, damage_type)
				if result < damage or result == 1:
					message(self.owner.name.title() + ' fires an arrow at ' + target.name.title() + ' for ' + str(result) + 
					' damage, but ' + target.name.title() + ' seems relatively unfazed.', libtcod.yellow)
				elif result == 'immune':
					message(self.owner.name.title() + ' attacks ' + target.name.title() + ' but ' + target.name.title() + ' shrugs it off completely!', libtcod.red)
				elif result > damage:
					message(self.owner.name.title() + ' fires an arrow at ' + target.name.title() + ' for ' + str(result) + ' damage, and ' + 
					+ target.name.title() + ' screams in pain!', libtcod.orange)
				else:
					message(self.owner.name.title() + ' fires an arrow at ' + target.name.title() + ' for ' + str(result) + ' damage.', libtcod.green)
				self.quiver -= 1
				#check for death
				if target.fighter.hp <= 0:
					if target != player:  #give experience
						player.fighter.xp += target.fighter.xp
						update_kills(target.name)
					function = target.fighter.death_function
					if function is not None:
						function(target)	
			elif roll == 'crit':
				#make target take crit damage if possible
				critDamage = damage * 2
				result = target.fighter.take_damage(critDamage, damage_type)
				#report half damage for resistant targets
				if result < damage or result == 1:
					message(self.owner.name.title() + ' punctures ' + target.name.title() + ' for ' + str(result) + 
						' damage, but ' + target.name.title() + ' seems relatively unfazed.', libtcod.yellow)
				#report no damage for immune targets
				elif result == 'immune':
					message(self.owner.name.title() + ' successfully punctures ' + target.name.title() + ' but ' + target.name.title() + ' shrugs it off completely!', libtcod.red)
				#report double damage for weak targets
				elif result > critDamage:
					message(self.owner.name.title() + ' brutally punctures ' + target.name.title() + ' for ' + str(result) + ' damage, and ' + 
						target.name.title() + ' screams in pain!', libtcod.orange)
				else:
					#report normal damage otherwise
					message(self.owner.name.title() + ' brutally punctures ' + target.name.title() + ' for ' + str(result) + ' damage.', libtcod.green)
				self.quiver -= 1
				#check for death
				if target.fighter.hp <= 0:
					if target != player:  #give experience
						player.fighter.xp += target.fighter.xp
						update_kills(target.name)
					function = target.fighter.death_function
					if function is not None:
						function(target)
			elif roll == 'miss':
				message(self.owner.name.title() + ' fires an arrow at ' + target.name.title() + ' but it misses!', libtcod.green)
				self.quiver -= 1
			#message('Orc quiver status: ' + str(self.quiver) + ' arrows!', libtcod.white)
		elif self.quiver <= 0:
			message(self.name.title() + ' ran out of arrows!', libtcod.green)
			return 'didnt-take-turn'
		elif get_equipped_in_slot('bow', player) is None and self.owner == player:
			message('You need a ranged weapon first!', libtcod.red)
			return 'didnt-take-turn'

	def heal(self, amount):
		#heal by a given amount, without going over max HP
		self.hp += amount
		if self.hp > self.max_hp:
			self.hp = self.max_hp
			
	def ranged_attack_roll(attacker, target):
		range = attacker.distance_to(target)
		if range >= 8:
			ranged_modifier = -4
		elif range >= 5 and range < 8:
			ranged_modifier = -2
		else:
			ranged_modifier = 0
		roll = damageRoll('1d20')
		attackRoll = roll + attacker.ranged - ranged_modifier
		defenseRoll = target.defense
		
		if roll == 20:
			return 'crit'
		elif attackRoll > defenseRoll:
			return 'hit'
		else:
			return 'miss'
	
	def AttackRoll(attacker, target):
		roll = damageRoll('1d20')
		attackRoll = roll + attacker.power
		defenseRoll = target.defense
		if roll == 20:
			return 'crit'
		elif attackRoll > defenseRoll:
			return 'hit'
		else:
			return 'miss'
			
def check_open_cell(x, y):
	#check for a random open cell neigbouring a target cell, return coordinates
	d = [(x - 1, y), (x, y + 1), (x + 1, y), (x, y - 1)]
	random.shuffle(d)
	for (xx, yy) in d:
		if map[xx][yy].blocked == True: continue
		elif map[xx][yy].blocked == False: return xx, yy
	return None		
	
class ClockGolem:
	#AI for ticker testing
	def take_turn(self, clock):
		monster = self.owner
		clock.schedule_turn(monster.fighter.speed, objects.index(monster))
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			#move toward player if far away
			if monster.distance_to(player) >= 2:
				monster.move_dijk(player)

			#attack if close enough, if player is still alive
			elif player.fighter.hp > 0 and 0 <= monster.distance_to(player) < 2:
				type = monster.fighter.damage_type
				dice = monster.fighter.damage_dice
				monster.fighter.attack(player, type, dice)
		

class BasicMonster:
	#AI for a basic monster
	def take_turn(self, clock):
		#basic monster takes its turn. If you can see it, it can see you
		monster = self.owner
		clock.schedule_turn(monster.fighter.speed, objects.index(monster))
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			#move toward player if far away
			if monster.distance_to(player) >= 2:
				monster.move_dijk(player)

			#attack if close enough, if player is still alive
			elif player.fighter.hp > 0:
				type = monster.fighter.damage_type
				dice = monster.fighter.damage_dice
				monster.fighter.attack(player, type, dice)
				
class SplitterAI:
	#AI for a monster that can split in two (slow-mover)
	def take_turn(self, clock):
		#monster takes turn, only active when within player's FOV
		monster = self.owner
		clock.schedule_turn(monster.fighter.speed, objects.index(monster))
		act_roll = damageRoll('1d6')
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y) and act_roll > 2:
			#move toward player
			if monster.distance_to(player) >= 2:
				monster.move_dijk(player)
			#attack if close enough, if player is still alive
			elif player.fighter.hp > 0:
				type = monster.fighter.damage_type
				dice = monster.fighter.damage_dice
				monster.fighter.attack(player, type, dice)
		elif libtcod.map_is_in_fov(fov_map, monster.x, monster.y) and act_roll <= 2 and monster.fighter.hp < 10:
			spotx, spoty = check_open_cell(monster.x, monster.y)
			spawn_monster(spotx, spoty, monster.name, 0, 0, clock)
			message('The ' + monster.name.title() + ' has split in two!', libtcod.red)
				
class BasicUndead:
	def take_turn(self, clock):
		#AI for a basic undead monster -- mindlessly advance, 1/4 of the time too stupid to act
		monster = self.owner
		clock.schedule_turn(monster.fighter.speed, objects.index(monster))
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y) and damageRoll('1d4') > 1:
			if monster.distance_to(player) >= 2:
				monster.move_dijk(player)
			elif player.fighter.hp > 0:
				type = monster.fighter.damage_type
				dice = monster.fighter.damage_dice
				monster.fighter.attack(player, type, dice)
			
class WolfAI:
	#AI for a wolf - they can attack from outside FOV, and howl for extra power when injured!
	def take_turn(self, clock):
		monster = self.owner
		clock.schedule_turn(monster.fighter.speed, objects.index(monster))
		type = monster.fighter.damage_type
		dice = monster.fighter.damage_dice
		if monster.distance_to(player) <= 20:
			if monster.distance_to(player) >= 2:
				monster.move_dijk(player)
			elif monster.fighter.hp <= 5 and monster.distance_to(player) <= 5 and monster.fighter.enraged == False:
				message('The ' + monster.name.title() + ' howls with rage!', libtcod.red)
				monster.fighter.enraged = True
				monster.fighter.power += 2
				monster.color = libtcod.red
				monster.fighter.attack(player, type, dice)
				packmate = closest_packmate(monster, 20)
				if packmate is not None:
					packmate.ai = AngryWolf
					packmate.ai.owner = packmate
					message('You hear an answering howl in the distance!', libtcod.red)
			else:
				monster.fighter.attack(player, type, dice)
				
class PoisonSpitterAI:
	#AI for poisonspitters -- they get to range and chuck poison goo, chance to hit based on Agility
	def take_turn(self, clock):
		monster = self.owner
		clock.schedule_turn(monster.fighter.speed, objects.index(monster))
		type = monster.fighter.damage_type
		dice = monster.fighter.damage_dice
		if monster.distance_to(player) <= 15 and monster.distance_to(player) > 5:
			monster.move_dijk(player)
			if libtcod.random_get_int(0, 1, 6) < 2:
				message('You hear a hissing sound in the distance....', libtcod.yellow)
		elif monster.distance_to(player) <= 5 and player.fighter.poisoned == False and libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
				message('The ' + monster.name.title() + ' spits poison at you!', libtcod.purple)
				if monster.fighter.ranged_attack_roll(player.fighter) == 'hit':
					message('The poison spit drips all over you!  You don\'t feel well...', libtcod.purple)
					player.fighter.poisoned = True
					player.fighter.poison_tick = player.fighter.turn_count
				else:
					message('You dodged the poison spit!', libtcod.purple)
				
		elif monster.distance_to(player) <= 5 and player.fighter.poisoned == True and monster.distance_to(player) >= 2:
			monster.move_dijk(player)
		elif monster.distance_to(player) <= 1:
			monster.fighter.attack(player, type, dice)
			
class ArcherAI:
	#AI for archers - they get to range and fire arrows
	def take_turn(self, clock):
		monster = self.owner
		clock.schedule_turn(monster.fighter.speed, objects.index(monster))
		type = monster.fighter.damage_type
		dice = monster.fighter.damage_dice
		range = monster.distance_to(player)
		if 7 < range <=15:
			monster.move_dijk(player)
		elif 2 <= range <= 7 and libtcod.map_is_in_fov(fov_map, monster.x, monster.y) and monster.fighter.quiver > 0:
			if libtcod.random_get_int(0, 1, 4) > 1:
				monster.fighter.ranged_attack(player, type, dice)
				if monster.fighter.quiver == 0:
					message('The ' + monster.name.title() + ' ran out of arrows!', libtcod.green)
			else:
				monster.move_astar(player)
		elif range <= 7 and not libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			monster.move_dijk(player)
		elif 2 <= range <= 7 and monster.fighter.quiver <= 0:
			monster.move_dijk(player)
		elif range < 2:
			monster.fighter.attack(player, type, dice)
			
class AngryWolf:
	#AI for wolf awoken by a packmate's howl -- they'll charge in from up to 25 tiles away!
	def take_turn(self, clock):
		monster = self.owner
		clock.schedule_turn(monster.fighter.speed, objects.index(monster))
		type = monster.fighter.damage_type
		dice = monster.fighter.damage_dice
		monster.fighter.enraged = True
		monster.fighter.power += 2
		monster.color = libtcod.red
		range = monster.distance_to(player)
		if range <=20 and range >= 2:
			move_dijk(player)
		if range < 2:
			monster.fighter.attack(player, type, dice)
			
	

				

class ConfusedMonster:
	#AI for a temporarily confused monster (reverts back after a few turns)
	def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
		self.old_ai = old_ai
		self.num_turns = num_turns

	def take_turn(self, clock):
		clock.schedule_turn(self.owner.fighter.speed, self.owner)
		if self.num_turns > 0: #still confused?
			#move in a random direction, decrease number of confused turns remaining
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
			self.num_turns -= 1
		else: #restore previous AI
			self.owner.ai = self.old_ai
			message('The ' + self.owner.name.title() + ' is no longer confused!', libtcod.red)

class Item:
	#an item that can be picked up and used
	def __init__(self, use_function=None):
		self.use_function = use_function

	def pick_up(self):
		arrows = self.owner.arrows
		#add to player's inventory and remove from the map
		if len(player.fighter.inventory) >= 26 and not arrows:
			message('Your inventory is full, cannot pick up ' + self.owner.name.title() + '.', libtcod.red)
		elif not arrows:
			player.fighter.inventory.append(self.owner)
			items.remove(self.owner)
			message('You picked up a ' + self.owner.name.title() + '!', libtcod.green)
		#special case: if item is Equipment, automatically equip if slot is open
		# equipment = self.owner.equipment
		# if equipment and get_equipped_in_slot(equipment.slot, player) is None:
			# equipment.equip()

		#special case: if item is Arrows, automatically add to Quiver if <= 99
		if arrows and player.fighter.quiver < 99:
			player.fighter.quiver += arrows.number
			items.remove(self.owner)
			if player.fighter.quiver >= 99:
				player.fighter.quiver = 99
			message('You now have ' + str(player.fighter.quiver) + ' arrows in your quiver.', libtcod.yellow)
		elif arrows and player.fighter.quiver >= 99:
			message('You have too many arrows!  Go shoot some monsters!', libtcod.yellow)
			
				
	
	def use(self):
		#special case: if object is Equipment, use action is equip/dequip
		if self.owner.equipment:
			self.owner.equipment.toggle_equip()
			return
		
		#special case: if object is Wand, use action is wand_use_function
		if self.owner.wand:
			self.owner.wand.wand_use_function()
			return
			
		#special case: if object is Food, add Nutrition to user's Hunger
		if self.owner.food and player.fighter.hunger < 500:
			self.owner.food.eat(self.owner.food.nutrition)
			player.fighter.inventory.remove(self.owner)
			return
		elif self.owner.food and player.fighter.hunger == 500:
			message('You are already full!', libtcod.green)
			return 'cancelled'
		
		#just call the use_function if it is defined
		if self.use_function is None:
			message('The ' + self.owner.name.title() + ' cannot be used.')
		else:
			if self.use_function() != 'cancelled':
				player.fighter.inventory.remove(self.owner) #destroy after use, unless cancelled

	def drop(self):
		#special case: if Equipment, dequip before dropping
		if self.owner.equipment:
			self.owner.equipment.dequip()
		
		#add to the map and remove from the player's inventory
		items.append(self.owner)
		player.fighter.inventory.remove(self.owner)
		self.owner.x = player.x
		self.owner.y = player.y
		message('You dropped a ' + self.owner.name.title() + '.', libtcod.yellow)

class Equipment:
	#an object that can be equipped, yielding bonuses/special abilities
	def __init__(self, slot, damage_type=None, damage_dice=None, damage_mod=0, power_bonus=0, ranged_bonus=0, defense_bonus=0, max_hp_bonus=0, is_equipped=False):
		self.slot = slot
		self.damage_type = damage_type
		self.damage_dice = damage_dice
		self.damage_mod = damage_mod
		self.power_bonus = power_bonus
		self.ranged_bonus = ranged_bonus
		self.defense_bonus = defense_bonus
		self.max_hp_bonus = max_hp_bonus
		self.is_equipped = is_equipped
		
	def toggle_equip(self):
		if self.is_equipped:
			self.dequip()
		else:
			self.equip()

	def equip(self):
		#if slot is used, dequip whatever's there first
		old_equipment = get_equipped_in_slot(self.slot, player)
		if old_equipment is not None:
			#message('Slot already full!  Dequip the equipped gear first.', libtcod.red)
			#return
			old_equipment.dequip()
		#else:
		#equip object and alert the player
		self.is_equipped = True
		message('Equipped ' + self.owner.name.title() + ' on ' + self.slot + '.', libtcod.light_green)

	def dequip(self):
		self.is_equipped = False
		message('Dequipped ' + self.owner.name.title() + ' from ' + self.slot + '.', libtcod.light_yellow)
		
class Arrows:
	#arrow items that can be picked up and added to player's Quiver for later firing
	def __init__(self, type, number):
		self.type = type
		self.number = number
		
class Food:
	#food items that can be eaten to replenish hunger
	def __init__(self, type, nutrition):
		self.type = type
		self.nutrition = nutrition
		
	def eat(self, amount):
		player.fighter.hunger += amount
		if player.fighter.hunger > player.fighter.max_hunger:
			player.fighter.hunger = player.fighter.max_hunger
		message('You feel more satisfied.', libtcod.light_green)
		
class Wand:
	#wand items that contain multi-use spells with limited charges. can be recharged with potions or scrolls.
	#wands can have up to three different functions:
	#Zap: every wand has this.  Use a single charge for a single instance of the wand's effect.  Ex: magic missile.
	#Emplace: some wands have this.  Install the wand in a location, deplete all charges to create an area effect until removed. Ex: magic missile turret!
	#Burn: some wands have this.  Deplete all charges at once to create a much larger effect, but with chaotic effects.
	#Ex: burn magic missile wand with 5 charges, get 2d6 magic missiles striking random enemies with a damage bonus.
	def __init__(self, charges=0, max_charges=0, zap_function=None, emplace_function=None, burn_function=None):
		self.charges = charges
		self.max_charges = max_charges
		self.zap_function = zap_function
		self.emplace_function = emplace_function
		self.burn_function = burn_function
	
	#generic wand usage function, called when (z)apping or using from Inventory
	def wand_use_function(self):
		if self.charges > 0:
			zap = self.zap_function()
			if zap != 'didnt-take-turn' and zap != 'cancelled':
				self.charges -= 1
				message('Charges remaining on ' + self.owner.name.title() + ': ' + str(self.charges), libtcod.light_blue)
				player.fighter.turn_count += 1
				pass
				initialize_fov()
				render_all()
				for object in objects:
					object.clear()
			elif zap == 'didnt-take-turn' or zap == 'cancelled':
				return 'didnt-take-turn'
		else:
			message('The wand is drained of all magical energy.', libtcod.light_blue)
			return 'didnt-take-turn'
		
def cast_magic_missile():
	#magic missile: zaps nearest target in FOV, always hits!
	message('Choose a target for the spell.', libtcod.light_blue)
	monster = target_monster()
	if monster is None: 
		message('No valid target found!', libtcod.red)
		return 'didnt-take-turn'
	else:
		#magic missile
		missile_damage = damageRoll('2d6') #+ player.fighter.sorcery - monster.fighter.magic_res
		attack = monster.fighter.take_damage(missile_damage, 'magic')
		if attack != 'immune':
			message('A spear of brilliant blue light strikes ' + monster.name.title() + ' for ' + str(missile_damage) + ' damage!', libtcod.light_blue)
			monster.fighter.check_death()
		else:
			message(monster.name.title() + ' is unaffected by the spell!', libtcod.red)
			
		
	

def get_equipped_in_slot(slot, creature): #returns equipment in slot, None if empty
	#print slot
	#flerp = get_all_equipped(player)
	#for gear in flerp:
	#	print(gear.owner.name, gear.slot, gear.is_equipped)
	# for gear in flerp:
		# print(gear.owner.name, gear.slot, slot)
		# if gear.slot == slot and gear.is_equipped:
			# return gear
		# else:
			# return None
	for item in creature.fighter.inventory:
		if item.equipment:
			#print(item.name, item.equipment.damage_dice, item.equipment.slot)
			if item.equipment.slot == slot and item.equipment.is_equipped:
				return item.equipment
	return None

def get_all_equipped(obj): #gets a list of equipped items
	if obj == player:
		equipped_list = []
		for item in player.fighter.inventory:
			if item.equipment and item.equipment.is_equipped:
				equipped_list.append(item.equipment)
		return equipped_list
	else:
		return [] #other objects have no slots (at the moment)
		
def get_weapon_damage(): #retrieve weapon damage from equipped weapon
	weapon = get_equipped_in_slot('right hand', player)
	if weapon is not None:
		return weapon.damage_dice
	else:
		return '1d4' #default unarmed damage
	
def get_damage_type(): #retrieve weapon damage type from equipped weapon
	weapon = get_equipped_in_slot('right hand', player)
	if weapon is not None:
		return weapon.damage_type
	else:
		return 'phys'
		
def get_bow_damage(): #retrieve damage dice value from bow slot
	bow = get_equipped_in_slot('bow', player)
	if bow is not None and bow.is_equipped:
		return bow.damage_dice
	else:
		return None
		
def get_bow_type(): #retrieve damage type of equipped missile weapon
	bow = get_equipped_in_slot('bow', player)
	if bow is not None and bow.is_equipped:
		return bow.damage_type
	else:
		return 'pierce'
	
def is_blocked(x, y):
	#test the map tile first
	if map[x][y].blocked:
		return True

	#now check for blocking objects
	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True

	return False
	
#############################
# MAP GEN FROM TUTORIAL
#############################

def create_room(room):
	global map
	#go through the tiles in a rectangle and make them passable
	for x in range(room.x1 + 1, room.x2):
		for y in range(room.y1 + 1, room.y2):
			map[x][y].blocked = False
			map[x][y].block_sight = False

def create_h_tunnel(x1, x2, y):
	global map
	#horizontal tunnel. min and max used for when x1>x2
	for x in range(min(x1, x2), max(x1, x2) + 1):
		map[x][y].blocked = False
		map[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
	global map
	#vertical tunnel
	for y in range(min(y1, y2), max(y1, y2) + 1):
		map[x][y].blocked = False
		map[x][y].block_sight = False

def make_map():
	global map, objects, stairs

	#list of objects with just the player
	#objects.append(player)
	
	#fill map with unblocked tiles
	map = [[ Tile(True)
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]

	rooms = []
	num_rooms = 0
	
	for r in range(MAX_ROOMS):
		#random width and height
		w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		#random position without going out of bounds
		x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
		y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

		new_room = Rect(x, y, w, h)

		#run through rooms and see if they intersect
		failed = False
		for other_room in rooms:
			if new_room.intersect(other_room):
				failed = True
				break
	
		if not failed:
			# no intersections so go ahead with room creation
			#paint it to map
			create_room(new_room)

			#center coordinates of new room
			(new_x, new_y) = new_room.center()

			if num_rooms == 0:
				#the first room will have the player in it
				player.x = new_x
				player.y = new_y
			else:
				#for all other rooms: connect to previous with a tunnel
				#center coordinates of previous room
				(prev_x, prev_y) = rooms[num_rooms-1].center()

				#flip a coin
				if libtcod.random_get_int(0, 0, 1) == 1:
					#first move horizontally, then vertically
					create_h_tunnel(prev_x, new_x, prev_y)
					create_v_tunnel(prev_y, new_y, new_x)
				else:
					#first move vertically, then horizontally
					create_v_tunnel(prev_y, new_y, prev_x)
					create_h_tunnel(prev_x, new_x, new_y)
			
			#add some objects to the room
			place_objects(new_room)

			#append new room to the room list
			rooms.append(new_room)
			num_rooms += 1
	#create stairs in the center of the last room
	stairs = Object(new_x, new_y, '>', 'stairs', libtcod.white, always_visible=True)
	objects.append(stairs)
	#stairs.send_to_back()

				
###############################
# BSP EXPERIMENTATION
###############################

def make_bsp():
	global player, map, objects, stairs, bsp_rooms
	#objects = [player]
	map = [[Tile(True) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]
	#empty global list for storing room coordinates
	bsp_rooms = []
	
	#new root node
	bsp = libtcod.bsp_new_with_size(0, 0, MAP_WIDTH, MAP_HEIGHT)
	
	#split into nodes
	libtcod.bsp_split_recursive(bsp, 0, DEPTH, MIN_SIZE + 1, MIN_SIZE + 1, 1.5, 1.5)
	
	#traverse the nodes and create rooms
	libtcod.bsp_traverse_inverted_level_order(bsp, traverse_node)
	
	#random room for the stairs
	stairs_location = random.choice(bsp_rooms)
	bsp_rooms.remove(stairs_location)
	stairs = Object(stairs_location[0], stairs_location[1], '>', 'stairs', libtcod.white, always_visible=True)
	objects.append(stairs)
	#stairs.send_to_back()
	
	#random room for player start
	player_room = random.choice(bsp_rooms)
	bsp_rooms.remove(player_room)
	player.x = player_room[0]
	player.y = player_room[1]
	
	#add monsters and items
	for room in bsp_rooms:
		new_room = Rect(room[0], room[1], 2, 2)
		place_objects(new_room)
		
	initialize_fov()
	
def traverse_node(node, dat):
	global map, bsp_rooms
	
	#create rooms
	if libtcod.bsp_is_leaf(node):
		minx = node.x + 1
		maxx = node.x + node.w - 1
		miny = node.y + 1
		maxy = node.y + node.h -1
		
		if maxx == MAP_WIDTH - 1:
			maxx -= 1
		if maxy == MAP_HEIGHT - 1:
			maxy -= 1
		
		#if False the room sizes are random, otherwise rooms filled to node size
		if FULL_ROOMS == False:
			minx = libtcod.random_get_int(None, minx, maxx - MIN_SIZE + 1)
			miny = libtcod.random_get_int(None, miny, maxy - MIN_SIZE + 1)
			maxx = libtcod.random_get_int(None, minx + MIN_SIZE - 2, maxx)
			maxy = libtcod.random_get_int(None, miny + MIN_SIZE -2, maxy)
			
		node.x = minx
		node.y = miny
		node.w = maxx - minx + 1
		node.h = maxy - miny + 1
		
		#dig room
		for x in range(minx, maxx + 1):
			for y in range(miny, maxy + 1):
				map[x][y].blocked = False
				map[x][y].block_sight = False
		#add center coordinates to list of rooms
		bsp_rooms.append(((minx + maxx) / 2, (miny + maxy) / 2))
		
	#create corridors
	else:
		left = libtcod.bsp_left(node)
		right = libtcod.bsp_right(node)
		node.x = min(left.x, right.x)
		node.y = min(left.y, right.y)
		node.w = max(left.x + left.w, right.x + right.w) - node.x
		node.h = max(left.y + left.h, right.y + right.h) -  node.y
		if node.horizontal:
			if left.x + left.w - 1 < right.x or right.x + right.w - 1 < left.x:
				x1 = libtcod.random_get_int(None, left.x, left.x + left.w - 1)
				x2 = libtcod.random_get_int(None, right.x, right.x + right.w - 1)
				y = libtcod.random_get_int(None, left.y + left.h, right.y)
				vline_up(map, x1, y - 1)
				hline(map, x1, y, x2)
				vline_down(map, x2, y + 1)
			else:
				minx = max(left.x, right.x)
				maxx = min(left.x + left.w - 1, right.x + right.w - 1)
				x = libtcod.random_get_int(None, minx, maxx)
				vline_down(map, x, right.y)
				vline_up(map, x, right.y - 1)
		else:
			if left.y + left.h - 1 < right.y or right.y + right.h - 1 < left.y:
				y1 = libtcod.random_get_int(None, left.y, left.y + left.h - 1)
				y2 = libtcod.random_get_int(None, right.y, right.y + right.h - 1)
				x = libtcod.random_get_int(None, left.x + left.w, right.x)
				hline_left(map, x - 1, y1)
				vline(map, x, y1, y2)
				hline_right(map, x + 1, y2)
			else:
				miny = max(left.y, right.y)
				maxy = min(left.y + left.h - 1, right.y + right.h - 1)
				y = libtcod.random_get_int(None, miny, maxy)
				hline_left(map, right.x - 1, y)
				hline_right(map, right.x, y)
	return True

def vline(map, x, y1, y2):
	if y1 > y2:
		y1,y2 = y2, y1
	for y in range(y1, y2+1):
		map[x][y].blocked = False
		map[x][y].block_sight = False

def vline_up(map, x, y):
	while y >= 0 and map[x][y].blocked == True:
		map[x][y].blocked = False
		map[x][y].block_sight = False
		y -= 1
		
def vline_down(map, x, y):
	while y < MAP_HEIGHT and map[x][y].blocked == True:
		map[x][y].blocked = False
		map[x][y].block_sight = False
		y += 1
		
def hline(map, x1, y, x2):
	if x1 > x2:
		x1,x2 = x2,x1
	for x in range(x1,x2+1):
		map[x][y].blocked = False
		map[x][y].block_sight = False
		
def hline_left(map, x, y):
	while x >= 0 and map[x][y].blocked == True:
		map[x][y].blocked = False
		map[x][y].block_sight = False
		x -= 1
		
def hline_right(map, x, y):
	while x < MAP_WIDTH and map[x][y].blocked == True:
		map[x][y].blocked = False
		map[x][y].block_sight = False
		x += 1
				
###############################
#END BSP STUFF
###############################

def spawn_monster(x, y, choice, mutation_roll, mutation_num, clock):
	#global clock
	if choice == 'clock golem':
		#create a clock golem to test ticker
		fighter_component = Fighter(x, y, speed=8, hp=10, defense=11,power=5, ranged=0, quiver=0, xp=20, damage_type='phys', damage_dice='1d4', death_function=monster_death)
		ai_component = ClockGolem()
		monster = Object(x, y, 'c', 'clock golem', libtcod.gold, blocks=True, fighter=fighter_component, ai=ai_component)
	if choice == 'zombie':
		#create a basic zombie
		fighter_component = Fighter(x, y, speed=15, hp=10, defense=11, power=5, ranged=0, quiver=0, xp=20, damage_type='phys', damage_dice='1d4', 
			immunities=['poison', 'death', 'mind'], weaknesses=['fire'], death_function=monster_death)
		ai_component = BasicUndead()
		monster = Object(x, y, 'z', 'zombie', libtcod.dark_purple, blocks=True, fighter=fighter_component, ai=ai_component)
	if choice == 'skel_warrior':
		#create a basic skeleton
		fighter_component = Fighter(x, y, speed=13, hp=15, defense=13, power=7, ranged=0, quiver=0, xp=45, damage_type='phys', damage_dice='1d6', 
			immunities=['poison', 'death', 'mind', 'pierce'], weaknesses=['blunt'], death_function=monster_death)
		ai_component = BasicUndead()
		monster = Object(x, y, 'z', 'skeleton warrior', libtcod.white, blocks=True, fighter=fighter_component, ai=ai_component)
	if choice == 'gelatinous mass':
		#create a nasty gloopy things
		fighter_component = Fighter(x, y, speed=20, hp=15, defense=11, power=3, ranged=0, quiver=0, xp=15, damage_type='water', damage_dice='1d4', 
			immunities=['water', 'mind'], weaknesses=['fire', 'thunder'], death_function=monster_death)
		ai_component = SplitterAI()
		monster = Object(x, y, 'j', 'gelatinous mass', libtcod.light_blue, blocks=True, fighter=fighter_component, ai=ai_component)
	if choice == 'flaming ooze':
		#create a flaming goopile
		fighter_component = Fighter(x, y, speed=20, hp=20, defense=15, power=5, ranged=0, quiver=0, xp=35, damage_type='fire', damage_dice='1d8', 
			immunities=['fire', 'mind'], weaknesses=['water', 'ice'], death_function=monster_death)
		ai_component = SplitterAI()
		monster = Object(x, y, 'j', 'flaming ooze', libtcod.light_red, blocks=True, fighter=fighter_component, ai=ai_component)
	if choice == 'sparking goop':
		#create a thunderous goo
		fighter_component = Fighter(x, y, speed=20, hp=25, defense=17, power=7, ranged=0, quiver=0, xp=50, damage_type='thunder', damage_dice='1d10', 
			immunities=['thunder', 'mind'], weaknesses=['fire', 'ice'], death_function=monster_death)
		ai_component = SplitterAI()
		monster = Object(x, y, 'j', 'sparking goop', libtcod.yellow, blocks=True, fighter=fighter_component, ai=ai_component)
	if choice == 'toxic slime':
		#create a gross sentient poison blob
		fighter_component = Fighter(x, y, speed=20, hp=30, defense=19, power=9, ranged=0, quiver=0, xp=75, damage_type='poison', damage_dice='1d12', 
			immunities=['poison', 'mind'], weaknesses=['fire', 'thunder'], death_function=monster_death)
		ai_component = SplitterAI()
		monster = Object(x, y, 'j', 'toxic slime', libtcod.violet, blocks=True, fighter=fighter_component, ai=ai_component)
	if choice == 'orc':
		#create an orc
		fighter_component = Fighter(x, y, speed=10, hp=10, defense=11, power=4, ranged=0, quiver=0, xp=35, damage_type='phys', damage_dice='1d4', 
			weaknesses=['mind', 'death'], death_function=monster_death)
		ai_component = BasicMonster()
		monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green, blocks=True, fighter=fighter_component, ai=ai_component)
		if mutation_roll > 6:
			monster.monster_mutator(mutation_num)
	elif choice == 'orc archer':
		#create an orc archer
		fighter_component = Fighter(x, y, speed=11, hp=8, defense=9, power=1, ranged=4, quiver=15, xp=50, damage_type='pierce', damage_dice='1d4', 
			weaknesses=['mind', 'death'], death_function=archer_death)
		ai_component = ArcherAI()
		monster = Object(x, y, 'o', 'orc archer', libtcod.light_green, blocks=True, fighter=fighter_component, ai=ai_component)
	elif choice == 'elite orc archer':
		#create an elite orc archer
		fighter_component = Fighter(x, y, speed=9, hp=18, defense=12, power=2, ranged=6, quiver=15, xp=80, damage_type='pierce', damage_dice='2d6', 
			weaknesses=['mind', 'death'], death_function=archer_death)
		ai_component = ArcherAI()
		monster = Object(x, y, 'o', 'elite orc archer', libtcod.light_red, blocks=True, fighter=fighter_component, ai=ai_component)
	elif choice == 'devil archer':
		#create a devil archer
		fighter_component = Fighter(x, y, speed=7, hp=30, defense=16, power=4, ranged=9, quiver=15, xp=130, damage_type='fire', damage_dice='2d10', 
			resistances=['thunder'], immunities=['fire'], weaknesses=['water', 'ice'], death_function=archer_death)
		ai_component = ArcherAI()
		monster = Object(x, y, 'd', 'devil archer', libtcod.orange, blocks=True, fighter=fighter_component, ai=ai_component)
	elif choice == 'orc captain':
		#create an orc captain
		fighter_component = Fighter(x, y, speed=12, hp=20, defense=14, power=6, ranged=0, quiver=0, xp=75, damage_type='phys', damage_dice='2d4', 
			weaknesses=['mind', 'death'], death_function=monster_death)
		ai_component = BasicMonster()
		monster = Object(x, y, 'O', 'orc captain', libtcod.dark_red, blocks=True, fighter=fighter_component, ai=ai_component)
		if mutation_roll > 6:
			monster.monster_mutator(mutation_num)
	elif choice == 'troll':
		#create a troll
		fighter_component = Fighter(x, y, speed=14, hp=30, defense=15, power=8, ranged=0, quiver=0, xp=100, damage_type='phys', damage_dice='2d6', 
			resistances=['phys'], weaknesses=['fire'], death_function=monster_death)
		ai_component = BasicMonster()
		monster = Object(x, y, 'T', 'troll', libtcod.darker_green, blocks=True, fighter=fighter_component, ai=ai_component)
		if mutation_roll > 6:
			monster.monster_mutator(mutation_num)
	elif choice == 'wolf':
		#create a wolf
		fighter_component = Fighter(x, y, speed=7, hp=8, defense=9, power=2, ranged=0, quiver=0, xp=10, damage_type='phys', damage_dice='1d4', 
			resistances=['ice'], weaknesses=['fire', 'poison'], death_function=monster_death)
		ai_component = WolfAI()
		monster = Object(x, y, 'w', 'wolf', libtcod.grey, blocks=True, fighter=fighter_component, ai=ai_component)
		if not is_blocked(x+1,y):
			fighter_component = Fighter(x, y, speed=7, hp=8, defense=9, power=2, ranged=0, quiver=0, xp=10, damage_type='phys', damage_dice='1d4', 
				resistances=['ice'], weaknesses=['fire', 'poison'], death_function=monster_death)
			ai_component = WolfAI()
			monster = Object(x+1, y, 'w', 'wolf', libtcod.grey, blocks=True, fighter=fighter_component, ai=ai_component)
	
	elif choice == 'rattlesnake':
		fighter_component = Fighter(x, y, speed=9, hp=8, defense=7, power=3, ranged=3, xp=15, quiver=0, damage_type='poison', damage_dice='1d6', death_function=monster_death)
		ai_component = PoisonSpitterAI()
		monster = Object(x, y, 'S', 'rattlesnake', libtcod.light_sepia, blocks=True, fighter=fighter_component, ai=ai_component)
	elif choice == 'naga hatchling':
		fighter_component = Fighter(x, y, speed=11, hp=16, defense=14, power=5, ranged=5, xp=40, quiver=0, damage_type='poison', damage_dice='2d4', death_function=monster_death)
		ai_component = PoisonSpitterAI()
		monster = Object(x, y, 'n', 'naga hatchling', libtcod.light_green, blocks=True, fighter=fighter_component, ai=ai_component)
		if mutation_roll > 6:
			monster.monster_mutator(mutation_num)
	elif choice == 'naga':
		fighter_component = Fighter(x, y, speed=12, hp=35, defense=16, power=7, ranged=6, xp=75, quiver=0, damage_type='poison', damage_dice='2d6', death_function=monster_death)
		ai_component = PoisonSpitterAI()
		monster = Object(x, y, 'N', 'naga', libtcod.light_green, blocks=True, fighter=fighter_component, ai=ai_component)
		if mutation_roll > 6:
			monster.monster_mutator(mutation_num)
	objects.append(monster)
	clock.schedule_turn(monster.fighter.speed + 1, objects.index(monster))	
	#print('Monster spawned!')
	#print(monster.name, monster.x, monster.y, monster.fighter.hp)
	
def place_item(x, y, choice):
	if choice == 'heal':
		#create a healing potion
		item_component = Item(use_function=cast_heal)
		item = Object(x, y, '!', 'healing potion', libtcod.pink, item=item_component)
	elif choice == 'tester sword':
		#create a tester sword
		equipment_component = Equipment(slot='right hand', damage_type='phys', damage_dice='3d12', power_bonus=7)
		item = Object(x, y, '-', 'tester sword', libtcod.gold, equipment=equipment_component)
	elif choice == 'ration pack':
		#create a ration pack
		food_component = Food('normal', 300)
		item = Object(x, y, '%', 'ration pack', libtcod.sepia, food=food_component)
	elif choice == 'recharge':
		#create a recharge potion
		item_component = Item(use_function=cast_recharge)
		item = Object(x, y, '!', 'recharge potion', libtcod.light_blue, item=item_component)
	elif choice == 'lightning':
		#create a lightning bolt scroll
		item_component = Item(use_function=cast_lightning)
		item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item=item_component)
	elif choice == 'fireball':
		#create a fireball scroll
		item_component = Item(use_function=cast_fireball)
		item = Object(x, y, '#', 'scroll of fireball', libtcod.light_yellow, item=item_component)
	elif choice == 'confuse':
		#create a confuse scroll
		item_component = Item(use_function=cast_confuse)
		item = Object(x, y, '#', 'scroll of confusion', libtcod.light_yellow, item=item_component)
	elif choice == 'warp':
		#create a warp scroll
		item_component = Item (use_function=cast_warp)
		item = Object(x, y, '#', 'scroll of teleportation', libtcod.light_yellow, item=item_component)
	elif choice == 'petrify':
		#create a petrify scroll
		item_component = Item(use_function=cast_petrify)
		item = Object(x, y, '#', 'scroll of petrification', libtcod.light_yellow, item=item_component)
	elif choice == 'antidote':
		#create an antidote:
		item_component = Item(use_function=cast_antidote)
		item = Object(x, y, '!', 'antidote', libtcod.purple, item=item_component)
	elif choice == 'orcbow':
		#create an Orcish shortbow
		equipment_component = Equipment(slot='bow', damage_type='pierce', damage_dice='1d6', power_bonus=0, ranged_bonus=2)
		item = Object(x, y, '{', 'Orcish shortbow', libtcod.brass, equipment=equipment_component)
	elif choice == 'longsword':
		#create a longsword
		equipment_component = Equipment(slot='right hand', damage_type='phys', damage_dice='2d4', power_bonus=3)
		item = Object(x, y, '-', 'longsword', libtcod.sky, equipment=equipment_component)
	elif choice == 'shield':
		#create a shield
		equipment_component = Equipment(slot='left hand', defense_bonus=2)
		item = Object(x, y, '[', 'shield', libtcod.darker_orange, equipment=equipment_component)
	elif choice == 'lance':
		#create a lance
		equipment_component = Equipment(slot='right hand', damage_type='pierce', damage_dice='2d6', power_bonus=3)
		item = Object(x, y, '-', 'lance', libtcod.sky, equipment=equipment_component)
	elif choice == 'battleaxe':
		#create a battleaxe
		equipment_component = Equipment(slot='right hand', damage_type='phys', damage_dice='1d10', power_bonus=3)
		item = Object(x, y, '-', 'battleaxe', libtcod.sky, equipment=equipment_component)
	elif choice == 'morningstar':
		#create a morningstar
		equipment_component = Equipment(slot='right hand', damage_type='blunt', damage_dice='1d8', power_bonus=3)
		item = Object(x, y, '-', 'morningstar', libtcod.sky, equipment=equipment_component)
	elif choice == 'Elvish longbow':
		#create a longbow
		equipment_component = Equipment(slot='bow', damage_type='pierce', damage_dice='2d6', ranged_bonus=3)
		item = Object(x, y, '{', 'Elvish longbow', libtcod.sky, equipment=equipment_component)
	elif choice == 'rapier':
		#create a lance
		equipment_component = Equipment(slot='right hand', damage_type='pierce', damage_dice='2d4', power_bonus=3)
		item = Object(x, y, '-', 'rapier', libtcod.sky, equipment=equipment_component)
	elif choice == 'h_rapier':
		#create an ornate rapier
		equipment_component = Equipment(slot='right hand', damage_type='pierce', damage_dice='2d8', power_bonus=5)
		item = Object(x, y, '-', 'ornate rapier', libtcod.yellow, equipment=equipment_component)
	elif choice == 'h_sword':
		#create bastard sword
		equipment_component = Equipment(slot='right hand', damage_type='phys', damage_dice='2d8', power_bonus=5)
		item = Object(x, y, '-', 'bastard sword', libtcod.yellow, equipment=equipment_component)
	elif choice == 'h_lance':
		#create a heavy lance
		equipment_component = Equipment(slot='right hand', damage_type='pierce', damage_dice='2d10', power_bonus=5)
		item = Object(x, y, '-', 'heavy lance', libtcod.yellow, equipment=equipment_component)
	elif choice == 'h_battleaxe':
		#create a greataxe
		equipment_component = Equipment(slot='right hand', damage_type='phys', damage_dice='2d10', power_bonus=5)
		item = Object(x, y, '-', 'greataxe', libtcod.yellow, equipment=equipment_component)
	elif choice == 'h_morningstar':
		#create a heavy morningstar
		equipment_component = Equipment(slot='right hand', damage_type='blunt', damage_dice='2d8', power_bonus=5)
		item = Object(x, y, '-', 'heavy morningstar', libtcod.yellow, equipment=equipment_component)
	elif choice == 'h_warhammer':
		#create a heavy warhammer
		equipment_component = Equipment(slot='right hand', damage_type='blunt', damage_dice='2d10', power_bonus=5)
		item = Object(x, y, '-', 'heavy warhammer', libtcod.yellow, equipment=equipment_component)
	elif choice == 'h_shortbow':
		#create a gleamwood shortbow
		equipment_component = Equipment(slot='bow', damage_type='pierce', damage_dice='2d10', ranged_bonus=5)
		item = Object(x, y, '{', 'gleamwood shortbow', libtcod.yellow, equipment=equipment_component)
	elif choice == 'demonic firebow':
		#create a demonic firebow
		equipment_component = Equipment(slot='bow', damage_type='fire', damage_dice='2d10', ranged_bonus=5)
		item = Object(x, y, '{', 'demonic firebow', libtcod.red, equipment=equipment_component)
	elif choice == 'w_mmissile':
		#WAND TEST: wand of magic missile
		wand_component = Wand(charges=10, max_charges=20, zap_function=cast_magic_missile)
		item = Object(x, y, '/', 'wand of magic missile', libtcod.orange, wand=wand_component)
	elif choice == 'w_lightning':
		#WAND TEST 2: wand of lightning
		wand_component = Wand(charges=5, max_charges=10, zap_function=cast_lightning)
		item = Object(x, y, '/', 'wand of lightning', libtcod.yellow, wand=wand_component)
	elif choice == 'w_confusion':
		#WAND TEST 3: wand of confusion
		wand_component = Wand(charges=7, max_charges=15, zap_function=cast_confuse)
		item = Object(x, y, '/', 'wand of confusion', libtcod.sky, wand=wand_component)
	elif choice == 'w_fireball':
		#WAND TEST 7: wand of fireball
		wand_component = Wand(charges=5, max_charges=10, zap_function=cast_fireball)
		item = Object(x, y, '/', 'wand of fireball', libtcod.red, wand=wand_component)
	elif choice == 'w_death':
		#WAND TEST 9: wand of death
		wand_component = Wand(charges=3, max_charges=10, zap_function=cast_death)
		item = Object(x, y, '/', 'wand of death', libtcod.light_grey, wand=wand_component)
	elif choice == 'w_warp':
		#WAND TEST 10: wand of teleportation
		wand_component = Wand(charges=10, max_charges=20, zap_function=cast_warp)
		item = Object(x, y, '/', 'wand of teleportation', libtcod.violet, wand=wand_component)
	elif choice == 'w_petrify':
		#WAND TEST 11: wand of petrification
		wand_component = Wand(charges=5, max_charges=10, zap_function=cast_petrify)
		item = Object(x, y, '/', 'wand of petrification', libtcod.sepia, wand=wand_component)
	elif choice == 'w_swap':
		#WAND TEST 12: wand of transposition
		wand_component = Wand(charges=10, max_charges=20, zap_function=cast_swap)
		item = Object(x, y, '/', 'wand of transposition', libtcod.light_green, wand=wand_component)
	elif choice == 'w2_mmissile':
		#WAND TEST4: fine wand of magic missile
		wand_component = Wand(charges=20, max_charges=20, zap_function=cast_magic_missile)
		item = Object(x, y, '/', 'wand of magic missile', libtcod.light_orange, wand=wand_component)
	elif choice == 'w2_lightning':
		#WAND TEST 5: fine wand of lightning
		wand_component = Wand(charges=10, max_charges=10, zap_function=cast_lightning)
		item = Object(x, y, '/', 'wand of lightning', libtcod.light_yellow, wand=wand_component)
	elif choice == 'w2_confusion':
		#WAND TEST 6: fine wand of confusion
		wand_component = Wand(charges=15, max_charges=15, zap_function=cast_confuse)
		item = Object(x, y, '/', 'wand of confusion', libtcod.light_sky, wand=wand_component)
	elif choice == 'w2_fireball':
		#WAND TEST 8: fine wand of fireball
		wand_component = Wand(charges=10, max_charges=10, zap_function=cast_fireball)
		item = Object(x, y, '/', 'wand of fireball', libtcod.light_red, wand=wand_component)
	elif choice == 'w2_death':
		#WAND TEST 9: ornate wand of death
		wand_component = Wand(charges=7, max_charges=10, zap_function=cast_death)
		item = Object(x, y, '/', 'ornate wand of death', libtcod.lighter_grey, wand=wand_component)
	elif choice == 'w2_warp':
		#WAND TEST 10: fine wand of teleportation
		wand_component = Wand(charges=20, max_charges=20, zap_function=cast_warp)
		item = Object(x, y, '/', 'wand of teleportation', libtcod.violet, wand=wand_component)
	elif choice == 'w2_petrify':
		#WAND TEST 12: wand of petrification
		wand_component = Wand(charges=10, max_charges=10, zap_function=cast_petrify)
		item = Object(x, y, '/', 'wand of petrification', libtcod.light_sepia, wand=wand_component)
	elif choice == 'w2_swap':
		#WAND TEST 12: wand of transposition
		wand_component = Wand(charges=20, max_charges=20, zap_function=cast_swap)
		item = Object(x, y, '/', 'wand of transposition', libtcod.light_green, wand=wand_component)
	items.append(item)
	#item.send_to_back() #items appear behind other objects
	item.always_visible=True #items always visible once explored

def place_objects(room):
	global clock
	
	#first we decide the chance of each monster or item showing up
	
	#max monsters per room
	max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])

	#chances for each monster
	monster_chances = {}
	#monster_chances['clock golem'] = 0 #testing testing 1 2 3
	monster_chances['orc'] = 60 #orc always shows up
	monster_chances['orc archer'] = 35 #orc archers always show up, for now
	monster_chances['wolf'] = 60 #wolf always shows up
	monster_chances['rattlesnake'] = 20 #snake always shows up, for now
	monster_chances['zombie'] = 20
	monster_chances['skel_warrior'] = 40
	monster_chances['gelatinous mass'] = 20
	monster_chances['elite orc archer'] = from_dungeon_level([[15, 6], [20, 8]])
	monster_chances['devil archer'] = from_dungeon_level([[15, 11], [20, 13]])
	monster_chances['orc captain'] = from_dungeon_level([[15, 5], [20, 7]])
	monster_chances['flaming ooze'] = from_dungeon_level([[15, 6], [20, 8]])
	monster_chances['sparking goop'] = from_dungeon_level([[15, 10], [20, 12]])
	monster_chances['toxic slime'] = from_dungeon_level([[15, 13], [20, 15]])
	monster_chances['troll'] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])
	monster_chances['naga hatchling'] = from_dungeon_level([[20, 8], [25, 10]])
	monster_chances['naga'] = from_dungeon_level([[10, 10], [15, 12]])

	#max items per room
	max_items = from_dungeon_level([[1, 1], [2, 4]])
	
	#chances for each item
	item_chances = {}
	item_chances['heal'] = 35 #healing pots always show up
	item_chances['ration pack'] = 20
	item_chances['antidote'] = 25 #antidotes always show up
	item_chances['tester sword'] = from_dungeon_level([[50, 5]]) #megadeath sword for testing
	item_chances['lightning'] = from_dungeon_level([[25, 4]])
	item_chances['fireball'] = from_dungeon_level([[25, 6]])
	item_chances['confuse'] = from_dungeon_level([[10, 2]])
	item_chances['orcbow'] = from_dungeon_level([[5, 3]])
	item_chances['longsword'] = from_dungeon_level([[5, 4]])
	item_chances['shield'] = from_dungeon_level([[15, 6]])
	item_chances['lance'] = from_dungeon_level([[15, 6]])
	item_chances['battleaxe'] = from_dungeon_level([[15, 6]])
	item_chances['morningstar'] = from_dungeon_level([[15, 6]])
	item_chances['Elvish longbow'] = from_dungeon_level([[15, 6]])
	item_chances['rapier'] = from_dungeon_level([[15, 6]])
	item_chances['h_rapier'] = from_dungeon_level([[15, 11]])
	item_chances['h_lance'] = from_dungeon_level([[15, 11]])
	item_chances['h_battleaxe'] = from_dungeon_level([[15, 11]])
	item_chances['h_morningstar'] = from_dungeon_level([[15, 11]])
	item_chances['h_shortbow'] = from_dungeon_level([[15, 11]])
	item_chances['h_warhammer'] = from_dungeon_level([[15, 11]])
	item_chances['h_sword'] = from_dungeon_level([[15, 11]])
	item_chances['recharge'] = from_dungeon_level([[10, 3]])
	item_chances['w_mmissile'] = from_dungeon_level([[10, 4]])
	item_chances['w_confusion'] = from_dungeon_level([[10, 3]])
	item_chances['w_fireball'] = from_dungeon_level([[5, 6]])
	item_chances['w_lightning'] = from_dungeon_level([[5, 5]])
	item_chances['w_death'] = from_dungeon_level([[3, 8]])
	item_chances['w_warp'] = from_dungeon_level([[10, 3]])
	item_chances['w_petrify'] = from_dungeon_level([[10, 5]])
	item_chances['w_swap'] = from_dungeon_level([[10, 3]])
	item_chances['w2_mmissile'] = from_dungeon_level([[10, 10]])
	item_chances['w2_confusion'] = from_dungeon_level([[10, 10]])
	item_chances['w2_fireball'] = from_dungeon_level([[5, 12]])
	item_chances['w2_lightning'] = from_dungeon_level([[5, 11]])
	item_chances['w2_death'] = from_dungeon_level([[3, 13]])
	item_chances['w2_warp'] = from_dungeon_level([[10, 8]])
	item_chances['w2_petrify'] = from_dungeon_level([[10, 10]])
	item_chances['w2_swap'] = from_dungeon_level([[10, 7]])
	

	#choose a random number of monsters
	num_monsters = libtcod.random_get_int(0, 0, max_monsters)

	for i in range(num_monsters):
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		
		#only place if tile is not blocked
		if not is_blocked(x, y):
			choice = random_choice(monster_chances)
			mutation_roll = libtcod.random_get_int(0, 1, 6) + dungeon_level
			mutation_num = 0
			if mutation_roll > 6:
				mutation_num = mutation_roll - 6
				if mutation_num > 2:
					mutation_num = 2
			spawn_monster(x, y, choice, mutation_roll, mutation_num, clock)

	#choose random number of items
	num_items = libtcod.random_get_int(0, 0, max_items)

	for i in range(num_items):
		#choose random spot for this item
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

		#only place it if tile is not blocked
		if not is_blocked(x, y):
			choice = random_choice(item_chances)
			place_item(x, y, choice)

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
	#render a bar (HP, experience, etc.) first calculate width
	bar_width = int(float(value) / maximum * total_width)

	#render the background first
	libtcod.console_set_default_background(panel, back_color)
	libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

	#now render the bar on top
	libtcod.console_set_default_background(panel, bar_color)
	if bar_width > 0:
		libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

	#finally, some centered text with the values
	libtcod.console_set_default_foreground(panel, libtcod.white)
	libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
		name + ': ' + str(value) + '/' + str(maximum))

def message(new_msg, color = libtcod.white):
	#split the message if necessary on multiple lines
	new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

	for line in new_msg_lines:
		#if buffer is full, remove first line to make way for the next
		if len(game_msgs) == MSG_HEIGHT:
			del game_msgs[0]

		#add the new line as a tuple, with the text and the color
		game_msgs.append( (line, color) )

def render_all():
	global dungeon_level_name, items, objects
	global color_dark_wall, color_light_wall
	global color_dark_ground, color_light_ground
	global fov_recompute
	
	#set names and colour schemes according to dungeon level
	if dungeon_level <= 2:
		dungeon_level_name = 'Dread Fortress'
		dark_wall = libtcod.darker_grey
		light_wall = libtcod.light_grey
	elif 3 <= dungeon_level < 5:
		dungeon_level_name = 'Deep Catacombs'
		dark_wall = libtcod.darker_sepia 
		light_wall = libtcod.sepia
	elif 5 <= dungeon_level < 7:
		dungeon_level_name = 'Slimy Caverns'
		dark_wall = libtcod.desaturated_blue
		light_wall = libtcod.light_blue
	elif 7 <= dungeon_level < 9:
		dungeon_level_name = 'Sickly Depths'
		dark_wall = libtcod.desaturated_han
		light_wall = libtcod.light_han
	elif 9 <= dungeon_level < 11:
		dungeon_level_name = 'Putrid Palace' 
		dark_wall = libtcod.desaturated_yellow
		light_wall = libtcod.yellow
	elif 11 <= dungeon_level < 13:
		dungeon_level_name = 'Fiery Hellscape'
		dark_wall = libtcod.darker_flame
		light_wall = libtcod.flame
	elif 13 <= dungeon_level < 15:
		dungeon_level_name = 'Twisted Abyss'
		idx_al = [0, 4, 8]
		col_al = [libtcod.red, libtcod.orange, libtcod.crimson]
		abyss_map_light = libtcod.color_gen_map(col_al, idx_al)
	
		idx_ad = [0, 4, 8]
		col_ad = [libtcod.desaturated_red, libtcod.desaturated_orange, libtcod.desaturated_crimson]
		abyss_map_dark = libtcod.color_gen_map(col_ad, idx_ad)
	elif dungeon_level == 15:
		dungeon_level_name = 'Swirling Chaos'
		idx_cl = [0, 4, 8]
		col_cl = [libtcod.han, libtcod.violet, libtcod.purple]
		chaos_map_light = libtcod.color_gen_map(col_cl, idx_cl)
	
		idx_cd = [0, 4, 8]
		col_cd = [libtcod.desaturated_han, libtcod.desaturated_violet, libtcod.desaturated_purple]
		chaos_map_dark = libtcod.color_gen_map(col_cd, idx_cd)

		
	

	if fov_recompute:
		#recompute FOV if needed
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
		
		#go through all tiles, set color according to FOV
		for y in range(MAP_HEIGHT):
			for x in range(MAP_WIDTH):
				visible = libtcod.map_is_in_fov(fov_map, x, y)
				wall = map[x][y].block_sight
				if not visible:
					#if it's not visible, players can only see already-explored tiles
					if map[x][y].explored:
						if wall:
							if 13 <= dungeon_level < 15:
								dark_wall = abyss_map_dark[libtcod.random_get_int(0, 0, 8)]
							if dungeon_level == 15:
								dark_wall = chaos_map_dark[libtcod.random_get_int(0, 0, 8)]
							libtcod.console_put_char_ex(con, x, y, '#', libtcod.black, libtcod.BKGND_SET)
							#libtcod.console_put_char_ex(con, x, y, '#', libtcod.darker_han, libtcod.black)
							#libtcod.console_put_char_ex(con, x, y, '#', libtcod.flame, libtcod.black)
							#libtcod.console_set_char_background(con, x, y, libtcod.color_dark_wall, libtcod.BKGND_SET)
							libtcod.console_set_char_background(con, x, y, dark_wall, libtcod.BKGND_SET)
						else:
							libtcod.console_put_char_ex(con, x, y, '.', libtcod.darker_grey, libtcod.black)
							#libtcod.console_put_char_ex(con, x, y, ' ', libtcod.black, libtcod.black)
							#libtcod.console_put_char_ex(con, x, y, '.', libtcod.flame, libtcod.black)
							#libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
				else:
					if wall:
						if 13 <= dungeon_level < 15:
							light_wall = abyss_map_light[libtcod.random_get_int(0, 0, 8)]
						if dungeon_level == 15:
							light_wall = chaos_map_light[libtcod.random_get_int(0, 0, 8)]
						#libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
						libtcod.console_put_char_ex(con, x, y, '#', libtcod.black, libtcod.BKGND_SET)
						#libtcod.console_put_char_ex(con, x, y, '#', libtcod.light_flame, libtcod.black)
						libtcod.console_set_char_background(con, x, y, light_wall, libtcod.BKGND_SET)
					else:
						#libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
						#libtcod.console_put_char_ex(con, x, y, '.', libtcod.light_flame, libtcod.black)
						libtcod.console_put_char_ex(con, x, y, '.', libtcod.lighter_grey, libtcod.black)
					#since it's visible, call it explored!
					map[x][y].explored = True
					
		#TILES VERSION
		# if fov_recompute:
		# #recompute FOV if needed
		# fov_recompute = False
		# libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
		
		# #go through all tiles, set color according to FOV
		# for y in range(MAP_HEIGHT):
			# for x in range(MAP_WIDTH):
				# visible = libtcod.map_is_in_fov(fov_map, x, y)
				# wall = map[x][y].block_sight
				# if not visible:
					# #if it's not visible, players can only see already-explored tiles
					# if map[x][y].explored:
						# if wall:
							# libtcod.console_put_char_ex(con, x, y, wall_tile, libtcod.darker_red, libtcod.black)
						# else:
							# libtcod.console_put_char_ex(con, x, y, floor_tile, libtcod.grey, libtcod.black)
				# else:
					# if wall:
						# libtcod.console_put_char_ex(con, x, y, wall_tile, libtcod.red, libtcod.black)
					# else:
						# libtcod.console_put_char_ex(con, x, y, floor_tile, libtcod.white, libtcod.black)
					# #since it's visible, call it explored!
					# map[x][y].explored = True
	
	#draw corpses and stairs first
	for object in objects:
		if object.name == 'stairs' or 'remains' in object.name:
			object.draw()
	#before objects, draw all items in the items list
	for item in items:
		item.draw()
	#draw all objects in the list except player!
	for object in objects:
		if object!= player and object.name != 'stairs' and 'remains' not in object.name:
			object.draw()
	#draw player last
	player.draw()

	#blit the contents of con to the root console
	libtcod.console_blit(con, 0, 0, MAP_WIDTH, MAP_HEIGHT, 0, 0, 0)

	#prepare to render GUI panel
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)

	#print game messages, one line at a time
	y = 1
	for (line, color) in game_msgs:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1

	#show the player's stats
	level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
	render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
		libtcod.light_red, libtcod.darker_red)
	render_bar(1, 2, BAR_WIDTH, 'Satiety', player.fighter.hunger, player.fighter.max_hunger, libtcod.dark_green, libtcod.darker_green)
	render_bar(1, 3, BAR_WIDTH, 'XP', player.fighter.xp, level_up_xp,
		libtcod.blue, libtcod.darker_blue)
	
	libtcod.console_print_ex(panel, 1, 4, libtcod.BKGND_NONE, libtcod.LEFT, 'Level ' + str(player.level) + ' ' + player.fighter.role)
	libtcod.console_print_ex(panel, 1, 5, libtcod.BKGND_NONE, libtcod.LEFT, dungeon_level_name + ' (' + str(dungeon_level) + ')')
	libtcod.console_print_ex(panel, 1, 6, libtcod.BKGND_NONE, libtcod.LEFT, 'Turns: ' + str(player.fighter.turn_count))
	#if player.fighter.poisoned == True:
	#	libtcod.console_print_ex(panel, 1, 6, libtcod.BKGND_NONE, libtcod.LEFT, '!!POISONED!!')

	#display names of objects under the mouse
	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())

	#blit the contents of the panel to the root console
	libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def player_move_or_attack(dx, dy):
	global fov_recompute

	#the coordinates the player is now going to
	x = player.x + dx
	y = player.y + dy

	#try to find an attackable object
	target = None
	for object in objects:
		if object.fighter and object.x == x and object.y == y:
			target = object
			break

	#attack if target found, otherwise move
	type = get_damage_type()
	damage_dice = get_weapon_damage()
	if target is not None:
		player.fighter.attack(target, type, damage_dice)
	else:
		player.move(dx, dy)
		fov_recompute = True
	
	#if poisoned, take damage
	if player.fighter.poisoned == True:
		if libtcod.random_get_int(0, 1, 6) < 3:
			poison_damage = libtcod.random_get_int(0, 1, player.level + 1)
			player.fighter.take_damage(poison_damage, 'poison')
			message('You took ' + str(poison_damage) + ' damage from poison!', libtcod.purple)
	#kill player if hp <= 0
	if player.fighter.hp <= 0:
		player.fighter.death_function
			
	#if poisoned for 10 turns, shake it off
	if player.fighter.poisoned and player.fighter.turn_count - player.fighter.poison_tick >= 15:
		player.fighter.poisoned = False
		message('You recovered from the poison\'s effects!', libtcod.yellow)
		
	player.fighter.turn_count += 1
	player.fighter.check_hunger()

def menu(header, options, width):
	if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
	#calculate total height for header after auto-wrap and one line per option
	header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
	if header == '':
		header_height = 0
	height = len(options) + header_height

	#create an off-screen console that represents menu's window
	window = libtcod.console_new(width, height)

	#print the header, with auto-wrap
	libtcod.console_set_default_foreground(window, libtcod.white)
	libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

	#print all the options
	y = header_height
	letter_index = ord('a')
	for option_text in options:
		text = '(' + chr(letter_index) + ') ' + option_text
		libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
		y += 1
		letter_index += 1

	#blit the contexts of window to the root console
	x = SCREEN_WIDTH/2 - width/2
	y = SCREEN_HEIGHT/2 - height/2
	libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

	time.sleep(0.3)
	#present the root console to the player and wait for a key-press
	libtcod.console_flush()
	key = libtcod.console_wait_for_keypress(True)

	#allow full-screening in menu
	if key.vk == libtcod.KEY_ENTER and key.lalt: #alt-Enter for fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

	#convert the ASCII code to an index; if it corresponds to an object return it
	index = key.c - ord('a')
	if index >= 0 and index < len(options): return index
	return None

def inventory_menu(header):
	#show a menu with each player.fighter.inventory item as an option
	if len(player.fighter.inventory) == 0:
		options = ['Inventory is empty.']
	else:
		options = []
		for item in player.fighter.inventory:
			text = item.name
			#show additional info, in case it's equipped
			if item.equipment and item.equipment.is_equipped and item.equipment.damage_dice is not None:
					text = text + ' (on ' + item.equipment.slot + ')' + '(' + item.equipment.damage_dice + ')'
			elif item.equipment and item.equipment.damage_dice is not None:
				text = text + '(' + item.equipment.damage_dice + ')'
			options.append(text)

	index = menu(header, options, INVENTORY_WIDTH)

	#if an item was chosen, return it
	if index is None or len(player.fighter.inventory) == 0: return None
	return player.fighter.inventory[index].item

def wand_menu():	
	#make a wand menu, let player use one if available
	wand_list = []
	menu_options = []
	for item in player.fighter.inventory:
		if item.wand is not None:
			wand_list.append(item)
	if len(wand_list) == 0:
		message('No wands in inventory.', libtcod.red)
		return 'didnt-take-turn'
	else:
		for wand in wand_list:
			text = wand.name + ' (' + str(wand.wand.charges) + ')'
			menu_options.append(text)
	index = menu('Choose a wand to zap:', menu_options, INVENTORY_WIDTH)
	if index is None: return 'didnt-take-turn'
	#check = wand_list[index].item.use()
	if wand_list[index].wand.wand_use_function() == 'didnt-take-turn':
		return 'didnt-take-turn'

def msgbox(text, width=50):
	menu(text, [], width) #use menu() for a message box
 
 
def handle_keys():
	global mouse, keys
 
    #key = libtcod.console_check_for_keypress()  #real-time
	key = libtcod.console_wait_for_keypress(True)  #turn-based

	if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
 
	elif key.vk == libtcod.KEY_ESCAPE:
		return 'exit'  #exit game
 
	if game_state == 'playing':
		key_char = chr(key.c)
		#movement keys
		if key.vk == libtcod.KEY_UP:
			player_move_or_attack(0, -1)
			return 'acted'
	 
		elif key.vk == libtcod.KEY_DOWN:
			player_move_or_attack(0, 1)
			return 'acted'
	 
		elif key.vk == libtcod.KEY_LEFT:
			player_move_or_attack(-1, 0)
			return 'acted'
	 
		elif key.vk == libtcod.KEY_RIGHT:
			player_move_or_attack(1, 0)
			return 'acted'
			
		elif key_char == 'z':
			if wand_menu() == 'didnt-take-turn':
				return 'didnt-take-turn'
			
			
		elif key_char == 'f':
			#fire an arrow if arrows are available
			if player.fighter.quiver > 0 and get_equipped_in_slot('bow', player) is not None:
				check = fire_arrow()
				if check == 'didnt-take-turn':
					return 'didnt-take-turn'
				else:
					return 'acted'
			elif player.fighter.quiver > 0 and get_equipped_in_slot('bow', player) is None:
				message('You do not have a ranged weapon!', libtcod.red)
				return 'didnt-take-turn'
			elif player.fighter.quiver <= 0:
				message('You do not have any arrows!', libtcod.red)
				return 'didnt-take-turn'
		
		elif key.vk == libtcod.KEY_TAB:
			pass #do nothing and let monsters approach
		
		else:
			#test for other keys
			key_char = chr(key.c)

			if key_char == 'g':
				#pick up an item
				for loot in items: #check for object in player's tile
					if loot.x == player.x and loot.y == player.y and loot.item:
						loot.item.pick_up()
						break
			if key_char == 'i':
				#show the inventory; if an item is selected, use it
				chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
				if chosen_item is not None:
					chosen_item.use()
			if key_char == 'd':
				#show the inventory, if an item is selected, drop it
				chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
				if chosen_item is not None:
					chosen_item.drop()
			if key_char == '>':
				#go down stairs if player is on them
				if stairs.x == player.x and stairs.y == player.y:
					next_level()
			if key_char == 'c':
				#show character info
				level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
				msgbox('Character Information\n\nLevel ' + str(player.level) + ' ' + player.fighter.role +  
					'\nExperience: ' + str(player.fighter.xp) + '\nExperience to Level Up: ' + 
					str(level_up_xp) + '\n\nMaximum HP: ' + str(player.fighter.max_hp) + 
					'\nAttack: ' + str(player.fighter.power) + '\nRanged Attack: ' + str(player.fighter.ranged) + '\nDefense: ' + str(player.fighter.defense) + 
					'\nSpeed: ' + str(player.fighter.speed) + '\nQuiver: ' + str(player.fighter.quiver), CHARACTER_SCREEN_WIDTH)
			# if key_char == 'v':
				# #debug -- testing get_equipped_in_slot
				# #derp = get_equipped_in_slot('right hand', player)
				# #print(derp.owner.name, derp.slot, derp.damage_dice)
				# derp = get_all_equipped(player)
				# slots = [obj.slot for obj in derp]
				# slots = ', '.join(slots)
				# names = [obj.owner.name for obj in derp]
				# names = ', '.join(names)
				# print names
				# print slots
			if key_char == 'm':
				#debug -- make all objects visible
				for object in objects:
					object.always_visible = True
				for y in range(MAP_HEIGHT):
					for x in range(MAP_WIDTH):
						map[x][y].explored = True
			if key_char == 'l':
				#look at a clicked object to get details (add descriptions later)
				look_at_object()
				initialize_fov()
				render_all()
				
					
			return 'didnt-take-turn'
			
def look_at_object():
	message('Click on the object you want to examine, or ESC/right-click to cancel.', libtcod.sky)
	obj = target_object()
	if obj is not None and obj.fighter:
		if len(obj.fighter.resistances) == 1:
			resists = obj.fighter.resistances[0]
		else:
			resists = ', '.join(obj.fighter.resistances)
		if len(obj.fighter.weaknesses) == 1:
			weak = obj.fighter.weaknesses[0]
		else:
			weak = ', '.join(obj.fighter.weaknesses)
		if len(obj.fighter.immunities) == 1:
			immune = obj.fighter.immunities[0]
		else:
			immune = ', '.join(obj.fighter.immunities)
		msgbox(obj.name.title() + '\n' + 'Hit Points: ' + str(obj.fighter.hp) + '\n' + 'Speed: ' + str(obj.fighter.speed) + '\n' + 'Damage: ' + obj.fighter.damage_dice + '\n' + 
			'Damage Type: ' + obj.fighter.damage_type + '\n' + 'Resistances: ' + resists + '\n' + 'Weaknesses: ' + weak + '\n' + 'Immunities: ' + immune + '\n')
	elif obj is None:
		message('No object selected!', libtcod.red)
	else:
		msgbox(obj.name.title())
	
	

def get_names_under_mouse():
	global mouse
	
	#return a string with the names of all objects under the mouse
	(x, y) = (mouse.cx, mouse.cy)
	#create a list with the names of all objects at the mouse's coordinates and in FOV
	names = [obj.name for obj in objects
				if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
	names = ', '.join(names) #join the names, comma-separated
	return names.title()

def check_level_up():
	#check if the player's experience is enough to level up
	level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
	if player.fighter.xp >= level_up_xp:
		#ding! time to level up
		player.level += 1
		player.fighter.xp -= level_up_xp
		message('Your battle skills grow stronger!  You reached Level ' + str(player.level) + '!', libtcod.yellow)

		choice = None
		while choice == None: #keep asking until a choice is made
			choice = menu('Level up!  Choose a stat to raise:\n',
				['Constitution (+20 HP, from ' + str(player.fighter.max_hp) + ')',
				'Strength (+1 Attack, from ' + str(player.fighter.power) + ')',
				'Accuracy (+1 Ranged Attack, from ' + str(player.fighter.ranged) + ')',
				'Agility (+1 Defense, from ' + str(player.fighter.defense) + ')'], LEVEL_SCREEN_WIDTH)
		if choice == 0:
			player.fighter.base_max_hp += 20
			player.fighter.hp += 20
		elif choice == 1:
			player.fighter.base_power += 1
		elif choice == 2:
			player.fighter.base_ranged += 1
		elif choice == 3:
			player.fighter.base_defense += 1

def player_death(player):
	#game over!
	global game_state
	message('You died!  Your exploits have been recorded.  Press Esc to return to the menu.', libtcod.red)
	game_state = 'dead'
	character_dump()

	#transform the player into a corpse
	player.char = '%'
	player.color = libtcod.dark_red

def monster_death(monster):
	global clock
	#transform monster into a corpse! no more moves or attacks, can't be attacked
	message(monster.name.title() + ' is dead! You gained ' + str(monster.fighter.xp) + ' experience points.', libtcod.orange)
	#print(len(clock.schedule))
	for k,v in clock.schedule.items():
		if v == objects.index(monster):
			del clock.schedule[k]
	#clock.schedule = {k: v for k, v in clock.schedule.items() if v != monster.fighter}
	#print(len(clock.schedule))
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.blocks = False
	monster.fighter = None
	monster.ai = None
	monster.name = 'remains of ' + monster.name
	#monster.send_to_back()
	# corpse = Object(monster.x, monster.y, '%', monster.name, libtcod.dark_red)
	# objects.append(corpse)
	# corpse.send_to_back()
	# objects.remove(monster)
	
	
def archer_death(monster):
	global objects
	#drop arrows for player to pick up!
	if monster.fighter.quiver > 0:
		arrows_component = Arrows(type=1, number=monster.fighter.quiver)
		item = Object(monster.x, monster.y, '^', str(monster.fighter.quiver) + ' arrows', libtcod.sepia, arrows=arrows_component)
		items.append(item)
		#item.send_to_back()
	dropRoll = damageRoll('1d10')
	if dropRoll > 9 and monster.name == 'orc archer':
		place_item(monster.x, monster.y, 'orcbow')
	elif dropRoll > 9 and monster.name == 'elite orc archer':
		place_item(monster.x, monster.y, 'Elvish longbow')
	elif dropRoll > 9 and monster.name == 'devil archer':
		place_item(monster.x, monster.y, 'demonic firebow')
	monster_death(monster)
	
def closest_packmate(monster, max_range):
	#find closest packmate for wolf-type monsters
	closest_mate = None
	closest_dist = max_range + 1
	for object in objects:
		if object.fighter and not object == player and 'wolf' in object.name:
			dist = monster.distance_to(object)
			if dist < closest_dist:
				closest_mate = object
				closest_dist = dist
	return closest_packmate
	

def closest_monster(max_range):
	#find closest enemy, up to a maximum range and in FOV
	closest_enemy = None
	closest_dist = max_range + 1
	for object in objects:
		if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
			#calculate distance between object and player
			dist = player.distance_to(object)
			if dist < closest_dist:
				closest_enemy = object
				closest_dist = dist
	return closest_enemy

def target_tile(max_range=None):
	#return the position of a tile clicked in player's FOV (optionally in a range)
	global key, mouse
	while True:
		#render the screen, erasing the inventory and showing object names under the cursor
		libtcod.console_flush()
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
		render_all()
		(x, y) = (mouse.cx, mouse.cy)
		#cancel with right click or Esc
		if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
			message('Effect cancelled!', libtcod.red)
			return (None, None)
		#accept the target if the player clicked in FOV, or if in range
		if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
			(max_range is None or player.distance(x, y) <= max_range)):
			return (x, y)

def target_monster(max_range=None):
	#returns a clicked monster inside FOV up to a range, or None if right-clicked
	while True:
		(x, y) = target_tile(max_range)
		if x is None: #player cancelled
			return None
		#return the first clicked monster, otherwise keep looping
		for obj in objects:
			if obj.x == x and obj.y == y and obj.fighter and obj != player:
				return obj
				
def target_object(max_range=None):
	#returns a clicked object inside FOV up to a range, or None if right-clicked
	while True:
		(x, y) = target_tile(max_range)
		if x is None: #player cancelled
			return None
		#return the first clicked monster, otherwise keep looping
		for obj in objects:
			if obj.x == x and obj.y == y and obj != player:
				return obj
				
def target_monster_or_player(max_range=None):
	#returns a clicked monster inside FOV up to a range, or None if right-clicked
	while True:
		(x, y) = target_tile(max_range)
		if x is None: #player cancelled
			return None
		#return the first clicked monster, otherwise keep looping
		for obj in objects:
			if obj.x == x and obj.y == y and obj.fighter:
				return obj

def random_choice_index(chances): #choose an object from a list of chances returning the index
	dice = libtcod.random_get_int(0, 1, sum(chances))

	#sum all the chances
	running_sum = 0
	choice = 0
	for w in chances:
		running_sum += w
		if dice <= running_sum:
			return choice
		choice += 1

def random_choice(chances_dict):
	#choose one option from a dictionary of chances, returning its key
	chances = chances_dict.values()
	strings = chances_dict.keys()

	return strings[random_choice_index(chances)]

def from_dungeon_level(table):
	#returns a value that depends on dungeon level
	for (value, level) in reversed(table):
		if dungeon_level >= level:
			return value
	return 0

def cast_heal():
	#heal the player
	if player.fighter.hp == player.fighter.max_hp:
		message('You are already at full health.', libtcod.red)
		return 'cancelled'
	
	message('Your wounds start to feel better!', libtcod.pink)
	player.fighter.heal(HEAL_AMOUNT)
	
def cast_recharge():
	#recharge a selected wand
	wand_list = []
	menu_options = []
	for item in player.fighter.inventory:
		if item.wand is not None:
			wand_list.append(item)
	if len(wand_list) == 0:
		message('No wands in inventory.', libtcod.red)
		return 'cancelled'
	else:
		for wand in wand_list:
			text = wand.name + ' (' + str(wand.wand.charges) + ')'
			menu_options.append(text)
	#libtcod.console_flush()
	render_all()
	time.sleep(0.5)
	index = menu('Choose a wand to zap:', menu_options, INVENTORY_WIDTH)
	if index is None: return 'cancelled'
	wand_list[index].wand.charges += 5
	if wand_list[index].wand.charges > wand_list[index].wand.max_charges:
		wand_list[index].wand.charges = wand_list[index].wand.max_charges
	message(wand_list[index].name.title() + ' recharged.  Current charges: ' + str(wand_list[index].wand.charges), libtcod.light_blue)
	
	
	
def cast_antidote():
	#get rid of poison status
	if player.fighter.poisoned == False:
		message('You are not poisoned.', libtcod.red)
		return 'cancelled'
	message('You are no longer poisoned!', libtcod.light_violet)
	player.fighter.poisoned = False

def cast_lightning():
	#find closest enemy inside range and damage it
	monster = closest_monster(LIGHTNING_RANGE)
	if monster is None: 
		message('No enemy is close enough to strike!', libtcod.red)
		return 'cancelled'

	#bolt of lightning
	attack = monster.fighter.take_damage(LIGHTNING_DAMAGE, 'thunder')
	if attack != 'immune':
		message('A lightning bolt strikes the ' + monster.name.title() + ' for ' + str(LIGHTNING_DAMAGE) + ' damage!', libtcod.light_blue)
		monster.fighter.check_death()
	else:
		message(monster.name.title() + ' is immune to the spell!', libtcod.red)
	

def cast_confuse():
	#ask the player for a target to confuse
	message('Left click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
	monster = target_monster(CONFUSE_RANGE)
	if monster is None: return 'cancelled'
	#replace monster AI with confused AI
	if 'mind' not in monster.fighter.immunities:
		old_ai = monster.ai
		monster.ai = ConfusedMonster(old_ai)
		monster.ai.owner = monster
		message('The eyes of the ' + monster.name.title() + ' look vacant as it starts to stumble around!', libtcod.light_green)
	else:
		message('The ' + monster.name.title() + ' is a mindless abomination, unaffected by spells of that type.', libtcod.red)
		return 'cancelled'
	
def cast_death():
	#ask player for a target for the lethal spell!
	message('Left click an enemy to cast, or right-click/ESC to cancel.', libtcod.light_cyan)
	monster = target_monster()
	if monster is None: return 'cancelled'
	#kill monster, unless immune
	death_strike = monster.fighter.hp * 2
	attack = monster.fighter.take_damage(death_strike, 'death')
	if attack != 'immune':
		message(monster.name.title() + ' dies instantly, its soul banished from existence.', libtcod.grey)
		monster.fighter.check_death()
	else:
		message(monster.name.title() + ' somehow survives the deadly magic attack.', libtcod.red)
	
	
	
def cast_petrify():
	#global player 
	#ask player for a target to petrify
	message('Left click on an enemy to cast petrify, or right click/ESC to cancel.', libtcod.light_cyan)
	monster = target_monster()
	if monster is None: return 'cancelled'
	message(monster.name.title() + ' gets turned into solid stone.', libtcod.sepia)
	#transform monster into a statue! no more moves or attacks, can't be attacked
	message(monster.name.title() + ' is petrified! You gained ' + str(int(monster.fighter.xp / 2)) + ' experience points.', libtcod.orange)
	player.fighter.xp += int(monster.fighter.xp / 2)
	monster.color = libtcod.sepia
	fighter_component = Fighter(monster.x, monster.y, speed=0, hp=25, defense=0, power=0, ranged=0, quiver=0, xp=0, damage_type='phys', damage_dice='', death_function=statue_crumble)
	monster.fighter = fighter_component
	monster.fighter.owner = monster
	monster.ai = None
	monster.name = 'Statue of ' + monster.name.title()
	
def statue_crumble(self):
	#let a petrified enemy crumble into rocks
	self.char = '*'
	self.blocks = False
	self.fighter = None
	self.name = 'pile of rocks'
	
	
def cast_warp():
	#warp: target creature in FOV gets warped away to a random location
	message('Choose a target to be teleported:', libtcod.light_blue)
	monster = target_monster_or_player()
	if monster is None:
		message('No valid target found!', libtcod.red)
		return 'didnt-take-turn'
	else:
		#do the teleport
		warpx = libtcod.random_get_int(0, 1, MAP_WIDTH)
		warpy = libtcod.random_get_int(0, 1, MAP_HEIGHT)
		while is_blocked(warpx, warpy):
			warpx = libtcod.random_get_int(0, 1, MAP_WIDTH)
			warpy = libtcod.random_get_int(0, 1, MAP_HEIGHT)
		monster.x = warpx
		monster.y = warpy
		message(monster.name.title() + ' suddenly teleports away in a vortex of swirling purple light.', libtcod.light_blue)
		#message('New location of creature: ' + str(monster.x) + ', ' + str(monster.y), libtcod.light_blue)
		
def	cast_swap():
	#warp: target creature in FOV gets warped away to a random location
	message('Choose a target to swap positions with you:', libtcod.light_blue)
	monster = target_monster_or_player()
	if monster is None:
		message('No valid target found!', libtcod.red)
		return 'didnt-take-turn'
	else:
		#do the swap
		player.x, monster.x = monster.x, player.x
		player.y, monster.y = monster.y, player.y
		message(monster.name.title() + ' abruptly finds themselves elsewhere.', libtcod.light_blue)
		#message('New location of creature: ' + str(monster.x) + ', ' + str(monster.y), libtcod.light_blue)
	

	
def cast_fireball():
	#ask the player for a target tile
	message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
	(x, y) = target_tile()
	if x is None: return 'cancelled'
	message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)
	for obj in objects: #damage every fighter in range, including the player
		if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
			attack = obj.fighter.take_damage(FIREBALL_DAMAGE, 'fire')
			if attack != 'immune':
				message('The ' + obj.name.title() + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' damage.', libtcod.orange)
				obj.fighter.check_death()
			else:
				message('The ' + obj.name.title() + ' is immune to fire!', libtcod.red)
			
			
def fire_arrow():
	#ask the player for a target
	message('Left click an enemy to target, or right-click/ESC to cancel.', libtcod.light_cyan)
	monster = target_monster()
	if monster is None:
		message('No valid target found!', libtcod.red)
		return 'didnt-take-turn'
	#monster = target_menu()
	elif monster:
		type = get_bow_type()
		damage = get_bow_damage()
		player.fighter.ranged_attack(monster, type, damage)
		player.fighter.turn_count += 1
		fov_recompute = True
		render_all()
		for object in objects:
			object.clear()
	else:
		message('You can\'t shoot that!', libtcod.red)
		return 'didnt-take-turn'
	
def check_targets_in_fov():
	targets = []
	for object in objects:
		if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
			targets.append(object)
	return targets
	
def target_menu():
	#show a menu with each possible target as an option
	targets = check_targets_in_fov()
	if not targets:
		options = ['No targets in sight!']
	else:
		options = []
		for monster in targets:
			text = monster.name
			options.append(text)
	index = menu('Choose a target:', options, INVENTORY_WIDTH)

def next_level():
	global dungeon_level
	#advance to the next dungeon level
	message('You take a moment to rest, and recover your strength.', libtcod.light_violet)
	player.fighter.heal(player.fighter.max_hp / 2) #recover 50% health

	message('After a rare moment of peace, you descend deeper into the labyrinth...', libtcod.red)
	dungeon_level += 1
	clock.schedule = {key:val for key, val in clock.schedule.items() if val == 'player'}
	while items: items.pop()
	while objects: objects.pop()
	objects.append(player)
	#objects = [object for object in objects if object is player]
	#print(objects)
	#print(clock.schedule)
	#print(clock.schedule)
	#make_bsp()
	make_map() #create a new level
	initialize_fov()

	
def load_customfont(): #TILES VERSION
	#the index of the first custom tile in the file
	a = 256
	
	#the 'y' is the row index, here we load the sixth row. increase the 6 to load any new rows from the file
	for y in range(5,20):
		libtcod.console_map_ascii_codes_to_font(a, 32, 0, y)
		a += 32

def new_game(choice):
	global player, objects, items, inventory, game_msgs, kill_count, game_state, dungeon_level, clock
	objects = []
	items = []
	clock = Ticker()
	if choice == 0:
		#create player object, Fighter class
		fighter_component = Fighter(0, 0, speed=10, hp=100, defense=10, power=4, ranged=2, quiver=0, xp=0, 
			damage_type='phys', damage_dice='1d4', hunger=500, max_hunger=500, death_function=player_death, role='Fighter')
		player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)
		player.level = 1
		objects.append(player)
		clock.schedule_turn(player.fighter.speed, objects.index(player))
	elif choice == 1:
		#create player object, Knight class
		fighter_component = Fighter(0, 0, speed=12, hp=1200, defense=11, power=7, ranged=1, quiver=0, xp=0, 
			damage_type='phys', damage_dice='1d4', hunger=500, max_hunger=500, death_function=player_death, role='Knight')
		player = Object(0, 0, '@', 'player', libtcod.brass, blocks=True, fighter=fighter_component)
		player.level = 1
		objects.append(player)
		clock.schedule_turn(player.fighter.speed, objects.index(player))
	elif choice == 2:
		#create player object, Ranger class
		fighter_component = Fighter(0, 0, speed=8, hp=80, defense=10, power=2, ranged=4, quiver=20, xp=0, 
			damage_type='phys', damage_dice='1d4', hunger=500, max_hunger=500, death_function=player_death, role='Ranger')
		player = Object(0, 0, '@', 'player', libtcod.gold, blocks=True, fighter=fighter_component)
		player.level = 1
		objects.append(player)
		clock.schedule_turn(player.fighter.speed, objects.index(player))
	elif choice == 3:
		#create player object, Wizard class
		fighter_component = Fighter(0, 0, speed=11, hp=60, defense=9, power=2, ranged=3, quiver=0, xp=0, 
			damage_type='phys', damage_dice='1d4', hunger=500, max_hunger=500, death_function=player_death, role='Wizard')
		player = Object(0, 0, '@', 'player', libtcod.sky, blocks=True, fighter=fighter_component)
		player.level = 1
		objects.append(player)
		clock.schedule_turn(player.fighter.speed, objects.index(player))
		
	#generate map (not drawn yet)
	dungeon_level = 1
	#make_bsp()
	make_map()
	initialize_fov()
	
	game_state = 'playing'
	#inventory = []
	kill_count = {}

	#create the list of game messages and their colors
	game_msgs = []

	#a welcome message!
	message('Welcome stranger!  Prepare to die in Eric\'s Maze of Deathery!', libtcod.red)
	
	#create starting equipment, based on class
	if choice == 0:
		#Fighter equipment
		#starting equipment: a short sword
		equipment_component = Equipment(slot='right hand', damage_type='phys', damage_dice='2d4', power_bonus=3, ranged_bonus=0)
		obj = Object(0, 0, '-', 'steel short sword', libtcod.sky, equipment=equipment_component)
		player.fighter.inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
		
		#starting equipment: wooden buckler shield
		equipment_component = Equipment(slot='left hand', damage_type='', damage_dice='', power_bonus=0, defense_bonus=2, ranged_bonus=0)
		obj = Object(0, 0, '(', 'wooden buckler shield', libtcod.brass, equipment=equipment_component)
		player.fighter.inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
	elif choice == 1:
		#Knight equipment
		#starting equipment: a warhammer
		equipment_component = Equipment(slot='right hand', damage_type='blunt', damage_dice='10d6', power_bonus=1, ranged_bonus=0)
		obj = Object(0, 0, '-', 'steel warhammer', libtcod.sky, equipment=equipment_component)
		player.fighter.inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
		
		#starting equipment: a steel tower shield
		equipment_component = Equipment(slot='left hand', damage_type='', damage_dice='', power_bonus=0, defense_bonus=3, ranged_bonus=0)
		obj = Object(0, 0, '[', 'tower shield', libtcod.brass, equipment=equipment_component)
		player.fighter.inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
	elif choice == 2:
		#Ranger equipment
		#starting equipment: a dagger
		equipment_component = Equipment(slot='right hand', damage_type='phys', damage_dice='1d6', power_bonus=2, ranged_bonus=0)
		obj = Object(0, 0, '-', 'steel dagger', libtcod.sky, equipment=equipment_component)
		player.fighter.inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
		
		#starting equipment: a fine Elvish shortbow
		equipment_component = Equipment(slot='bow', damage_type='pierce', damage_dice='1d6', power_bonus=0, ranged_bonus=4)
		obj = Object(0, 0, '{', 'Elvish short bow', libtcod.brass, equipment=equipment_component)
		player.fighter.inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
		
	elif choice == 3:
		#Wizard equipment
		#starting equipment: a staff
		equipment_component = Equipment(slot='right hand', damage_type='phys', damage_dice='1d4', power_bonus=2, ranged_bonus=0)
		obj = Object(0, 0, '|', 'old wooden staff', libtcod.sepia, equipment=equipment_component)
		player.fighter.inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
		
		#WAND TEST: wand of magic missile
		wand_component = Wand(charges=10, max_charges=20, zap_function=cast_magic_missile)
		obj = Object(0, 0, '/', 'wand of magic missile', libtcod.orange, wand=wand_component)
		player.fighter.inventory.append(obj)
		obj.always_visible = True
		
		#WAND TEST 11: wand of petrification
		wand_component = Wand(charges=5, max_charges=20, zap_function=cast_petrify)
		obj = Object(0, 0, '/', 'wand of petrification', libtcod.sepia, wand=wand_component)
		player.fighter.inventory.append(obj)
		obj.always_visible = True
		
		#wand test 12: wand of transposition
		wand_component = Wand(charges=20, max_charges=20, zap_function=cast_swap)
		obj = Object(0, 0, '/', 'wand of transposition', libtcod.light_green, wand=wand_component)
		player.fighter.inventory.append(obj)
		obj.always_visible = True
		
		#recharge potion test
		#create a recharge potion
		item_component = Item(use_function=cast_recharge)
		obj = Object(0, 0, '!', 'recharge potion', libtcod.light_blue, item=item_component)
		player.fighter.inventory.append(obj)
		
		#WAND TEST 7: wand of fireball
		wand_component = Wand(charges=5, max_charges=10, zap_function=cast_fireball)
		obj = Object(0, 0, '/', 'wand of fireball', libtcod.red, wand=wand_component)
		player.fighter.inventory.append(obj)
		
		#WAND TEST 9: wand of death
		wand_component = Wand(charges=3, max_charges=10, zap_function=cast_death)
		obj = Object(0, 0, '/', 'wand of death', libtcod.light_grey, wand=wand_component)
		player.fighter.inventory.append(obj)
		
		# #WAND TEST 10: wand of teleportation
		# wand_component = Wand(charges=10, max_charges=20, zap_function=cast_warp)
		# obj = Object(0, 0, '/', 'wand of teleportation', libtcod.violet, wand=wand_component)
		# player.fighter.inventory.append(obj)
		# obj.always_visible = True
		
		#WAND TEST 2: wand of lightning
		wand_component = Wand(charges=5, max_charges=10, zap_function=cast_lightning)
		obj = Object(0, 0, '/', 'wand of lightning', libtcod.yellow, wand=wand_component)
		player.fighter.inventory.append(obj)
		obj.always_visible = True
		
		# #WAND TEST 3: wand of confusion
		# wand_component = Wand(charges=5, max_charges=15, zap_function=cast_confuse)
		# obj = Object(0, 0, '/', 'wand of confusion', libtcod.sky, wand=wand_component)
		# player.fighter.inventory.append(obj)
		# obj.always_visible = True
	
	for rations in range(3):
		food_component = Food('normal', 500)
		obj = Object(0, 0, '%', 'ration pack', libtcod.sepia, food=food_component)
		player.fighter.inventory.append(obj)
		


	

def initialize_fov():
	global fov_recompute, fov_map
	fov_recompute = True
	
	#create the FOV map, according to the generated map
	fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
	
	libtcod.console_clear(con) #unexplored areas start black (default background color)

def save_game():
	global clock, kill_count, objects
	#open a new shelf (overwriting any old one) to write the game data
	#clock.schedule = {key:val for key, val in clock.schedule.items() if val == 'player'} #clear schedule
	#clock.schedule.clear()
	# for object in objects:
		# if object.fighter is not None:
			# object.fighter.ticker = None
	file = shelve.open('savegame', 'n')
	file['map'] = map
	file['objects'] = objects
	file['items'] = items
	file['player_index'] = objects.index(player) #location of player in objects list
	#file['inventory'] = inventory
	file['clock'] = clock
	#file['schedule'] = clock.schedule
	file['kill_count'] = kill_count
	file['game_msgs'] = game_msgs
	file['game_state'] = game_state
	file['stairs_index'] = objects.index(stairs)
	file['dungeon_level'] = dungeon_level
	file.close()

def load_game():
	#open the previously saved shelf and load game data
	global map, objects, items, player, clock, game_msgs, game_state, stairs, dungeon_level, kill_count
	
	file = shelve.open('savegame', 'r')
	map = file['map']
	objects = file['objects']
	items = file['items']
	player = objects[file['player_index']] #get index of player and access it
	clock = file['clock']
	kill_count = file['kill_count']
	game_msgs = file['game_msgs']
	game_state = file['game_state']
	stairs = objects[file['stairs_index']]
	dungeon_level = file['dungeon_level']
	file.close()

	#print(player.fighter.turn_count)
	#print(clock.ticks)
	clock.schedule.clear()
	for object in objects:
		#if object == player:
		#	print('found him!')
		if object.fighter is not None:
			clock.schedule_turn(object.fighter.speed, objects.index(object))
	#print(clock.schedule)
	#print(player)
	initialize_fov()

def character_dump():
	global dungeon_level_name
	timestr = time.strftime("%Y%m%d-%H%M%S")
	with open('morgue' + timestr + '.txt', 'w') as morgue:
		morgue.write('Player died in the ' + dungeon_level_name + ' (dungeon level ' + str(dungeon_level) + '), and had ' + 
			str(player.fighter.xp) + ' experience points.\n')
		morgue.write('\n')
		morgue.write('Player was a Level ' + str(player.level) + ' ' + str(player.fighter.role) + '.\n')
		morgue.write('\n')
		morgue.write('Monsters killed:\n')
		for k, v in kill_count.items():
			#line = '{}: {}'.format(k,v)
			#print(line, file=morgue)
			morgue.write('\t%s: %s\n' % (k.title(), v))
		morgue.write('\n')
		morgue.write('\tTotal monster kills: {}\n'.format(sum(kill_count.itervalues())))
		morgue.write('\n')
		morgue.write('Player\'s inventory:\n')
		for item in player.fighter.inventory:
			morgue.write('\t%s\n' % (item.name.title()))
		morgue.close()
			

def play_game():
	global key, mouse, clock

	#player_action = None

	mouse = libtcod.Mouse()
	key = libtcod.Key()
	 
	while not libtcod.console_is_window_closed():
		#render the screen
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
		render_all()

		libtcod.console_flush()

		#level up if needed
		check_level_up()

		#erase all objects at their old locations, before they move
		for object in objects:
			object.clear()

		#handle keys and exit if needed
		#player_action = handle_keys()
		# if player_action == 'exit':
			# save_game()
			# break
		#clock.next_turn()
		
		# if game_state == 'playing':
			# action = clock.check_player_turn()
			# if action == 'player':
				# player_action = handle_keys()
				# while True:
					# if player_action == 'exit':
						# save_game()
						# break
					# if player_action == 'acted':
						# break
				# clock.next_turn()
				# clock.schedule_turn(player.fighter.speed, objects.index(player))
			# else:
				# clock.next_turn()
			# clock.ticks += 1

		#let monsters take their turn
		if game_state == 'playing':# and clock.last_turn == 'player':
			clock.ticks += 1
			#print(clock.ticks)
			#print(clock.schedule)
			turn = clock.next_turn()
			if turn == 'exit':
				save_game()
				break
				
			# for object in objects:
				# if object.ai:
					# object.ai.take_turn()
					
		if game_state == 'dead':
			key = libtcod.console_wait_for_keypress(True)
			if key.vk == libtcod.KEY_ESCAPE:
				break  #exit game
			
					
def graphics_menu():
	libtcod.console_clear(con)
	choice = menu('Graphics mode selection:', ['Terminal style', 'Colored tiles', 'Quit'], 24)
	if choice == 0:
		SET_CONSOLE_MODE = True
	if choice == 1:
		SET_CONSOLE_MODE = False
	libtcod.console_clear(con)

def class_menu():
	img = libtcod.image_load('menu_background1.png')
	
	while not libtcod.console_is_window_closed():
		#show background image, at twice regular console resolution
		libtcod.image_blit_2x(img, 0, 0, 0)

		#show the title and credits
		libtcod.console_set_default_foreground(0, libtcod.light_yellow)
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER,
			'Eric\'s Maze of Deathery')
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-2, libtcod.BKGND_NONE, libtcod.CENTER,
			'by Eric Silverman')

		#show options and wait for the player's choice
		choice = menu('Choose your class:', ['Fighter', 'Knight', 'Ranger', 'Wizard', 'Back to main menu'], 24)

		if choice == 0: #start new game as Fighter (Power focus)
			new_game(0)
			play_game()
		elif choice == 1: #start new game as Knight (Defense focus)
			new_game(1)
			play_game()
		elif choice == 2: #start new game as Ranger (Accuracy focus)
			new_game(2)
			play_game()
		elif choice == 3: #start new game as Wizard (Magic focus)
			new_game(3)
			play_game()
		elif choice == 4: #retreat to main menu
			main_menu()
	

def main_menu():
	img = libtcod.image_load('menu_background1.png')
	
	while not libtcod.console_is_window_closed():
		#show background image, at twice regular console resolution
		libtcod.image_blit_2x(img, 0, 0, 0)

		#show the title and credits
		libtcod.console_set_default_foreground(0, libtcod.light_yellow)
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER,
			'Eric\'s Maze of Deathery')
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-2, libtcod.BKGND_NONE, libtcod.CENTER,
			'by Eric Silverman')

		#show options and wait for the player's choice
		choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)

		if choice == 0: #new game
			time.sleep(0.5)
			class_menu()
			#new_game()
			#play_game()
		if choice == 1: #load last game
			try:
				load_game()
			except:
				msgbox('\n No saved game to load.\n', 24)
				continue
			play_game()
		elif choice == 2: #quit
			raise SystemExit
		


#############################################
# Initialization & Main Loop
#############################################

#run command for Notepad++ "C:\Python27\debugpy.bat" "$(CURRENT_DIRECTORY)" $(FILE_NAME)
libtcod.console_set_custom_font('terminal16x16_gs_ro.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_ASCII_INROW, 16, 16) 
#libtcod.console_set_custom_font('terminal8x8_aa_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
#libtcod.console_set_custom_font('tiledFont6.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD, 32, 24) #TILES VERSION
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Eric\'s Maze of Deathery', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

#load_customfont() #TILES VERSION
main_menu()





