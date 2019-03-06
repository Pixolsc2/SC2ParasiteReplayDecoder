import sc2reader
import numpy as np
import subprocess
import json
import sys
import xml.etree.ElementTree

def get_bank_info(data_json_):
    list_player_karma_ = ['N/A']*12
    list_player_games_ = ['N/A']*12
    list_player_spawned_ = ['N/A']*12
    list_player_human_ = ['N/A']*12
    list_player_innocent_ = ['0']*12
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

        # Spawned
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Game.SBankKeyEvent' and 'm_name' in datum.keys() and datum['m_name'] == 'Spawned':
            user_id = datum['_userid']['m_userId']
            user_val = datum['m_data']
            list_player_spawned_[user_id] = user_val

        # Human
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Game.SBankKeyEvent' and 'm_name' in datum.keys() and datum['m_name'] == 'Human':
            user_id = datum['_userid']['m_userId']
            user_val = datum['m_data']
            list_player_human_[user_id] = user_val

        # Innocent
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Game.SBankKeyEvent' and 'm_name' in datum.keys() and datum['m_name'] == 'InnocentKilled':
            user_id = datum['_userid']['m_userId']
            user_val = datum['m_data']
            list_player_innocent_[user_id] = user_val
    return list_player_karma_, list_player_games_, list_player_spawned_, list_player_human_, list_player_innocent_

def filter_abildata(e_):
    e_parsed_ = []
    for atype_ in e_:
        if atype_.tag == 'CAbilBuild':
            continue
        if atype_.tag == 'CAbilAugment':
            continue
        list_tags_children = [child.tag for child in atype_._children]
        if len(list_tags_children) == 0:
            continue
        if len(list_tags_children) == 1 and 'EditorCategories' in list_tags_children:
            continue
        if atype_.tag == 'CAbilTrain' and len(list_tags_children) == 1 and 'InfoArray' in list_tags_children:
            continue
        if atype_.tag in ['CAbilEffectTarget']:
            if atype_.attrib['id'] == 'EnergyChannel': # bandage fix for unknown issue
                e_parsed_.append(atype_)
            elif 'CmdButtonArray' in [child.tag for child in atype_._children]:
                e_parsed_.append(atype_)
            continue
        e_parsed_.append(atype_)
    return e_parsed_

list_names = {}
list_names['SJMineralFormation2222'] = 'Black Hole'
list_names['Beacon_TerranSmall2332322264'] = 'Head Crab'
list_names['RoguePurifier'] = 'C.O.R.E'
list_names['MengskWraith2'] = 'Shuttle'
list_names['TechLab2'] = 'Blood Tester'
list_names['SJSpaceStationMercenary'] = 'Station'
list_names['WidowMineBurrowed2'] = 'Remote Mine'
list_names['NovaAlarmBot'] = 'AIED'
def substitute_name(original_name_):
    if original_name_ in list_names.keys():
        return list_names[original_name_]
    else:
        return original_name_

def get_unit_type_name(unit_id_,list_unit_id_,list_unit_type_name_):
    try:
        unit_type_name_ = list_unit_type_name_[[ii for ii,unit_id_tmp in enumerate(list_unit_id_) if unit_id_ == unit_id_tmp][0]]
    except:
        unit_type_name_ = 'N/A'
    return unit_type_name_

def get_game_events(data_json_,list_player_name,replay):
    output = []
    death_tracker = [None] * 12
    remotemine_id_tracker = []
    remotemine_owner_tracker = []
    radiojammer_id_tracker = []
    radiojammer_owner_tracker = []
    debri_fire_tracker = []
    tank_tracker = []
    tank_loc_ptcoord = [[926406., 201907.], [829717., 960161.], [814268., 689009.], [940391., 321852.],
                        [880390., 490999.], [944118., 837361.]]  # y,x
    tank_loc_blkcoord = [[221.3, 48.4], [204.0, 232.3], [196.6, 169.9], [232.4, 77.0], [214.9, 115.7],
                         [231.2, 203.5]]  # y,x

    station_life_modules_mtags = [86769665, 86245377, 85721089, 85458945, 85983233, 86507521]
    bunker_life_modules_mtags = [308543489, 267911169]


    map_archive = replay.map.archive.extract()
    list_abilData = xml.etree.ElementTree.fromstring(map_archive['Base.SC2Data\\GameData\\AbilData.xml'])
    list_objects = xml.etree.ElementTree.fromstring(map_archive['Objects'])


    # Crab Infest ID
    try:
        list_crab_id = [2501, 2505] # T1 and T2+
        crab_id_offset = np.where([abilData.attrib['id'] == 'Corruption2' for abilData in filter_abildata(list_abilData)])[0][0] - 155
        list_crab_id = [crab_id + crab_id_offset for crab_id in list_crab_id]
    except:
        list_crab_id = []

    # Bridge Targetting ID
    try:
        list_bridge_target_id = [2733, 2734, 2735, 2736, 2737, 2738, 2739, 2740, 2741, 2742, 2743, 2744, 2745]
        list_bridge_target_id_offset = np.where([abilData.attrib['id'] == 'PowerOn5' for abilData in filter_abildata(list_abilData)])[0][0] - 416
        list_bridge_target_id = [bridge_target_id + list_bridge_target_id_offset for bridge_target_id in list_bridge_target_id]
    except:
        list_bridge_target_id = []


    def check_dist(yx1, yx2):
        return np.sqrt(np.square(yx1[0] - yx2[0]) + np.square(yx1[1] - yx2[1]))

    for datum in data_json_:
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Replay.Tracker.SUnitBornEvent' and datum[
            'm_unitTypeName'] == 'Marine':
            death_tracker[datum['m_upkeepPlayerId'] - 1] = datum['m_unitTagIndex']

        # track item use near gas tanks (experimental since ability link value may change each patch)
        if 'm_abil' in datum.keys() and datum['m_abil'] and 'm_abilLink' in datum['m_abil'].keys() and datum['m_abil'][
            'm_abilLink'] == 528 and datum['m_abil']['m_abilCmdIndex'] == 4:
            id_src = datum['_userid']['m_userId']  # for some reason, this one is already 0-based.
            name_src = list_player_name[id_src] + ' (#%02d)'%(1+id_src)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            ability_loc = None

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

        # Track radio jammer placements
        if '_event' in datum.keys() and datum[
            '_event'] == "NNet.Replay.Tracker.SUnitBornEvent" and 'm_creatorAbilityName' in datum.keys() and datum[
            'm_creatorAbilityName'] == 'PlaceRadioJammer' and 'm_unitTypeName' in datum.keys() and datum[
            'm_unitTypeName'] == 'RadioJammer':
            id_dst = datum['m_controlPlayerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            radiojammer_id_tracker.append(datum['m_unitTagIndex'])
            radiojammer_owner_tracker.append(id_dst)
            output.append([time_gameloop, '[%02d:%02d] %s placed a radio jammer' % (time_min, time_sec, name_dst)])

        # Track radio jammer death
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Replay.Tracker.SUnitDiedEvent':
            if datum['m_unitTagIndex'] in radiojammer_id_tracker:
                id_src = datum['m_killerPlayerId'] - 1
                if id_src >= 12:
                    name_src = 'Alien A.I.'
                else:
                    name_src = list_player_name[id_src] + ' (#%02d)' % (1+id_src)
                idx = np.where([datum['m_unitTagIndex'] == tracker_enum for tracker_enum in radiojammer_id_tracker])[0][
                    0]
                id_dst = radiojammer_owner_tracker[idx]
                name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
                time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
                time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
                time_gameloop = datum['_gameloop']
                output.append([time_gameloop, '[%02d:%02d] %s\'s radio jammer has been destroyed by %s' % (
                time_min, time_sec, name_dst,name_src)])
                radiojammer_id_tracker.pop(idx)
                radiojammer_owner_tracker.pop(idx)

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

        # Track remote mine detonations
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Replay.Tracker.SUnitDiedEvent':
            if datum['m_unitTagIndex'] in remotemine_id_tracker:
                idx = np.where([datum['m_unitTagIndex'] == tracker_enum for tracker_enum in remotemine_id_tracker])[0][
                    0]
                id_dst = remotemine_owner_tracker[idx]
                name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
                time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
                time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
                time_gameloop = datum['_gameloop']
                output.append([time_gameloop, '[%02d:%02d] %s\'s remote mine has been detonated/disarmed' % (
                time_min, time_sec, name_dst)])
                remotemine_id_tracker.pop(idx)
                remotemine_owner_tracker.pop(idx)

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

        # # Track player deaths
        # if '_event' in datum.keys() and datum['_event'] == 'NNet.Replay.Tracker.SUnitDiedEvent':
        #     if datum['m_unitTagIndex'] in death_tracker:
        #         id_dst = np.where([datum['m_unitTagIndex'] == tracker_enum for tracker_enum in death_tracker])[0][0]
        #         death_tracker[id_dst] = None
        #         name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
        #         time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
        #         time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
        #         time_gameloop = datum['_gameloop']
        #         if datum['m_killerPlayerId'] is not None:
        #             id_src = datum['m_killerPlayerId'] - 1
        #             if id_src >= 0 and id_src <= 11:
        #                 name_src = list_player_name[id_src] + ' (#%02d)'%(1+id_src)
        #             else:
        #                 name_src = 'Misc. Obj.'
        #         else:
        #             name_src = 'Misc. Obj.'
        #         output.append(
        #             [time_gameloop, '[%02d:%02d] %s was killed by %s' % (time_min, time_sec, name_dst, name_src)])

        # Track Player Leaves
        if '_event' in datum.keys() and datum['_event'] == 'NNet.Game.SGameUserLeaveEvent':
            id_dst = datum['_userid']['m_userId']  # for some reason, this one is already 0-based.
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            leave_reason = datum['m_leaveReason']
            output.append(
                [time_gameloop, '[%02d:%02d] %s has left the game (%s)' % (time_min, time_sec, name_dst, leave_reason)])

        # Check who is Psion
        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'PlayerIsPsion':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s is Psion' % (time_min, time_sec, name_dst)])

        # Check when Psion goes evil
        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'Haveanegativepsionicalignment':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s is now an EVIL PSION' % (time_min, time_sec, name_dst)])

        # Psionic Abilities
        if 'm_upgradeTypeName' in datum.keys() and 'Unlock' in datum['m_upgradeTypeName'][:6]:
            psionic_ability = str(datum['m_upgradeTypeName'])[6:]
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s unlocked %s' % (time_min, time_sec, name_dst,psionic_ability)])

        # Psionic Abilities
        if 'm_upgradeTypeName' in datum.keys() and 'Upgrade' in datum['m_upgradeTypeName'][:7]:
            psionic_ability = str(datum['m_upgradeTypeName'])[7:]
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s upgraded %s' % (time_min, time_sec, name_dst,psionic_ability)])            

        # Evil Psion Alignment
        if 'm_upgradeTypeName' in datum.keys() and 'HaveaNegativePsionicAlignmentbelow' in datum['m_upgradeTypeName'] and datum['m_count']>0:
            psionic_alignment = int(filter(str.isdigit,str(datum['m_upgradeTypeName'])))
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s\'s Psionic Alignment: -%d (EVIL)' % (time_min, time_sec, name_dst, psionic_alignment)])

        # Positive Psion Alignment
        if 'm_upgradeTypeName' in datum.keys() and 'HaveaPositivePsionicAlignmentabove' in datum['m_upgradeTypeName'] and datum['m_count']>0:
            psionic_alignment = int(filter(str.isdigit,str(datum['m_upgradeTypeName'])))
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s\'s Psionic Alignment: %d (GOOD)' % (time_min, time_sec, name_dst, psionic_alignment)])

        # Check who is Android
        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'PlayerisAndroid':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s is Android' % (time_min, time_sec, name_dst)])

        # # Android upgrade to T800
        # if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'ChassisSelectedT800':
        #     id_dst = datum['m_playerId'] - 1
        #     name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
        #     time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
        #     time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
        #     time_gameloop = datum['_gameloop']
        #     output.append([time_gameloop, '[%02d:%02d] %s upgraded to T-800 Android Chassis' % (time_min, time_sec, name_dst)])

        # Check Core Directive Assignment (experimental since there's no upgrade-tag for evil vs good role)
        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'COREDIRECTIVE':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            if time_gameloop == 3088:
                output.append([time_gameloop, '[%02d:%02d] %s received GOOD DIRECTIVE: OBEDIENCE' % (time_min, time_sec, name_dst)])
            elif time_gameloop == 3072:
                output.append([time_gameloop, '[%02d:%02d] %s received EVIL DIRECTIVE: THE TRUE END HAS COME' % (time_min, time_sec, name_dst)])
            else:
                output.append([time_gameloop, '[%02d:%02d] %s received an UNKNOWN DIRECTIVE (debug code: %d)' % (time_min, time_sec, name_dst, time_gameloop)])

        # Check who is Alien Host/Spawn
        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'CanUseGeneModAlien':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            if time_gameloop > 50:
                output.append([time_gameloop, '[%02d:%02d] %s is now an Alien Spawn' % (time_min, time_sec, name_dst)])

        # Check who is Alien Host/Spawn
        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'AlienIdentificationUpgrade2':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            if time_gameloop <= 50:
                output.append([time_gameloop, '[%02d:%02d] %s is Alien Host' % (time_min, time_sec, name_dst)])
            else:
                output.append([time_gameloop, '[%02d:%02d] %s is now Alien Host' % (time_min, time_sec, name_dst)])

        # Check who crabbed who (experimental since ability link value may change each patch)
        try:
            if 'm_abil' in datum.keys() and datum['m_abil'] and 'm_abilLink' in datum['m_abil'].keys() and (datum['m_abil']['m_abilLink'] in list_crab_id):
                id_dst = datum['m_data']['TargetUnit']['m_snapshotControlPlayerId'] - 1
                id_src = datum['_userid']['m_userId']  # for some reason, this one is already 0-based.
                id_dst_is_player = id_dst >= 0 and id_dst < len(list_player_name)
                mtag = datum['m_data']['TargetUnit']['m_tag']

                name_src = list_player_name[id_src] + ' (#%02d)'%(1+id_src)
                time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
                time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
                time_gameloop = datum['_gameloop']

                if id_dst_is_player:
                    name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
                    output.append([time_gameloop, '[%02d:%02d] %s was crabbed by %s' % (time_min, time_sec, name_dst, name_src)])
                elif not id_dst_is_player and mtag in station_life_modules_mtags:
                    module_num = np.where([mtag==mtag_enum for mtag_enum in station_life_modules_mtags])[0][0]+1
                    output.append([time_gameloop, '[%02d:%02d] Station module #%d was infested by %s' % (time_min, time_sec, module_num, name_src)])
                elif not id_dst_is_player and mtag in bunker_life_modules_mtags:
                    module_num = np.where([mtag==mtag_enum for mtag_enum in bunker_life_modules_mtags])[0][0]+1
                    output.append([time_gameloop, '[%02d:%02d] Bunker module #%d was infested by %s' % (time_min, time_sec, module_num, name_src)])
                else:
                    name_dst = 'Misc. Obj.'
                    output.append([time_gameloop, '[%02d:%02d] %s was crabbed by %s' % (time_min, time_sec, name_dst, name_src)])
        except:
            pass
            

            

    for ii in range(len(debri_fire_tracker)):
        output.append([debri_fire_tracker[ii][0], '[%02d:%02d] An explosion has occurred (%d debris formed)' % (
        debri_fire_tracker[ii][1], debri_fire_tracker[ii][2], debri_fire_tracker[ii][3])])

    for ii in range(len(tank_tracker)):
        output.append([tank_tracker[ii][0], '[%02d:%02d] Tank #%d has an explosion nearby (%d debris formed)' % (
        tank_tracker[ii][1], tank_tracker[ii][2], tank_tracker[ii][3], tank_tracker[ii][4])])




    # Track mass targetting
    list_event_bridge_target = [[x.frame, x.ability_link, x.player.sid] for x in [replay.events[idx] for idx in
                                            np.where([event.name == 'BasicCommandEvent' for event in replay.events])[0]]
                               if x.ability_link in list_bridge_target_id and x.command_index == 0]

    mass_target_min_req = 4
    for player_id in range(len(list_player_name)):
        list_event_cur = [event for event in list_event_bridge_target if event[2] == player_id]
        if len(list_event_cur) >= mass_target_min_req:
            targetting_tracker = []
            for event in list_event_cur:
                time_gameloop = event[0]
                time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
                time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
                if len(targetting_tracker) > 0 and abs(time_gameloop - targetting_tracker[-1][0]) < (16*10):
                    targetting_tracker[-1][-1] = targetting_tracker [-1][-1] + 1
                else:
                    targetting_tracker.append([time_gameloop, time_min, time_sec, 1])

            name_src = list_player_name[player_id] + ' (#%02d)' % (1 + player_id)
            for ii in range(len(targetting_tracker)):
                if targetting_tracker[ii][-1] >= mass_target_min_req:
                    output.append([targetting_tracker[ii][0], '[%02d:%02d] %s has mass target toggled (cnt: %d) ' % (
                        targetting_tracker[ii][1], targetting_tracker[ii][2], name_src, targetting_tracker[ii][3])])

    # Track Power Links
    powerlink_left_loc = (48.0, 141.0)
    powerlink_right_loc = (70.0, 141.0)
    list_event_powerlink_click = [[x.frame, x.player.sid, x.location[0:2]] for x in replay.events if
                                  x.name == 'UpdateTargetUnitCommandEvent' and x.target_unit_id != 0 and (
                                  x.location[:2] == powerlink_left_loc or x.location[:2] == powerlink_right_loc)]

    list_event_powerlink_off = [[event.frame, event.unit.location] for event in replay.events if
                                event.name == 'UnitTypeChangeEvent' and event.unit_type_name == 'PsiDisintegratorPowerLinkOff']

    for event in list_event_powerlink_off:
        time_gameloop = event[0]
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        powerlink_loc = event[1]
        if powerlink_loc == powerlink_left_loc[:2]:
            powerlink_loc_str = 'Left'
        elif powerlink_loc == powerlink_right_loc[:2]:
            powerlink_loc_str = 'Right'
        else:
            powerlink_loc_str = 'Unknown'
        list_click_events = [click_event for click_event in list_event_powerlink_click if
                             click_event[0] >= time_gameloop - 100 and click_event[0] < time_gameloop - 5 and
                             click_event[2] == powerlink_loc]
        if len(list_click_events) > 0:
            list_id_src = list(set([click_event[1] for click_event in list_click_events]))
            for id_num in range(len(list_id_src)):
                id_src = list_id_src[id_num]
                if id_num > 0:
                    name_src = name_src + ' or ' + list_player_name[id_src] + ' (#%02d)' % (1 + id_src)
                else:
                    name_src = list_player_name[id_src] + ' (#%02d)' % (1 + id_src)
            output.append([time_gameloop, '[%02d:%02d] %s turned off %s Power Link' % (
            time_min, time_sec, name_src, powerlink_loc_str)])

    # Track Player Deaths
    list_unit_id = [event.unit.id for event in replay.events if event.name == 'UnitBornEvent']
    list_unit_type_name = [event.unit_type_name for event in replay.events if event.name == 'UnitBornEvent']
    list_atk_events = [[x.frame, x.player.sid, x.ability_type_data['upkeep_player_id'] - 1] for x in
                       [replay.events[idx] for idx in
                        np.where([event.name == 'TargetUnitCommandEvent' for event in replay.events])[0]] if
                       x.ability_type_data['upkeep_player_id'] > 0 and x.ability_type_data['upkeep_player_id'] <= 12]
    for entity_key in replay.entity.keys():
        list_marines = [unit for unit in replay.entity[entity_key].units if unit.name == u'SCV']
        for marine in list_marines:
            if marine.died_at is None:
                continue

            list_ppl_who_atkd_marine = list(set([atk_event[1] for atk_event in list_atk_events if marine.owner.sid == atk_event[2] and
                                                 (marine.died_at - atk_event[0]) > 0 and (
                                                 marine.died_at - atk_event[0]) < (16 * 60)]))
            list_ppl_who_atkd_marine = [person for person in list_ppl_who_atkd_marine if person != marine.owner.sid]
            if len(list_ppl_who_atkd_marine) > 0:
                ppl_who_atkd_marine = ''
                for person_num in range(len(list_ppl_who_atkd_marine)):
                    id_src = list_ppl_who_atkd_marine[person_num]
                    name_src = list_player_name[id_src] + ' (#%02d)' % (1 + id_src)
                    ppl_who_atkd_marine = ppl_who_atkd_marine + ' [%s]' % name_src
            else:
                ppl_who_atkd_marine = ''
            id_dst = marine.owner.sid
            name_dst = list_player_name[id_dst] + ' (#%02d)' % (1 + id_dst)
            if marine.killing_unit is None:
                deaths = [[marine.died_at - unit.died_at, unit.died_at, unit.killing_unit] for unit in
                          replay.entity[entity_key].units if
                          (unit.killing_unit is not None) and (unit.killing_unit.owner is not None) and abs(
                              marine.died_at - unit.died_at) <= (16 * 5)]

                if len(deaths) > 0:
                    idx_min = np.argmin([death[0] for death in deaths])
                    time_gameloop = deaths[idx_min][1]
                    time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
                    time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
                    id_src = deaths[idx_min][2].owner.sid
                    if id_src >= 0 and id_src < 12:
                        name_src = list_player_name[id_src] + ' (#%02d)' % (1 + id_src)
                        list_ppl_who_atkd_marine = [person for person in list_ppl_who_atkd_marine if
                                                    person != id_src]
                        if len(list_ppl_who_atkd_marine) > 0:
                            ppl_who_atkd_marine = ''
                            for person_num in range(len(list_ppl_who_atkd_marine)):
                                id_src2 = list_ppl_who_atkd_marine[person_num]
                                name_src2 = list_player_name[id_src2] + ' (#%02d)' % (1 + id_src2)
                                ppl_who_atkd_marine = ppl_who_atkd_marine + ' [%s]' % name_src2
                        else:
                            ppl_who_atkd_marine = ''
                    elif id_src == 12:
                        if deaths[idx_min][2].name is not None:
                            name_src = replay.entity[13].name + ' (AI) (%s)' % deaths[idx_min][2].name
                        else:
                            # unit_type_name = list_unit_type_name[[tmp_id for tmp_id,tmp_unit_id in enumerate(list_unit_id) if deaths[idx_min][2].id == tmp_unit_id][0]]
                            unit_type_name = substitute_name(get_unit_type_name(deaths[idx_min][2].id, list_unit_id, list_unit_type_name))
                            name_src = replay.entity[13].name + ' (AI) (%s)' % unit_type_name
                            # name_src = replay.entity[13].name + ' (AI) (unitId: %d)' % deaths[idx_min][2].id
                    elif id_src == 13:
                        if deaths[idx_min][2].name is not None:
                            name_src = replay.entity[14].name + ' (AI) (%s)' % deaths[idx_min][2].name
                        else:
                            # unit_type_name = list_unit_type_name[[tmp_id for tmp_id,tmp_unit_id in enumerate(list_unit_id) if deaths[idx_min][2].id == tmp_unit_id][0]]
                            unit_type_name = substitute_name(get_unit_type_name(deaths[idx_min][2].id, list_unit_id, list_unit_type_name))
                            name_src = replay.entity[14].name + ' (AI) (%s)' % unit_type_name
                            # name_src = replay.entity[14].name + ' (AI) (unitId: %d)' % deaths[idx_min][2].id
                    else:
                        # unit_type_name = list_unit_type_name[[tmp_id for tmp_id,tmp_unit_id in enumerate(list_unit_id) if deaths[idx_min][2].id == tmp_unit_id][0]]
                        unit_type_name = substitute_name(get_unit_type_name(deaths[idx_min][2].id, list_unit_id, list_unit_type_name))
                        name_src = 'Misc. Obj. (%s)' % unit_type_name
                        # name_src = 'Misc. Obj. (unitId: %d)' % deaths[idx_min][2].id
                    output.append(
                        [time_gameloop, '[%02d:%02d] %s was killed by %s' % (
                        time_min, time_sec, name_dst, name_src) + ppl_who_atkd_marine])
                else:
                    deaths = [[marine.died_at - unit.died_at, unit.died_at, unit.killing_unit] for unit in
                              replay.entity[entity_key].units if
                              (unit.killing_unit is not None) and abs(marine.died_at - unit.died_at) <= (16 * 5)]
                    if len(deaths) > 0:
                        idx_min = np.argmin([death[0] for death in deaths])
                        id_src = deaths[idx_min][2].id
                        # unit_type_name = list_unit_type_name[[tmp_id for tmp_id,tmp_unit_id in enumerate(list_unit_id) if deaths[idx_min][2].id == tmp_unit_id][0]]
                        unit_type_name = substitute_name(get_unit_type_name(deaths[idx_min][2].id, list_unit_id, list_unit_type_name))
                        name_src = ' (%s)' % unit_type_name
                        # name_src = ' (unitId: %d)'%id_src
                        list_ppl_who_atkd_marine = [person for person in list_ppl_who_atkd_marine if
                                                    person != id_src]
                        if len(list_ppl_who_atkd_marine) > 0:
                            ppl_who_atkd_marine = ''
                            for person_num in range(len(list_ppl_who_atkd_marine)):
                                id_src2 = list_ppl_who_atkd_marine[person_num]
                                name_src2 = list_player_name[id_src2] + ' (#%02d)' % (1 + id_src2)
                                ppl_who_atkd_marine = ppl_who_atkd_marine + ' [%s]' % name_src2
                        else:
                            ppl_who_atkd_marine = ''
                    else:
                        name_src = ''
                    time_gameloop = marine.died_at
                    time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
                    time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
                    output.append([time_gameloop, '[%02d:%02d] %s was killed by Misc. Obj.%s' % (
                        time_min, time_sec, name_dst, name_src) + ppl_who_atkd_marine])
            else:
                time_gameloop = marine.died_at
                time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
                time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
                if marine.killing_unit.owner is not None:
                    id_src = marine.killing_unit.owner.sid
                else:
                    id_src = -1
                if id_src >= 0 and id_src < 12:
                    name_src = list_player_name[id_src] + ' (#%02d)' % (1 + id_src)
                    list_ppl_who_atkd_marine = [person for person in list_ppl_who_atkd_marine if
                                                person != id_src]
                    if len(list_ppl_who_atkd_marine) > 0:
                        ppl_who_atkd_marine = ''
                        for person_num in range(len(list_ppl_who_atkd_marine)):
                            id_src2 = list_ppl_who_atkd_marine[person_num]
                            name_src2 = list_player_name[id_src2] + ' (#%02d)' % (1 + id_src2)
                            ppl_who_atkd_marine = ppl_who_atkd_marine + ' [%s]' % name_src2
                    else:
                        ppl_who_atkd_marine = ''
                elif id_src == 12:
                    if marine.killing_unit.name is not None:
                        name_src = replay.entity[13].name + ' (AI) (%s)' % marine.killing_unit.name
                    else:
                        # unit_type_name = list_unit_type_name[[tmp_id for tmp_id,tmp_unit_id in enumerate(list_unit_id) if marine.killing_unit.id == tmp_unit_id][0]]
                        unit_type_name = substitute_name(get_unit_type_name(marine.killing_unit.id, list_unit_id, list_unit_type_name))
                        name_src = replay.entity[13].name + ' (AI) (%s)' % unit_type_name
                        # name_src = replay.entity[13].name + ' (AI) (unitId: %d)' % marine.killing_unit.id
                elif id_src == 13:
                    if marine.killing_unit.name is not None:
                        name_src = replay.entity[14].name + ' (AI) (%s)' % marine.killing_unit.name
                    else:
                        # unit_type_name = list_unit_type_name[[tmp_id for tmp_id,tmp_unit_id in enumerate(list_unit_id) if marine.killing_unit.id == tmp_unit_id][0]]
                        unit_type_name = substitute_name(get_unit_type_name(marine.killing_unit.id, list_unit_id, list_unit_type_name))
                        name_src = replay.entity[14].name + ' (AI) (%s)' % unit_type_name
                        # name_src = replay.entity[14].name + ' (AI) (unitId: %d)' % marine.killing_unit.id
                else:
                    # unit_type_name = list_unit_type_name[[tmp_id for tmp_id,tmp_unit_id in enumerate(list_unit_id) if marine.killing_unit.id == tmp_unit_id][0]]
                    unit_type_name = substitute_name(get_unit_type_name(marine.killing_unit.id, list_unit_id, list_unit_type_name))
                    name_src = 'Misc. Obj. (%s)' % unit_type_name
                    # name_src = 'Misc. Obj. (unitId: %d)' % marine.killing_unit.id
                output.append([time_gameloop, '[%02d:%02d] %s was killed by %s' % (
                time_min, time_sec, name_dst, name_src) + ppl_who_atkd_marine])


    # Track Alien Evolutions
    list_evo = [None]*4
    list_evo[0] = [['ZerglingCarbot','Zergling (T2)'],
                   ['PrisonZealot','Psychic (T2)'],
                   ]

    list_evo[1] = [['HunterKiller','Hydra (T3)'],
                   ['PrimalRoach', 'Roach (T3)'],
                   ['Mutalisk', 'Bat (T3)'],
                   ['HotSSwarmling', 'Veloci Zergling (T3)'],
                   ['Zeratul','Cosmic Assassin (T3)'],
                   ['WhizzardAlien','Whizzard (T3)'],
                   ['Archon','Voltaic (T3)'],
                   ]

    list_evo[2] = [['Ravager','Flame Roach (T4)'],
                   ['LargeSwarmQueen','Queen (T4)'],
                   ['PrimalHydralisk','Ice Hydra (T4)'],
                   ['HotSTorrasque2','Ultralisk (T4)'],
                   ['MutaliskBroodlord', 'Venom Bat (T4)'],
                   ['DehakaMirrorImage', 'Veloci Dehaka (T4)'],
                   ['HybridDominator','Subvoltaic (T4)'],
                   ]

    list_evo[3] = [['XenomorphMatriarch','Matriarch Queen (T5)'],
                   ['Yagdra','Flame Gargantuan (T5)'],
                   ['AlphaXenodon','Ultralisk (T5)'],
                   ['Broodlord','Flying Crab (T5)'],
                   ['Dehaka','Veloci Dehaka (T5)'],
                   ]

    list_evo_upgrades = ['AlienTier12','AlienTier13','AlienTier14','AlienTier15']

    for evo_num in range(len(list_evo)):
        time_evo = min([np.inf] + [event.frame for event in replay.events if event.name == 'UpgradeCompleteEvent' if event.upgrade_type_name == list_evo_upgrades[evo_num]])
        chosen_evo = [idx_evo for event in replay.events if event.name == 'UnitBornEvent' for idx_evo,evo_type_name in enumerate([evo[0] for evo in list_evo[evo_num]]) if event.unit_type_name == evo_type_name and abs(event.frame-time_evo) <= 3]

        if time_evo < 16*3600*24:
            time_min = np.floor(time_evo / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(time_evo / 1000. * 62.5 % 60)
            if len(chosen_evo) > 0:
                output.append([time_evo, '[%02d:%02d] Alien Evolution: %s' % (time_min, time_sec, list_evo[evo_num][chosen_evo[0]][1])])
            else:
                output.append([time_evo, '[%02d:%02d] Alien Evolution: Unknown (T%d)' % (time_min, time_sec,evo_num+2)])
        elif len(chosen_evo) == 0 and evo_num == (len(list_evo) - 1):
            time_evo = min([np.inf] + [event.frame for event in replay.events if event.name == 'UnitTypeChangeEvent' and event.unit_type_name == 'BroodLord'])
            if time_evo < 16*3600*24:
                time_min = np.floor(time_evo / 1000. * 62.5 / 60).astype('int')
                time_sec = np.floor(time_evo / 1000. * 62.5 % 60)
                output.append([time_evo, '[%02d:%02d] Alien Evolution: Flying Crab (T5)' % (time_min, time_sec)])

    # Track Android Evolution
    time_t800 = [[event.player.sid,event.frame] for event in replay.events if event.name == 'UpgradeCompleteEvent' and event.upgrade_type_name == 'ChassisSelectedT800']
    time_synth = [[event.player.sid,event.frame] for event in replay.events if event.name == 'UpgradeCompleteEvent' and event.upgrade_type_name == 'ChassisSelectedSyntheticForm']
    if len(time_t800) == 1 and len(time_synth) == 1 and time_t800[0][0] == time_synth[0][0]:
        id_dst = time_t800[0][0]
        name_dst = list_player_name[id_dst] + ' (#%02d)' % (1 + id_dst)
        if time_synth[0][1] > time_t800[0][1]:
            time_gameloop = time_synth[0][1]
            android_chassis = 'T-800'
        elif time_t800[0][1] > time_synth[0][1]:
            time_gameloop = time_t800[0][1]
            android_chassis = 'Synthetic'
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        output.append([time_gameloop, '[%02d:%02d] %s upgraded to %s Chassis' % (time_min, time_sec, name_dst, android_chassis)])

    # Track AIED usage
    list_event_aied_born = [event for event in replay.events if
                            event.name == 'UnitBornEvent' and event.unit_type_name == 'NovaAlarmBot']
    for event in list_event_aied_born:
        time_destroyed = event.frame
        time_min = np.floor(time_destroyed / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_destroyed / 1000. * 62.5 % 60)
        if event.unit_controller is not None:
            id_src = event.unit_controller.sid
            name_src = list_player_name[id_src] + ' (#%02d)' % (1+id_src)
            output.append([time_destroyed,'[%02d:%02d] %s used an AIED' % (time_min, time_sec, name_src)])

    # Track AIED explosion
    list_event_aied_death = [event for event in replay.events if
                                event.name == 'UnitDiedEvent' and event.unit.id in [event2.unit.id for event2 in list_event_aied_born]]
    for event in list_event_aied_death:
        time_destroyed = event.frame
        time_min = np.floor(time_destroyed / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_destroyed / 1000. * 62.5 % 60)
        if event.unit.owner is not None:
            id_src = event.unit.owner.sid
            name_src = list_player_name[id_src] + ' (#%02d)' % (1+id_src)
            output.append([time_destroyed,'[%02d:%02d] %s\'s AIED has been detonated/disarmed' % (time_min, time_sec, name_src)])

    def get_destruction_by_obj_name(output_,obj_name_disp_,obj_name_file_,disable_spam_):
        list_unit_tmp_ = [event.unit.id for event in replay.events if event.name == 'UnitBornEvent' and event.unit_type_name == obj_name_file_]
        list_event_death_ = [event for event in replay.events if event.name == 'UnitDiedEvent' and event.unit.id in list_unit_tmp_]
        for event in list_event_death_:
            time_destroyed = event.frame
            time_min = np.floor(time_destroyed / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(time_destroyed / 1000. * 62.5 % 60)
            killing_unit = event.killing_unit
            if killing_unit is not None and killing_unit.owner is not None:
                id_src = killing_unit.owner.sid
                if id_src == 12:
                    name_src = replay.entity[13].name + ' (AI) (%s)' % substitute_name(get_unit_type_name(killing_unit.id,list_unit_id,list_unit_type_name))
                elif id_src == 13:
                    name_src = replay.entity[14].name + ' (AI) (%s)' % substitute_name(get_unit_type_name(killing_unit.id,list_unit_id,list_unit_type_name))
                else:
                    name_src = list_player_name[id_src] + ' (#%02d) (%s)' % (1+id_src, substitute_name(get_unit_type_name(killing_unit.id,list_unit_id,list_unit_type_name)))
                output.append([time_destroyed,'[%02d:%02d] %s has been destroyed by %s' % (time_min, time_sec, obj_name_disp_, name_src)])
            elif killing_unit is not None:
                name_src = 'Misc. Obj. (%s)' % substitute_name(get_unit_type_name(killing_unit.id, list_unit_id, list_unit_type_name))
                output.append([time_destroyed,'[%02d:%02d] %s has been destroyed by %s' % (time_min, time_sec, obj_name_disp_, name_src)])
            else:
                if not disable_spam_:
                    output.append([time_destroyed,'[%02d:%02d] %s has been destroyed' % (time_min, time_sec, obj_name_disp_)])

    def get_attacks_by_obj_name(output_,obj_name_disp_,obj_name_file_):
        list_atks = [event for event in replay.events if event.name in ['UpdateTargetUnitCommandEvent','TargetUnitCommandEvent'] and event.ability_name == 'Attack' and event.ability.name != 'RightClick' and get_unit_type_name(event.target.id, list_unit_id, list_unit_type_name) == obj_name_file_]
        for event in list_atks:
            time_gameloop = event.frame
            time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
            id_src = event.player.sid
            name_src = list_player_name[id_src] + ' (#%02d)' % (1 + id_src)
            output_.append([time_gameloop, '[%02d:%02d] %s has been attacked by %s' % (time_min, time_sec, obj_name_disp_, name_src)])

    def get_attacks_by_obj_loc(output_,obj_name_disp_,obj_name_file_):
        obj_loc_blkcoord = [[float(val) for val in child.attrib['Position'].split(',')[0:2]] for child in
                   list_objects._children if
                   'UnitType' in child.keys() and child.attrib['UnitType'] == obj_name_file_]
        list_atks = [event for event in replay.events if event.name in ['UpdateTargetUnitCommandEvent','TargetUnitCommandEvent'] and event.ability_name == 'Attack' and event.ability.name != 'RightClick' and any([check_dist(list(event.location[0:2]),loc)<3. for loc in obj_loc_blkcoord])]
        for event in list_atks:
            time_gameloop = event.frame
            time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
            id_src = event.player.sid
            name_src = list_player_name[id_src] + ' (#%02d)' % (1 + id_src)
            output_.append([time_gameloop, '[%02d:%02d] %s has been attacked by %s' % (time_min, time_sec, obj_name_disp_, name_src)])

    get_destruction_by_obj_name(output,'C.O.R.E.','RoguePurifier',False)
    get_destruction_by_obj_name(output,'A shuttle','MengskWraith2',True)
    get_destruction_by_obj_name(output,'A camera','SentryGun2',True)
    get_destruction_by_obj_name(output,'The blood tester','TechLab2',False)
    get_destruction_by_obj_name(output,'Moon LZ-1486A','MoonLZ1486A',False)
    get_destruction_by_obj_name(output,'Station','SJSpaceStationMercenary',False)

    get_attacks_by_obj_name(output, 'Shuttle', 'MengskWraith2')
    get_attacks_by_obj_name(output, 'Shuttle engine', 'SpaceshipEngine')
    get_attacks_by_obj_name(output, 'Station', 'SJSpaceStationMercenary')

    get_attacks_by_obj_loc(output, 'Security Module', 'PlatformPowerCore222')
    get_attacks_by_obj_loc(output, 'Radiator', 'PlatformPowerCore2')
    get_attacks_by_obj_loc(output, 'Power transformer', 'PlatformPowerCore')

    # Black Hole Appears
    list_bh_enter_events = [event for event in replay.events if event.name == 'UnitBornEvent' and event.unit_type_name == 'SJMineralFormation2222']
    for event in list_bh_enter_events:
        time_gameloop = event.frame
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        output.append([time_gameloop,'[%02d:%02d] Black Hole has appeared.' % (time_min, time_sec)])

    # Black Hole Exits
    list_unit_id_bh = [event.unit.id for event in replay.events if event.name == 'UnitBornEvent' and event.unit_type_name == 'SJMineralFormation2222']
    list_bh_exit_events = [event for event in replay.events if event.name == 'UnitDiedEvent' and event.unit.id in list_unit_id_bh]
    for event in list_bh_exit_events:
        time_gameloop = event.frame
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        output.append([time_gameloop,'[%02d:%02d] Black Hole has exited.' % (time_min, time_sec)])

    # Self Destruct Timer Enable/Disable
    spinalarm_born_tracker = []
    spinalarm_death_tracker = []
    list_unit_id_spinalarm = [event.unit.id for event in replay.events if event.name == 'UnitBornEvent' and event.unit_type_name == 'SJMineralFormation22234']
    list_event_spinalarm_born = [event for event in replay.events if event.name == 'UnitBornEvent' and event.unit_type_name == 'SJMineralFormation22234']
    list_event_spinalarm_death = [event for event in replay.events if event.name == 'UnitDiedEvent' and event.unit.id in list_unit_id_spinalarm]
    for event in list_event_spinalarm_born:
        time_gameloop = event.frame
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        if len(spinalarm_born_tracker) > 0 and abs(time_gameloop - spinalarm_born_tracker[-1][0]) < 5:
            spinalarm_born_tracker[-1][-1] = spinalarm_born_tracker[-1][-1] + 1
        else:
            spinalarm_born_tracker.append([time_gameloop, time_min, time_sec, 1])

    for event in list_event_spinalarm_death:
        time_gameloop = event.frame
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        if len(spinalarm_death_tracker) > 0 and abs(time_gameloop - spinalarm_death_tracker[-1][0]) < 5:
            spinalarm_death_tracker[-1][-1] = spinalarm_death_tracker[-1][-1] + 1
        else:
            spinalarm_death_tracker.append([time_gameloop, time_min, time_sec, 1])

    for ii in range(len(spinalarm_born_tracker)):
        if spinalarm_born_tracker[ii][3] > 30:
            output.append([spinalarm_born_tracker[ii][0], '[%02d:%02d] Self-destruct sequence enabled' % (spinalarm_born_tracker[ii][1], spinalarm_born_tracker[ii][2])])

    for ii in range(len(spinalarm_death_tracker)):
        if spinalarm_death_tracker[ii][3] > 30:
            output.append([spinalarm_death_tracker[ii][0], '[%02d:%02d] Self-destruct sequence cancelled' % (spinalarm_death_tracker[ii][1], spinalarm_death_tracker[ii][2])])


    # Self Destruct Reactor Switches
    spinalarm_born_tracker = []
    spinalarm_death_tracker = []
    list_unit_id_spinalarm = [event.unit.id for event in replay.events if event.name == 'UnitBornEvent' and event.unit_type_name == 'SpiningAlarmYellow2']
    list_event_spinalarm_born = [event for event in replay.events if event.name == 'UnitBornEvent' and event.unit_type_name == 'SpiningAlarmYellow2']
    list_event_spinalarm_death = [event for event in replay.events if event.name == 'UnitDiedEvent' and event.unit.id in list_unit_id_spinalarm]
    for event in list_event_spinalarm_born:
        time_gameloop = event.frame
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        if len(spinalarm_born_tracker) > 0 and abs(time_gameloop - spinalarm_born_tracker[-1][0]) < 5:
            spinalarm_born_tracker[-1][-1] = spinalarm_born_tracker[-1][-1] + 1
        else:
            spinalarm_born_tracker.append([time_gameloop, time_min, time_sec, 1])

    for event in list_event_spinalarm_death:
        time_gameloop = event.frame
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        if len(spinalarm_death_tracker) > 0 and abs(time_gameloop - spinalarm_death_tracker[-1][0]) < 5:
            spinalarm_death_tracker[-1][-1] = spinalarm_death_tracker[-1][-1] + 1
        else:
            spinalarm_death_tracker.append([time_gameloop, time_min, time_sec, 1])

    for ii in range(len(spinalarm_born_tracker)):
        if spinalarm_born_tracker[ii][3] > 1:
            output.append([spinalarm_born_tracker[ii][0], '[%02d:%02d] Self Destruct Switch Enabled (A)' % (spinalarm_born_tracker[ii][1], spinalarm_born_tracker[ii][2])])

    for ii in range(len(spinalarm_death_tracker)):
        if spinalarm_death_tracker[ii][3] > 1:
            output.append([spinalarm_death_tracker[ii][0], '[%02d:%02d] Self Destruct Switch Disabled (A)' % (spinalarm_death_tracker[ii][1], spinalarm_death_tracker[ii][2])])

    # Self Destruct Reactor Switches
    spinalarm_born_tracker = []
    spinalarm_death_tracker = []
    list_unit_id_spinalarm = [event.unit.id for event in replay.events if event.name == 'UnitBornEvent' and event.unit_type_name == 'SpiningAlarmYellow22']
    list_event_spinalarm_born = [event for event in replay.events if event.name == 'UnitBornEvent' and event.unit_type_name == 'SpiningAlarmYellow22']
    list_event_spinalarm_death = [event for event in replay.events if event.name == 'UnitDiedEvent' and event.unit.id in list_unit_id_spinalarm]
    for event in list_event_spinalarm_born:
        time_gameloop = event.frame
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        if len(spinalarm_born_tracker) > 0 and abs(time_gameloop - spinalarm_born_tracker[-1][0]) < 5:
            spinalarm_born_tracker[-1][-1] = spinalarm_born_tracker[-1][-1] + 1
        else:
            spinalarm_born_tracker.append([time_gameloop, time_min, time_sec, 1])

    for event in list_event_spinalarm_death:
        time_gameloop = event.frame
        time_min = np.floor(time_gameloop / 1000. * 62.5 / 60).astype('int')
        time_sec = np.floor(time_gameloop / 1000. * 62.5 % 60)
        if len(spinalarm_death_tracker) > 0 and abs(time_gameloop - spinalarm_death_tracker[-1][0]) < 5:
            spinalarm_death_tracker[-1][-1] = spinalarm_death_tracker[-1][-1] + 1
        else:
            spinalarm_death_tracker.append([time_gameloop, time_min, time_sec, 1])

    for ii in range(len(spinalarm_born_tracker)):
        if spinalarm_born_tracker[ii][3] > 1:
            output.append([spinalarm_born_tracker[ii][0], '[%02d:%02d] Self Destruct Switch Enabled (B)' % (spinalarm_born_tracker[ii][1], spinalarm_born_tracker[ii][2])])

    for ii in range(len(spinalarm_death_tracker)):
        if spinalarm_death_tracker[ii][3] > 1:
            output.append([spinalarm_death_tracker[ii][0], '[%02d:%02d] Self Destruct Switch Disabled (B)' % (spinalarm_death_tracker[ii][1], spinalarm_death_tracker[ii][2])])




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

    # Get player information
    list_player_handles = [data['toon_handle'] for data in replay.raw_data['replay.initData']['lobby_state']['slots'][:12]]
    list_player_clan = [data['clan_tag'] for data in replay.raw_data['replay.initData']['user_initial_data'][:12]]
    # for data in replay.raw_data['replay.initData']['user_initial_data'][:12]:
    list_player_name = [data['name'] for data in replay.raw_data['replay.initData']['user_initial_data'][:12]]
    list_player_karma, list_player_games, list_player_spawned, list_player_human, list_player_innocent = get_bank_info(data_json)
    


    # Get player colors
    list_color_map = ['red', 'blue', 'teal', 'purple', 'yellow', 'oj', 'green', 'lp', 'N/A', 'grey', 'dg', 'brown',
                      'N/A', 'black', 'pink']
    list_player_color_id = [slot['colorPref'] for slot in replay.raw_data['replay.initData']['lobby_state']['slots']][
                           :12]
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


    output = get_game_events(data_json,list_player_name,replay)

    print('\n[Date of Replay: %s][Time Zone: %s]'%(replay.start_time,replay.time_zone))

    print('\nPlayer List:')
    for ii in range(num_players):
        if ii>0 and ii%3 == 0:
            print('')
        try:
            spawn_rate = '%d%%' %(100.*int(list_player_spawned[ii])/int(list_player_human[ii]))
        except:
            spawn_rate = 'N/A'
        
        tmp_metadata = ('[#%2d] [K: %3s] [G: %4s] [I: %2s] [S: %s ] [%-15s] [%3s] [%6s] ' % (ii+1, list_player_karma[ii], list_player_games[ii],
                                     list_player_innocent[ii],spawn_rate,
                                     list_player_handles[ii], list_player_role[ii], list_player_color_txt[ii])).encode('utf-8')
        if len(list_player_clan[ii]) > 0:
            tmp_playername = ('<%s> %s'%(list_player_clan[ii],list_player_name[ii])).encode('utf-8')
        else:
            tmp_playername = ('%s'%(list_player_name[ii])).encode('utf-8')
        print(tmp_metadata+tmp_playername)

    print('\nEvents:')
    for ii in range(len(output)):
        if ii>0 and ii%3 == 0:
            print('')
        print(output[ii].encode('utf-8'))

if __name__ == '__main__':
    main()