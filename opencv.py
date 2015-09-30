from cv2 import *
import time
import psutil
import subprocess 
import os

refPtA = (0,0)
refPtB = (0,0)
cropping = False
mouse_coordinates = [0, 0]

coord_home_score = [(0, 0), (0, 0)]
coord_away_score = [(0, 0), (0, 0)]

CACHE_IMAGE_FILENAME = 'filename.jpg'
SSOCR_PATH = os.path.abspath(os.path.dirname(__file__)) + '/ssocr'
CACHE_IMAGE_PATH = os.path.abspath(os.path.dirname(__file__)) + '/' + CACHE_IMAGE_FILENAME

print SSOCR_PATH
print CACHE_IMAGE_PATH

def click_and_crop(event, x, y, flags, param):
	# grab references to the global variables
	global refPtA, refPtB, cropping, mouse_coordinates
 
	# if the left mouse button was clicked, record the starting
	# (x, y) coordinates and indicate that cropping is being
	# performed
	if event == EVENT_MOUSEMOVE:
		mouse_coordinates = [x, y]

	if event == EVENT_LBUTTONDOWN:
		refPtA = (x, y)
		cropping = True
 
	# check to see if the left mouse button was released
	elif event == EVENT_LBUTTONUP:
		# record the ending (x, y) coordinates and indicate that
		# the cropping operation is finished
		refPtB = (x, y)
		cropping = False
 



# initialize the camera
cam = VideoCapture(0)   # 0 -> index of camera

print cam.get(cv.CV_CAP_PROP_FRAME_WIDTH), cam.get(cv.CV_CAP_PROP_FRAME_HEIGHT)

cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 640)
cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 360)

namedWindow("image", CV_WINDOW_AUTOSIZE)
setMouseCallback("image", click_and_crop)

while True:
	img = imread('flintridge_test.jpg')
	success = True

	#success, img = cam.read()

	if success: # frame captured without any errors
		rectangle(img, (0, 0), (90, 35), (0,0,0), -1)
		putText(img, "X = "+ str(mouse_coordinates[0]), (10, 15), FONT_ITALIC, 0.5, (255,255,255))
		putText(img, "Y = "+ str(mouse_coordinates[1]), (10, 30), FONT_ITALIC, 0.5, (255,255,255))

		imshow("image", img)
		imwrite(CACHE_IMAGE_FILENAME, img) 
		waitKey(100)

		_command = SSOCR_PATH + ' grayscale r_threshold invert remove_isolated crop 202 80 95 43 ' + CACHE_IMAGE_PATH + ' -D -d -1'
		proc = subprocess.Popen(_command, stdout=subprocess.PIPE, shell=True)
		tmp = proc.stdout.read()

		#testbild = imread('testbild.png') # Show processed debug image by ssocr
		#imshow("image", testbild)




 		print "CPU %: " + str(psutil.cpu_percent())
 		print tmp


