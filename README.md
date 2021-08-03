All of these scripts are written in Python3.5

```
cd ~/catkin_ws/src
git clone https://github.com/ROBOTIS-GIT/turtlebot3.git
cd ~/catkin_ws
catkin_make
python3 -m pip install nltk SpeechRecognition vosk PyAudio
```
then in command prompt, type python3 to open python3.5
```
>>> import nltk
>>> nltk.download('wordnet')
>>> nltk.download('punkt')
```

From this page https://alphacephei.com/vosk/models, download any english models you want and extract it, put in same directory with hrd and vosk.py, name the folder 'model'

First, setup both PC and turtlebot3, then bringup the robot(https://emanual.robotis.com/docs/en/platform/turtlebot3/quick-start/#pc-setup)

After that, Ctrl + Shift + T to open new tab
```
roslaunch turtlebot3_teleop turtlebot3_teleop_key.launch
```
Again, open another tab and go to directory that has the script ```hrd```
```
python3 hrd
```
