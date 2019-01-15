# What does this do?
This decodes .SC2Replay files for the game Parasite Zeta so that you may quickly extract a list of events without going through SC2's Replay. It can currently output the following:
* Player karma / games played / handles
* Assignments of Alien Host / Android / Psion
* Explosions
* Explosions near gas tanks on levels 1-6
* Items used near gas tank
* Remote mine placement / despawns (explosion or defused)
* Vent radiator destroyed (cannot track who destroyed it)
* Crab infest target and source
* Player spawning
* Player death
* Player leaving the game


# Required Software
Python 2.7 with numpy (https://www.anaconda.com/download/)

s2protocol (https://github.com/Blizzard/s2protocol/)

sc2reader (https://github.com/ggtracker/sc2reader)


# Installation for Windows
### Python 2.7
Download and install Anaconda's Python 2.7. If you're not familiar with python, make sure to select "Add to Environment Variables" so python is easily accessible from command line.

Once Python 2.7 is installed, open windows start menu and type "Command Prompt" and open it. Then type in "python" and press enter to verify installation was successful.

### SC2ParasiteReplay Decoder
Download the files from this github and place them in a folder (where %YOURDIRECTORY% is replaced with your own directory location):
```python
%YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/main.bat
%YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/main.py
```
### s2protocol & sc2reader
Download s2protocol and sc2reader and place them in the same folder:
```python
%YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/s2protocol-master/...
%YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/sc2reader-upstream/...
```

Install s2protocol by opening "Command Prompt" and type in:
```python
cd %YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/s2protocol-master/
python %YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/s2protocol-master/setup.py install
```

Install s2reader by opening "Command Prompt" and type in:
```python
cd %YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/s2protocol-master/
python %YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/s2protocol-master/setup.py install
```
### Installation/Usage Video
https://streamable.com/w44db



# Usage
### Bat File
Drag a .SC2Replay file over main.bat and it will automatically open a Command Prompt window, process the replay, and output results in the window.

### Command Line
Open a "Command Prompt" window and type in:
```python
cd %YOURDIRECTORY%/SC2ParasiteReplayDecoder-master
python main.py "PATHTOREPLAYFILE.SC2Replay"
```
