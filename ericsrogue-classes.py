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

#dungeon generation parameters
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

#BSP dungeon parameters
DEPTH = 10
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
 
LIMIT_FPS = 20  #20 frames-per-second maximum

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

class Object:
	#this is a generic object
	#it's always represented by an ASCII character
	def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None, arrows=None):
		self.x = x
		self.y = y
		self.char = char
		self.name = name
		self.color = color
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

	def move(self, dx, dy):
		if not is_blocked(self.x + dx, self.y + dy):
			#move by the given amount if not blocked
			self.x += dx
			self.y += dy
			self.fighter.x = self.x
			self.fighter.y = self.y

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
			libtcod.console_put_char_ex(con, self.x, self.y, '.', libtcod.grey, libtcod.black)
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
		global objects
		objects.remove(self)
		objects.insert(0, self)
	def clear(self):
		#erase the character that represents this object
		libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

class Fighter:
	#combat-related properties and methods (monsters, players, and NPCs)
	def __init__(self, x, y, hp, defense, power, ranged, quiver, xp, turn_count=0, poison_tick=0, enraged=False, poisoned=False, death_function=None, role=None):
		self.x = x
		self.y = y
		self.base_max_hp = hp
		self.hp = hp
		self.base_defense = defense
		self.base_power = power
		self.base_ranged = ranged
		self.quiver = quiver
		self.xp = xp
		self.turn_count = turn_count
		self.poison_tick = poison_tick
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

	def take_damage(self, damage):
		#apply damage if possible
		if damage > 0:
			self.hp -= damage
			
			#check for death
			if self.hp <= 0:
				function = self.death_function
				if function is not None:
					function(self.owner)

				if self.owner != player:  #give experience
					player.fighter.xp += self.xp
					
	def distance_to(self, other):
		#return the distance to another object
		dx = other.x - self.x
		dy = other.y - self.y
		return math.sqrt(dx ** 2 + dy ** 2)
	
	def attack(self, target):
		#a simple formula for attack damage
		damage = libtcod.random_get_int(0, 2, self.power) - target.fighter.defense
		if damage <= 0:
			damage = 1
		
		if self.AttackRoll(target.fighter) == 'hit':
			#make target take damage
			message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' damage.', libtcod.white)
			target.fighter.take_damage(damage)
		elif self.AttackRoll(target.fighter) == 'miss':
			message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but misses.', libtcod.white)
			
	def ranged_attack(self, target):
		#simple formula for ranged damage -- to change later
		damage = libtcod.random_get_int(0, 2, self.ranged) - target.fighter.defense
		if damage <= 0:
			damage = 1
		if self.quiver > 0 and get_equipped_in_slot('bow') is not None: 
			if self.ranged_attack_roll(target.fighter) == 'hit':
				#make target take damage
				message(self.owner.name.capitalize() + ' fires an arrow at ' + target.name + ' for ' + str(damage) + ' damage.', libtcod.green)
				target.fighter.take_damage(damage)
				self.quiver -= 1
			elif self.ranged_attack_roll(target.fighter) == 'miss':
				message(self.owner.name.capitalize() + ' fires an arrow at ' + target.name + ' but it misses!', libtcod.green)
				self.quiver -= 1
			#message('Orc quiver status: ' + str(self.quiver) + ' arrows!', libtcod.white)
		elif self.quiver <= 0 and get_equipped_in_slot('bow') is not None:
			message(self.name + ' ran out of arrows!', libtcod.green)
			return 'didnt-take-turn'
		else:
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
		attackRoll = libtcod.random_get_int(0, 1, 20) + attacker.ranged - ranged_modifier
		defenseRoll = libtcod.random_get_int(0, 1, 20) + target.defense
		
		if attackRoll > defenseRoll:
			return 'hit'
		else:
			return 'miss'
	
	def AttackRoll(attacker, target):
		attackRoll = libtcod.random_get_int(0, 1, 20) + attacker.power
		defenseRoll = libtcod.random_get_int(0, 1, 20) + target.defense
		# if attacker is player:
			# attackRoll = libtcod.random_get_int(0, 1, 20) + attacker.fighter.base_power
		# else:
			# attackRoll = libtcod.random_get_int(0, 1, 20) + attacker.base_power
		# if target is player:
			# defenseRoll = libtcod.random_get_int(0, 1, 20) + target.fighter.base_defense
		# else:
			# defenseRoll = libtcod.random_get_int(0, 1, 20) + target.base_defense
		if attackRoll > defenseRoll:
			return 'hit'
		else:
			return 'miss'

class BasicMonster:
	#AI for a basic monster
	def take_turn(self):
		#basic monster takes its turn. If you can see it, it can see you
		monster = self.owner
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			#move toward player if far away
			if monster.distance_to(player) >= 2:
				monster.move_astar(player)

			#attack if close enough, if player is still alive
			elif player.fighter.hp > 0:
				monster.fighter.attack(player)

class WolfAI:
	#AI for a wolf - they can attack from outside FOV, and howl for extra power when injured!
	def take_turn(self):
		monster = self.owner
		if monster.distance_to(player) <= 20:
			if monster.distance_to(player) >= 2:
				monster.move_astar(player)
			elif monster.fighter.hp <= 5 and monster.distance_to(player) <= 5 and monster.fighter.enraged == False:
				message('The wolf howls with rage!', libtcod.red)
				monster.fighter.enraged = True
				monster.fighter.power += 1
				monster.color = libtcod.red
				packmate = closest_packmate(monster, 30)
				if packmate is not None:
					packmate.ai = AngryWolf
					packmate.ai.owner = packmate
					message('You hear an answering howl in the distance!', libtcod.red)
			else:
				monster.fighter.attack(player)
				
class PoisonSpitterAI:
	#AI for poisonspitters -- they get to range and chuck poison goo, chance to hit based on Agility
	def take_turn(self):
		monster = self.owner
		if monster.distance_to(player) <= 15 and monster.distance_to(player) > 5:
			monster.move_astar(player)
			if libtcod.random_get_int(0, 1, 6) < 3:
				message('You hear a rattling in the distance....', libtcod.yellow)
		elif monster.distance_to(player) <= 5 and player.fighter.poisoned == False and libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
				message('The ' + monster.name + ' spits poison at you!', libtcod.purple)
				if monster.fighter.ranged_attack_roll(player.fighter) == 'hit':
					message('The poison spit drips all over you!  You don\'t feel well...', libtcod.purple)
					player.fighter.poisoned = True
					player.fighter.poison_tick = player.fighter.turn_count
				else:
					message('You dodged the poison spit!', libtcod.purple)
				
		elif monster.distance_to(player) <= 5 and player.fighter.poisoned == True and monster.distance_to(player) >= 2:
			monster.move_astar(player)
		elif monster.distance_to(player) <= 1:
			monster.fighter.attack(player)
			
class ArcherAI:
	#AI for archers - they get to range and fire arrows
	def take_turn(self):
		monster = self.owner
		range = monster.distance_to(player)
		if range <=15 and range > 7:
			monster.move_astar(player)
		elif range <= 7 and libtcod.map_is_in_fov(fov_map, monster.x, monster.y) and monster.fighter.quiver > 0:
			monster.fighter.ranged_attack(player)
			if monster.fighter.quiver == 0:
				message('The ' + monster.name + ' ran out of arrows!', libtcod.green)
		elif range <= 7 and not libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			monster.move_astar(player)
		elif monster.fighter.quiver <= 0 and range >= 2:
			monster.move_astar(player)
		elif monster.fighter.quiver <= 0 and range <= 1:
			monster.fighter.attack(player)
			
class AngryWolf:
	#AI for wolf awoken by a packmate's howl -- they'll charge in from up to 25 tiles away!
	def take_turn(self):
		monster = self.owner
		range = monster.distance_to(player)
		if range <=16 and range >= 2:
			move_astar_player
		if range < 2:
			monster.fighter.attack(player)
			
	

				

class ConfusedMonster:
	#AI for a temporarily confused monster (reverts back after a few turns)
	def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
		self.old_ai = old_ai
		self.num_turns = num_turns

	def take_turn(self):
		if self.num_turns > 0: #still confused?
			#move in a random direction, decrease number of confused turns remaining
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
			self.num_turns -= 1
		else: #restore previous AI
			self.owner.ai = self.old_ai
			message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)

class Item:
	#an item that can be picked up and used
	def __init__(self, use_function=None):
		self.use_function = use_function

	def pick_up(self):
		arrows = self.owner.arrows
		#add to player's inventory and remove from the map
		if len(inventory) >= 26 and not arrows:
			message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
		elif not arrows:
			inventory.append(self.owner)
			objects.remove(self.owner)
			message('You picked up a ' + self.owner.name + '!', libtcod.green)
		#special case: if item is Equipment, automatically equip if slot is open
		equipment = self.owner.equipment
		if equipment and get_equipped_in_slot(equipment.slot) is None:
			equipment.equip()

		#special case: if item is Arrows, automatically add to Quiver if <= 99
		if arrows and player.fighter.quiver < 99:
			player.fighter.quiver += arrows.number
			objects.remove(self.owner)
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
		
		#just call the use_function if it is defined
		if self.use_function is None:
			message('The ' + self.owner.name + ' cannot be used.')
		else:
			if self.use_function() != 'cancelled':
				inventory.remove(self.owner) #destroy after use, unless cancelled

	def drop(self):
		#special case: if Equipment, dequip before dropping
		if self.owner.equipment:
			self.owner.equipment.dequip()
		
		#add to the map and remove from the player's inventory
		objects.append(self.owner)
		inventory.remove(self.owner)
		self.owner.x = player.x
		self.owner.y = player.y
		message('You dropped a ' + self.owner.name + '.', libtcod.yellow)

class Equipment:
	#an object that can be equipped, yielding bonuses/special abilities
	def __init__(self, slot, power_bonus=0, ranged_bonus=0, defense_bonus=0, max_hp_bonus=0):
		self.slot = slot
		self.power_bonus = power_bonus
		self.ranged_bonus = ranged_bonus
		self.defense_bonus = defense_bonus
		self.max_hp_bonus = max_hp_bonus
		self.is_equipped = False
	def toggle_equip(self):
		if self.is_equipped:
			self.dequip()
		else:
			self.equip()
	def equip(self):
		#if slot is used, dequip whatever's there first
		old_equipment = get_equipped_in_slot(self.slot)
		if old_equipment is not None:
			old_equipment.dequip
		
		#equip object and alert the player
		self.is_equipped = True
		message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)
	def dequip(self):
		self.is_equipped = False
		message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)
		
class Arrows:
	#arrow items that can be picked up and added to player's Quiver for later firing
	def __init__(self, type, number):
		self.type = type
		self.number = number
		

def get_equipped_in_slot(slot): #returns equipment in slot, None if empty
	for obj in inventory:
		if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
			return obj.equipment
	return None

def get_all_equipped(obj): #gets a list of equipped items
	if obj == player:
		equipped_list = []
		for item in inventory:
			if item.equipment and item.equipment.is_equipped:
				equipped_list.append(item.equipment)
		return equipped_list
	else:
		return [] #other objects have no slots (at the moment)

def is_blocked(x, y):
	#test the map tile first
	if map[x][y].blocked:
		return True

	#now check for blocking objects
	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True

	return False

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
	objects = [player]
	
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
	stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
	objects.append(stairs)
	stairs.send_to_back()
	
###############################
# BSP EXPERIMENTATION
###############################

def make_bsp():
	global player, map, objects, stairs, bsp_rooms
	objects = [player]
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
	stairs = Object(stairs_location[0], stairs_location[1], '<', 'stairs', libtcod.white, always_visible=True)
	objects.append(stairs)
	stairs.send_to_back()
	
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

def place_objects(room):
	#first we decide the chance of each monster or item showing up
	
	#max monsters per room
	max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])

	#chances for each monster
	monster_chances = {}
	monster_chances['orc'] = 60 #orc always shows up
	monster_chances['orc archer'] = 35 #orc archers always show up, for now
	monster_chances['wolf'] = 60 #wolf always shows up
	monster_chances['rattlesnake'] = 20 #snake always shows up, for now
	monster_chances['troll'] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])

	#max items per room
	max_items = from_dungeon_level([[1, 1], [2, 4]])
	
	#chances for each item
	item_chances = {}
	item_chances['heal'] = 35 #healing pots always show up
	item_chances['antidote'] = 25 #antidotes always show up
	item_chances['lightning'] = from_dungeon_level([[25, 4]])
	item_chances['fireball'] = from_dungeon_level([[25, 6]])
	item_chances['confuse'] = from_dungeon_level([[10, 2]])
	item_chances['longsword'] = from_dungeon_level([[5, 4]])
	item_chances['shield'] = from_dungeon_level([[15, 8]])

	#choose a random number of monsters
	num_monsters = libtcod.random_get_int(0, 0, max_monsters)

	for i in range(num_monsters):
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		
		#only place if tile is not blocked
		if not is_blocked(x, y):
			choice = random_choice(monster_chances)
			if choice == 'orc':
				#create an orc
				fighter_component = Fighter(x, y, hp=10, defense=0, power=4, ranged=0, quiver=0, xp=35, death_function=monster_death)
				ai_component = BasicMonster()
				monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green, blocks=True, fighter=fighter_component, ai=ai_component)
			elif choice == 'orc archer':
				#create an orc archer
				fighter_component = Fighter(x, y, hp=8, defense=0, power=1, ranged=4, quiver=15, xp=50, death_function=archer_death)
				ai_component = ArcherAI()
				monster = Object(x, y, 'o', 'orc archer', libtcod.light_green, blocks=True, fighter=fighter_component, ai=ai_component)
			elif choice == 'troll':
				#create a troll
				fighter_component = Fighter(x, y, hp=30, defense=2, power=8, ranged=0, quiver=0, xp=100, death_function=monster_death)
				ai_component = BasicMonster()
				monster = Object(x, y, 'T', 'troll', libtcod.darker_green, blocks=True, fighter=fighter_component, ai=ai_component)
			elif choice == 'wolf':
				#create a wolf
				fighter_component = Fighter(x, y, hp=8, defense=0, power=2, ranged=0, quiver=0, xp=10, death_function=monster_death)
				ai_component = WolfAI()
				monster = Object(x, y, 'w', 'wolf', libtcod.grey, blocks=True, fighter=fighter_component, ai=ai_component)
				if not is_blocked(x+1,y):
					fighter_component = Fighter(x, y, hp=10, defense=0, power=2, ranged=0, quiver=0, xp=10, death_function=monster_death)
					ai_component = WolfAI()
					monster = Object(x+1, y, 'w', 'wolf', libtcod.grey, blocks=True, fighter=fighter_component, ai=ai_component)
			elif choice == 'rattlesnake':
				fighter_component = Fighter(x, y, hp=8, defense=1, power=3, ranged=3, xp=15, quiver=0, death_function=monster_death)
				ai_component = PoisonSpitterAI()
				monster=Object(x, y, 'S', 'rattlesnake', libtcod.light_sepia, blocks=True, fighter=fighter_component, ai=ai_component)
					
			objects.append(monster)

	#choose random number of items
	num_items = libtcod.random_get_int(0, 0, max_items)

	for i in range(num_items):
		#choose random spot for this item
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

		#only place it if tile is not blocked
		if not is_blocked(x, y):
			choice = random_choice(item_chances)
			if choice == 'heal':
				#create a healing potion
				item_component = Item(use_function=cast_heal)
				item = Object(x, y, '!', 'healing potion', libtcod.pink, item=item_component)
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
			elif choice == 'antidote':
				#create an antidote:
				item_component = Item(use_function=cast_antidote)
				item = Object(x, y, '!', 'antidote', libtcod.purple, item=item_component)
			elif choice == 'longsword':
				#create a longsword
				equipment_component = Equipment(slot='right hand', power_bonus=3)
				item = Object(x, y, '/', 'longsword', libtcod.sky, equipment=equipment_component)
			elif choice == 'shield':
				#create a shield
				equipment_component = Equipment(slot='left hand', defense_bonus=2)
				item = Object(x, y, '[', 'shield', libtcod.darker_orange, equipment=equipment_component)
			objects.append(item)
			item.send_to_back() #items appear behind other objects
			item.always_visible=True #items always visible once explored

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
	global color_dark_wall, color_light_wall
	global color_dark_ground, color_light_ground
	global fov_recompute

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
							libtcod.console_put_char_ex(con, x, y, '#', libtcod.grey, libtcod.black)
							#libtcod.console_put_char_ex(con, x, y, '#', libtcod.flame, libtcod.black)
							#libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
						else:
							libtcod.console_put_char_ex(con, x, y, '.', libtcod.grey, libtcod.black)
							#libtcod.console_put_char_ex(con, x, y, ' ', libtcod.black, libtcod.black)
							#libtcod.console_put_char_ex(con, x, y, '.', libtcod.flame, libtcod.black)
							#libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
				else:
					if wall:
						#libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
						libtcod.console_put_char_ex(con, x, y, '#', libtcod.lighter_grey, libtcod.black)
						#libtcod.console_put_char_ex(con, x, y, '#', libtcod.light_flame, libtcod.black)
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

	#draw all objects in the list except player!
	for object in objects:
		if object!= player:
			object.draw()
	#draw player
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
	render_bar(1, 2, BAR_WIDTH, 'XP', player.fighter.xp, level_up_xp,
		libtcod.blue, libtcod.darker_blue)
	libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'Level ' + str(player.level) + ' ' + player.fighter.role)
	libtcod.console_print_ex(panel, 1, 4, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon Level: ' + str(dungeon_level))
	libtcod.console_print_ex(panel, 1, 5, libtcod.BKGND_NONE, libtcod.LEFT, 'Turns: ' + str(player.fighter.turn_count))
	if player.fighter.poisoned == True:
		libtcod.console_print_ex(panel, 1, 6, libtcod.BKGND_NONE, libtcod.LEFT, '!!POISONED!!')

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
	if target is not None:
		player.fighter.attack(target)
	else:
		player.move(dx, dy)
		fov_recompute = True
	
	#if poisoned, take damage
	if player.fighter.poisoned == True:
		if libtcod.random_get_int(0, 1, 6) < 3:
			poison_damage = libtcod.random_get_int(0, 1, player.level + 1)
			player.fighter.take_damage(poison_damage)
			message('You took ' + str(poison_damage) + ' damage from poison!', libtcod.purple)
			
	#if poisoned for 10 turns, shake it off
	if player.fighter.poisoned and player.fighter.turn_count - player.fighter.poison_tick >= 10:
		player.fighter.poisoned = False
		message('You recovered from the poison\'s effects!', libtcod.yellow)
		
	player.fighter.turn_count += 1
		

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
	#show a menu with each inventory item as an option
	if len(inventory) == 0:
		options = ['Inventory is empty.']
	else:
		options = []
		for item in inventory:
			text = item.name
			#show additional info, in case it's equipped
			if item.equipment and item.equipment.is_equipped:
				text = text + ' (on ' + item.equipment.slot + ')'
			options.append(text)

	index = menu(header, options, INVENTORY_WIDTH)

	#if an item was chosen, return it
	if index is None or len(inventory) == 0: return None
	return inventory[index].item

def msgbox(text, width=50):
	menu(text, [], width) #use menu() for a message box
 
 
def handle_keys():
	global keys
 
    #key = libtcod.console_check_for_keypress()  #real-time
	#key = libtcod.console_wait_for_keypress(True)  #turn-based

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
	 
		elif key.vk == libtcod.KEY_DOWN:
			player_move_or_attack(0, 1)
	 
		elif key.vk == libtcod.KEY_LEFT:
			player_move_or_attack(-1, 0)
	 
		elif key.vk == libtcod.KEY_RIGHT:
			player_move_or_attack(1, 0)
			
		elif key_char == 'f':
			#fire an arrow if arrows are available
			if player.fighter.quiver > 0 and get_equipped_in_slot('bow') is not None:
				fire_arrow()
			elif player.fighter.quiver > 0 and get_equipped_in_slot('bow') is None:
				message('You don\'t have a ranged weapon!', libtcod.red)
				return 'didnt-take-turn'
			elif player.fighter.quiver <= 0:
				message('You don\'t have any arrows!', libtcod.red)
				return 'didnt-take-turn'
		
		elif key.vk == libtcod.KEY_TAB:
			pass #do nothing and let monsters approach
		
		else:
			#test for other keys
			key_char = chr(key.c)

			if key_char == 'g':
				#pick up an item
				for object in objects: #check for object in player's tile
					if object.x == player.x and object.y == player.y and object.item:
						object.item.pick_up()
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
			if key_char == '<':
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
					'\nQuiver: ' + str(player.fighter.quiver), CHARACTER_SCREEN_WIDTH)
			return 'didnt-take-turn'

def get_names_under_mouse():
	global mouse
	
	#return a string with the names of all objects under the mouse
	(x, y) = (mouse.cx, mouse.cy)
	#create a list with the names of all objects at the mouse's coordinates and in FOV
	names = [obj.name for obj in objects
				if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
	names = ', '.join(names) #join the names, comma-separated
	return names.capitalize()

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
	message('You died!', libtcod.red)
	game_state = 'dead'

	#transform the player into a corpse
	player.char = '%'
	player.color = libtcod.dark_red

def monster_death(monster):
	#transform monster into a corpse! no more moves or attacks, can't be attacked
	message(monster.name.capitalize() + ' is dead! You gained ' + str(monster.fighter.xp) + ' experience points.', libtcod.orange)
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.blocks = False
	monster.fighter = None
	monster.ai = None
	monster.name = 'remains of ' + monster.name
	monster.send_to_back()
	
def archer_death(monster):
	global objects
	#drop arrows for player to pick up!
	if monster.fighter.quiver > 0:
		arrows_component = Arrows(type=1, number=monster.fighter.quiver)
		item = Object(monster.x, monster.y, '^', str(monster.fighter.quiver) + ' arrows', libtcod.sepia, arrows=arrows_component)
		objects.append(item)
		item.send_to_back()
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
	message('A lightning bolt strikes the ' + monster.name + ' for ' + str(LIGHTNING_DAMAGE) + ' damage!', libtcod.light_blue)
	monster.fighter.take_damage(LIGHTNING_DAMAGE)

def cast_confuse():
	#ask the player for a target to confuse
	message('Left click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
	monster = target_monster(CONFUSE_RANGE)
	if monster is None: return 'cancelled'
	#replace monster AI with confused AI
	old_ai = monster.ai
	monster.ai = ConfusedMonster(old_ai)
	monster.ai.owner = monster
	message('The eyes of the ' + monster.name + ' look vacant as it starts to stumble around!', libtcod.light_green)
	
def cast_fireball():
	#ask the player for a target tile
	message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
	(x, y) = target_tile()
	if x is None: return 'cancelled'
	message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)
	for obj in objects: #damage every fighter in range, including the player
		if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
			message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' damage.', libtcod.orange)
			obj.fighter.take_damage(FIREBALL_DAMAGE)
			
def fire_arrow():
	#ask the player for a target
	message('Left click an enemy to target, or right-click/ESC to cancel.', libtcod.light_cyan)
	monster = target_monster()
	if monster is None:
		message('No valid target found!', libtcod.red)
		return 'didnt-take-turn'
	#monster = target_menu()
	elif monster:
		player.fighter.ranged_attack(monster)
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
	make_bsp()
	#make_map() #create a new level
	initialize_fov()
	
def load_customfont(): #TILES VERSION
	#the index of the first custom tile in the file
	a = 256
	
	#the 'y' is the row index, here we load the sixth row. increase the 6 to load any new rows from the file
	for y in range(5,20):
		libtcod.console_map_ascii_codes_to_font(a, 32, 0, y)
		a += 32

def new_game(choice):
	global player, inventory, game_msgs, game_state, dungeon_level
	if choice == 0:
		#create player object, Fighter class
		fighter_component = Fighter(0, 0, hp=100, defense=2, power=4, ranged=2, quiver=10, xp=0, death_function=player_death, role='Fighter')
		player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)
		player.level = 1
	elif choice == 1:
		#create player object, Knight class
		fighter_component = Fighter(0, 0, hp=120, defense=4, power=2, ranged=1, quiver=10, xp=0, death_function=player_death, role='Knight')
		player = Object(0, 0, '@', 'player', libtcod.brass, blocks=True, fighter=fighter_component)
		player.level = 1
	elif choice == 2:
		#create player object, Ranger class
		fighter_component = Fighter(0, 0, hp=80, defense=1, power=2, ranged=4, quiver=20, xp=0, death_function=player_death, role='Ranger')
		player = Object(0, 0, '@', 'player', libtcod.gold, blocks=True, fighter=fighter_component)
		player.level = 1
		
	#generate map (not drawn yet)
	dungeon_level = 1
	make_bsp()
	#make_map()
	initialize_fov()
	
	game_state = 'playing'
	inventory = []

	#create the list of game messages and their colors
	game_msgs = []

	#a welcome message!
	message('Welcome stranger!  Prepare to die in Eric\'s Maze of Deathery!', libtcod.red)
	
	#create starting equipment, based on class
	if choice == 0:
		#Fighter equipment
		#starting equipment: a short sword
		equipment_component = Equipment(slot='right hand', power_bonus=3, ranged_bonus=0)
		obj = Object(0, 0, '-', 'steel short sword', libtcod.sky, equipment=equipment_component)
		inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
		
		#starting equipment: wooden buckler shield
		equipment_component = Equipment(slot='left hand', power_bonus=0, defense_bonus=2, ranged_bonus=0)
		obj = Object(0, 0, '(', 'wooden buckler shield', libtcod.brass, equipment=equipment_component)
		inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
	elif choice == 1:
		#Knight equipment
		#starting equipment: a warhammer
		equipment_component = Equipment(slot='right hand', power_bonus=3, ranged_bonus=0)
		obj = Object(0, 0, '-', 'steel warhammer', libtcod.sky, equipment=equipment_component)
		inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
		
		#starting equipment: a steel tower shield
		equipment_component = Equipment(slot='left hand', power_bonus=0, defense_bonus=3, ranged_bonus=0)
		obj = Object(0, 0, '{', 'Elvish short bow', libtcod.brass, equipment=equipment_component)
		inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
	elif choice == 2:
		#Ranger equipment
		#starting equipment: a dagger
		equipment_component = Equipment(slot='right hand', power_bonus=2, ranged_bonus=0)
		obj = Object(0, 0, '-', 'steel dagger', libtcod.sky, equipment=equipment_component)
		inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True
		
		#starting equipment: a fine Elvish shortbow
		equipment_component = Equipment(slot='bow', power_bonus=0, ranged_bonus=4)
		obj = Object(0, 0, '{', 'Elvish short bow', libtcod.brass, equipment=equipment_component)
		inventory.append(obj)
		equipment_component.equip()
		obj.always_visible = True


	

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
	#open a new shelf (overwriting any old one) to write the game data
	file = shelve.open('savegame', 'n')
	file['map'] = map
	file['objects'] = objects
	file['player_index'] = objects.index(player) #location of player in objects list
	file['inventory'] = inventory
	file['game_msgs'] = game_msgs
	file['game_state'] = game_state
	file['stairs_index'] = objects.index(stairs)
	file['dungeon_level'] = dungeon_level
	file.close()

def load_game():
	#open the previously saved shelf and load game data
	global map, objects, player, inventory, game_msgs, game_state, stairs, dungeon_level
	
	file = shelve.open('savegame', 'r')
	map = file['map']
	objects = file['objects']
	player = objects[file['player_index']] #get index of player and access it
	inventory = file['inventory']
	game_msgs = file['game_msgs']
	game_state = file['game_state']
	stairs = objects[file['stairs_index']]
	dungeon_level = file['dungeon_level']
	file.close()

	initialize_fov()


def play_game():
	global key, mouse

	player_action = None

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
		player_action = handle_keys()
		if player_action == 'exit':
			save_game()
			break

		#let monsters take their turn
		if game_state == 'playing' and player_action != 'didnt-take-turn':
			for object in objects:
				if object.ai:
					object.ai.take_turn()
					
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
		choice = menu('Choose your class:', ['Fighter', 'Knight', 'Ranger', 'Back to main menu'], 24)

		if choice == 0: #start new game as Fighter (Power focus)
			new_game(0)
			play_game()
		elif choice == 1: #start new game as Knight (Defense focus)
			new_game(1)
			play_game()
		elif choice == 2: #start new game as Ranger (Accuracy focus)
			new_game(2)
			play_game()
		elif choice == 3: #back to main menu
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
 
libtcod.console_set_custom_font('terminal8x8_aa_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
#libtcod.console_set_custom_font('tiledFont6.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD, 32, 24) #TILES VERSION
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Eric\'s Maze of Deathery', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

#load_customfont() #TILES VERSION
main_menu()





