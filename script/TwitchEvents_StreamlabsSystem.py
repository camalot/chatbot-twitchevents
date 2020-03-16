#---------------------------------------
#   Import Libraries
#---------------------------------------
import sys
import clr
import json
import codecs
import os
import re
import random
import datetime
import glob
import time
import threading
import shutil
import tempfile
#import weakref
# point at lib folder for classes / references
sys.path.append(os.path.join(os.path.dirname(__file__), "..\Libs"))
clr.AddReferenceToFileAndPath(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "./libs/StreamlabsEventReceiver.dll"))
from StreamlabsEventReceiver import StreamlabsEventClient

clr.AddReference("IronPython.SQLite.dll")
clr.AddReference("IronPython.Modules.dll")

#---------------------------------------
#   [Required] Script Information
#---------------------------------------
ScriptName = "Twitch Events"
Website = "https://github.com/camalot/chatbot-twitchevents"
Description = "Let the bot respond to specific twitch events."
Creator = "DarthMinos"
Version = "1.0.0-snapshot"

# ---------------------------------------
#	Set Variables
# ---------------------------------------

Repo = "camalot/chatbot-twitchevents"
DonateLink = "https://paypal.me/camalotdesigns"
ReadMeFile = "https://github.com/" + Repo + "/blob/develop/ReadMe.md"
SettingsFile = os.path.join(os.path.dirname(__file__), "settings.json")

EventReceiver = None
ScriptSettings = None
LAST_PARSED = 1
Initialized = False
# ---------------------------------------
#	Script Classes
# ---------------------------------------


class Settings(object):
    """ Class to hold the script settings, matching UI_Config.json. """

    def __init__(self, settingsfile=None):
        """ Load in saved settings file if available else set default values. """
        try:
            self.StreamlabsToken = ""
            self.EnableFollow = True
            self.EnableSubscribe = True
            self.EnableCheer = True
            self.CheerMinimum = 1
            self.EnableHost = True
            self.EnableRaid = True
            self.EnableDonation = True

            self.FollowResponse = ""
            self.SubscriptionResponse = ""
            self.CheerResponse = ""
            self.DonationResponse = ""
            self.HostResponse = ""
            self.RaidResponse = ""

            SOEPath = os.path.realpath(os.path.join(os.path.dirname(__file__), "../Shoutout"))
            SOEExists = os.path.isdir(SOEPath)
            self.EnableRaidShoutoutHook = SOEExists
            self.EnableHostShoutoutHook = SOEExists

            with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
                fileSettings = json.load(f, encoding="utf-8")
                self.__dict__.update(fileSettings)
        except Exception as e:
            Parent.Log(ScriptName, str(e))

    def Reload(self, jsonData):
        fileLoadedSettings = json.loads(jsonData, encoding="utf-8")
        self.__dict__.update(fileLoadedSettings)

#---------------------------------------
#   [Required] Initialize Data / Load Only
#---------------------------------------


def Init():
    global ScriptSettings
    global EventReceiver
    global Initialized

    if Initialized:
        return
    ScriptSettings = Settings(SettingsFile)

    EventReceiver = StreamlabsEventClient()
    EventReceiver.StreamlabsSocketConnected += EventReceiverConnected
    EventReceiver.StreamlabsSocketDisconnected += EventReceiverDisconnected
    EventReceiver.StreamlabsSocketEvent += EventReceiverEvent
    Parent.Log(ScriptName, "Loaded")
    if ScriptSettings.StreamlabsToken and not EventReceiver.IsConnected:
        Parent.Log(ScriptName, "Connecting")
        EventReceiver.Connect(ScriptSettings.StreamlabsToken)
    Initialized = True
    return
def ScriptToggled(state):
    if state:
        Init()
    else:
        Unload()
    return

def ReloadSettings(jsondata):
    Unload()
    Init()
    return


def Unload():
    global EventReceiver
    global Initialized
    if EventReceiver is not None:
        EventReceiver.StreamlabsSocketConnected -= EventReceiverConnected
        EventReceiver.StreamlabsSocketDisconnected -= EventReceiverDisconnected
        EventReceiver.StreamlabsSocketEvent -= EventReceiverEvent
        if EventReceiver.IsConnected:
            EventReceiver.Disconnect()
        EventReceiver = None
    Initialized = False    
    return


def Execute(data):
    return


def Tick():
    return

def Parse(parseString, userid, username, targetid, targetname, message):
    resultString = parseString or ""
    resultString = resultString.replace("$username", username or "")
    resultString = resultString.replace("$userid", userid or "")
    resultString = resultString.replace("$targetname", targetname or "")
    resultString = resultString.replace("$targetid", targetid or "")
    Parent.Log(ScriptName, resultString)
    return resultString

def EventReceiverConnected(sender, args):
    Parent.Log(ScriptName, "Streamlabs event websocket connected")
    return


def EventReceiverDisconnected(sender, args):
    Parent.Log(ScriptName, "Streamlabs event websocket disconnected")
    return


def EventReceiverEvent(sender, args):
    global ScriptSettings
    global LAST_PARSED
    evntdata = args.Data
    if LAST_PARSED == evntdata.GetHashCode() or evntdata is None:
        return  # Fixes a strange bug where Chatbot registers to the DLL multiple times
    LAST_PARSED = evntdata.GetHashCode()
    Parent.Log(ScriptName, "type: " + evntdata.Type)
    for message in evntdata.Message:
        if message:
            outMessage = None
            if evntdata.Type == "follow" or (evntdata.Type == "subscription" and evntdata.For == "youtube_account") and ScriptSettings.EnableFollow:
                outMessage = Parse(ScriptSettings.FollowResponse, str(message.Name).lower(),
                                   str(message.Name), str(message.Name).lower(),
                                   str(message.Name), None)
            elif (evntdata.Type == "subscription" or evntdata.Type == "resub") and evntdata.For == "twitch_account" and ScriptSettings.EnableSubscribe:
                outMessage = Parse(ScriptSettings.SubscriptionResponse, str(message.Name).lower(),
                                   str(message.Name), str(message.Name).lower(),
                                   str(message.Name), None)
            elif evntdata.Type == "subMysteryGift" and ScriptSettings.EnableSubscribe:
                outMessage = Parse(ScriptSettings.SubscriptionResponse, str(message.Name).lower(),
                                   str(message.Name), str(message.Name).lower(),
                                   str(message.Name), None)
            elif evntdata.Type == "bits" and ScriptSettings.EnableCheer and message.Amount >= ScriptSettings.CheerMinimum:
                outMessage = Parse(ScriptSettings.CheerResponse, str(message.Name).lower(),
                                   str(message.Name), str(message.Name).lower(),
                                   str(message.Name), None)
            elif evntdata.Type == "host" and ScriptSettings.EnableHost:
                outMessage = Parse(ScriptSettings.HostResponse, str(message.Name).lower(),
                                   str(message.Name), str(message.Name).lower(),
                                   str(message.Name), None)
            elif evntdata.Type == "raid" and ScriptSettings.EnableRaid:
                outMessage = Parse(ScriptSettings.RaidResponse, str(message.Name).lower(),
                                   str(message.Name), str(message.Name).lower(),
                                   str(message.Name), None)
                if ScriptSettings.EnableHostShoutoutHook:
                    SendShoutoutWebsocket(str(message.Name))
            elif evntdata.Type == "donation" and ScriptSettings.EnableDonation:
                outMessage = Parse(ScriptSettings.DonationResponse, str(message.Name).lower(),
                                   str(message.Name), str(message.Name).lower(),
                                   str(message.Name), None)
                if ScriptSettings.EnableRaidShoutoutHook:
                    SendShoutoutWebsocket(str(message.Name))

            if outMessage != "" and outMessage is not None:
                Parent.SendTwitchMessage(outMessage)
    return


def SendShoutoutWebsocket(username):
    payload = {
        "user": username
    }
    SendWebsocketData("EVENT_SO_COMMAND", payload)
    return

def SendWebsocketData(eventName, payload):
    Parent.Log(ScriptName, "Trigger Event: " + eventName)
    Parent.BroadcastWsEvent(eventName, json.dumps(payload))
    return

def OpenFollowOnTwitchLink():
    os.startfile("https://twitch.tv/DarthMinos")
    return

def OpenReadMeLink():
    os.startfile(ReadMeFile)
    return
def OpenDonateLink():
    os.startfile(DonateLink)
    return


def OpenShoutoutOverlayLink():
    os.startfile("https://github.com/camalot/chatbot-shoutout")
    return

def OpenScriptUpdater():
    currentDir = os.path.realpath(os.path.dirname(__file__))
    chatbotRoot = os.path.realpath(os.path.join(currentDir, "../../../"))
    libsDir = os.path.join(currentDir, "libs/updater")
    try:
        src_files = os.listdir(libsDir)
        tempdir = tempfile.mkdtemp()
        Parent.Log(ScriptName, tempdir)
        for file_name in src_files:
            full_file_name = os.path.join(libsDir, file_name)
            if os.path.isfile(full_file_name):
                Parent.Log(ScriptName, "Copy: " + full_file_name)
                shutil.copy(full_file_name, tempdir)
        updater = os.path.join(tempdir, "ChatbotScriptUpdater.exe")
        updaterConfigFile = os.path.join(tempdir, "update.manifest")
        repoVals = Repo.split('/')
        updaterConfig = {
            "path": os.path.realpath(os.path.join(currentDir,"../")),
            "version": Version,
            "name": ScriptName,
            "requiresRestart": True,
            "kill": [],
            "execute": {
                "before": [],
                "after": []
            },
            "chatbot": os.path.join(chatbotRoot, "Streamlabs Chatbot.exe"),
            "script": os.path.basename(os.path.dirname(os.path.realpath(__file__))),
            "website": Website,
            "repository": {
                "owner": repoVals[0],
                "name": repoVals[1]
            }
        }
        configJson = json.dumps(updaterConfig)
        with open(updaterConfigFile, "w+") as f:
            f.write(configJson)
        os.startfile(updater)
    except OSError as exc: # python >2.5
        raise
