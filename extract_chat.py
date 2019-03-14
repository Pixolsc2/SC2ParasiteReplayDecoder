import sc2reader
import numpy as np
import subprocess
import json
import sys

def main():
    try:
        file_sc2replay = sys.argv[1]
    except:
        print('No replay file.')
        return

    # load replay in another format
    replay = sc2reader.load_replay(file_sc2replay)

    # Get player names
    list_player_name = [data['name'] for data in replay.raw_data['replay.initData']['user_initial_data'][:12]]
    list_player_clan = [data['clan_tag'] for data in replay.raw_data['replay.initData']['user_initial_data'][:12]]


    # Get player handles
    list_player_handles = [data['toon_handle'] for data in replay.raw_data['replay.initData']['lobby_state']['slots'][:12]]

    # Get player colors
    list_color_map = ['red', 'blue', 'teal', 'purp', 'yell', 'oj', 'grn', 'lp', 'N/A', 'grey', 'dg', 'brwn',
                      'N/A', 'blk', 'pink']
    list_player_color_id = [slot['colorPref'] for slot in replay.raw_data['replay.initData']['lobby_state']['slots']][:12]
    list_player_color_txt = [list_color_map[id - 1] for id in list_player_color_id]

    # Get role assignments
    key_role = {}
    key_role['CaptainUpgrade'] = 'Cap'
    key_role['ChiefMaitanenceOfficerUpgrade2222'] = 'Maj'
    key_role['ChiefMaitanenceOfficerUpgrade22222'] = 'Sgt'
    key_role['ChiefMaitanenceOfficerUpgrade222222'] = 'Doc'
    key_role['ChiefMaitanenceOfficerUpgrade2222222'] = 'LT'
    key_role['ChiefMaitanenceOfficerUpgrade2222223'] = 'Eng'
    key_role['SecurityOfficer'] = 'Off'
    key_role['ChiefMaitanenceOfficerUpgrade2'] = 'SG'
    key_role['ChiefMaitanenceOfficerUpgrade22'] = 'DSM'

    list_player_role = ['Unknown'] * 12
    list_event_role_assn = [event for event in replay.events if
                            event.name == 'UpgradeCompleteEvent' and event.upgrade_type_name in key_role.keys()]
    for event in list_event_role_assn:
        list_player_role[event.player.sid] = key_role[event.upgrade_type_name]

    # Display player list
    print('\nPlayer List:')
    for ii in range(len(list_player_name)):
        tmp_metadata = ('[#%2d] [%-15s] [%3s] [%6s] ' % (ii+1, list_player_handles[ii], list_player_role[ii], list_player_color_txt[ii])).encode('utf-8')
        if len(list_player_clan[ii]) > 0:
            tmp_playername = ('<%s> %s'%(list_player_clan[ii],list_player_name[ii])).encode('utf-8')
        else:
            tmp_playername = ('%s'%(list_player_name[ii])).encode('utf-8')
        print(tmp_metadata+tmp_playername)

    # Check for player name search
    print('\n')
    list_search_names = raw_input('To filter the chat...\nPlease type in the names or player numbers (separated by space) then press enter.\nLeave blank for unfiltered.\n').split()
    print('\n')
    if len(list_search_names) > 0:
        enable_filter = True
        search_ID = []
        for x in list_search_names:
            if x.isdigit():
                if int(x) >= 1 and int(x) <= 12:
                    search_ID.append(int(x)-1)
                    print('Adding %s (#%d) to filter list'%(list_player_name[int(x)-1],int(x)))
                else:
                    print('Player Number #%d incorrect. Please enter a number between 1 and 12' % int(x))
            else:
                player_found = False
                for yy in range(len(list_player_name)):
                    if x.lower() in list_player_name[yy].lower():
                        player_found = True
                        search_ID.append(yy)
                        print('Adding %s (#%d) to filter list'%(list_player_name[yy],yy+1))
                if not player_found:
                    print('Could not find player: %s'%x)
    else:
        enable_filter = False

    # Get player death times
    output_msg = []
    list_player_death_times = [np.inf]*12
    for entity_key in replay.entity.keys():
        list_marine_scv_died_at = [unit.died_at for unit in replay.entity[entity_key].units if unit.name in ['SCV', 'Marine']]

        # skip if player did not die
        if len(list_marine_scv_died_at) == 0 or np.any([died_at == None for died_at in list_marine_scv_died_at]):
            continue

        id_dst = replay.entity[entity_key].sid
        name_dst = list_player_name[id_dst] + ' (#%02d)' % (1 + id_dst)
        time_gameloop = max(list_marine_scv_died_at)
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        list_player_death_times[id_dst] = time_gameloop
        if (not enable_filter) or (enable_filter and id_dst in search_ID):
            output_msg.append([time_gameloop, '[%02d:%02d] [---DEATH] [%4s] [%3s] %s has died' % (time_min, time_sec, list_player_color_txt[id_dst], list_player_role[id_dst], name_dst)])

    # Extract messages and categorize into Observer, Infested, or All chat
    # Currently unable to differentiate between Alien and Human form while they are talking in All-Chat
    print('\n\nNow extracting chat log...\n')
    str_cmd_json = r'python ".\s2protocol-master\s2protocol\s2_cli.py" --all --ndjson "' + file_sc2replay
    data_json = [json.loads(line) for line in subprocess.check_output(str_cmd_json).split('\n')[:-1]]
    list_player_alienchat_mode = [0]*12
    for datum in data_json:
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Game.STriggerDialogControlEvent' and 'm_eventData' in datum.keys() and 'MouseButton' in datum['m_eventData'].keys() and datum['m_eventData']['MouseButton'] == 1:
            id_dst = datum['_userid']['m_userId']
            list_player_alienchat_mode[id_dst] = not list_player_alienchat_mode[id_dst]

        # Check who is Alien Host/Spawn
        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'CanUseGeneModAlien':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            if time_gameloop <= 50:
                if (not enable_filter) or (enable_filter and id_dst in search_ID):
                    output_msg.append([time_gameloop, '[%02d:%02d] [NEWSPAWN] [%4s] [%3s] %s is Alien Host' % (time_min, time_sec, list_player_color_txt[id_dst], list_player_role[id_dst], name_dst)])
            else:
                if (not enable_filter) or (enable_filter and id_dst in search_ID):
                    output_msg.append([time_gameloop, '[%02d:%02d] [NEWSPAWN] [%4s] [%3s] %s is now an Alien Spawn' % (time_min, time_sec, list_player_color_txt[id_dst], list_player_role[id_dst], name_dst)])


        if '_event' in datum.keys() and datum['_event'] == 'NNet.Game.STriggerChatMessageEvent':
            id_dst = datum['_userid']['m_userId']
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            msg = datum['m_chatMessage']

            if time_gameloop >= list_player_death_times[id_dst]:
                chat_mode = 'Observer'
            elif list_player_alienchat_mode[id_dst]:
                chat_mode = 'Infested'
            else:
                chat_mode = 'All'

            if (not enable_filter) or (enable_filter and id_dst in search_ID):
                output_msg.append([time_gameloop, '[%02d:%02d] [%8s] [%4s] [%3s] %s: %s' % (time_min, time_sec, chat_mode, list_player_color_txt[id_dst], list_player_role[id_dst], name_dst, msg)])

    output_msg = [output_msg[idx][1] for idx in np.argsort(np.array([out[0] for out in output_msg]))]
    print('\nEvents:')
    for ii in range(len(output_msg)):
        if ii>0 and ii%3 == 0:
            print('')
        print(output_msg[ii].encode('utf-8'))

if __name__ == '__main__':
    main()