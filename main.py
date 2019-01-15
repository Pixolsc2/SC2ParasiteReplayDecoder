import sc2reader
import numpy as np
import subprocess
import json
import sys

def get_bank_info(data_json_):
    list_player_karma_ = ['N/A']*12
    list_player_games_ = ['N/A']*12
    for datum in data_json_:
        # karma
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Game.SBankKeyEvent' and 'm_name' in datum.keys() and datum['m_name'] == 'K':
            user_id = datum['_userid']['m_userId']
            user_val = datum['m_data']
            list_player_karma_[user_id] = user_val

        # games played
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Game.SBankKeyEvent' and 'm_name' in datum.keys() and datum['m_name'] == 'GamesPlayed':
            user_id = datum['_userid']['m_userId']
            user_val = datum['m_data']
            list_player_games_[user_id] = user_val
    return list_player_karma_, list_player_games_




def get_game_events(data_json_,list_player_name):
    output = []
    death_tracker = [None] * 12
    remotemine_id_tracker = []
    remotemine_owner_tracker = []
    debri_fire_tracker = []
    tank_tracker = []
    tank_loc_ptcoord = [[926406., 201907.], [829717., 960161.], [814268., 689009.], [940391., 321852.],
                        [880390., 490999.], [944118., 837361.]]  # y,x
    tank_loc_blkcoord = [[221.3, 48.4], [204.0, 232.3], [196.6, 169.9], [232.4, 77.0], [214.9, 115.7],
                         [231.2, 203.5]]  # y,x

    def check_dist(yx1, yx2):
        return np.sqrt(np.square(yx1[0] - yx2[0]) + np.square(yx1[1] - yx2[1]))

    for datum in data_json_:
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Replay.Tracker.SUnitBornEvent' and datum[
            'm_unitTypeName'] == 'Marine':
            # print(datum['m_upkeepPlayerId'])
            # print(datum['m_unitTagIndex'])
            death_tracker[datum['m_upkeepPlayerId'] - 1] = datum['m_unitTagIndex']

        # track item use near gas tanks
        if 'm_abil' in datum.keys() and datum['m_abil'] and 'm_abilLink' in datum['m_abil'].keys() and datum['m_abil'][
            'm_abilLink'] == 528 and datum['m_abil']['m_abilCmdIndex'] == 4:
            id_src = datum['_userid']['m_userId']  # for some reason, this one is already 0-based.
            name_src = list_player_name[id_src] + ' (#%02d)'%(1+id_src)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']

            if 'TargetPoint' in datum['m_data'].keys():
                ability_loc = [datum['m_data']['TargetPoint']['y'], datum['m_data']['TargetPoint']['x']]
            elif 'TargetUnit' in datum['m_data'].keys() and 'm_snapshotPoint' in datum['m_data']['TargetUnit'].keys():
                ability_loc = [datum['m_data']['TargetUnit']['m_snapshotPoint']['y'],
                               datum['m_data']['TargetUnit']['m_snapshotPoint']['x']]

            if ability_loc:
                for tank_num in range(len(tank_loc_ptcoord)):
                    if check_dist(ability_loc, tank_loc_ptcoord[tank_num]) <= 20000:
                        output.append([time_gameloop, '[%02d:%02d] %s used an item near gas tank #%d' % (
                        time_min, time_sec, name_src, tank_num + 1)])
                        break

        # Track remote mine placements
        if '_event' in datum.keys() and datum[
            '_event'] == "NNet.Replay.Tracker.SUnitBornEvent" and 'm_creatorAbilityName' in datum.keys() and datum[
            'm_creatorAbilityName'] == 'BuildAutoTurret2' and 'm_unitTypeName' in datum.keys() and datum[
            'm_unitTypeName'] == 'WidowMineBurrowed2':
            id_dst = datum['m_controlPlayerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            remotemine_id_tracker.append(datum['m_unitTagIndex'])
            remotemine_owner_tracker.append(id_dst)
            output.append([time_gameloop, '[%02d:%02d] %s placed a remote mine' % (time_min, time_sec, name_dst)])
            # print(remotemine_id_tracker)
            # print(remotemine_owner_tracker)

        # Track remote mine detonations
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Replay.Tracker.SUnitDiedEvent':
            if datum['m_unitTagIndex'] in remotemine_id_tracker:
                idx = np.where([datum['m_unitTagIndex'] == tracker_enum for tracker_enum in remotemine_id_tracker])[0][
                    0]
                # print(datum['m_unitTagIndex'])
                # print(idx)
                id_dst = remotemine_owner_tracker[idx]
                name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
                time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
                time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
                time_gameloop = datum['_gameloop']
                output.append([time_gameloop, '[%02d:%02d] %s\'s remote mine has been detonated/disarmed' % (
                time_min, time_sec, name_dst)])
                remotemine_id_tracker.pop(idx)
                remotemine_owner_tracker.pop(idx)
                # print(remotemine_id_tracker)
                # print(remotemine_owner_tracker)

        # Track debris from explosions
        if '_event' in datum.keys() and datum['_event'] == "NNet.Replay.Tracker.SUnitBornEvent" and datum[
            'm_unitTypeName'] == 'CastanarDestructibleDebris':
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            if len(debri_fire_tracker) > 0 and abs(time_gameloop - debri_fire_tracker[-1][0]) < 64:
                debri_fire_tracker[-1][-1] = debri_fire_tracker[-1][-1] + 1
            else:
                debri_fire_tracker.append([time_gameloop, time_min, time_sec, 1])

            if np.sqrt(np.square(datum["m_y"] - 153.) + np.square(datum["m_x"] - 141.)) <= 10:
                output.append([time_gameloop, '[%02d:%02d] Radiator (right) has debris nearby' % (time_min, time_sec)])

            for tank_num in range(len(tank_loc_blkcoord)):
                if check_dist([datum["m_y"], datum["m_x"]], tank_loc_blkcoord[tank_num]) <= 7:
                    if len(tank_tracker) > 0 and abs(time_gameloop - tank_tracker[-1][0]) < 64:
                        tank_tracker[-1][-1] = tank_tracker[-1][-1] + 1
                    else:
                        tank_tracker.append([time_gameloop, time_min, time_sec, tank_num + 1, 1])
                    break

        # Track fire from explosions
        if '_event' in datum.keys() and datum['_event'] == "NNet.Replay.Tracker.SUnitBornEvent" and datum[
            'm_unitTypeName'] == 'Beacon_TerranSmall233232224' and datum['m_upkeepPlayerId'] == 0 and datum[
            'm_creatorUnitTagRecycle'] == None:
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            if len(debri_fire_tracker) > 0 and abs(time_gameloop - debri_fire_tracker[-1][0]) < 64:
                debri_fire_tracker[-1][-1] = debri_fire_tracker[-1][-1] + 1
            else:
                debri_fire_tracker.append([time_gameloop, time_min, time_sec, 1])

            if np.sqrt(np.square(datum["m_y"] - 152.) + np.square(datum["m_x"] - 114.)) <= 10:
                output.append([time_gameloop, '[%02d:%02d] Radiator (left) has fire nearby' % (time_min, time_sec)])

            for tank_num in range(len(tank_loc_blkcoord)):
                if check_dist([datum["m_y"], datum["m_x"]], tank_loc_blkcoord[tank_num]) <= 7:
                    if len(tank_tracker) > 0 and abs(time_gameloop - tank_tracker[-1][0]) < 64:
                        tank_tracker[-1][-1] = tank_tracker[-1][-1] + 1
                    else:
                        tank_tracker.append([time_gameloop, time_min, time_sec, tank_num + 1, 1])
                    break

        # Track player deaths
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Replay.Tracker.SUnitDiedEvent':
            if datum['m_unitTagIndex'] in death_tracker:
                id_dst = np.where([datum['m_unitTagIndex'] == tracker_enum for tracker_enum in death_tracker])[0][0]
                death_tracker[id_dst] = None
                name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
                time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
                time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
                time_gameloop = datum['_gameloop']
                if datum['m_killerPlayerId'] is not None:
                    id_src = datum['m_killerPlayerId'] - 1
                    if id_src >= 0 and id_src <= 11:
                        name_src = list_player_name[id_src] + ' (#%02d)'%(1+id_src)
                    else:
                        name_src = 'Misc. Obj.'
                else:
                    name_src = 'Misc. Obj.'
                output.append(
                    [time_gameloop, '[%02d:%02d] %s was killed by %s' % (time_min, time_sec, name_dst, name_src)])

        if '_event' in datum.keys() and datum['_event'] == 'NNet.Game.SGameUserLeaveEvent':
            id_dst = datum['_userid']['m_userId']  # for some reason, this one is already 0-based.
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            leave_reason = datum['m_leaveReason']
            output.append(
                [time_gameloop, '[%02d:%02d] %s has left the game (%s)' % (time_min, time_sec, name_dst, leave_reason)])

        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'PlayerIsPsion':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s is Psion' % (time_min, time_sec, name_dst)])

        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'PlayerisAndroid':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s is Android' % (time_min, time_sec, name_dst)])

        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'CanUseGeneModAlien':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            if time_gameloop <= 50:
                output.append([time_gameloop, '[%02d:%02d] %s is Alien Host' % (time_min, time_sec, name_dst)])
            else:
                output.append([time_gameloop, '[%02d:%02d] %s is now an Alien Spawn' % (time_min, time_sec, name_dst)])

        if 'm_abil' in datum.keys() and datum['m_abil'] and 'm_abilLink' in datum['m_abil'].keys() and (
                datum['m_abil']['m_abilLink'] == 2478 or datum['m_abil']['m_abilLink'] == 2474):
            id_dst = datum['m_data']['TargetUnit']['m_snapshotControlPlayerId'] - 1
            id_src = datum['_userid']['m_userId']  # for some reason, this one is already 0-based.
            if id_dst >= 0 and id_dst < len(list_player_name):
                name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            else:
                name_dst = 'Misc. Obj.'
            name_src = list_player_name[id_src] + ' (#%02d)'%(1+id_src)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append(
                [time_gameloop, '[%02d:%02d] %s was crabbed by %s' % (time_min, time_sec, name_dst, name_src)])

    for ii in range(len(debri_fire_tracker)):
        output.append([debri_fire_tracker[ii][0], '[%02d:%02d] An explosion has occurred (%d debris formed)' % (
        debri_fire_tracker[ii][1], debri_fire_tracker[ii][2], debri_fire_tracker[ii][3])])

    for ii in range(len(tank_tracker)):
        output.append([tank_tracker[ii][0], '[%02d:%02d] Tank #%d has an explosion nearby (%d debris formed)' % (
        tank_tracker[ii][1], tank_tracker[ii][2], tank_tracker[ii][3], tank_tracker[ii][4])])

    output = [output[idx][1] for idx in np.argsort(np.array([out[0] for out in output]))]

    return output

















def main():
    try:
        file_sc2replay = sys.argv[1]
    except:
        print('No replay file.')
        return
    file_json = r'tmp.ndjson'
    str_cmd_json = r'python ".\s2protocol-master\s2protocol\s2_cli.py" --all --ndjson "' + file_sc2replay + '" > "' + file_json + '"'
    subprocess.check_call(str_cmd_json, shell=True)
    with open(file_json) as f:
        data_json = [json.loads(line) for line in f]


    num_players = 12

    replay = sc2reader.load_replay(file_sc2replay, load_map=True)
    list_player_handles = [data['toon_handle'] for data in replay.raw_data['replay.initData']['lobby_state']['slots'][:12]]
    list_player_clan = [data['clan_tag'] for data in replay.raw_data['replay.initData']['user_initial_data'][:12]]
    list_player_name = [str(data['name']) for data in replay.raw_data['replay.initData']['user_initial_data'][:12]]
    list_player_karma, list_player_games = get_bank_info(data_json)

    output = get_game_events(data_json,list_player_name)

    print('\nPlayer List:')
    for ii in range(num_players):
        if ii>0 and ii%3 == 0:
            print('')
        if len(list_player_clan[ii]) > 0:
            print('[#%2d] [K: %3s] [G: %4s] [%-15s] <%s> %s' % (ii+1, list_player_karma[ii], list_player_games[ii],
                                                             list_player_handles[ii], list_player_clan[ii],
                                                             list_player_name[ii]))
        else:
            print('[#%2d] [K: %3s] [G: %4s] [%-15s] %s' % (ii+1, list_player_karma[ii], list_player_games[ii],
                                                          list_player_handles[ii], list_player_name[ii]))

    print('\nEvents:')
    for ii in range(len(output)):
        if ii>0 and ii%3 == 0:
            print('')
        print(output[ii])

if __name__ == '__main__':
    main()