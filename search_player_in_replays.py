import glob
import os
import sc2reader
import numpy as np

dir_sc2replays = raw_input('Please input directory containing Parasite .SC2Replay files:\n')
list_replays = sorted(glob.glob(os.path.join(dir_sc2replays,'P A R A S I T E*.SC2Replay')))
list_replays = list_replays + sorted(glob.glob(os.path.join(dir_sc2replays,'P_A_R_A_S_I_T_E*.SC2Replay')))
print('Found %d P A R A S I T E replay files...'%(len(list_replays)))

print('\n')
list_replay_idx = []
player_name = raw_input('Please enter the player name (case-insensitive) that you are searching for:\n')
print('\n')
print('Now searching replays for %s...'%(player_name))
for replay_num in range(len(list_replays)):
    if replay_num%100 == 0:
        print('Checking Replay #%d/%d'%(replay_num,len(list_replays)))
    try:
        replay = sc2reader.load_replay(list_replays[replay_num], load_level=2)
        list_players = replay.players
        idx = np.where([player_name.lower() in player.name.lower() for player in list_players])[0]
        if len(idx)>0:
            list_replay_idx.append(replay_num)
            print('Found %d replays so far'%(len(list_replay_idx)))
    except:
        pass
        
print('\n')
print('Replays with %s in them:'%(player_name))
for idx in list_replay_idx:
    print(list_replays[idx])