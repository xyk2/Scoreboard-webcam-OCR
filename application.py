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


GroupBoxStyleSheet = u"QGroupBox { border: 1px solid #AAAAAA;margin-top: 12px;} QGroupBox::title {top: -5px;left: 10px;}"

class MainWindow(QtGui.QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)

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
		self.setWindowTitle('Basketball OCR and Scoreboard Control')
		self.resize(300,400)
		self.show()


class Window(QtGui.QWidget):
	def __init__(self, parent):
		super(Window, self).__init__(parent)
		grid = QtGui.QGridLayout()
		self.qsettings = QSettings('settings.ini', QSettings.IniFormat)
		self.qsettings.setFallbacksEnabled(False)


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

		grid.addWidget(self.createTeamNameGroup(), 0, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createTickerGraphicGroup(), 2, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createStatSelectorGroup(), 4, 0, 2, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.createOCRGroup(), 0, 1, 6, 1) # MUST BE HERE, initializes all QObject lists
		grid.addWidget(self.updateScoreboard, 6, 0, 1, 1) # MUST BE HERE, initializes all QObject lists
		
		self.init_WebSocketsWorker() # Start ws:// server at port 9000
		#self.init_OCRWorker() # Start OpenCV, open webcam

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

	def init_WebSocketsWorker(self):
		self.webSocketsWorker = WebSocketsWorker()
		self.webSocketsWorker.error.connect(self.close)
		self.webSocketsWorker.start()

	def init_OCRWorker(self):
		self.OCRWorker = OCRWorker()
		self.OCRWorker.error.connect(self.close)
		self.OCRWorker.start()
		
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

	def createOCRGroup(self):
		groupBox = QtGui.QGroupBox("Scoreboard OCR")
		groupBox.setStyleSheet(GroupBoxStyleSheet)

		# Select webcam dropdown
		# Start OCR, Stop OCR
		# XY values for each digit (Top Left, Bottom Right)
		# Text box for ssocr command line arguments
		# CPU usage %, write bytes



		grid = QtGui.QGridLayout()
		grid.setHorizontalSpacing(10)
		grid.setVerticalSpacing(10)

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



class OCRWorker(QtCore.QThread):
	error = QtCore.Signal(int)

	def __init__(self):
		QtCore.QThread.__init__(self)

		self._CACHE_IMAGE_FILENAME = 'filename.jpg'
		self._SSOCR_PATH = os.path.abspath(os.path.dirname(__file__)) + '/ssocr'
		self._CACHE_IMAGE_PATH = os.path.abspath(os.path.dirname(__file__)) + '/' + self._CACHE_IMAGE_FILENAME
		self.mouse_coordinates = [0, 0]

		self.cam = None # VideoCapture object, created in run()

	def mouse_hover_coordinates(self, event, x, y, flags, param):
		if event == EVENT_MOUSEMOVE:
			self.mouse_coordinates = [x, y]

	def run(self):
		print "OCRWorker QThread successfully opened."
		print "ssocr path: " + self._SSOCR_PATH
		print "Cache image path: " + self._CACHE_IMAGE_PATH

		try:
			self.cam = VideoCapture(0)   # 0 -> index of camera
			print self.cam.get(cv.CV_CAP_PROP_FRAME_WIDTH), self.cam.get(cv.CV_CAP_PROP_FRAME_HEIGHT)

			self.cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 640)
			self.cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 360)

			namedWindow("image", CV_WINDOW_AUTOSIZE)
			setMouseCallback("image", self.mouse_hover_coordinates)

			while True:
				#img = imread('flintridge_test.jpg')
				#success = True

				success, img = self.cam.read()

				if success: # frame captured without any errors
					rectangle(img, (0, 0), (90, 35), (0,0,0), -1)
					putText(img, "X = "+ str(self.mouse_coordinates[0]), (10, 15), FONT_ITALIC, 0.5, (255,255,255))
					putText(img, "Y = "+ str(self.mouse_coordinates[1]), (10, 30), FONT_ITALIC, 0.5, (255,255,255))

					imshow("image", img)
					imwrite(self._CACHE_IMAGE_FILENAME, img) 
					waitKey(100)

					_command = self._SSOCR_PATH + ' grayscale r_threshold invert remove_isolated crop 202 80 95 43 ' + self._CACHE_IMAGE_PATH + ' -D -d -1'
					proc = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
					tmp = proc.stdout.read()

					#testbild = imread('testbild.png') # Show processed debug image by ssocr
					#imshow("image", testbild)

			 		print "CPU %: " + str(psutil.cpu_percent())
			 		print tmp



		except:
			self.error.emit(1)










if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	ex = MainWindow()
	sys.exit(app.exec_())
