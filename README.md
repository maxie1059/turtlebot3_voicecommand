All of these scripts are written in Python3.5

python3 -m pip install nltk
python3 -m pip install SpeechRecognition
python3 -m pip install vosk
python3 -m pip install PyAudio

then in command prompt, type python3 to open python3.5
```
>>> import nltk
>>> nltk.download('wordnet')
```

From this page https://alphacephei.com/vosk/models, download any english models you want and extract it, put in same directory with hrd and vosk.py, name the folder 'model'

In command prompt, go to directory that has the script hrd, then python3 hrd
