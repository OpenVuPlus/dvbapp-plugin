#
#  Partnerbox E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2009
#  Support: www.dreambox-tools.info
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#

import urllib
from twisted.internet import reactor
from twisted.web import client
from twisted.web.client import HTTPClientFactory
from base64 import encodestring
import xml.etree.cElementTree

remote_timer_list = None
oldIP = None

def getTimerType(refstr, beginTime, duration, eventId, timer_list):
	pre = 1
	post = 2
	type = 0
	endTime = beginTime + duration
	for x in timer_list:
		if x.servicereference.upper() == refstr.upper():
			if x.eventId == eventId:
				return True
			beg = x.timebegin
			end = x.timeend
			if beginTime > beg and beginTime < end and endTime > end:
				type |= pre
			elif beginTime < beg and endTime > beg and endTime < end:
				type |= post
	if type == 0:
		return True
	elif type == pre:
		return False
	elif type == post:
		return False
	else:
		return True

def isInTimerList(begin, duration, service, eventid, timer_list):
	time_match = 0
	chktime = None
	chktimecmp = None
	chktimecmp_end = None
	end = begin + duration
	timerentry = None
	for x in timer_list:
		if x.servicereference.upper() == service.upper():
			if x.repeated != 0:
				if chktime is None:
					chktime = localtime(begin)
					chktimecmp = chktime.tm_wday * 1440 + chktime.tm_hour * 60 + chktime.tm_min
					chktimecmp_end = chktimecmp + (duration / 60)
				time = localtime(x.timebegin)
				for y in range(7):
					if x.repeated & (2 ** y):
						timecmp = y * 1440 + time.tm_hour * 60 + time.tm_min
						if timecmp <= chktimecmp < (timecmp + ((x.timeend - x.timebegin) / 60)):
							time_match = ((timecmp + ((x.timeend - x.timebegin) / 60)) - chktimecmp) * 60
						elif chktimecmp <= timecmp < chktimecmp_end:
							time_match = (chktimecmp_end - timecmp) * 60
			else: 
				if begin <= x.timebegin <= end:
					diff = end - x.timebegin
					if time_match < diff:
						time_match = diff
				elif x.timebegin <= begin <= x.timeend:
					diff = x.timeend - begin
					if time_match < diff:
						time_match = diff
			if time_match:
				if getTimerType(service, begin, duration, eventid, timer_list):
					timerentry = x
				break
	return timerentry


class E2Timer:
	def __init__(self, servicereference = "", servicename = "", name = "", disabled = 0, timebegin = 0, timeend = 0, duration = 0, startprepare = 0, state = 0, repeated = 0, justplay = 0, eventId = 0, afterevent = 0, dirname = "", description = "", type = 0):
		self.servicereference = servicereference
		self.servicename = servicename
		self.name = name
		self.disabled = disabled
		self.timebegin = timebegin
		self.timeend = timeend
		self.duration = duration
		self.startprepare = startprepare
		self.state = state
		self.repeated = repeated
		self.justplay = justplay
		self.eventId = eventId
		self.afterevent = afterevent
		self.dirname = dirname
		self.description = description
		self.type = type
		if type != 0: # E1 Timerlist
			self.timeend = timebegin + duration
			self.name = description
			if type & PlaylistEntry.isRepeating:
				self.repeated = 1
			self.dirname = "/hdd/movie/"

def FillE2TimerList(xmlstring):
	E2TimerList = []
	try: root = xml.etree.cElementTree.fromstring(xmlstring)
	except: return E2TimerList
	for timer in root.findall("e2timer"):
		E2TimerList.append(E2Timer(
			servicereference = str(timer.findtext("e2servicereference", '').encode("utf-8", 'ignore')),
			servicename = str(timer.findtext("e2servicename", 'n/a').encode("utf-8", 'ignore')),
			name = str(timer.findtext("e2name", '').encode("utf-8", 'ignore')),
			disabled = int(timer.findtext("e2disabled", 0)),
			timebegin = int(timer.findtext("e2timebegin", 0)),
			timeend = int(timer.findtext("e2timeend", 0)),
			duration = int(timer.findtext("e2duration", 0)),
			startprepare = int(timer.findtext("e2startprepare", 0)),
			state = int(timer.findtext("e2state", 0)),
			repeated = int(timer.findtext("e2repeated", 0)),
			justplay = int(timer.findtext("e2justplay", 0)),
			eventId = int(timer.findtext("e2eit", -1)),
			afterevent = int(timer.findtext("e2afterevent", 0)),
			dirname = str(timer.findtext("e2dirname", '').encode("utf-8", 'ignore')),
			description = str(timer.findtext("e2description", '').encode("utf-8", 'ignore')),
			type = 0))
	return E2TimerList


def FillE1TimerList(xmlstring):
	E1TimerList = []
	try: root = xml.etree.cElementTree.fromstring(xmlstring)
	except: return E1TimerList
	for timer in root.findall("timer"):
		typedata = int(timer.findtext("typedata", 0))
		for service in timer.findall("service"):
			servicereference = str(service.findtext("reference", '').encode("utf-8", 'ignore'))
			servicename = str(service.findtext("name", 'n/a').encode("utf-8", 'ignore'))
		for event in timer.findall("event"):
			timebegin = int(event.findtext("start", 0))
			duration = int(event.findtext("duration", 0))
			description = str(event.findtext("description", '').encode("utf-8", 'ignore'))
		E1TimerList.append(E2Timer(servicereference = servicereference, servicename = servicename, name = "", disabled = 0, timebegin = timebegin, timeend = 0, duration = duration, startprepare = 0, state = 0 , repeated = 0, justplay= 0, eventId = -1, afterevent = 0, dirname = "", description = description, type = typedata))
	return E1TimerList

class myHTTPClientFactory(HTTPClientFactory):
	def __init__(self, url, method='GET', postdata=None, headers=None,
	agent="Twisted Remotetimer", timeout=0, cookies=None,
	followRedirect=1, lastModified=None, etag=None):
		HTTPClientFactory.__init__(self, url, method=method, postdata=postdata,
		headers=headers, agent=agent, timeout=timeout, cookies=cookies,followRedirect=followRedirect)


def sendPartnerBoxWebCommand(url, contextFactory=None, timeout=60, username = "root", password = "", *args, **kwargs):
	scheme, host, port, path = client._parse(url)
	basicAuth = encodestring(("%s:%s")%(username,password))
	authHeader = "Basic " + basicAuth.strip()
	AuthHeaders = {"Authorization": authHeader}
	if kwargs.has_key("headers"):
		kwargs["headers"].update(AuthHeaders)
	else:
		kwargs["headers"] = AuthHeaders
	factory = myHTTPClientFactory(url, *args, **kwargs)
	reactor.connectTCP(host, port, factory, timeout=timeout)
	return factory.deferred

class PlaylistEntry:

	PlaylistEntry=1			# normal PlaylistEntry (no Timerlist entry)
	SwitchTimerEntry=2		#simple service switch timer
	RecTimerEntry=4			#timer do recording
	
	recDVR=8				#timer do DVR recording
	recVCR=16				#timer do VCR recording (LIRC) not used yet
	recNgrab=131072			#timer do record via Ngrab Server

	stateWaiting=32			#timer is waiting
	stateRunning=64			#timer is running
	statePaused=128			#timer is paused
	stateFinished=256		#timer is finished
	stateError=512			#timer has error state(s)

	errorNoSpaceLeft=1024	#HDD no space Left ( recDVR )
	errorUserAborted=2048	#User Action aborts this event
	errorZapFailed=4096		#Zap to service failed
	errorOutdated=8192		#Outdated event

	boundFile=16384			#Playlistentry have an bounded file
	isSmartTimer=32768		#this is a smart timer (EIT related) not uses Yet
	isRepeating=262144		#this timer is repeating
	doFinishOnly=65536		#Finish an running event/action

	doShutdown=67108864		#timer shutdown the box
	doGoSleep=134217728		#timer set box to standby

	Su=524288
	Mo=1048576
	Tue=2097152
	Wed=4194304
	Thu=8388608
	Fr=16777216
	Sa=33554432


def SetPartnerboxTimerlist(partnerboxentry = None):
	global remote_timer_list
	global CurrentIP
	if partnerboxentry is None:
		return	
	try:
		password = partnerboxentry.password.value
		username = "root"
		CurrentIP = partnerboxentry.ip.value
		ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		port = partnerboxentry.port.value
		if int(partnerboxentry.enigma.value) == 0:
			sCommand = "http://%s:%s@%s:%d/web/timerlist" % (username, password, ip,port)
		else:
			sCommand = "http://%s:%s@%s:%d/xml/timers" % (username, password, ip,port)
		print "[RemoteEPGList] Getting timerlist data from %s..."%ip
		f = urllib.urlopen(sCommand)
		sxml = f.read()
		if int(partnerboxentry.enigma.value) == 0:
			remote_timer_list = FillE2TimerList(sxml)
		else:
			remote_timer_list = FillE1TimerList(sxml)
	except: pass