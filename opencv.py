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
cam = VideoCapture(1)   # 0 -> index of camera

print cam.get(cv.CV_CAP_PROP_FRAME_WIDTH), cam.get(cv.CV_CAP_PROP_FRAME_HEIGHT)



namedWindow("image", CV_WINDOW_AUTOSIZE)
setMouseCallback("image", mouse_hover_coordinates)

while True:
	#img = imread('flintridge_test.jpg')
	#success = True

	success, img = cam.read()

	if success: # frame captured without any errors
		rectangle(img, (0, 0), (90, 35), (0,0,0), -1)
		putText(img, "X = "+ str(mouse_coordinates[0]), (10, 15), FONT_ITALIC, 0.5, (255,255,255))
		putText(img, "Y = "+ str(mouse_coordinates[1]), (10, 30), FONT_ITALIC, 0.5, (255,255,255))

		imshow("image", img)
		imwrite(CACHE_IMAGE_FILENAME, img) 
		waitKey(100)

		_command = SSOCR_PATH + ' grayscale r_threshold invert remove_isolated crop 202 80 95 43 ' + CACHE_IMAGE_PATH + ' -D -d -1'
		#proc = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
		#tmp = proc.stdout.read()

		#testbild = imread('testbild.png') # Show processed debug image by ssocr
		#imshow("image", testbild)

 		#print "CPU %: " + str(psutil.cpu_percent())
 		#print tmp


