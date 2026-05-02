from itertools import groupby

import requests
import math
import numpy as np

# Define the base URL for FPL API
BASE_URL = "https://fantasy.premierleague.com/api/"
GENERAL_INFO = "bootstrap-static/"
FIXTURES = "fixtures/"
TEAM_IDS = 0
OWNERSHIP = 1
PLAYER_NAME = 2
TEAM_NAME = 0
VALUE_TO_PRINT = 1
GAMEWEEK = 1
TEAM_ENTRIES = 0
STARTING_GW = 1
BENCH_POS = 11
IN_PLAYERS_LIST = 0
IN_POINTS = 1
OUT_PLAYERS_LIST = 2
OUT_POINTS = 3
FINE = 4


# Function to make a GET request to the FPL API
def fpl_api_get(endpoint):
    url = f'{BASE_URL}{endpoint}'
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error: {response.status_code}')
        return None


# Function to get info on a player
def getPlayerInfo(playerID):
    playerData = f"element-summary/{playerID}/"
    data = fpl_api_get(playerData)
    return data


# Function to get info on a fpl team
def getTeamInfo(teamID):
    teamData = f"entry/{teamID}/"
    data = fpl_api_get(teamData)
    return data


# Function to get info on a fpl team's gameweek
def getTeamGWInfo(teamID, gw):
    gwEntry = f"entry/{teamID}/event/{gw}/picks/"
    data = fpl_api_get(gwEntry)
    return data


def getTeamHistoryInfo(teamID):
    gwEntry = f"entry/{teamID}/history/"
    data = fpl_api_get(gwEntry)
    return data


# Function to get info on a fpl team's transfers
def getTeamTransfersInfo(teamID):
    transfersData = f"entry/{teamID}/transfers/"
    data = fpl_api_get(transfersData)
    return data


# Function to get info on a fpl league
def getLeagueInfo(leagueID):
    leagueData = f"leagues-classic/{leagueID}/standings/"
    data = fpl_api_get(leagueData)
    return data


def getManagerInfo(teamID):
    managerData = f"entry/{teamID}/"
    data = fpl_api_get(managerData)
    return data


def getFixtures():
    data = fpl_api_get(FIXTURES)
    return data


# Function to get Effective Ownership on players in the teams
def getEO(gw, verbose=True):
    EO = {}
    captains = {}
    for team in teams:
        teamID = team['entry']
        team_name = team['entry_name']
        data = getTeamGWInfo(teamID, gw)
        for pick in data["picks"]:
            if not pick["multiplier"]:
                continue
            playerID = pick["element"]
            if playerID in EO.keys():
                EO[playerID][1] += pick['multiplier']
                EO[playerID][0].append(team_name)
            elif pick['multiplier']:
                EO[playerID] = [[team_name], pick['multiplier']]
            if pick['multiplier'] > 1:
                pName = idToName(playerID)
                if pName in captains.keys():
                    captains[pName].append(team["entry_name"])
                else:
                    captains[pName] = [team["entry_name"]]
    players = []
    for player in EO:
        pName = idToName(player)
        players.append((EO[player][TEAM_IDS], round(100 * (EO[player][OWNERSHIP] / len(teams)), 2),
                        pName, captains[pName] if pName in captains.keys() else [], player))
    players = sorted(players, key=lambda x: x[OWNERSHIP], reverse=True)
    if verbose:
        for player in players:
            if len(player[0]) == len(teams):
                print(player[PLAYER_NAME], "{0}%".format(player[OWNERSHIP]), "ALL", "\n")
            else:
                print(player[PLAYER_NAME], "{0}%".format(player[OWNERSHIP]), player[0], "\n")
    return players


def idToName(pid):
    index = pid
    while pid != sgdata[index - 1]["id"]:
        index -= 1
    return sgdata[index - 1]["web_name"]


def teamIDtoName(teamID):
    for team in teams:
        if team["entry"] == teamID:
            return team["entry_name"]


def teamIDtoStruct(teamID):
    for team in teams:
        if team["entry"] == teamID:
            return team


def idToPStruct(pid):
    index = pid
    while pid != sgdata[index - 1]["id"]:
        index -= 1
    return sgdata[index - 1]


def gwPointsByPlayerID(pid, gw):
    pInfo = getPlayerInfo(pid)
    gwLoc = gw - 1 - (currentGW - len(pInfo['history']))
    while pInfo['history'][gwLoc]['round'] > gw:
        gwLoc -= 1
    if currentGW != gw:
        while pInfo['history'][gwLoc]['round'] < gw:
            gwLoc += 1
    if pInfo['history'][gwLoc]['round'] != gw:
        return 0

    # if pInfo['history'][gwLoc - 1]['round'] == gw:
    #    return pInfo['history'][gwLoc - 1]['total_points'] + pInfo['history'][gwLoc]['total_points']
    return pInfo['history'][gwLoc]['total_points']


def gwStructByPlayerID(pid, gw):
    pInfo = getPlayerInfo(pid)
    gwLoc = 0
    while pInfo['history'][gwLoc]['round'] != gw:
        if pInfo['history'][gwLoc]['round'] > gw:
            return []
        else:
            gwLoc += 1
        if gwLoc >= len(pInfo['history']):
            return []

    if gwLoc + 1 != len(pInfo['history']):
        if pInfo['history'][gwLoc + 1]['round'] == gw:
            return [pInfo['history'][gwLoc], pInfo['history'][gwLoc + 1]]
    return [pInfo['history'][gwLoc]]


def getBestxStats(endGW=38):
    players = {}
    for gw in range(STARTING_GW, endGW):
        print(gw)
        for pid in range(1, len(sgdata)):
            print(pid)
            struct = gwStructByPlayerID(pid, gw)
            if gw == 1:
                players[idToName(pid)] = {}
            for game in struct:
                players[idToName(pid)][gw] = []
                players[idToName(pid)][gw].append((game['expected_goals_conceded'], game["expected_goals"],
                                                   game["expected_assists"], game["minutes"], game["bonus"]))
    return players


def getReturnsStatsFromPlayers():
    managers = {}
    for team in teams:
        teamID = team["entry"]
        print("\n", team["entry_name"])
        managers[team["entry_name"]] = {}
        for gw in range(STARTING_GW, currentGW + 1):
            tdata = getTeamGWInfo(teamID, gw)
            for pick in tdata["picks"]:
                if not pick["multiplier"]:
                    continue
                tempPoints = gwPointsByPlayerID(pick["element"], gw)
                if not pick["element"] in managers[team["entry_name"]].keys():
                    managers[team["entry_name"]][pick["element"]] = [0, 0]
                if tempPoints > 3:
                    managers[team["entry_name"]][pick["element"]][0] += 1
                else:
                    managers[team["entry_name"]][pick["element"]][1] += 1
        players = sorted(managers[team["entry_name"]].items(), key=lambda x: x[1][0] - x[1][1], reverse=True)
        for player in players:
            print(idToName(player[0]), player[1])
    return managers


def getNumberOfTransfers():
    teamList = []
    for team in teams:
        print(team["entry_name"])
        teamID = team['entry']
        tdata = getTeamInfo(teamID)
        teamList.append((tdata['name'], tdata['last_deadline_total_transfers']))
    teamList = sorted(teamList, key=lambda x: x[1], reverse=True)
    for p in teamList:
        print(p[TEAM_NAME], p[VALUE_TO_PRINT])


def bestBench(gw):
    teamList = []
    for team in teams:
        teamID = team['entry']
        tdata = getTeamGWInfo(teamID, gw)
        teamList.append((team['entry_name'], tdata['entry_history']['points_on_bench']))
    teamList = sorted(teamList, key=lambda x: x[1], reverse=True)
    for p in teamList:
        print(p[TEAM_NAME], p[VALUE_TO_PRINT])
    return teamList


def benchPointsOverall():
    teamDict = {}
    for team in teams:
        totalPoints = 0
        for gw in range(STARTING_GW, currentGW):
            teamID = team['entry']
            tdata = getTeamGWInfo(teamID, gw)
            totalPoints += tdata['entry_history']['points_on_bench']
        teamDict[team['entry_name']] = totalPoints
    teamList = sorted(teamDict.items(), key=lambda x: x[1], reverse=True)
    for team in teamList:
        print(f"{team[0]} has left {team[1]} points on the bench\n")


def bestBenchOverAll():
    teamList = []
    for gw in range(1, currentGW):
        tempList = bestBench(gw)
        for tt in tempList:
            teamList.append((tt, gw))
    teamList = sorted(teamList, key=lambda x: x[TEAM_ENTRIES][VALUE_TO_PRINT], reverse=True)
    for p in teamList:
        print(p[TEAM_ENTRIES][TEAM_NAME], p[TEAM_ENTRIES][VALUE_TO_PRINT], "GW-{}".format(p[GAMEWEEK]))


def worstBenchingPlayers(startingGW=STARTING_GW):
    playersList = []
    for team in teams:
        print(team["entry"])
        for gw in range(startingGW, currentGW):
            teamID = team['entry']
            tdata = getTeamGWInfo(teamID, gw)
            for pick in tdata["picks"][11:15]:
                playersList.append((pick["element"], gwPointsByPlayerID(pick["element"], gw), team["entry_name"], gw))

    playersList = sorted(playersList, key=lambda x: x[1], reverse=True)

    for i in range(10):
        print(f"{playersList[i][2]} GW{playersList[i][3]}: {idToName(playersList[i][0])} {playersList[i][1]} points")


def bestTransfers(startingGW=STARTING_GW, useTeams=[], ret=False):
    transferList = []
    if not useTeams:
        useTeams = teams
    for team in useTeams:
        teamID = team['entry']
        # print(f"Analyzing the Transfers of: {teamID}")
        transfers = getTeamTransfersInfo(teamID)
        costs = {}
        for gw in range(startingGW, currentGW + 1):
            gwInfo = getTeamGWInfo(teamID, gw)
            costs[gw] = gwInfo["entry_history"]["event_transfers_cost"]
            if gwInfo["active_chip"] == 'wildcard':
                costs[gw] = 'wildcard'
            if gwInfo["active_chip"] == 'freehit':
                costs[gw] = 'freehit'
        oldgw = 0
        for transfer in transfers:
            inPlayer = transfer['element_in']
            outPlayer = transfer['element_out']
            gw = transfer['event']
            if gw < startingGW:
                break
            if costs[gw] in ['wildcard', 'freehit']:
                continue
            inPoints = gwPointsByPlayerID(inPlayer, gw)  # * multiplier
            outPoints = gwPointsByPlayerID(outPlayer, gw)  # * multiplier
            fine = 0
            if costs[gw]:
                fine = 4
                costs[gw] -= 4
            if oldgw != gw:
                transferList.append([[inPlayer], inPoints, [outPlayer], outPoints, fine, team['entry_name'], gw])
            else:
                transferList[-1] = [transferList[-1][IN_PLAYERS_LIST] + [inPlayer],
                                    transferList[-1][IN_POINTS] + inPoints,
                                    transferList[-1][OUT_PLAYERS_LIST] + [outPlayer],
                                    transferList[-1][OUT_POINTS] + outPoints, transferList[-1][FINE] + fine,
                                    team['entry_name'], gw]
            oldgw = gw

    # t=sorted(t,key=lambda x : x[1],reverse=True)
    transferList = sorted(transferList, key=lambda x: x[IN_POINTS] - x[OUT_POINTS] - x[FINE], reverse=True)
    if ret:
        return transferList
    printTransfers(transferList)


def printTransfers(transferList):
    for p in transferList:
        top = f""
        top += f"{p[5]} GW{p[6]}: "
        top += f"IN ({p[IN_POINTS]} points): "
        for player in p[IN_PLAYERS_LIST]:
            top += f"{idToName(player)}, "
        top = top[:-2]
        top += f" | OUT ({p[OUT_POINTS]} points): "
        for player in p[OUT_PLAYERS_LIST]:
            top += f"{idToName(player)}, "
        top = top[:-2]
        top += f" | hit: {p[FINE] * -1} | "
        top += f"OVR - {p[IN_POINTS] - p[OUT_POINTS] - p[FINE]}"
        print(top)


def getUninqePlayers(gw):
    u = {}
    players = getEO(gw)
    for player in players:
        if len(player[TEAM_IDS]) > 1:
            continue
        else:
            if player[TEAM_IDS][0] in u.keys():
                u[player[TEAM_IDS][0]].append(player[PLAYER_NAME])
            else:
                u[player[TEAM_IDS][0]] = [player[PLAYER_NAME]]
    for team in teams:
        if team['entry_name'] in u.keys():
            print(team['entry_name'], u[team['entry_name']], "\n")
        else:
            print(team['entry_name'], "[]")
    return u


def getCaptaincy(gw):
    caps = {}
    for team in teams:
        data = getTeamGWInfo(team["entry"], gw)
        for player in data["picks"]:
            if player["is_captain"]:
                # print(team["entry_name"], idToName(player["element"]))
                if player["element"] in caps.keys():
                    caps[player["element"]].append(team["entry_name"])
                else:
                    caps[player["element"]] = [team["entry_name"]]
                break
    for cap in caps.keys():
        print(f"{idToName(cap)}: {caps[cap] if not len(caps[cap]) == len(teams) else 'ALL'}")


def getCaptain(teamID, gw):
    data = getTeamGWInfo(teamID, gw)
    for player in data["picks"]:
        if player["is_captain"]:
            return player["element"]


def getLeaguePlayers(gw):
    players = set()
    for team in teams:
        teamID = team["entry"]
        data = getTeamGWInfo(teamID, gw)
        for player in data["picks"]:
            players.add(player["element"])
    return players


def getAllTimePlayers():
    players = {}
    for gw in range(1, currentGW):
        for team in teams:
            teamID = team["entry"]
            data = getTeamGWInfo(teamID, gw)
            for player in data["picks"]:
                if player["element"] in players.keys():
                    players[player["element"]].append((team["entry_name"], gw))
                else:
                    players[player["element"]] = [(team["entry_name"], gw)]
    playersList = sorted(players.items(), key=lambda x: len(x[1]), reverse=False)
    return playersList


def nichePlayers():
    players = getAllTimePlayers()[:70]
    for player in players:
        print(idToName(player[0]), player[1])


def calcXPoints(pid, gw, is_captain):
    pStruct = idToPStruct(pid)
    pos = pStruct["element_type"]
    gwStruct = gwStructByPlayerID(pid, gw)
    if not gwStruct:
        return 0
    xG = round(sum(float(x['expected_goals']) for x in gwStruct))
    xA = round(sum(float(x['expected_assists']) for x in gwStruct))
    xGC = round(sum(float(x['expected_goals_conceded']) for x in gwStruct))
    yellow_cards = sum(x['yellow_cards'] for x in gwStruct)
    red_cards = sum(x['red_cards'] for x in gwStruct)
    penalties_missed = sum(x['penalties_missed'] for x in gwStruct)
    own_goals = sum(x['own_goals'] for x in gwStruct)
    minutes = sum(x['minutes'] for x in gwStruct)
    bonus = sum(x['bonus'] for x in gwStruct)

    basePoints = yellow_cards * -1 + red_cards * -3 + penalties_missed * -2 + own_goals * -2 + math.ceil(
        minutes / 59) + xA * 3 + bonus
    match pos:
        case 1:
            additional_points = xG * 6 - math.floor(xGC / 2) + math.floor(sum(x['saves'] for x in gwStruct) / 3) + \
                                sum(x['penalties_saved'] for x in gwStruct) * 5 + (not bool(xGC)) * 4 * math.floor(
                minutes / 60)
        case 2:
            additional_points = xG * 6 - math.floor(xGC / 2) + (not bool(xGC)) * 4 * math.floor(minutes / 60)
        case 3:
            additional_points = xG * 5 + (not bool(xGC))
        case 4:
            additional_points = xG * 4
    return (basePoints + additional_points) * (1 + is_captain)


def luckiestPlayer(startingGW=STARTING_GW):
    points = []
    for team in teams:
        teamID = team['entry']
        print(f"Analyzing the Points of: {teamID}")
        temp_total = 0
        rPoints = 0
        for gw in range(startingGW, currentGW + 1):
            data = getTeamGWInfo(teamID, gw)
            for pick in data["picks"][:BENCH_POS]:
                pid = pick["element"]
                temp_total += calcXPoints(pid, gw, pick["is_captain"])
            rPoints += data["entry_history"]["points"] - data["entry_history"]["event_transfers_cost"]
            temp_total -= data["entry_history"]["event_transfers_cost"]
        points.append([team["entry_name"], rPoints, temp_total])
    points = sorted(points, key=lambda x: x[1] - x[2], reverse=True)
    for p in points:
        print(f"{p[0]} Scored {p[1]} Points while his Xpoints is {p[2]} Lucky Points: {p[1] - p[2]}\n")


def captaincyAccuracy():
    badList = []
    for team in teams[:]:
        teamID = team["entry"]
        print(f"Analyzing the Captains of: {teamID}")
        badCaptains = 0
        for gw in range(STARTING_GW, currentGW + 1):
            gwInfo = getTeamGWInfo(teamID, gw)
            cid = getCaptain(teamID, gw)
            captainPoints = gwPointsByPlayerID(cid, gw)
            for pick in gwInfo["picks"]:
                done = True
                tempID = pick["element"]
                tempPoints = gwPointsByPlayerID(tempID, gw)
                if tempPoints > captainPoints:
                    badCaptains += 1
                    # print(gw, idToName(tempID), tempPoints, idToName(cid), captainPoints)
                    done = False
                    break
            if (done):
                # print(gw,captainPoints)
                pass
        badList.append([team["entry_name"], currentGW - badCaptains])
    badList = sorted(badList, key=lambda x: x[1], reverse=True)
    for team in badList:
        print(f" {team[0]} captain accuracy is {team[1]}/{currentGW}\n")


def captaincyLoses():
    badList = []
    for team in teams:
        teamID = team["entry"]
        print(f"Analyzing the Captains of: {teamID}")
        loses = 0
        for gw in range(STARTING_GW, currentGW + 1):
            gwInfo = getTeamGWInfo(teamID, gw)
            best = 0
            # tempInfo = getPlayerInfo(getCaptain(teamID, gw))
            # captainPoints = tempInfo['history'][gw - 1 - (currentGW - len(tempInfo['history']))]['total_points']
            for pick in gwInfo["picks"]:
                pid = pick["element"]
                tempPoints = gwPointsByPlayerID(pid, gw)
                if pick["is_captain"]:
                    captainPoints = tempPoints
                if tempPoints > best:
                    best = tempPoints
            loses += (best - captainPoints) * 2
        badList.append([team["entry_name"], loses])
    badList = sorted(badList, key=lambda x: x[1], reverse=True)
    for team in badList:
        print(f" {team[0]} captain inaccuracy lost him {team[1]} points\n")


def teamRepresentation(gw):
    teamList = {}
    c = 0
    for pt in gdata["teams"]:
        teamList[pt["name"]] = 0
    for team in teams:
        teamID = team["entry"]
        gwInfo = getTeamGWInfo(teamID, gw)
        for pick in gwInfo["picks"]:
            c += 1
            playerID = pick["element"]
            playerInfo = idToPStruct(playerID)
            pTeam = gdata["teams"][playerInfo["team"] - 1]["name"]
            if pTeam in teamList.keys():
                teamList[pTeam] += 1
    teamsList = sorted(teamList.items(), key=lambda x: x[1], reverse=True)
    for t in teamsList:
        print(f"{t[0]} has {round(t[1] * 100 / c, ndigits=2)}% of the players in GW{gw}\n ")


def bestWildcard():
    transferList = []
    for team in teams:
        teamID = team['entry']
        GWs = []
        print(f"Analyzing the Transfers of: {teamID}")
        for gw in range(currentGW, STARTING_GW, -1):
            gwInfo = getTeamGWInfo(teamID, gw)
            if gwInfo["active_chip"] == 'wildcard':
                print(team["entry_name"], gwInfo)
                GWs.append(gw)
        if GWs:
            transfers = getTeamTransfersInfo(teamID)
        else:
            continue
        oldgw = 0
        for transfer in transfers:
            gw = transfer['event']
            if not gw in GWs:
                continue
            inPlayer = transfer['element_in']
            outPlayer = transfer['element_out']
            picks = getTeamGWInfo(teamID, gw)['picks']
            multipliers = [pick["multiplier"] for pick in picks if pick["element"] == inPlayer]
            if multipliers:
                multiplier = multipliers[0]
            else:
                continue
            inPoints = gwPointsByPlayerID(inPlayer, gw) * multiplier
            outPoints = gwPointsByPlayerID(outPlayer, gw) * multiplier
            fine = 0
            if oldgw != gw:
                transferList.append([[inPlayer], inPoints, [outPlayer], outPoints, fine, team['entry_name'], gw])
            else:
                if inPlayer in transferList[-1][IN_PLAYERS_LIST] or inPlayer in transferList[-1][OUT_PLAYERS_LIST]:
                    inList = []
                    inPoints = 0
                else:
                    inList = [inPlayer]
                if outPlayer in transferList[-1][IN_PLAYERS_LIST] or outPlayer in transferList[-1][OUT_PLAYERS_LIST]:
                    outList = []
                    outPoints = 0
                else:
                    outList = [outPlayer]
                transferList[-1] = [transferList[-1][IN_PLAYERS_LIST] + inList,
                                    transferList[-1][IN_POINTS] + inPoints,
                                    transferList[-1][OUT_PLAYERS_LIST] + outList,
                                    transferList[-1][OUT_POINTS] + outPoints, transferList[-1][FINE] + fine,
                                    team['entry_name'], gw]
            oldgw = gw
    transferList = sorted(transferList, key=lambda x: x[IN_POINTS] - x[OUT_POINTS], reverse=True)
    for p in transferList:
        top = f""
        top += f"{p[5]} GW{p[6]}: "
        top += f"IN ({p[IN_POINTS]} points): "
        for player in p[IN_PLAYERS_LIST]:
            top += f"{idToName(player)}, "
        top = top[:-2]
        top += f"|OUT ({p[OUT_POINTS]} points): "
        for player in p[OUT_PLAYERS_LIST]:
            top += f"{idToName(player)}, "
        top = top[:-2]
        top += f"|OVR - {p[IN_POINTS] - p[OUT_POINTS] - p[FINE]}"
        print(top)


def managerPointsAllocation(teamID, verbose=True):
    teamDict = {}
    for pt in gdata["teams"]:
        teamDict[pt["name"]] = 0
    for gw in range(STARTING_GW, currentGW):
        gwInfo = getTeamGWInfo(teamID, gw)
        for pick in gwInfo["picks"]:
            playerID = pick["element"]
            playerInfo = idToPStruct(playerID)
            pTeam = gdata["teams"][playerInfo["team"] - 1]["name"]
            if pTeam in teamDict.keys():
                teamDict[pTeam] += pick["multiplier"] * \
                                   gwPointsByPlayerID(playerID, gw)
    teamList = sorted(teamDict.items(), key=lambda x: x[1], reverse=True)
    totalPoints = sum(teamDict.values())
    if verbose:
        for t in teamList:
            print(f"{t[0]} has {round(t[1] * 100 / totalPoints, ndigits=2)}% of {teamIDtoName(teamID)} points \n")
    return teamList


def managerAllstars(teamID):
    teamDict = {}
    for gw in range(STARTING_GW, currentGW):
        # print(f"starting GW{gw}")
        gwInfo = getTeamGWInfo(teamID, gw)
        for pick in gwInfo["picks"]:
            playerID = pick["element"]
            playerInfo = idToPStruct(playerID)
            pos = playerInfo["element_type"]
            # pTeam = gdata["teams"][playerInfo["team"] - 1]["name"]
            if not (playerID in teamDict.keys()):
                teamDict[playerID] = [pick["multiplier"] * \
                                      gwPointsByPlayerID(playerID, gw), pos]
            else:
                teamDict[playerID] = [pick["multiplier"] * \
                                      gwPointsByPlayerID(playerID, gw) + teamDict[playerID][0], pos]
    teamList = sorted(teamDict.items(), key=lambda x: x[1][0], reverse=True)
    # totalPoints = sum(teamDict.values())
    allstars = {1: [], 2: [], 3: [], 4: []}
    for t in teamList:
        # print(f"{t[0]} has {round(t[1] * 100 / totalPoints, ndigits=2)}% of {teamIDtoName(teamID)} points \n")
        if (len(allstars[1]) + len(allstars[2]) + len(allstars[3]) + len(allstars[4])) == 15:
            break
        tmpPos = t[1][1]
        match tmpPos:
            case 1:
                if len(allstars[tmpPos]) < 2:
                    allstars[tmpPos].append(t)
                else:
                    continue
            case 2:
                if len(allstars[tmpPos]) < 5:
                    allstars[tmpPos].append(t)
                else:
                    continue
            case 3:
                if len(allstars[tmpPos]) < 5:
                    allstars[tmpPos].append(t)
                else:
                    continue
            case 4:
                if len(allstars[tmpPos]) < 3:
                    allstars[tmpPos].append(t)
                else:
                    continue

    for pos in allstars:
        for p in allstars[pos]:
            print(idToName(p[0]), p[1][0])
    return allstars


def pointsAllocation():
    for team in teams:
        managerPointsAllocation(team['entry'])
        print("-----------------------------------------------------------")


def mostPopularCaptain(teamID):
    captains = {}
    for gw in range(STARTING_GW, currentGW):
        tempCaptain = idToName(getCaptain(teamID, gw))
        if tempCaptain in captains.keys():
            captains[tempCaptain] += 1
        else:
            captains[tempCaptain] = 1
    # return idToName(max(captains, key=captains.get))
    return captains


def bestBenchByManager(teamID):
    benchPoints = []
    for gw in range(STARTING_GW, currentGW + 1):
        tdata = getTeamGWInfo(teamID, gw)
        benchPoints.append(tdata['entry_history']['points_on_bench'])
    maxPoints = max(benchPoints)
    return f"{maxPoints} in GW{benchPoints.index(maxPoints) + 1}"


def pointsByManager(teamID):
    for gw in range(STARTING_GW, currentGW + 1):
        tdata = getTeamGWInfo(teamID, gw)
        print(tdata['entry_history']['points'])


def worldAvg():
    for event in gdata["events"]:
        print(event["average_entry_score"])


def leagueAvg():
    for gw in range(STARTING_GW, currentGW):
        gwPoints = 0
        for team in teams:
            teamID = team["entry"]
            tdata = getTeamGWInfo(teamID, gw)
            gwPoints += tdata['entry_history']['points']
        print(round(gwPoints / len(teams)))


'''def managerProfile(teamID):
    # print (mostPopularCaptain(teamID))
    # print (bestBenchByManager(teamID))
    # pAlloc = managerPointsAllocation(teamID)
    # bestTransfers(useTeams=[teamIDtoStruct(teamID)])
    allStars = managerAllstars(teamID)
    for pos in allStars:
        for p in allStars[pos]:
            print(idToName(p[0]), p[1][0])
    # pointsByManager(teamID)
    t = managerPointsAllocation(teamID)
    for tt in t:
        print(tt[0])
    for tt in t:
        print(tt[1])
    # worldAvg()
    # leagueAvg()'''


def mostUniqueManager():
    uniqueCount = {}
    for gw in range(STARTING_GW, currentGW + 1):
        u = getUninqePlayers(gw)
        for team in u.keys():
            if team in uniqueCount.keys():
                uniqueCount[team] += len(u[team])
            else:
                uniqueCount[team] = len(u[team])

    uniqueCount = sorted(uniqueCount.items(), key=lambda x: x[1], reverse=True)
    for team in uniqueCount:
        print(team[0], " ", team[1])


def hitKing():
    costs = {}
    for gw in range(STARTING_GW, currentGW + 1):
        for team in teams:
            teamID = team["entry"]
            data = getTeamGWInfo(teamID, gw)
            if team["entry_name"] in costs.keys():
                costs[team["entry_name"]] += data["entry_history"]["event_transfers_cost"]
            else:
                costs[team["entry_name"]] = data["entry_history"]["event_transfers_cost"]
    costs = sorted(costs.items(), key=lambda x: x[1], reverse=True)
    for cost in costs:
        print(f"{cost[0]} - {cost[1]} ({int(cost[1] / 4)} hits)")


def bestFreeHit():
    '''for team in teams:
        teamID = team["entry"]
        for gw in range(currentGW, STARTING_GW, -1):
            gwInfo = getTeamGWInfo(teamID, gw)
            if gwInfo["active_chip"] == 'freehit':
                print(gwInfo, teamIDtoName(teamID))'''
    transferList = []
    for team in teams:
        teamID = team['entry']
        GWs = []
        print(f"Analyzing the Transfers of: {teamID}")
        for gw in range(currentGW, STARTING_GW, -1):
            gwInfo = getTeamGWInfo(teamID, gw)
            if gwInfo["active_chip"] == 'freehit':
                print(team["entry_name"], gwInfo)
                GWs.append(gw)
        if GWs:
            transfers = getTeamTransfersInfo(teamID)
        else:
            continue
        oldgw = 0
        for transfer in transfers:
            gw = transfer['event']
            if not gw in GWs:
                continue
            inPlayer = transfer['element_in']
            outPlayer = transfer['element_out']
            picks = getTeamGWInfo(teamID, gw)['picks']
            multipliers = [pick["multiplier"] for pick in picks if pick["element"] == inPlayer]
            if multipliers:
                multiplier = multipliers[0]
            else:
                continue
            inPoints = gwPointsByPlayerID(inPlayer, gw) * multiplier
            outPoints = gwPointsByPlayerID(outPlayer, gw) * multiplier
            fine = 0
            if oldgw != gw:
                transferList.append([[inPlayer], inPoints, [outPlayer], outPoints, fine, team['entry_name'], gw])
            else:
                transferList[-1] = [transferList[-1][IN_PLAYERS_LIST] + [inPlayer],
                                    transferList[-1][IN_POINTS] + inPoints,
                                    transferList[-1][OUT_PLAYERS_LIST] + [outPlayer],
                                    transferList[-1][OUT_POINTS] + outPoints, transferList[-1][FINE] + fine,
                                    team['entry_name'], gw]
            oldgw = gw
    transferList = sorted(transferList, key=lambda x: x[IN_POINTS] - x[OUT_POINTS], reverse=True)
    for p in transferList:
        top = f""
        top += f"{p[5]} GW{p[6]}: "
        top += f"IN ({p[IN_POINTS]} points): "
        for player in p[IN_PLAYERS_LIST]:
            top += f"{idToName(player)}, "
        top = top[:-2]
        top += f"|OUT ({p[OUT_POINTS]} points): "
        for player in p[OUT_PLAYERS_LIST]:
            top += f"{idToName(player)}, "
        top = top[:-2]
        top += f"|OVR - {p[IN_POINTS] - p[OUT_POINTS] - p[FINE]}"
        print(top)


def managerOriginalityRating(startingw=2):
    originDict = {}
    usedPlayers = set()
    for gw in range(STARTING_GW, startingw):
        for team in teams:
            teamID = team['entry']
            gwInfo = getTeamGWInfo(teamID, gw)
            for pick in gwInfo["picks"]:
                usedPlayers.add(pick["element"])
    tmpDict = {}
    for gw in range(startingw, currentGW):
        gwPlayers = set()
        for player, manager in tmpDict.items():
            if len(manager) > 1:
                continue
            if manager[0] in originDict.keys():
                originDict[manager[0]].append(player)
            else:
                originDict[manager[0]] = [player]

        tmpDict = {}
        for team in teams:
            teamID = team['entry']
            gwInfo = getTeamGWInfo(teamID, gw)
            for pick in gwInfo["picks"]:
                if pick["element"] in usedPlayers:
                    continue
                else:
                    if pick["element"] in tmpDict.keys():
                        tmpDict[pick["element"]].append(team["entry_name"])
                    else:
                        tmpDict[pick["element"]] = [team["entry_name"]]
                    gwPlayers.add(pick["element"])
        for p in gwPlayers:
            usedPlayers.add(p)
    return originDict


def gwNumOfPlayers(gw, STARTING_ONLY=False):
    usedPlayers = set()
    bench_pos = 11 if STARTING_ONLY else 15
    for team in teams:
        teamID = team['entry']
        gwInfo = getTeamGWInfo(teamID, gw)
        for pick in gwInfo["picks"][:bench_pos]:
            usedPlayers.add(pick["element"])

    # return f"In GW{gw} there are {len(usedPlayers)} different players"
    return len(usedPlayers)


def bestManagerTable():
    teamsDict = {}
    for team in teams:
        teamsDict[team['entry_name']] = []
    for gw in range(STARTING_GW, currentGW + 1):
        bestTmp = bestManagerInGW(gw)
        teamsDict[bestTmp[0]].append(gw)
    teamsList = sorted(teamsDict.items(), key=lambda x: len(x[1]), reverse=True)
    for team in teamsList:
        print(f"{team[0]} won manager of the week {len(team[1])} times : {team[1]}")


def allTimeBestManagers():
    for gw in range(STARTING_GW, currentGW + 1):
        bestTmp = bestManagerInGW(gw)
        print(f"{bestTmp[0]} won GW{gw} by {bestTmp[2]}-point margin scoring {bestTmp[1]} points")


def managersPodium(gw, minus=0):
    scoreList = []
    for team in teams:
        teamID = team['entry']
        gwInfo = getTeamGWInfo(teamID, gw)['entry_history']
        gwPoints = gwInfo['points'] - (gwInfo['event_transfers_cost'] * minus)
        scoreList.append([[team['entry_name']], gwPoints])
    scoreList = sorted(scoreList, key=lambda x: x[1], reverse=True)
    s = 0
    while s < len(scoreList) - 1:
        if scoreList[s][1] == scoreList[s + 1][1]:
            scoreList[s][0].append(scoreList[s + 1][0][0])
            scoreList.remove(scoreList[s + 1])
        s += 1
    return scoreList[:3]


def allTimePodium(minus=0):
    podiumDict = {}
    for team in teams:
        podiumDict[team["entry_name"]] = []
    for gw in range(STARTING_GW, currentGW + 1):
        podium = managersPodium(gw, minus)
        for p in range(len(podium)):
            for t in range(len(podium[p][0])):
                podiumDict[podium[p][0][t]].append(4 - p - 1)

    podiumList = sorted(podiumDict.items(), key=lambda x: sum(x[1]), reverse=True)
    for pod in range(len(podiumList)):
        podiumList[pod] = list(podiumList[pod])
        podiumList[pod].append(podiumList[pod][1].count(3))
        podiumList[pod].append(podiumList[pod][1].count(2))
        podiumList[pod].append(podiumList[pod][1].count(1))
        podiumList[pod].append(sum(podiumList[pod][1]))
    print(podiumList)


def bestManagerInGW(gw, minus=0):
    scoreList = []
    for team in teams:
        teamID = team['entry']
        gwInfo = getTeamGWInfo(teamID, gw)['entry_history']
        gwPoints = gwInfo['points'] - (gwInfo['event_transfers_cost'] * minus)
        scoreList.append([team['entry_name'], gwPoints])
    scoreList = sorted(scoreList, key=lambda x: x[1], reverse=True)
    best = scoreList[0]
    best.append(best[1] - scoreList[1][1])
    return best


def minsPerGW(teamID, startingGW=STARTING_GW):
    score = 0
    for gw in range(startingGW, currentGW + 1):
        print(gw)
        gwInfo = getTeamGWInfo(teamID, gw)
        for pick in gwInfo["picks"][:BENCH_POS]:
            playerInfo = getPlayerInfo(pick["element"])
            score += playerInfo["history"][gw - 1 - (currentGW - len(playerInfo['history']))]["minutes"]
    print(score / (11 * (currentGW - startingGW + 1)))
    return score / (11 * (currentGW - startingGW + 1))


def bestGWsAllTime():
    scoreList = []
    for team in teams:
        teamID = team['entry']
        team_name = team['entry_name']
        for gw in range(STARTING_GW, currentGW + 1):
            gwInfo = getTeamGWInfo(teamID, gw)['entry_history']
            gwPoints = gwInfo['points'] - gwInfo['event_transfers_cost']
            scoreList.append([team_name, gwPoints, gw])
    scoreList = sorted(scoreList, key=lambda x: x[1], reverse=True)
    print(scoreList)
    return scoreList


def playersMinsU60(teamID, startingGW=STARTING_GW):
    count = 0
    for gw in range(startingGW, currentGW + 1):
        print(gw)
        gwInfo = getTeamGWInfo(teamID, gw)
        for pick in gwInfo["picks"]:
            if not pick["multiplier"]:
                continue
            pStruct = gwStructByPlayerID(pick["element"], gw)
            for p in pStruct:
                count += (p["minutes"] < 60) and (p['minutes'] > 1)
            # minutes = sum(x["minutes"] for x in pStruct)

    print(count)
    return count


def redCards(startingGW=STARTING_GW):
    for team in teams:
        teamID = team["entry"]
        print(teamID)
        count = 0
        ownCount = 0
        for gw in range(startingGW, currentGW + 1):
            # print(gw)
            gwInfo = getTeamGWInfo(teamID, gw)
            for pick in gwInfo["picks"]:
                if not pick["multiplier"]:
                    continue
                pStruct = gwStructByPlayerID(pick["element"], gw)
                for p in pStruct:
                    count += p["red_cards"]
                    ownCount += p["own_goals"]
        print(count, ownCount)
    # return count


def ownGoals(startingGW=STARTING_GW):
    teamsList = []
    for team in teams:
        teamID = team["entry"]
        count = 0
        for gw in range(startingGW, currentGW + 1):
            print(gw)
            gwInfo = getTeamGWInfo(teamID, gw)
            for pick in gwInfo["picks"]:
                if not pick["multiplier"]:
                    continue
                pStruct = gwStructByPlayerID(pick["element"], gw)
                for p in pStruct:
                    count += p["own_goals"]
        teamsList.append((team["entry_name"], count))
    for c in teamsList:
        print(c)


def bonusKing(startingGW=STARTING_GW):
    for team in teams:
        teamID = team["entry"]
        print(teamID)
        count = 0
        for gw in range(startingGW, currentGW + 1):
            print(gw)
            gwInfo = getTeamGWInfo(teamID, gw)
            for pick in gwInfo["picks"]:
                if not pick["multiplier"]:
                    continue
                pStruct = gwStructByPlayerID(pick["element"], gw)
                for p in pStruct:
                    count += p["bonus"]
        print(count)


def pointsByPos(startingGW=STARTING_GW):
    for team in teams:
        teamPoints = [0, 0, 0, 0, 0]
        teamID = team["entry"]
        print(teamID)
        for gw in range(startingGW, currentGW + 1):
            # print(gw)
            gwInfo = getTeamGWInfo(teamID, gw)
            for pick in gwInfo["picks"]:
                if not pick["multiplier"]:
                    continue
                playerInfo = idToPStruct(pick["element"])
                pos = playerInfo["element_type"]
                pStruct = gwStructByPlayerID(pick["element"], gw)
                for p in pStruct:
                    teamPoints[pos - 1] += p["total_points"]
        print(teamPoints)


def lostCSAllTeams():
    players = {}
    for team in teams:
        # players[team["entry_name"]] = lostCS(team["entry"])
        pass
    players = sorted(players.items(), key=lambda x: x[1], reverse=True)
    for team in players:
        print(f"{team[0]} has {round(team[1], 2)} players that lost CS in the last 5 minutes of the game")


def playersU60AllTeams():
    players = {}
    for team in teams:
        players[team["entry_name"]] = playersMinsU60(team["entry"])
    players = sorted(players.items(), key=lambda x: x[1], reverse=True)
    for team in players:
        print(f"{team[0]} has {round(team[1], 2)} players that played under 60 minutes")


def csToManagers():
    teamDict = {}
    for pt in gdata["teams"]:
        teamDict[pt["id"]] = [pt["name"]]
    for team in teams:
        teamID = team["entry"]
        gwInfo = getTeamGWInfo(teamID, currentGW)
        for pick in gwInfo["picks"]:
            pStruct = idToPStruct(pick["element"])
            if pStruct["element_type"] > 3:
                break
            else:
                if not (team["entry_name"] in teamDict[pStruct["team"]]):
                    teamDict[pStruct["team"]].append(team["entry_name"])


def transferSummaryByGW(gw):
    transfersIn = {}
    transfersOut = {}
    for team in teams:
        teamID = team["entry"]
        team_name = team["entry_name"]
        transfers = getTeamTransfersInfo(teamID)
        for transfer in transfers:
            inPlayer = transfer['element_in']
            outPlayer = transfer['element_out']
            tgw = transfer['event']
            if tgw > gw:
                continue
            if gw != tgw:
                break
            if not inPlayer in transfersIn.keys():
                transfersIn[inPlayer] = []
            transfersIn[inPlayer].append(team_name)
            if outPlayer not in transfersOut.keys():
                transfersOut[outPlayer] = []
            transfersOut[outPlayer].append(team_name)
            if inPlayer in transfersOut.keys():
                if team_name in transfersOut[inPlayer]:
                    if len(transfersOut[inPlayer]) == 1:
                        transfersOut.pop(inPlayer)
                    else:
                        transfersOut[inPlayer].remove(team_name)
                    if len(transfersIn[inPlayer]) == 1:
                        transfersIn.pop(inPlayer)
                    else:
                        transfersIn[inPlayer].remove(team_name)
    transfersIn = sorted(transfersIn.items(), key=lambda x: len(x[1]), reverse=True)
    transfersOut = sorted(transfersOut.items(), key=lambda x: len(x[1]), reverse=True)
    print("Players transferred IN:\n")
    for transfer in transfersIn:
        print(f"{idToName(transfer[0])}: {transfer[1]}")
    print("\nPlayers transferred OUT:\n")
    for transfer in transfersOut:
        print(f"{idToName(transfer[0])}: {transfer[1]}")


def minsPerGWAllTeams():
    avgMins = {}
    for team in teams:
        avgMins[team["entry_name"]] = minsPerGW(team["entry"])
    avgMins = sorted(avgMins.items(), key=lambda x: x[1], reverse=True)
    for team in avgMins:
        print(f"{team[0]} players average {round(team[1], 2)} minutes per game")


def top10BestGWs():
    scores = bestGWsAllTime()[:10]
    for score in scores:
        print(f"{score[0]} scored {score[1]} points in GW{score[2]}\n")


def top10WorstGWs():
    scores = reversed(bestGWsAllTime()[-10:])
    for score in scores:
        print(f"{score[0]} scored {score[1]} points in GW{score[2]}\n")


def managerProfile(team):
    teamID = team["entry"]
    print("Team:", team['entry_name'])
    # print("Points:", team['total'])
    # print("Rank:", team['rank'])
    info = getManagerInfo(teamID)
    print("OVR:", info["summary_overall_rank"], "Israel:", info["leagues"]["classic"][1]["entry_rank"])
    print("Most Used Captains:", sorted(mostPopularCaptain(teamID).items(), key=lambda x: x[1], reverse=True)[:3])
    print("Most Bench Points:", bestBenchByManager(teamID))
    print("Best & Worst Transfers:")
    transfers = bestTransfers(useTeams=[teamIDtoStruct(teamID)], ret=True)
    printTransfers([transfers[0], transfers[-1]])
    print("Points per PL Team:", managerPointsAllocation(teamID, verbose=False))
    print("GW Points:")
    print(pointsByManager(teamID))
    # print("AllStars:")
    # print(managerAllstars(teamID))


def generalSeasonStats():
    # newPlayers = managerOriginalityRating()
    # for team in teams[10:10]:
    # managerProfile(team)
    #    print([idToName(p) for p in newPlayers[team["entry_name"]]], len(newPlayers[team["entry_name"]]))

    # bestManagerTable()
    # top10BestGWs()
    # top10WorstGWs()
    # bestTransfers()
    # pointsByPos()
    # bonusKing()
    # hitKing()
    worstBenchingPlayers()
    # getNumberOfTransfers()
    # mostUniqueManager()
    managersXGandXA()
    redCards()
    playersU60AllTeams()
    # ownGoals()
    # leagueAvg()
    benchPointsOverall()
    captaincyAccuracy()
    captaincyLoses()
    bestWildcard()
    # leagueAvg()
    # bestTransfers()
    bestFreeHit()
    # worldAvg()
    # luckiestPlayer()
    # captaincyAccuracy()
    # a = managerOriginalityRating()
    # a = sorted(a.items(), key=lambda x: len(x[1]), reverse=True)
    # for aa in a:
    #    print(f"{aa[0]} has introduced the league to {len(aa[1])} players: {list(map(idToName, aa[1]))}")


def mostOwnedNotInLeague(gw):
    sorted_players = sorted(sgdata, key=lambda x: float(x['selected_by_percent']), reverse=True)
    i = 0
    players = getLeaguePlayers(gw)
    while float(sorted_players[i]['selected_by_percent']) > 10:
        if not (sorted_players[i]["id"] in players):
            print('Name: {}, Selected by: {}%'.format(sorted_players[i]['web_name'],
                                                      sorted_players[i]['selected_by_percent']))
        i += 1
    print("\n")


def CSEffect(gw):
    teamDict = {}
    for pt in gdata["teams"]:
        teamDict[pt["name"]] = {}
    for team in teams:
        teamID = team["entry"]
        teamName = team["entry_name"]
        gwInfo = getTeamGWInfo(teamID, gw)
        if len(gwInfo["picks"]) == 16:
            pick = gwInfo["picks"][-1]
            playerID = pick["element"]
            playerInfo = idToPStruct(playerID)
            pTeam = gdata["teams"][playerInfo["team"] - 1]["name"]
            gamesNum = len(gwStructByPlayerID(playerID, gw))
            if not (teamName in teamDict[pTeam].keys()):
                teamDict[pTeam][teamName] = 0
            teamDict[pTeam][teamName] += 2 * gamesNum
        for pick in gwInfo["picks"]:
            playerID = pick["element"]
            playerInfo = idToPStruct(playerID)
            gamesNum = len(gwStructByPlayerID(playerID, gw))
            pTeam = gdata["teams"][playerInfo["team"] - 1]["name"]
            if not playerInfo['element_type'] in [1, 2, 3]:
                continue
            if not (teamName in teamDict[pTeam].keys()):
                teamDict[pTeam][teamName] = 0
            if playerInfo['element_type'] in [1, 2]:
                teamDict[pTeam][teamName] += 4 * pick["multiplier"] * gamesNum
            elif playerInfo['element_type'] == 3:
                teamDict[pTeam][teamName] += 1 * pick["multiplier"] * gamesNum
    newDict = {}
    for pTeam, teamData in teamDict.items():
        newTeamData = {}
        for teamName, score in teamData.items():
            if score not in newTeamData:
                newTeamData[score] = []
            newTeamData[score].append(teamName)
        newDict[pTeam] = newTeamData
    teamDict = newDict
    for pTeam, mTeam in teamDict.items():
        print(f"{pTeam} effective CS points:")
        if not mTeam:
            print("None\n")
            continue
        points = sorted(mTeam.items(), key=lambda x: x[0], reverse=True)
        i = 0
        while points[i][0]:
            print(f"{points[i][0]} points: {points[i][1]}")
            i += 1
            if i >= len(points):
                break
        print("\n")


def managersXGandXA():
    scores = []
    for team in teams:
        teamID = team["entry"]
        print(teamID)
        G, A, GC, xG, xA, xGC = 0, 0, 0, 0, 0, 0
        for gw in range(STARTING_GW, currentGW):
            gwInfo = getTeamGWInfo(teamID, gw)
            for pick in gwInfo["picks"][:11]:
                pid = pick["element"]
                gwStruct = gwStructByPlayerID(pid, gw)
                for struct in gwStruct:
                    xG += round(float(struct['expected_goals']), 2)
                    xA += round(float(struct['expected_assists']), 2)
                    xGC += round(float(struct['expected_goals_conceded']), 2)
                    G += round(float(struct['goals_scored']), 2)
                    A += round(float(struct['assists']), 2)
                    GC += round(float(struct['goals_conceded']), 2)
        scores.append((team["entry_name"], [round(xG, 2), G, round(xA, 2), A, round(xGC, 2), GC]))
    scores = sorted(scores, key=lambda x: x[1][0] + x[1][2] - (x[1][1] - x[1][3]), reverse=True)
    for score in scores:
        print(score)
    # for score in scores:
    #    print(score[0])
    # print(f"{score[0]} has scored {score[1][1]} goals while getting {score[1][0]} xG and {score[1][3]} assists "
    #      f"while getting {score[1][2]} xA - OVR diff {score[1][0] + score[1][2] - (score[1][1] - score[1][3])}")


def gwFuncs(gw):
    getCaptaincy(gw)
    transferSummaryByGW(gw)
    getUninqePlayers(gw)
    teamRepresentation(gw)
    mostOwnedNotInLeague(gw)
    CSEffect(gw)
    matrixByPLTeam(gw)


def playerRankingMatrix(gw, verbose=True):
    players = getEO(gw, verbose=False)
    matrix = {}
    for team in teams:
        matrix[team["entry_name"]] = {}
    for player in players:
        for manager in teams:
            if manager["entry_name"] in player[0]:
                triples = TripleCaptainsByPlayerEOStruct(player, gw)
                if manager["entry_name"] in player[3]:
                    capVal = 2
                    if manager["entry_name"] in triples:
                        capVal = 3
                        triples.remove(manager["entry_name"])
                    tempScore = capVal - (((len(player[0]) - 1 - (len(player[3]) - 1)) / len(teams)) + 3 *
                                          (len(triples) / len(teams)) + 2 * ((len(player[3]) - len(triples) - 1) /
                                                                             len(teams)))
                else:
                    tempScore = 1 - (((len(player[0]) - 1 - len(player[3])) / len(teams)) + 3 *
                                     (len(triples) / len(teams)) + 2 * ((len(player[3]) - len(triples)) / len(teams)))
            else:
                tempScore = player[1] / (len(teams) * -10)
            matrix[manager["entry_name"]][player[2]] = round(tempScore, 2)
    if verbose:
        for manager in matrix.keys():
            pTemp = sorted(matrix[manager].items(), key=lambda x: x[1], reverse=True)
            print(manager, "\n", pTemp[:5], "\n", list(reversed(pTemp[-5:])), "\n")
    return matrix, players


def calculate_weighted_percentage(distances):
    # Apply an exponential decay function to prioritize smaller distances
    calcWeights = np.exp(-np.array(distances) / 40)  # Adjust denominator to control decay rate

    # Normalize weights to sum to 100%
    total_weight = np.sum(calcWeights)
    percentages = (calcWeights / total_weight)
    percentages = list(percentages)
    for p in range(len(percentages)):
        percentages[p] = float(percentages[p])
    return percentages


def playerRankingMatrixByPointsDiff(gw, verbose=True):
    players = getEO(gw, verbose=False)
    matrix = {}
    weights = {}
    for team in teams:
        matrix[team["entry_name"]] = {}
        tpoints = team["history"]["current"][gw - 1]["total_points"]
        distances = []
        for otherTeam in teams:
            if otherTeam == team:
                continue
            distances.append(abs(tpoints - otherTeam["history"]["current"][gw - 1]["total_points"]))
        weights[team["entry_name"]] = list(calculate_weighted_percentage(distances))
        weights[team["entry_name"]].insert(teams.index(team), 0)
    for player in players:
        triples = TripleCaptainsByPlayerEOStruct(player, gw)
        for manager in teams:
            if manager["entry_name"] in player[0]:
                capVal = 1
                if manager["entry_name"] in player[3]:
                    capVal = 2
                    if manager["entry_name"] in triples:
                        capVal = 3
                        # triples.remove(manager["entry_name"])
            else:
                # tempScore = player[1] / (len(teams) * -10)
                capVal = 0
            tempScore = capVal
            for otherManager in range(len(teams)):
                if teams[otherManager] == manager:
                    continue
                if teams[otherManager]["entry_name"] in player[0]:
                    mul = 1
                    if teams[otherManager]["entry_name"] in player[3]:
                        mul = 2
                        if teams[otherManager]["entry_name"] in triples:
                            mul = 3
                    tempScore -= weights[manager["entry_name"]][otherManager] * mul
            matrix[manager["entry_name"]][player[2]] = round(tempScore, 2)
    if verbose:
        for manager in matrix.keys():
            pTemp = sorted(matrix[manager].items(), key=lambda x: x[1], reverse=True)
            print(manager, "\n", pTemp[:5], "\n", list(reversed(pTemp[-5:])), "\n")
    return matrix, players


def TripleCaptainsByPlayerEOStruct(player, gw):
    triples = []
    for team in teams:
        if not team["entry_name"] in player[3]:
            continue
        teamID = team["entry"]
        gwInfo = getTeamGWInfo(teamID, gw)
        if gwInfo["active_chip"] == '3xc':
            triples.append(team["entry_name"])
    return triples


'''def playerRankingMatrixByPostion(gw):
    players = getEO(gw)
    matrix = {}
    releventManagers = {}
    for team in teams:
        matrix[team["entry_name"]] = {}
    for teamIndex in range(teams):
        if teamIndex <teamIndex
        releventManagers[teams[teamIndex]["entry_name"]] =
    for player in players:
        for manager in teams:
            rank = team.index(manager["entry_name"])
            up = player[0][:index]
            down = player[0][index + 1:]
            if len(down) > 2:
                up += down[:2]
            else:
                up += down
            if manager["entry_name"] in player[0]:

                index = player[3].index(manager["entry_name"])
                c_up = player[3][:index]
                c_down = player[3][index + 1:]
                if len(c_down) > 2:
                    c_up+=c_down[:2]
                else:
                    c_up+=c_down
                if manager["entry_name"] in player[3]:
                    tempScore = 2 - (((len(player[0]) - 1 - (len(player[3]) - 1)) / len(teams)) + 2 * (
                                (len(player[3]) - 1) / len(teams)))
                else:
                    tempScore = 1 - (((len(player[0]) - 1 - len(player[3])) / len(teams)) + 2 * (
                                len(player[3]) / len(teams)))
            else:
                tempScore = player[1] / (len(teams) * -10)
            matrix[manager["entry_name"]][player[2]] = round(tempScore, 2)

    for manager in matrix.keys():
        pTemp = sorted(matrix[manager].items(), key=lambda x: x[1], reverse=True)
        print(manager, "\n", pTemp[:5], "\n", list(reversed(pTemp[-5:])), "\n")
    return matrix, players
    
    '''


def getMatrixScoreTotal(gw):
    scores = []
    matrix, players = playerRankingMatrix(gw)
    for team in teams:
        pTemp = sorted(matrix[team["entry_name"]].items(), key=lambda x: x[1], reverse=True)
        print(pTemp)
        total = round(sum([x[1] for x in pTemp]), 2)
        scores.append((team["entry_name"], total))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    for score in scores:
        print(f"{score[0]} has a total rating of {score[1]}")


def top5DifferenceMakers(teamName, startingGW=STARTING_GW):
    pDict = {}
    for gw in range(startingGW, currentGW + 1):
        matrix, players = playerRankingMatrixByPointsDiff(gw, verbose=False)
        for p in matrix[teamName].keys():
            if p in pDict.keys():
                pDict[p] += round(matrix[teamName][p], 2)
            else:
                pDict[p] = round(matrix[teamName][p], 2)
            pDict[p] = round(pDict[p], 2)
    pTemp = sorted(pDict.items(), key=lambda x: x[1], reverse=True)
    print(teamName, "\n", pTemp[:5], "\n", list(reversed(pTemp[-5:])), "\n")


def matrixByPLTeam(gw):
    matrix, players = playerRankingMatrix(gw)
    teamDict = {}
    for pt in gdata["teams"]:
        teamDict[pt["name"]] = {}
    for player in players:
        playerID = player[4]
        playerInfo = idToPStruct(playerID)
        pTeam = gdata["teams"][playerInfo["team"] - 1]["name"]
        for manager in matrix.keys():
            if player[2] in teamDict[pTeam].keys():
                teamDict[pTeam][player[2]].append((manager, matrix[manager][player[2]]))
            else:
                teamDict[pTeam][player[2]] = [(manager, matrix[manager][player[2]])]
    for plTeam in teamDict.keys():
        print(plTeam)
        for p in teamDict[plTeam].keys():
            print(f"{p}:")
            managers = sorted(teamDict[plTeam][p], key=lambda x: x[1], reverse=True)
            for key, group in groupby(managers, lambda x: x[1]):
                print(f"{key}: {[x[0] for x in list(group)]}")
            # print(p, for )
        print("\n")


def getGKsInfo():
    info = {}
    for player in sgdata:
        if player['element_type'] == 1:
            if player['minutes'] <= 100:
                info[player['web_name']] = ["NA", "NA", "NA", "NA", "NA", "NA",
                                            gdata['teams'][player['team'] - 1]['name'],
                                            player['now_cost'], player['id']]
            else:
                info[player['web_name']] = [player['clean_sheets_per_90'], player['saves_per_90'],
                                            player['starts'], round(player['bps'] / (player["minutes"] / 90), 2),
                                            player['expected_goals_conceded_per_90'], player['points_per_game'],
                                            gdata['teams'][player['team'] - 1]['name'], player['now_cost'],
                                            player['id']]
    for gk in info.keys():
        print(info[gk][-4])


def getDEFsInfo():
    info = {}
    for player in sgdata:
        if player['element_type'] == 2:
            if player['minutes'] <= 100:
                info[player['web_name']] = ["NA", "NA", "NA", "NA", "NA", "NA",
                                            gdata['teams'][player['team'] - 1]['name'],
                                            player['now_cost'], player['id'], "NA"]
            else:
                info[player['web_name']] = [player['clean_sheets_per_90'], player['expected_goals_per_90'],
                                            player['expected_assists_per_90'], player['starts_per_90'],
                                            round(player['bps'] / (player["minutes"] / 90), 2),
                                            player['expected_goals_conceded_per_90'], player['points_per_game'],
                                            gdata['teams'][player['team'] - 1]['name'], player['now_cost'],
                                            player['id'], player['first_name'] + " " + player['second_name']]
    for df in info.keys():
        print(info[df][-1])


def getPosInfo(pos):
    info = {}
    for player in sgdata:
        if player['element_type'] == pos:
            if player['minutes'] <= 100:
                info[player['web_name']] = ["NA", "NA", "NA", "NA", "NA", "NA",
                                            gdata['teams'][player['team'] - 1]['name'],
                                            player['now_cost'], player['id'], "NA"]
            else:
                info[player['web_name']] = [player['clean_sheets_per_90'], player['expected_goals_per_90'],
                                            player['expected_assists_per_90'], player['starts_per_90'],
                                            round(player['bps'] / (player["minutes"] / 90), 2),
                                            player['expected_goals_conceded_per_90'], player['points_per_game'],
                                            gdata['teams'][player['team'] - 1]['name'], player['now_cost'],
                                            player['id'], player['first_name'] + " " + player['second_name']]
    for p in info.keys():
        print(info[p][-1])


def FDRInfo():
    games = {}
    for i in range(1, 21):
        games[i] = []
    for f in fixtures:
        games[f['team_h']].append([f['team_a'], f['team_h_difficulty'], " (H)"])
        games[f['team_a']].append([f['team_h'], f['team_a_difficulty'], " (A)"])
    for t in games.keys():
        # print("---------------------------------------")
        print(gdata["teams"][t - 1]['name'])
        for game in games[t]:
            pass
        #    print(gdata["teams"][game[0] - 1]['name'] + game[2] + '\t', game[1])


def main():
    # FDRInfo()
    #getPosInfo(1)
    # getGKsInfo()
    # gwFuncs(currentGW)
    # bestTransfers()
    # captaincyLoses()
    # bestWildcard()
    gwFuncs(currentGW)
    # pointsAllocation()
    # allStars = managerAllstars(teams[2]["entry"])
    """for pos in allStars:
        for p in allStars[pos]:
            print(idToName(p[0]), p[1][0])
    a = managerOriginalityRating()
    a = sorted(a.items(), key=lambda x: len(x[1]), reverse=True)
    for aa in a:
        print(f"{aa[0]} has introduced the league to {len(aa[1])} players: {list(map(idToName, aa[1]))}")
"""


if __name__ == "__main__":

    # initial info gathering
    # --------------------------------------------------#
    gdata = fpl_api_get(GENERAL_INFO)
    fixtures = getFixtures()
    sgdata = sorted(gdata["elements"], key=lambda x: x['id'])
    i = 0
    while gdata['events'][i]:
        if gdata['events'][i]['is_next']:
            currentGW = i
            break
        i += 1
        if i == 38:
            currentGW = i
            break

    leagueID = "11862"
    ldata = getLeagueInfo(leagueID)
    teams = ldata["new_entries"]['results']
    #teams = ldata['standings']['results']
    for team in teams:
        team["history"] = getTeamHistoryInfo(team["entry"])
    # teams=[{"entry" : 146442, "entry_name": "Fpl_OzL"}]

    # ---------------------------------------------------#
    main()
