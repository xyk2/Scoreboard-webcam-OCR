import numpy
from cv2 import *
import time
import psutil
import subprocess 
import os

mouse_coordinates = [0, 0]

coord_home_score = [(0, 0), (0, 0)]
coord_away_score = [(0, 0), (0, 0)]

CACHE_IMAGE_FILENAME = 'filename.jpg'
SSOCR_PATH = os.path.abspath(os.path.dirname(__file__)) + '/ssocr'
CACHE_IMAGE_PATH = os.path.abspath(os.path.dirname(__file__)) + '/' + CACHE_IMAGE_FILENAME

print SSOCR_PATH
print CACHE_IMAGE_PATH

def mouse_hover_coordinates(event, x, y, flags, param):
	# grab references to the global variables
	global mouse_coordinates

	if event == EVENT_MOUSEMOVE:
		mouse_coordinates = [x, y]
 



# initialize the camera
cam = VideoCapture(0)   # 0 -> index of camera

print cam.get(cv.CV_CAP_PROP_FRAME_WIDTH), cam.get(cv.CV_CAP_PROP_FRAME_HEIGHT)

namedWindow("image", CV_WINDOW_AUTOSIZE)
setMouseCallback("image", mouse_hover_coordinates)

while True:
	img = imread('tpe_gym_test_2.jpg')
	success = True

	#success, img = cam.read()

	if success: # frame captured without any errors
		rectangle(img, (0, 0), (90, 35), (0,0,0), -1)
		putText(img, "X = "+ str(mouse_coordinates[0]), (10, 15), FONT_ITALIC, 0.5, (255,255,255))
		putText(img, "Y = "+ str(mouse_coordinates[1]), (10, 30), FONT_ITALIC, 0.5, (255,255,255))

		imshow("image", img)
		imwrite(CACHE_IMAGE_FILENAME, img) 
		waitKey(50)



		_command = SSOCR_PATH + ' gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 ' + CACHE_IMAGE_PATH + ' -D -d -1'
		procA = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
		_command = SSOCR_PATH + ' gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 ' + CACHE_IMAGE_PATH + ' -D -d -1'
		procB = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
		_command = SSOCR_PATH + ' gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 ' + CACHE_IMAGE_PATH + ' -D -d -1'
		procC = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
		_command = SSOCR_PATH + ' gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 ' + CACHE_IMAGE_PATH + ' -D -d -1'
		procD = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
		_command = SSOCR_PATH + ' gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 ' + CACHE_IMAGE_PATH + ' -D -d -1'
		procE = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
		_command = SSOCR_PATH + ' gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 ' + CACHE_IMAGE_PATH + ' -D -d -1'
		procF = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)

		tmp = procA.stdout.read()
 		print tmp
		tmp = procB.stdout.read()
 		print tmp
		tmp = procC.stdout.read()
 		print tmp
		tmp = procD.stdout.read()
 		print tmp
		tmp = procE.stdout.read()
 		print tmp
		tmp = procF.stdout.read()
 		print tmp


		#testbild = imread('testbild.png') # Show processed debug image by ssocr
		#imshow("image", testbild)

 		print "CPU %: " + str(psutil.cpu_percent())
 		#print tmp


