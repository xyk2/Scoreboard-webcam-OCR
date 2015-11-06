from cv2 import *
import numpy
import time

namedWindow("Shot Clock OCR Webcam", CV_WINDOW_AUTOSIZE)
namedWindow("Processed", CV_WINDOW_AUTOSIZE)
image = imread('test_images/HDMI_UVC_2.png')
imshow("Shot Clock OCR Webcam", image)


def shiftImage(img, x, y):
	_img = img
	if(x >= 0):
		_img = _img[0:_img.shape[0], x:_img.shape[1]]
	else:
		_img = copyMakeBorder(_img,0,0,abs(x),0,BORDER_CONSTANT, value=[255,255,255])
	if(y >= 0):
		_img = _img[y:_img.shape[0], 0:_img.shape[1]]
	else:
		_img = copyMakeBorder(_img,abs(y),0,0,0,BORDER_CONSTANT, value=[255,255,255])
	return _img



image_out = None
image_out = cvtColor(image, COLOR_BGR2HSV)

rows,cols,_ = image_out.shape
M = getRotationMatrix2D((cols/2,rows/2), -2.444, 1)
image_out = warpAffine(image_out, M, (cols,rows))

threshA = inRange(image_out, (20, 40, 40), (40, 255, 255))
threshB = inRange(image_out, (170, 60, 60), (180, 255, 255))
threshC = inRange(image_out, (0, 60, 60), (10, 255, 255))
th3 = threshA + threshB + threshC
ret3, th3 = threshold(th3, 127, 255, THRESH_BINARY_INV)
img_processed = erode(th3, numpy.ones((2,2),numpy.uint8), iterations = 4)

img_processed = shiftImage(img_processed, 0, -100)

imshow("Processed", img_processed)

waitKey(0)

