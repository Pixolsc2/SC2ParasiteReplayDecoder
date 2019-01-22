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

### Recently Added:
* Player role / color
* Android directive (good or evil)
* Module infestation
* Mass-Targetting (at least 4 players are targetted/un-targetted at bridge console)
* Turning Off Power Link




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

# Errors
### S2Protocol Errors
If you receive an error like this after a recent Starcraft 2 patch update:
```
Unsupported base build: 71663 (No module named protocol71663)
Traceback (most recent call last):
  File "main.py", line 549, in <module>
    main()
  File "main.py", line 486, in main
    subprocess.check_call(str_cmd_json, shell=True)
  File ".........\Anaconda2\lib\subprocess.py", line 186, in check_call
    raise CalledProcessError(retcode, cmd)
subprocess.CalledProcessError: Command 'python ".\s2protocol-master\s2protocol\s2_cli.py" --all --ndjson "P A R A S I T E - ZETA (1266).SC2Replay" > "tmp.ndjson"' returned non-zero exit status 1
```



Take note of the protocol number from the first line of error above:
```
protocol71663
```

Then check if there is a file named "protocol71663.py" at:
https://github.com/Blizzard/s2protocol/tree/master/s2protocol/versions

If it exists then download it and place it as follows:
```
%YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/s2protocol-master/s2protocol/versions/protocol71663.py
```

If Blizzard has not updated their protocol yet, you may attempt to remedy the situation by copying the latest version of the protocol file that exists and then renaming it, i.e. create a copy of:
```
%YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/s2protocol-master/s2protocol/versions/protocol71523.py
```
and rename it to:
```
%YOURDIRECTORY%/SC2ParasiteReplayDecoder-master/s2protocol-master/s2protocol/versions/protocol71663.py
```
