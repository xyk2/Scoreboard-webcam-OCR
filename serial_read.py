import serial

score_digits = [63, 6, 91, 79, 102, 109, 125, 7, 127, 103]
score_digits_100s = [191, 134, 219, 207, 230, 237, 253, 135, 255, 231] # Indexes for >99 score

serial_arg  = dict(port = 2, baudrate = 9600, stopbits = serial.STOPBITS_ONE, parity = serial.PARITY_NONE, timeout  = None)
serial_port = serial.Serial(**serial_arg) # Open serial port with given arguments


def returnTeamScore(ord1, ord2):
	digit1, digit2, hundreds = "", "", ""
	try: digit1 = str(score_digits.index(ord1))
	except: pass
	try: digit2 = str(score_digits.index(ord2))
	except: pass

	try: # Do 100s anyway as it will escape out if its <99. <99 will pass both these statements
		digit1 = str(score_digits_100s.index(ord1))
		hundreds = "1" 
	except: pass
	try: digit2 = str(score_digits_100s.index(ord2))
	except: pass

	return hundreds + digit1 + digit2

def returnFouls(ord1):
	return str(int(ord1) - 48) # Fouls are direct, if ASCII byte = 0 then fouls = 0

def returnQuarter(ord1, ord2):
	return str(int(ord1) + int(ord2) - 48 - 48) # ord1 + ord2 is the current quarter

def returnPosession(ord1):
	if(ord1 == 50): return "HOME"
	if(ord1 == 52): return "GUEST"
	return ""

def returnGameTime(seconds_ord, deciseconds_ord, minutes_ord, deciminutes_ord):
	seconds, deciseconds, minutes, deciminutes, colon = "", "", "", "", ":"
	try: seconds = str(score_digits.index(seconds_ord))
	except: pass
	try: deciseconds = str(score_digits_100s.index(deciseconds_ord))
	except: pass
	try: 
		deciseconds = str(score_digits.index(deciseconds_ord))
		colon = '.'
	except: pass
	try: minutes = str(score_digits_100s.index(minutes_ord))
	except: pass
	try: deciminutes = str(score_digits.index(deciminutes_ord))
	except: pass

	return deciminutes + minutes + colon + deciseconds + seconds

def returnShotClock(seconds_ord):
	return str(seconds_ord)

while True:
		line = serial_port.readline(0xA0)
		line = str(line.rstrip('\r\n')) # Remove newline, ensure string data type

		if len(line):
			print len(line), line

		if len(line) == 25:
			#print line
			ascii_to_int = [""] * 100 # Holds ord() of all incoming bytes
			for x, char in enumerate(line):
				ascii_to_int[x] = ord(char)


			print "GAME TIME: " + returnGameTime(ascii_to_int[8], ascii_to_int[9], ascii_to_int[10], ascii_to_int[11])
			print "SHOT CLOCK: " + returnShotClock(ascii_to_int[23])
			print "QUARTER: " + returnQuarter(ascii_to_int[14], ascii_to_int[15])
			print "POSESSION: " + returnPosession(ascii_to_int[16])
			print ""
			print "GUEST: " + returnTeamScore(ascii_to_int[5], ascii_to_int[4])
			print "GUEST FOULS: " + returnFouls(ascii_to_int[20])
			print ""
			print "HOME: " + returnTeamScore(ascii_to_int[7], ascii_to_int[6])
			print "HOME FOULS: " + returnFouls(ascii_to_int[21])
			print ""
			print "\n\n\n\n\n\n\n\n\n\n\n"


			#print "GAME TIME: " + returnGameTime(ascii_to_int[15], ascii_to_int[16], ascii_to_int[17], ascii_to_int[18])
			#print "SHOT CLOCK: " + returnShotClock(ascii_to_int[30])
			#print "QUARTER: " + returnQuarter(ascii_to_int[21], ascii_to_int[22])
			#print "POSESSION: " + returnPosession(ascii_to_int[23])
			##print ""
			#print "GUEST: " + returnTeamScore(ascii_to_int[12], ascii_to_int[11])
			#print "GUEST FOULS: " + returnFouls(ascii_to_int[27])
			##print ""
			#print "HOME: " + returnTeamScore(ascii_to_int[14], ascii_to_int[13])
			#print "HOME FOULS: " + returnFouls(ascii_to_int[28])
			#print ""
			#print "\n\n\n\n\n\n\n\n\n\n\n"

