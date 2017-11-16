# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.events
import octoprint._version
import requests

# TODO:
# - End user configurable messages
# - Parse req.text for error and display popup on web ui
# - Get actual error details /  {error} is not working as expected

# Known Bugs:
# - Pause is not triggering when M600 is ran. Need to check norma pause mode.

# Custom variables
informerurl = 'https://informer.repetier-apps.com/api/1/message.php'

# App Ids for the notifications. Found via packet capture. (And asking nicely for my own!)
# Repetier-Host / Xh9lPgJujHahKiUq; 1: OK, 2: ERROR, 3: INFO, 4: PAUSE
# Repetier-Server / uH6CeLoNu8X4AfQp; 5: OK, 6: ERROR, 7: INFO, 8: PAUSE
# OctoPrint / 0dd1065d141a856b22ef89b7d84b1ed5; 9: OK, 10: ERROR, 11: INFO, 12: PAUSE

informerappid = '0dd1065d141a856b22ef89b7d84b1ed5'
inform_ok = '9'
inform_err = '10'
inform_info = '11'
inform_pause = '12'

# Timer
from octoprint.util import RepeatedTimer
timerStarted = False
timerProgress = '0'
timer = None

# Grab OctoPrint version info
# Please tell me if there is a better or cleaner way to grab the x.y.z version
from octoprint._version import get_versions
versions = get_versions()
octoversion = versions['version']

class RepetierinformerPlugin(octoprint.plugin.StartupPlugin,
				octoprint.plugin.ProgressPlugin,
				octoprint.plugin.EventHandlerPlugin,
				octoprint.plugin.SettingsPlugin,
				octoprint.plugin.AssetPlugin,
				octoprint.plugin.TemplatePlugin):

	def get_settings_defaults(self):
		return dict(
			enabled=False,
			hostname="OctoPrint",
			informergroup="",
			url="",
			devrelease=False,
			notify=dict(
				startup=False,
				printstart=False,
				printfailed=True,
				printdone=True,
				printcancel=False,
				printpause=False,
				printresume=False,
				timelapsestart=False,
				timelapsefinish=True,
				timelapsefailed=True,
				printerconnected=False,
				printerdisconnected=False,
				printererror=True,
				interval=0
			)
		)

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False)
		]

	def get_update_information(self):
		mybranch = 'master'
		if self._settings.get(['devrelease']):
			mybranch = 'dev'
			
		return dict(
			RepetierInformer=dict(
				displayName=self._plugin_name,
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="drdelaney",
				repo="OctoPrint-RepetierInformer",
				current=self._plugin_version,
				branch=mybranch,

				# update method: pip
				pip="https://github.com/drdelaney/OctoPrint-RepetierInformer/archive/{target_version}.zip"
			)
		)

	# Function to handle the message generation
	def sendInformer(self,header,preview,message,image=inform_info):
		# Easier to read variables
		customurl = ""
		group = self._settings.get(["informergroup"])
		useragent = 'OctoPrint/'+octoversion+' ('+self._plugin_name+'/'+self._plugin_version+')'

		# Return if not enabled
		if not self._settings.get(['enabled']):
			self._logger.info("Not enabled, will not send.")
			return

		# Add the hostname if defined
		if self._settings.get(['hostname']):
			header = self._settings.get(['hostname'])+': '+header

		# Set Custom URL if defined
		if self._settings.get(["url"]):
			customurl = self._settings.get(["url"])

		# Build the data to post
		informerdata = {'app':informerappid,'g':group,'img':image,'head':header,'short':preview,'msg':message,'url':customurl}

		# Call the normal headers so we can update the user-agent
		headers = requests.utils.default_headers()
		headers.update( { 'User-Agent': useragent, } )

		req = requests.post(informerurl, headers=headers, data=informerdata)
		self._logger.info("Sent header: "+header)
		self._logger.info(req.text)

	def sendTest(self):
		self.sendInformer("header text","preview","hello world",inform_info)

	def sendInformerIp(self):
		# We only need socket here, to grab the IP
		import socket

		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('google.com', 0))
		ipaddr = s.getsockname()[0]
		self.sendInformer("My IP Address",self._settings.get(['hostname'])+": "+ipaddr,"My IP is "+ipaddr,inform_info)

	def sendInformerStatus(self):
		global timerProgress

		self.sendInformer("Print Progress","Print Progress "+str(timerProgress)+"%","Print Progress "+str(timerProgress)+"%",inform_info)

	def startTimer(self):
		global timerStarted
		global timer

		if not self._settings.get(['enabled']):
			self._logger.info("Not enabled, will not start timer.")
			return

		# We know 0 is off/false
		if not int(self._settings.get(['notify','interval'])):
			self._logger.info("Notify interval disabled")

			timerStarted = False

			return

		# Protect ourself from spamming Repetier
		if (int(self._settings.get(['notify','interval'])) <= 299):
			self._logger.info("Notify interval of "+str(self._settings.get(['notify','interval']))+" is set too low. Not starting timer.")
			return

		self._logger.info("Starting timer with an interval of "+str(self._settings.get(['notify','interval']))+" seconds")

		timerStarted = True

		# Blank in case an old timer exists
		timer = None
		timer = RepeatedTimer(int(self._settings.get(['notify','interval'])), self.sendInformerStatus, run_first=False)
		timer.start()

		return

	def stopTimer(self):
		global timerStarted
		global timerProgress
		global timer
		self._logger.info("Stopping the timer")

		timer.cancel()

		timerStarted = False
		timerProgress = '0'

#       def on_settings_save(self, data):
#       return


	def on_print_progress(self, storage, path, progress):
		global timerProgress

		timerProgress = progress

	def on_after_startup(self):
		if not self._settings.get(['enabled']):
			return

		if self._settings.get(['notify','startup']):
			self._logger.info("Sending IP to group "+self._settings.get(["informergroup"]))
			self.sendInformerIp()
			return

	def on_event(self, event, payload):
		# Return if not enabled
		if not self._settings.get(['enabled']):
			self._logger.info("Not enabled, will not send.")
			return

		# Handle events
		if event == 'Connected':
			if self._settings.get(['notify','printerconnected']):
				self.sendInformer("Printer Connected","Connected to Printer","A connection has been established with the printer",inform_info)
				return
		if event == 'Disconnected':
			if self._settings.get(['notify','printerdisconnected']):
				self.sendInformer("Printer Disconnected","Disconnected from Printer","The connection to the printer has been disconnected",inform_info)
				return
		if event == 'Error':
			if self._settings.get(['notify','printererror']):
                                # FIXME
				#self.sendInformer("Printer Error","Communication error with Printer","{error}",inform_err)
				self.sendInformer("Printer Error","Communication error with Printer","Communication error with Printer",inform_err)
				return
		if event == 'PrintStarted':
			if not timerStarted:
				self.startTimer()

			if self._settings.get(['notify','printstart']):
				self.sendInformer("Printing started","Printng has started","Printing has started",inform_info)
				return
		if event == 'PrintFailed':
			if timerStarted:
				self.stopTimer()

			if self._settings.get(['notify','printfailed']):
				self.sendInformer("Printing failed","Printng has failed","Printing has Failed",inform_err)
				return
		if event == 'PrintDone':
			if timerStarted:
				self.stopTimer()

			if self._settings.get(['notify','printdone']):
				self.sendInformer("Printing finished","Printng has finished","Printing has finished",inform_ok)
				return
		if event == 'PrintCancelled':
			if timerStarted:
				self.stopTimer()

			if self._settings.get(['notify','printcancel']):
				self.sendInformer("Printing canceled","Printng has been canceled","Printing has been cacnceled by user",inform_err)
				return
		if event == 'PrintPaused':
			if self._settings.get(['notify','printpause']):
				self.sendInformer("Printing paused","Printng has been paused","Printing has been paused",inform_pause)
				return
		if event == 'PrintResumed':
			if self._settings.get(['notify','printresume']):
				self.sendInformer("Printing resumed","Printng has been resumed","Printing has been resumed",inform_ok)
				return
		if event == 'MovieRendering':
			if self._settings.get(['notify','timelapsestart']):
				self.sendInformer("Timelapse started","Timelapse rendering has stared","Timelapse rendering has started",inform_info)
				return
		if event == 'MovieDone':
			if self._settings.get(['notify','timelapsefinish']):
				self.sendInformer("Timelapse finshed","Timelapse rendering has finished","Timelapse rendering has finished",inform_ok)
				return
		if event == 'MovieFailed':
			if self._settings.get(['notify','timelapsefailed']):
                                # FIXME
				#self.sendInformer("Timelapse failed","Timelapse rendering has failed","{error}",inform_err)
				self.sendInformer("Timelapse failed","Timelapse rendering has failed","Timelapse rendering has failed",inform_err)
				return

        def hook_gcode_pause(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
                # Return if not enabled
                if not self._settings.get(['enabled']):
                        self._logger.info("Not enabled, will not send.")
                        return

                # Handle pause/resume gcodes
                if gcode and gcode == "M24":
                        if self._settings.get(['notify','printresume']):
                                self.sendInformer("Printing resumed","Printng has been resumed","Printing has been resumed via M24",inform_ok)
                                return
                if gcode and gcode == "M25":
                        if self._settings.get(['notify','printpause']):
                                self.sendInformer("Printing paused","Printng has been paused","Printing has been paused via M25",inform_pause)
                                return
                if gcode and gcode == "M226":
                        if self._settings.get(['notify','printpause']):
                                self.sendInformer("Printing paused","Printng has been paused","Printing has been paused via M226",inform_pause)
                                return
                if gcode and gcode == "M600":
                        if self._settings.get(['notify','printpause']):
                                self.sendInformer("Printing paused","Printng has been paused","Printing has been paused via M600",inform_pause)
                                return


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Repetier-Informer for OctoPrint"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = RepetierinformerPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
                "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.hook_gcode_pause
                
	}

