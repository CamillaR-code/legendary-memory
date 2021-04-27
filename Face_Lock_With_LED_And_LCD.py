
# import the necessary packages and local import
from imutils.video import VideoStream
from imutils.video import FPS
import face_recognition
import imutils
import pickle
import time
import cv2
import RPi.GPIO as GPIO
from gpiozero import LED
import lcd_prod as lcd

# set up of GPIO for Relay. Setwarnings are set to False to prevent warnings from popping up in terminal.
# setmode set to BCM; this uses the GPIO number, not the pin number on Raspberry Pi.
# GPIO.output state of relay set to LOW
RELAY = 26
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY, GPIO.OUT)
GPIO.output(RELAY,GPIO.LOW)

# set LEDs to GPIO 18 and 17. The led_1 (red) stayes on by default
led_1 = LED(18)
led_2 = LED(17)
led_1.on()


#Initialize 'currentname' to trigger only when a new person is identified.
currentname = "unknown"
#Determine faces from encodings.pickle file model created from training_model.py
encodingsP = "encodings.pickle"
#use this xml file
#https://github.com/opencv/opencv/blob/master/data/haarcascades/haarcascade_frontalface_default.xml
cascade = "haarcascade_frontalface_default.xml"

# load the known faces and embeddings along with OpenCV's Haar
# cascade for face detection
print("[INFO] loading encodings + face detector…")
data = pickle.loads(open(encodingsP, "rb").read())
detector = cv2.CascadeClassifier(cascade)

# initialize the video stream and allow the camera sensor to warm up
print("[INFO] starting video stream…")
vs = VideoStream(src=0).start()
#vs = VideoStream(usePiCamera=True).start()
time.sleep(2.0)

# start the FPS (Frames Per Second)counter
fps = FPS().start()

prevTime = 0
doorUnlock = False

# initialize lcd display and display "DOOR" one line 1 and "LOCKED" on line 2 on LCD screen
lcd.lcd_init()
lcd.display_message("DOOR", "LOCKED")

# loop over frames from the video file stream
while True:
	# grab the frame from the threaded video stream and resize it
	# to 500px (to speedup processing)
	frame = vs.read()
	frame = imutils.resize(frame, width=500)

	# convert the input frame from (1) BGR to grayscale (for face
	# detection) and (2) from BGR to RGB (for face recognition)
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

	# detect faces in the grayscale frame
	rects = detector.detectMultiScale(gray, scaleFactor=1.1,
		minNeighbors=5, minSize=(30, 30),
		flags=cv2.CASCADE_SCALE_IMAGE)

	# OpenCV returns bounding box coordinates in (x, y, w, h) order
	# but we need them in (top, right, bottom, left) order, so we
	# need to do a bit of reordering
	boxes = [(y, x + w, y + h, x) for (x, y, w, h) in rects]

	# compute the facial embeddings for each face bounding box
	encodings = face_recognition.face_encodings(rgb, boxes)
	names = []

	# loop over the facial embeddings
	for encoding in encodings:
		# attempt to match each face in the input image to our known
		# encodings
		matches = face_recognition.compare_faces(data["encodings"],
			encoding)
		name = "Unknown" #if face is not recognized, then print Unknown in terminal

		# check to see if we have found a match
		if True in matches:
			# find the indexes of all matched faces then initialize a
			# dictionary to count the total number of times each face
			# was matched
			matchedIdxs = [i for (i, b) in enumerate(matches) if b]
			counts = {}
			
			# call on lcd_prod.py and print message to lcd display
			# display "ACCESS" on line 1 and "GRANTED" on line 2 on LCD screen
			if doorUnlock == False:
				lcd.display_message("ACCESS", "GRANTED")
			
			# to unlock the door
			# switch off led_1 and switch on led_2
			# GPIO.output changes state of relay to HIGH
			led_1.off()
			led_2.on()
			GPIO.output(RELAY,GPIO.HIGH)
			prevTime = time.time()
			doorUnlock = True
			print("door unlocked") # printed in terminal
			
			

			# loop over the matched indexes and maintain a count for
			# each recognized face
			for i in matchedIdxs:
				name = data["names"][i]
				counts[name] = counts.get(name, 0) + 1

			# determine the recognized face with the largest number
			# of votes (note: in the event of an unlikely tie Python
			# will select first entry in the dictionary)
			name = max(counts, key=counts.get)

			#If someone in your dataset is identified, print their name in terminal
			if currentname != name:
				currentname = name
				print(currentname)

		# update the list of names
		names.append(name)
        
        #lock the door after 5 seconds
	# switch off led_2 (green) and switch on led_1 (red)
	# GPIO.output changes state of relay to LOW
	if doorUnlock == True and time.time() – prevTime > 5:
		doorUnlock = False
		led_2.off()
		led_1.on()
		GPIO.output(RELAY,GPIO.LOW)
		print("door lock") # printed in terminal
		
		
		# display "DOOR" on line 1 and "LOCKED" on line 2 on LCD screen
		lcd.display_message("DOOR", "LOCKED")
		

	# loop over the recognized faces
	for ((top, right, bottom, left), name) in zip(boxes, names):
		# draw the predicted face name on the image – color is in BGR
		cv2.rectangle(frame, (left, top), (right, bottom),
			(0, 255, 0), 2)
		y = top – 15 if top – 15 > 15 else top + 15
		cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
			.8, (255, 0, 0), 2)

	# display the image to our screen
	cv2.imshow("Facial Recognition is Running", frame)
	key = cv2.waitKey(1) & 0xFF

	# quit when 'q' key is pressed
	if key == ord("q"):
		break

	# update the FPS counter
	fps.update()

# stop the timer and display FPS information
fps.stop()
print("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
