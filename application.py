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

import numpy
from cv2 import * # OpenCV imports
import psutil # CPU usage
import subprocess # ssocr command line calling
import re # Integers only from ssocr output


if getattr(sys, 'frozen', False):
    _applicationPath = os.path.dirname(sys.executable)
elif __file__:
    _applicationPath = os.path.dirname(__file__)

_settingsFilePath = os.path.join(_applicationPath, 'settings.ini')
_athleteDataFilePath = os.path.join(_applicationPath, 'athlete_data.csv')
_ssocrFilePath = os.path.join(_applicationPath, 'ssocr')
_cacheImageFilePath = os.path.join(_applicationPath, 'filename.jpg')

GroupBoxStyleSheet = u"QGroupBox { border: 1px solid #AAAAAA;margin-top: 12px;} QGroupBox::title {top: -5px;left: 10px;}"

class MainWindow(QtGui.QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)

		######## QSettings #########
		self.qsettings = QSettings(_settingsFilePath, QSettings.IniFormat)
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
		self.setWindowTitle('Basketball OCR and Scoreboard Control')
		self.resize(300,400)
		self.show()


class Window(QtGui.QWidget):
	def __init__(self, parent):
		super(Window, self).__init__(parent)
		grid = QtGui.QGridLayout()
		self.qsettings = QSettings(_settingsFilePath, QSettings.IniFormat)
		self.qsettings.setFallbacksEnabled(False)


		self.updateScoreboard = QtGui.QPushButton("Update")
		self.updateScoreboard.clicked.connect(self.sendCommandToBrowser)

		self.teamAImagePath = QtGui.QLineEdit(u"")
		self.teamAColor = QtGui.QLineEdit(u"")
		self.teamAName = QtGui.QLineEdit(u"")
		#self.teamASelector = QtGui.QComboBox(self)
		self.teamBImagePath = QtGui.QLineEdit(u"")
		self.teamBName = QtGui.QLineEdit(u"")
		self.teamBColor = QtGui.QLineEdit(u"")
		#self.teamBSelector = QtGui.QComboBox(self)

		self.tickerRadioGroup = QtGui.QButtonGroup()
		self.tickerTextRadio = QtGui.QRadioButton("Text")
		self.tickerStatsRadio = QtGui.QRadioButton("Player Stats")
		self.tickerTextLineEdit = QtGui.QLineEdit(u"")
		self.tickerTeamSelector = QtGui.QComboBox(self)
		self.tickerPlayerSelector = QtGui.QComboBox(self)
		self.selectedPlayerMetadata = ''


		self.OCRcoordinates = {
			"clock": [QtGui.QLabel("Clock"), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLabel("0"), QtGui.QLabel("0")],
			"shot_clock": [QtGui.QLabel("Shot Clock"), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLabel("0"), QtGui.QLabel("0")],
			"quarter": [QtGui.QLabel("Quarter"), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLabel("0"), QtGui.QLabel("0")],
			"home_score": [QtGui.QLabel("Home Score"), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLabel("0"), QtGui.QLabel("0")],
			"home_fouls": [QtGui.QLabel("Home Fouls"), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLabel("0"), QtGui.QLabel("0")],
			"away_score": [QtGui.QLabel("Away Score"), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLabel("0"), QtGui.QLabel("0")],
			"away_fouls": [QtGui.QLabel("Away Fouls"), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLineEdit(u""), QtGui.QLabel("0"), QtGui.QLabel("0")]
		}
		self.ssocrArguments = QtGui.QLineEdit(u"gray_stretch 190 254 invert remove_isolated crop")
		self.startOCRButton = QtGui.QPushButton("Start OCR")
		self.startOCRButton.clicked.connect(self.init_OCRWorker)
		self.terminateOCRButton = QtGui.QPushButton("Stop OCR")
		self.terminateOCRButton.clicked.connect(self.terminate_OCRWorker)

		self.onAirStatsComboBoxes = [QtGui.QComboBox(self), QtGui.QComboBox(self), QtGui.QComboBox(self), QtGui.QComboBox(self), QtGui.QComboBox(self)]
		self.tickerTeamSelector.currentIndexChanged.connect(self.populatePlayersSelector)
		self.initializeStatisticsSelectors() # Populate self.tickerTeamSelector and self.onAirStatsComboBoxes
		self.initializeOCRCoordinatesList()

		grid.addWidget(self.createTeamNameGroup(), 0, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createTickerGraphicGroup(), 2, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createStatSelectorGroup(), 4, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createOCRGroup(), 0, 1, 4, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createSSOCRGroup(), 4, 1, 1, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createOCRButtonGroup(), 5, 1, 1, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.updateScoreboard, 6, 0, 1, 1) # MUST BE HERE, initializes all QObject lists
		
		self.init_WebSocketsWorker() # Start ws:// server at port 9000
		#self.init_OCRWorker() # Start OpenCV, open webcam

		grid.setColumnStretch(0,5)
		grid.setColumnStretch(1,100)


		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(10)
		self.setLayout(grid)

	def initializeOCRCoordinatesList(self):
		loadedOCRCoordinates = self.qsettings.value("OCRcoordinates")

		for key, param in self.OCRcoordinates.iteritems():
			for index, qobj in enumerate(param):
				qobj.setText(loadedOCRCoordinates[key][index])

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

		#msg['guest']['name'] = self.teamASelector.currentText()
		msg['guest']['name'] = self.teamAName.text()
		msg['guest']['imagePath'] = self.teamAImagePath.text()
		msg['guest']['color'] = self.teamAColor.text()
		#msg['home']['name'] = self.teamBSelector.currentText()
		msg['home']['name'] = self.teamBName.text()
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

	def sendRealTimeCommandToBrowser(self, recognizedDigits):
		msg_game = {
			"clock": recognizedDigits['clock'],
			"shot_clock": '',
			"quarter": recognizedDigits['quarter'],
			"possesion": ''
		}
		msg_guest = {
			"score": recognizedDigits['away_score'],
			"fouls": recognizedDigits['away_fouls']
		}
		msg_home = {
			"score": recognizedDigits['home_score'],
			"fouls": recognizedDigits['home_fouls']
		}

		packet = {
			"game": msg_game,
			"guest": msg_guest,
			"home": msg_home
		}

		self.webSocketsWorker.send(json.dumps(packet))

	def initializeStatisticsSelectors(self):
		file_object = open(_athleteDataFilePath, 'rU')
		reader = unicodecsv.reader(file_object , delimiter=',', dialect='excel')
		hrow = reader.next()

		unique_teams = []
		for row in reader:
			try:
				unique_teams.index(row[1])
			except ValueError: # If error is raised, means its not in unique list
				unique_teams.append(row[1])
				self.tickerTeamSelector.addItem(row[1])
				#self.teamASelector.addItem(row[1])
				#self.teamBSelector.addItem(row[1])

		for x, comboBox in enumerate(self.onAirStatsComboBoxes):
			self.onAirStatsComboBoxes[x].addItem("-")


		for header in hrow: # For loop through column headers
			for x, comboBox in enumerate(self.onAirStatsComboBoxes):
				self.onAirStatsComboBoxes[x].addItem(header)



		file_object.close()

	def populatePlayersSelector(self):
		file_object = open(_athleteDataFilePath, 'rU')
		reader = unicodecsv.reader(file_object , delimiter=',', dialect='excel')
		hrow = reader.next()

		self.tickerPlayerSelector.clear() # Empty team ComboBox

		for row in reader:
			if(row[1] == self.tickerTeamSelector.currentText()):
				self.tickerPlayerSelector.addItem(row[2]) # Add name to player selector comboBox

		file_object.close()

	def init_WebSocketsWorker(self):
		self.webSocketsWorker = WebSocketsWorker()
		self.webSocketsWorker.error.connect(self.close)
		self.webSocketsWorker.start()# Call to start WebSockets server

	def init_OCRWorker(self):
		self.OCRWorker = OCRWorker(self.returnOCRCoordinatesList(), self.ssocrArguments.text())
		self.OCRWorker.error.connect(self.close)
		self.OCRWorker.recognizedDigits.connect(self.sendRealTimeCommandToBrowser)
		self.OCRWorker.start() # Call to start OCR openCV thread

	def returnOCRCoordinatesList(self): # Returns 1:1 copy of self.OCRcoordinates without QObjects
		response = {
			"clock": ["", "", "", "", "", "", ""],
			"shot_clock": ["", "", "", "", "", "", ""],
			"quarter": ["", "", "", "", "", "", ""],
			"home_score": ["", "", "", "", "", "", ""],
			"home_fouls": ["", "", "", "", "", "", ""],
			"away_score": ["", "", "", "", "", "", ""],
			"away_fouls": ["", "", "", "", "", "", ""]
		}
		for key, param in self.OCRcoordinates.iteritems():
			for index, qobj in enumerate(param):
				response[key][index] = qobj.text()

		return response

	def terminate_OCRWorker(self):
		self.OCRWorker.terminate()
		del(self.OCRWorker)
		
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
		grid.setVerticalSpacing(5)

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
		grid.setVerticalSpacing(5)

		grid.addWidget(QtGui.QLabel("Name"), 0, 1)
		grid.addWidget(QtGui.QLabel("Image URL"), 0, 2)
		grid.addWidget(QtGui.QLabel("Color #Hex "), 0, 3)
		grid.addWidget(QtGui.QLabel("Guest"), 1, 0)
		#grid.addWidget(self.teamASelector, 1, 1)
		grid.addWidget(self.teamAName, 1, 1)
		grid.addWidget(self.teamAImagePath, 1, 2)
		grid.addWidget(self.teamAColor, 1, 3)
		grid.addWidget(QtGui.QLabel("Home"), 2, 0)
		#grid.addWidget(self.teamBSelector, 2, 1)
		grid.addWidget(self.teamBName, 2, 1)
		grid.addWidget(self.teamBImagePath, 2, 2)
		grid.addWidget(self.teamBColor, 2, 3)

		grid.setColumnStretch(0,5)
		grid.setColumnStretch(1,100)
		groupBox.setLayout(grid)
		return groupBox

	def widthHeightAutoFiller(self): # Calculates width and height, then saves to settings.ini file
		for key, value in self.OCRcoordinates.iteritems():
			tl_X = int('0' + value[1].text()) # '0' to avoid int('') empty string error
			tl_Y = int('0' + value[2].text())
			br_X = int('0' + value[3].text())
			br_Y = int('0' + value[4].text())
			value[5].setText(str(br_X - tl_X))
			value[6].setText(str(br_Y - tl_Y))

		self.qsettings.setValue("OCRcoordinates", self.returnOCRCoordinatesList())

	def createOCRGroup(self):
		groupBox = QtGui.QGroupBox("OCR Coordinates")
		groupBox.setStyleSheet(GroupBoxStyleSheet)

		grid = QtGui.QGridLayout()
		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(5)


		# Select webcam dropdown
		# Start OCR, Stop OCR
		# Text box for ssocr command line arguments
		# CPU usage %, write bytes

		_tlLabel = QtGui.QLabel("Top-Left")
		_brLabel = QtGui.QLabel("Bottom-Right")
		_tlLabel.setAlignment(Qt.AlignCenter)
		_brLabel.setAlignment(Qt.AlignCenter)
		grid.addWidget(_tlLabel, 0, 1, 1, 2)
		grid.addWidget(_brLabel, 0, 3, 1, 2)

		grid.addWidget(QtGui.QLabel(""), 1, 0)
		grid.addWidget(QtGui.QLabel("X"), 1, 1)
		grid.addWidget(QtGui.QLabel("Y"), 1, 2)
		grid.addWidget(QtGui.QLabel("X"), 1, 3)
		grid.addWidget(QtGui.QLabel("Y"), 1, 4)
		grid.addWidget(QtGui.QLabel("Width"), 1, 5)
		grid.addWidget(QtGui.QLabel("Height"), 1,6)

		for key, param in self.OCRcoordinates.iteritems(): # Right justify parameter QLabels
			param[0].setAlignment(Qt.AlignRight)
			param[1].setValidator(QIntValidator()) # Require integer pixel input
			param[2].setValidator(QIntValidator())
			param[3].setValidator(QIntValidator())
			param[4].setValidator(QIntValidator())
			param[1].setMaxLength(3) # Set 3 digit maximum for pixel coordinates
			param[2].setMaxLength(3)
			param[3].setMaxLength(3)
			param[4].setMaxLength(3)
			param[1].editingFinished.connect(self.widthHeightAutoFiller) # On change in X or Y, update width + height
			param[2].editingFinished.connect(self.widthHeightAutoFiller)
			param[3].editingFinished.connect(self.widthHeightAutoFiller)
			param[4].editingFinished.connect(self.widthHeightAutoFiller)
			param[5].setAlignment(Qt.AlignCenter)
			param[6].setAlignment(Qt.AlignCenter)



		for index, qobj in enumerate(self.OCRcoordinates["clock"]):
			grid.addWidget(qobj, 2, index)

		for index, qobj in enumerate(self.OCRcoordinates["shot_clock"]):
			grid.addWidget(qobj, 3, index)

		for index, qobj in enumerate(self.OCRcoordinates["quarter"]):
			grid.addWidget(qobj, 4, index)

		for index, qobj in enumerate(self.OCRcoordinates["home_score"]):
			grid.addWidget(qobj, 5, index)
		for index, qobj in enumerate(self.OCRcoordinates["home_fouls"]):
			grid.addWidget(qobj, 6, index)

		for index, qobj in enumerate(self.OCRcoordinates["away_score"]):
			grid.addWidget(qobj, 7, index)
		for index, qobj in enumerate(self.OCRcoordinates["away_fouls"]):
			grid.addWidget(qobj, 8, index)


		grid.setColumnMinimumWidth(1, 30)
		grid.setColumnMinimumWidth(2, 30)
		grid.setColumnMinimumWidth(3, 30)
		grid.setColumnMinimumWidth(4, 30)

		groupBox.setLayout(grid)
		return groupBox

	def createSSOCRGroup(self):
		groupBox = QtGui.QGroupBox("SSOCR Arguments")
		groupBox.setStyleSheet(GroupBoxStyleSheet)

		grid = QtGui.QGridLayout()
		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(5)

		grid.addWidget(self.ssocrArguments, 0, 0)

		groupBox.setLayout(grid)
		return groupBox

	def createOCRButtonGroup(self):
		groupBox = QtGui.QGroupBox("Start / Stop")
		groupBox.setStyleSheet(GroupBoxStyleSheet)

		grid = QtGui.QGridLayout()
		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(5)

		grid.addWidget(self.startOCRButton, 0, 0)
		grid.addWidget(self.terminateOCRButton, 0, 1)

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
		webdir = File(_applicationPath)
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

class OCRWorker(QtCore.QThread):
	error = QtCore.Signal(int)
	recognizedDigits = QtCore.Signal(dict)

	def __init__(self, OCRCoordinatesList, ssocrArguments):
		QtCore.QThread.__init__(self)

		self.ssocrArguments = ssocrArguments
		self.OCRCoordinatesList = OCRCoordinatesList

		self.mouse_coordinates = [0, 0]

		self.cam = None # VideoCapture object, created in run()

	def mouse_hover_coordinates(self, event, x, y, flags, param):
		if event == EVENT_MOUSEMOVE:
			self.mouse_coordinates = [x, y]

	def run(self):
		print "OCRWorker QThread successfully opened."
		print "ssocr path: " + _ssocrFilePath
		print "Cache image path: " + _cacheImageFilePath

		try:
			self.cam = VideoCapture(1)   # 0 -> index of camera
			#self.cam = VideoCapture('test_video.mov')   # 0 -> index of camera
			print "Webcam native resolution: ",
			print self.cam.get(cv.CV_CAP_PROP_FRAME_WIDTH), self.cam.get(cv.CV_CAP_PROP_FRAME_HEIGHT)

			self.cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 640)
			self.cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 360)

			namedWindow("OCR Webcam", CV_WINDOW_AUTOSIZE)
			setMouseCallback("OCR Webcam", self.mouse_hover_coordinates)

			while True:
				#img = imread('tpe_gym_test.jpg')
				#success = True

				success, img = self.cam.read()
				#img = flip(img, 1)


				if success:
					rectangle(img, (0, 0), (90, 35), (0,0,0), -1)
					putText(img, "X = "+ str(self.mouse_coordinates[0]), (10, 15), FONT_ITALIC, 0.5, (255,255,255))
					putText(img, "Y = "+ str(self.mouse_coordinates[1]), (10, 30), FONT_ITALIC, 0.5, (255,255,255))

					rectangle(img, (int('0' + self.OCRCoordinatesList["clock"][1]), int('0' + self.OCRCoordinatesList["clock"][2])), (int('0' + self.OCRCoordinatesList["clock"][3]), int('0' + self.OCRCoordinatesList["clock"][4])), (0,255,0), 1)
					rectangle(img, (int('0' + self.OCRCoordinatesList["quarter"][1]), int('0' + self.OCRCoordinatesList["quarter"][2])), (int('0' + self.OCRCoordinatesList["quarter"][3]), int('0' + self.OCRCoordinatesList["quarter"][4])), (0,255,0), 1)
					rectangle(img, (int('0' + self.OCRCoordinatesList["home_score"][1]), int('0' + self.OCRCoordinatesList["home_score"][2])), (int('0' + self.OCRCoordinatesList["home_score"][3]), int('0' + self.OCRCoordinatesList["home_score"][4])), (0,255,0), 1)
					rectangle(img, (int('0' + self.OCRCoordinatesList["home_fouls"][1]), int('0' + self.OCRCoordinatesList["home_fouls"][2])), (int('0' + self.OCRCoordinatesList["home_fouls"][3]), int('0' + self.OCRCoordinatesList["home_fouls"][4])), (0,255,0), 1)
					rectangle(img, (int('0' + self.OCRCoordinatesList["away_score"][1]), int('0' + self.OCRCoordinatesList["away_score"][2])), (int('0' + self.OCRCoordinatesList["away_score"][3]), int('0' + self.OCRCoordinatesList["away_score"][4])), (0,255,0), 1)
					rectangle(img, (int('0' + self.OCRCoordinatesList["away_fouls"][1]), int('0' + self.OCRCoordinatesList["away_fouls"][2])), (int('0' + self.OCRCoordinatesList["away_fouls"][3]), int('0' + self.OCRCoordinatesList["away_fouls"][4])), (0,255,0), 1)

					imshow("OCR Webcam", img)
					imwrite(_cacheImageFilePath, img) 
					waitKey(100)

					_command = _ssocrFilePath + ' ' + self.ssocrArguments + ' ' + self.OCRCoordinatesList["clock"][1] + ' ' + self.OCRCoordinatesList["clock"][2] + ' ' + self.OCRCoordinatesList["clock"][5] + ' ' + self.OCRCoordinatesList["clock"][6] + ' ' + _cacheImageFilePath + ' -D -d -1'
					procA = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
					_command = _ssocrFilePath + ' ' + self.ssocrArguments + ' ' + self.OCRCoordinatesList["quarter"][1] + ' ' + self.OCRCoordinatesList["quarter"][2] + ' ' + self.OCRCoordinatesList["quarter"][5] + ' ' + self.OCRCoordinatesList["quarter"][6] + ' ' + _cacheImageFilePath + ' -D -d -1'
					procB = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
					_command = _ssocrFilePath + ' ' + self.ssocrArguments + ' ' + self.OCRCoordinatesList["home_score"][1] + ' ' + self.OCRCoordinatesList["home_score"][2] + ' ' + self.OCRCoordinatesList["home_score"][5] + ' ' + self.OCRCoordinatesList["home_score"][6] + ' ' + _cacheImageFilePath + ' -D -d -1'
					procC = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
					_command = _ssocrFilePath + ' ' + self.ssocrArguments + ' ' + self.OCRCoordinatesList["home_fouls"][1] + ' ' + self.OCRCoordinatesList["home_fouls"][2] + ' ' + self.OCRCoordinatesList["home_fouls"][5] + ' ' + self.OCRCoordinatesList["home_fouls"][6] + ' ' + _cacheImageFilePath + ' -D -d -1'
					procD = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
					_command = _ssocrFilePath + ' ' + self.ssocrArguments + ' ' + self.OCRCoordinatesList["away_score"][1] + ' ' + self.OCRCoordinatesList["away_score"][2] + ' ' + self.OCRCoordinatesList["away_score"][5] + ' ' + self.OCRCoordinatesList["away_score"][6] + ' ' + _cacheImageFilePath + ' -D -d -1'
					procE = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
					_command = _ssocrFilePath + ' ' + self.ssocrArguments + ' ' + self.OCRCoordinatesList["away_fouls"][1] + ' ' + self.OCRCoordinatesList["away_fouls"][2] + ' ' + self.OCRCoordinatesList["away_fouls"][5] + ' ' + self.OCRCoordinatesList["away_fouls"][6] + ' ' + _cacheImageFilePath + ' -D -d -1'
					procF = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)

					clock = procA.stdout.read()
					quarter = procB.stdout.read()
					home_score = procC.stdout.read()
					home_fouls = procD.stdout.read()
					away_score = procE.stdout.read()
					away_fouls = procF.stdout.read()

					digits = { "clock": clock, "quarter": quarter, "home_score": home_score, "home_fouls": home_fouls, "away_score": away_score, "away_fouls": away_fouls }

					for key, value in digits.iteritems(): # Remove all non integer digits from ssocr output
						digits[key] = re.sub("[^0-9]", "", value)


					if(len(digits['clock']) == 5): # Clock filtering and validation
						digits['clock'] = digits['clock'][:2] + ':' + digits['clock'][3:]
					if(len(digits['clock']) == 4): 
						digits['clock'] = digits['clock'][:1] + ':' + digits['clock'][2:]

					for key, value in digits.iteritems():
						print key, value

			 		print "CPU %: " + str(psutil.cpu_percent())

			 		self.recognizedDigits.emit(digits)



		except:
			self.error.emit(1)






if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	ex = MainWindow()
	sys.exit(app.exec_())
