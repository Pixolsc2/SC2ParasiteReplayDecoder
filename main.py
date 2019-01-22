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




def get_game_events(data_json_,list_player_name,replay):
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

    station_life_modules_mtags = [86769665, 86245377, 85721089, 85458945, 85983233, 86507521]
    bunker_life_modules_mtags = [308543489, 267911169]

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

        # Check who is Android
        if 'm_upgradeTypeName' in datum.keys() and datum['m_upgradeTypeName'] == 'PlayerisAndroid':
            id_dst = datum['m_playerId'] - 1
            name_dst = list_player_name[id_dst] + ' (#%02d)'%(1+id_dst)
            time_min = np.floor(datum['_gameloop'] / 1000. * 62.5 / 60).astype('int')
            time_sec = np.floor(datum['_gameloop'] / 1000. * 62.5 % 60)
            time_gameloop = datum['_gameloop']
            output.append([time_gameloop, '[%02d:%02d] %s is Android' % (time_min, time_sec, name_dst)])

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
            if time_gameloop <= 50:
                output.append([time_gameloop, '[%02d:%02d] %s is Alien Host' % (time_min, time_sec, name_dst)])
            else:
                output.append([time_gameloop, '[%02d:%02d] %s is now an Alien Spawn' % (time_min, time_sec, name_dst)])

        # Check who crabbed who (experimental since ability link value may change each patch)
        list_crab_id = [2477, 2478, 2479, 2473, 2474, 2475]
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
                                if x.ability_link >= 2710 and x.ability_link <= 2739 and x.command_index == 0]

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
    list_atk_events = [[x.frame, x.player.sid, x.ability_type_data['upkeep_player_id'] - 1] for x in
                       [replay.events[idx] for idx in
                        np.where([event.name == 'TargetUnitCommandEvent' for event in replay.events])[0]] if
                       x.ability_type_data['upkeep_player_id'] > 0 and x.ability_type_data['upkeep_player_id'] <= 12]
    for entity_key in replay.entity.keys():
        list_marines = [unit for unit in replay.entity[entity_key].units if unit.name == u'Marine']
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
                    if id_src < 12:
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
                            name_src = replay.entity[13].name + ' (AI) (unitId: %d)' % deaths[idx_min][2].id
                    elif id_src == 13:
                        if deaths[idx_min][2].name is not None:
                            name_src = replay.entity[14].name + ' (AI) (%s)' % deaths[idx_min][2].name
                        else:
                            name_src = replay.entity[14].name + ' (AI) (unitId: %d)' % deaths[idx_min][2].id
                    else:
                        name_src = 'Misc. Obj. (unitId: %d)' % deaths[idx_min][2].id
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
                        name_src = ' (unitId: %d)'%id_src
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
                if id_src < 12:
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
                        name_src = replay.entity[13].name + ' (AI) (unitId: %d)' % marine.killing_unit.id
                elif id_src == 13:
                    if marine.killing_unit.name is not None:
                        name_src = replay.entity[14].name + ' (AI) (%s)' % marine.killing_unit.name
                    else:
                        name_src = replay.entity[14].name + ' (AI) (unitId: %d)' % marine.killing_unit.id
                else:
                    name_src = 'Misc. Obj. (unitId: %d)' % marine.killing_unit.id
                output.append([time_gameloop, '[%02d:%02d] %s was killed by %s' % (
                time_min, time_sec, name_dst, name_src) + ppl_who_atkd_marine])

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
    list_player_karma, list_player_games = get_bank_info(data_json)

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

    print('\nPlayer List:')
    for ii in range(num_players):
        if ii>0 and ii%3 == 0:
            print('')
        if len(list_player_clan[ii]) > 0:
            print('[#%2d] [K: %3s] [G: %4s] [%-15s] [%3s] [%6s] <%s> %s' % (ii+1, list_player_karma[ii], list_player_games[ii],
                                                             list_player_handles[ii], list_player_role[ii], list_player_color_txt[ii], list_player_clan[ii],
                                                             list_player_name[ii]))
        else:
            print('[#%2d] [K: %3s] [G: %4s] [%-15s] [%3s] [%6s] %s' % (ii+1, list_player_karma[ii], list_player_games[ii],
                                                                list_player_handles[ii], list_player_role[ii], list_player_color_txt[ii], list_player_name[ii]))

    print('\nEvents:')
    for ii in range(len(output)):
        if ii>0 and ii%3 == 0:
            print('')
        print(output[ii])

if __name__ == '__main__':
    main()