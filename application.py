# coding: utf8

from PySide import QtCore, QtGui
from PySide.QtCore import *
from PySide.QtGui import *
import sys
import time

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory, listenWS
from twisted.internet import reactor
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

import json
import serial
import os
import urllib2
import webbrowser
import unicodecsv
import glob


GroupBoxStyleSheet = u"QGroupBox { border: 1px solid #AAAAAA;margin-top: 12px;} QGroupBox::title {top: -5px;left: 10px;}"

class Example(QtGui.QMainWindow):
	def __init__(self, parent=None):
		super(Example, self).__init__(parent)

		######## QSettings #########
		self.qsettings = QSettings('settings.ini', QSettings.IniFormat)
		self.qsettings.setFallbacksEnabled(False)

		######## ACTIONS ###########
		exitItem = QtGui.QAction('Exit', self)
		exitItem.setStatusTip('Exit application...')
		exitItem.triggered.connect(self.close)

		self.openChromaKeyDisplay = QtGui.QAction('Open Key Output for Vision Mixer', self)
		self.openChromaKeyDisplay.setStatusTip('Open chroma-key output display for the vision mixer...')
		self.openChromaKeyDisplay.triggered.connect(lambda: webbrowser.open_new("http://localhost:8080/"))
		######## END ACTIONS ###########


		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(self.openChromaKeyDisplay)
		fileMenu.addSeparator()
		fileMenu.addAction(exitItem)


		self.main_widget = Window(self)
		self.setCentralWidget(self.main_widget)
		self.statusBar()
		self.setWindowTitle('Basketball Scoreboard Control')
		#self.resize(700,750)
		self.resize(500,400)
		self.show()


class Window(QtGui.QWidget):
	def __init__(self, parent):
		super(Window, self).__init__(parent)
		grid = QtGui.QGridLayout()
		self.qsettings = QSettings('settings.ini', QSettings.IniFormat)
		self.qsettings.setFallbacksEnabled(False)

		self.reScanButton = QtGui.QPushButton("Re-Scan Serial Ports")
		self.connectButton = QtGui.QPushButton("Connect")
		self.connectButton.clicked.connect(lambda: self.init_SerialWorker())
		self.reScanButton.clicked.connect(self.scan)

		self.COMselector = QtGui.QComboBox(self)
		self.scan() # Populate COM selector

		self.updateScoreboard = QtGui.QPushButton("Update")
		self.updateScoreboard.clicked.connect(self.sendCommandToBrowser)

		self.teamAImagePath = QtGui.QLineEdit(u"")
		self.teamAColor = QtGui.QLineEdit(u"")
		self.teamASelector = QtGui.QComboBox(self)
		self.teamBImagePath = QtGui.QLineEdit(u"")
		self.teamBColor = QtGui.QLineEdit(u"")
		self.teamBSelector = QtGui.QComboBox(self)

		self.tickerRadioGroup = QtGui.QButtonGroup()
		self.tickerTextRadio = QtGui.QRadioButton("Text")
		self.tickerStatsRadio = QtGui.QRadioButton("Player Stats")
		self.tickerTextLineEdit = QtGui.QLineEdit(u"")
		self.tickerTeamSelector = QtGui.QComboBox(self)
		self.tickerPlayerSelector = QtGui.QComboBox(self)
		self.selectedPlayerMetadata = ''

		self.onAirStatsComboBoxes = [QtGui.QComboBox(self), QtGui.QComboBox(self), QtGui.QComboBox(self), QtGui.QComboBox(self), QtGui.QComboBox(self)]
		self.tickerTeamSelector.currentIndexChanged.connect(self.populatePlayersSelector)
		self.initializeStatisticsSelectors() # Populate self.tickerTeamSelector and self.onAirStatsComboBoxes

		grid.addWidget(self.createSerialConfigurationGroup(), 0, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createTeamNameGroup(), 2, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createTickerGraphicGroup(), 4, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createStatSelectorGroup(), 6, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.updateScoreboard, 8, 0, 1, 1) # MUST BE HERE, initializes all QObject lists
		self.init_WebSocketsWorker() # Start ws:// server at port 9000

		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(10)

		self.setLayout(grid)

	def sendCommandToBrowser(self):
		msg = {
			'ticker': '',
			'guest': { 'name': '',
						'imagePath': '',
						'color': ''
			},
			'home': { 'name': '',
						'imagePath': '',
						'color': ''
			}
		}

		msg['guest']['name'] = self.teamASelector.currentText()
		msg['guest']['imagePath'] = self.teamAImagePath.text()
		msg['guest']['color'] = self.teamAColor.text()
		msg['home']['name'] = self.teamBSelector.currentText()
		msg['home']['imagePath'] = self.teamBImagePath.text()
		msg['home']['color'] = self.teamBColor.text()


		if self.tickerRadioGroup.checkedId() == 0:
			msg["ticker"] = self.tickerTextLineEdit.text()

		if self.tickerRadioGroup.checkedId() == 1: # Player stats selected
			file_object = open('athlete_data.csv', 'rU')
			reader = unicodecsv.reader(file_object , delimiter=',', dialect='excel')

			statIndexes = []
			hrow = reader.next()

			for x, comboBox in enumerate(self.onAirStatsComboBoxes):
				try:
					index = hrow.index(self.onAirStatsComboBoxes[x].currentText())
				except ValueError: # No stat selected ("-")
					index = -1
				statIndexes.append({'index': index, 'statName': self.onAirStatsComboBoxes[x].currentText()})

			for row in reader:
				if(row[2] == self.tickerPlayerSelector.currentText()):
					for x in statIndexes:
						x["statText"] = row[x["index"]]

			msg["ticker"] = self.tickerTeamSelector.currentText() + " " + self.tickerPlayerSelector.currentText() + " - "
			for stat in statIndexes:
				if(stat["index"] != -1):
					msg["ticker"] += stat["statName"] + " " + stat["statText"] + " "

			file_object.close() # Close opened CSV file

		self.webSocketsWorker.send(json.dumps(msg));

	def initializeStatisticsSelectors(self):
		file_object = open('athlete_data.csv', 'rU')
		reader = unicodecsv.reader(file_object , delimiter=',', dialect='excel')
		hrow = reader.next()

		unique_teams = []
		for row in reader:
			try:
				unique_teams.index(row[1])
			except ValueError: # If error is raised, means its not in unique list
				unique_teams.append(row[1])
				self.tickerTeamSelector.addItem(row[1])
				self.teamASelector.addItem(row[1])
				self.teamBSelector.addItem(row[1])

		for x, comboBox in enumerate(self.onAirStatsComboBoxes):
			self.onAirStatsComboBoxes[x].addItem("-")


		for header in hrow: # For loop through column headers
			for x, comboBox in enumerate(self.onAirStatsComboBoxes):
				self.onAirStatsComboBoxes[x].addItem(header)



		file_object.close()

	def populatePlayersSelector(self):
		file_object = open('athlete_data.csv', 'rU')
		reader = unicodecsv.reader(file_object , delimiter=',', dialect='excel')
		hrow = reader.next()

		self.tickerPlayerSelector.clear() # Empty team ComboBox

		for row in reader:
			if(row[1] == self.tickerTeamSelector.currentText()):
				self.tickerPlayerSelector.addItem(row[2]) # Add name to player selector comboBox

		file_object.close()

	def scan(self): #scan for available ports. return a list of tuples (num, name)
		available = []

		ports = glob.glob('/dev/tty.*')

		for index, port in enumerate(ports):
		        try:
		            s = serial.Serial(port)
		            s.close()
		            available.append((index, port))
		        except (OSError, serial.SerialException):
		            pass

		self.COMselector.clear()
		for n,s in available:
			self.COMselector.addItem(s, n)

	def init_WebSocketsWorker(self):
		self.webSocketsWorker = WebSocketsWorker()
		self.webSocketsWorker.error.connect(self.close)
		self.webSocketsWorker.start()

	def init_SerialWorker(self):
		self.serialWorker = SerialWorker(self.COMselector.currentText(), "9600")
		self.serialWorker.error.connect(lambda: QtGui.QMessageBox.critical(self, "Serial Error", str("Serial connection error."), QtGui.QMessageBox.Abort))
		self.serialWorker.to_browser.connect(self.rx_to_browser)
		self.serialWorker.start()
		
	def rx_to_browser(self, data): # Send data to browser. Serial thread -> to_browser QSignal -> rx_to_browser()
		self.webSocketsWorker.send(data);

	def createSerialConfigurationGroup(self):
		groupBox = QtGui.QGroupBox("Serial Configuration")
		groupBox.setStyleSheet(GroupBoxStyleSheet)

		self.COMlabel = QtGui.QLabel("COM Port", self)
		self.COMlabel.setAlignment(QtCore.Qt.AlignRight)

		grid = QtGui.QGridLayout()
		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(10)
		grid.addWidget(self.COMlabel, 0, 1)
		grid.addWidget(self.COMselector, 0, 2)
		grid.addWidget(self.reScanButton, 3, 2)
		grid.addWidget(self.connectButton, 4, 2)

		groupBox.setLayout(grid)
		return groupBox

	def createTickerGraphicGroup(self):
		groupBox = QtGui.QGroupBox("Ticker")
		groupBox.setStyleSheet(GroupBoxStyleSheet)

		self.tickerRadioGroup.setExclusive(True)
		self.tickerRadioGroup.addButton(self.tickerTextRadio, 0)
		self.tickerRadioGroup.addButton(self.tickerStatsRadio, 1)
		self.tickerRadioGroup.button(0).setChecked(True)

		grid = QtGui.QGridLayout()
		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(10)
		grid.addWidget(self.tickerTextRadio, 0, 0)
		grid.addWidget(self.tickerTextLineEdit, 1, 0, 1, 2)
		grid.addWidget(self.tickerStatsRadio, 2, 0)
		grid.addWidget(self.tickerTeamSelector, 3, 0)
		grid.addWidget(self.tickerPlayerSelector, 3, 1)

		groupBox.setLayout(grid)
		return groupBox

	def createStatSelectorGroup(self):
		groupBox = QtGui.QGroupBox("On Air Statistics")
		groupBox.setStyleSheet(GroupBoxStyleSheet)

		grid = QtGui.QGridLayout()
		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(10)

		for x, comboBox in enumerate(self.onAirStatsComboBoxes):
			grid.addWidget(QtGui.QLabel(str(x+1) + ":"), x, 0)
			grid.addWidget(self.onAirStatsComboBoxes[x], x, 1)

		grid.setColumnStretch(0,5)
		grid.setColumnStretch(1,100)
		groupBox.setLayout(grid)
		return groupBox


	def createTeamNameGroup(self):
		groupBox = QtGui.QGroupBox("Teams")
		groupBox.setStyleSheet(GroupBoxStyleSheet)

		grid = QtGui.QGridLayout()
		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(10)

		grid.addWidget(QtGui.QLabel("Image URL"), 0, 2)
		grid.addWidget(QtGui.QLabel("Color #Hex "), 0, 3)
		grid.addWidget(QtGui.QLabel("Team A: "), 1, 0)
		grid.addWidget(self.teamASelector, 1, 1)
		grid.addWidget(self.teamAImagePath, 1, 2)
		grid.addWidget(self.teamAColor, 1, 3)
		grid.addWidget(QtGui.QLabel("Team B"), 2, 0)
		grid.addWidget(self.teamBSelector, 2, 1)
		grid.addWidget(self.teamBImagePath, 2, 2)
		grid.addWidget(self.teamBColor, 2, 3)

		grid.setColumnStretch(0,5)
		grid.setColumnStretch(1,100)
		groupBox.setLayout(grid)
		return groupBox






class WebSocketsWorker(QtCore.QThread):
	updateProgress = QtCore.Signal(list)
	error = QtCore.Signal(str)
	socket_opened = QtCore.Signal(int)

	class BroadcastServerProtocol(WebSocketServerProtocol):
		def onOpen(self):
			self.factory.register(self)

		def onMessage(self, payload, isBinary):
			if not isBinary:
				msg = "{} from {}".format(payload.decode('utf8'), self.peer)
				self.factory.broadcast(msg)

		def connectionLost(self, reason):
			WebSocketServerProtocol.connectionLost(self, reason)
			self.factory.unregister(self)

	class BroadcastServerFactory(WebSocketServerFactory):
		def __init__(self, url, debug=False, debugCodePaths=False):
			WebSocketServerFactory.__init__(self, url, debug=debug, debugCodePaths=debugCodePaths)
			self.clients = []
			self.tickcount = 0
			#self.tick()

		def tick(self):
			self.tickcount += 1
			self.broadcast("tick %d from server" % self.tickcount)
			reactor.callLater(0.5, self.tick)

		def register(self, client):
			if client not in self.clients:
				print("registered client {}".format(client.peer))
				self.clients.append(client)

		def unregister(self, client):
			if client in self.clients:
				print("unregistered client {}".format(client.peer))
				self.clients.remove(client)

		def broadcast(self, msg):
			#print("broadcasting message '{}' ..".format(msg))
			for c in self.clients:
				c.sendMessage(msg.encode('utf8'))
				#print("message {} sent to {}".format(msg, c.peer))

		def returnClients(self):
			return
			#for c in self.clients:
				#print(c.peer)


	def __init__(self):
		QtCore.QThread.__init__(self)
		self.factory = self.BroadcastServerFactory("ws://localhost:9000", debug=False, debugCodePaths=False)

	def run(self):
		self.factory.protocol = self.BroadcastServerProtocol
		try:
			listenWS(self.factory)
		except:
			self.error.emit("Fail")
		webdir = File(".")
		webdir.indexNames = ['index.php', 'index.html']
		web = Site(webdir)
		try:
			reactor.listenTCP(8080, web)
			self.socket_opened.emit(1)
		except: 
			self.error.emit("Fail")
		reactor.run(installSignalHandlers=0)

	def send(self, data):
		reactor.callFromThread(self.factory.broadcast, data)
		self.updateProgress.emit([self.factory.returnClients()])

class SerialWorker(QtCore.QThread):
	success = QtCore.Signal(int)
	to_browser = QtCore.Signal(str)
	error = QtCore.Signal(str)

	def __init__(self, port_num, port_baud, port_stopbits = serial.STOPBITS_ONE, port_parity = serial.PARITY_NONE):
		QtCore.QThread.__init__(self)

		self.serial_port = None
		self.serial_arg  = dict(port = port_num, baudrate = port_baud, stopbits = port_stopbits, parity = port_parity, timeout  = None)
		self.score_digits = [63, 6, 91, 79, 102, 109, 125, 7, 127, 103]
		self.score_digits_100s = [191, 134, 219, 207, 230, 237, 253, 135, 255, 231] # Indexes for >99 score


	def run(self):
		try: 
			self.serial_port = serial.Serial(**self.serial_arg) # Open serial port with given arguments
			self.success.emit(True)
			print "Successfully connected to COM port."
		except serial.SerialException, e:
			self.error.emit(True)
			print e.message
			return

		while True:
			try:
				line = self.serial_port.readline() # Emit error if cannot read from device anymore; means disconnection
				line = str(line.rstrip('\r\n')) # Remove newline, ensure string data type
			except: 
				self.error.emit(True)

			if len(line):
				print len(line), line
				
			if (len(line) == 30) or (len(line) == 25):
				#print line
				ascii_to_int = [""] * 100 # Holds ord() of all incoming bytes
				for x, char in enumerate(line):
					ascii_to_int[x] = ord(char)

				msg_game = {
					"clock": self.returnGameTime(ascii_to_int[8], ascii_to_int[9], ascii_to_int[10], ascii_to_int[11]),
					"shot_clock": self.returnShotClock(ascii_to_int[23]),
					"quarter": self.returnQuarter(ascii_to_int[14], ascii_to_int[15]),
					"possesion": self.returnPosession(ascii_to_int[16])
				}
				msg_guest = {
					"score": self.returnTeamScore(ascii_to_int[5], ascii_to_int[4]),
					"fouls": self.returnFouls(ascii_to_int[20])
				}
				msg_home = {
					"score": self.returnTeamScore(ascii_to_int[7], ascii_to_int[6]),
					"fouls": self.returnFouls(ascii_to_int[21])
				}

				packet = {
					"game": msg_game,
					"guest": msg_guest,
					"home": msg_home
				}

			#	self.to_browser.emit(packet)
				self.to_browser.emit(json.dumps(packet))

				print "GAME TIME: " + self.returnGameTime(ascii_to_int[8], ascii_to_int[9], ascii_to_int[10], ascii_to_int[11])
				print "SHOT CLOCK: " + self.returnShotClock(ascii_to_int[23])
				print "QUARTER: " + self.returnQuarter(ascii_to_int[14], ascii_to_int[15])
				print "POSESSION: " + self.returnPosession(ascii_to_int[16])
				print ""
				print "GUEST: " + self.returnTeamScore(ascii_to_int[5], ascii_to_int[4])
				print "GUEST FOULS: " + self.returnFouls(ascii_to_int[20])
				print ""
				print "HOME: " + self.returnTeamScore(ascii_to_int[7], ascii_to_int[6])
				print "HOME FOULS: " + self.returnFouls(ascii_to_int[21])
				print ""
				print "\n\n\n\n\n\n\n\n\n\n\n"



	def returnTeamScore(self, ord1, ord2):
		digit1, digit2, hundreds = "", "", ""
		try: digit1 = str(self.score_digits.index(ord1))
		except: pass
		try: digit2 = str(self.score_digits.index(ord2))
		except: pass

		try: # Do 100s anyway as it will escape out if its <99. <99 will pass both these statements
			digit1 = str(self.score_digits_100s.index(ord1))
			hundreds = "1" 
		except: pass
		try: digit2 = str(self.score_digits_100s.index(ord2))
		except: pass

		return hundreds + digit1 + digit2

	def returnFouls(self, ord1):
		return str(int(ord1) - 48) # Fouls are direct, if ASCII byte = 0 then fouls = 0

	def returnQuarter(self, ord1, ord2):
		return str(int(ord1) + int(ord2) - 48 - 48) # ord1 + ord2 is the current quarter

	def returnPosession(self, ord1):
		if(ord1 == 50): return "HOME"
		if(ord1 == 52): return "GUEST"
		return ""

	def returnGameTime(self, seconds_ord, deciseconds_ord, minutes_ord, deciminutes_ord):
		seconds, deciseconds, minutes, deciminutes, colon = "", "", "", "", ":"
		try: seconds = str(self.score_digits.index(seconds_ord))
		except: pass
		try: deciseconds = str(self.score_digits_100s.index(deciseconds_ord))
		except: pass
		try: 
			deciseconds = str(self.score_digits.index(deciseconds_ord))
			colon = '.'
		except: pass
		try: minutes = str(self.score_digits_100s.index(minutes_ord))
		except: pass
		try: deciminutes = str(self.score_digits.index(deciminutes_ord))
		except: pass

		return deciminutes + minutes + colon + deciseconds + seconds


	def returnShotClock(self, seconds_ord):
		return str(seconds_ord)


	def port_write(self, command):
		self.serial_port.write(command.encode())

	def port_close(self):
		self.serial_port.close()


if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	ex = Example()
	sys.exit(app.exec_())
