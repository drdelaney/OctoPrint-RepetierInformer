# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint._version
import requests

# TODO:
# - Print status every X minutes
# - End user configurable messages
# - Parse req.text for error and display popup on web ui

# Custom variables
informerappid = 'Xh9lPgJujHahKiUq' # this should be changed. for now, we are cloning Repetier
informerurl = 'http://informer.repetier-apps.com/api/1/message.php'

# Grab OctoPrint version info
# Please tell me if there is a better or cleaner way to grab the x.y.z version
from octoprint._version import get_versions
versions = get_versions()
octoversion = versions['version']

# Make a generic useragent string
#useragent = 'OctoPrint/xx ('+self._plugin_name+'/'+self._plugin_version+')'

class RepetierinformerPlugin(octoprint.plugin.StartupPlugin,
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
				printererror=True
			)
		)

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False)
		]

	def get_update_information(self):
		return dict(
			RepetierInformer=dict(
				displayName="Repetier-Informer for OctoPrint",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="drdelaney",
				repo="OctoPrint-RepetierInformer",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/drdelaney/OctoPrint-RepetierInformer/archive/{target_version}.zip"
			)
		)

	# Function to handle the message generation
	def sendInformer(self,header,preview,message,image="3"):
		# Image numbers; 1: OK, 2: ERROR, 3: INFO, 4: PAUSE

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
		self._logger.info(req.text)

	def sendTest(self):
		self.sendInformer("header text","preview","hello world","3")

	def sendInformerIp(self):
		# We only need socket here, to grab the IP
		import socket

		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('google.com', 0))
		ipaddr = s.getsockname()[0]
		self.sendInformer("My IP Address",ipaddr,"My IP is "+ipaddr,"3")

	def on_after_startup(self):
		if not self._settings.get(['enabled']):
			return

		if self._settings.get(['notify','startup']):
			self._logger.info("Sending IP to group")
			self.sendInformerIp()
			return

	def on_event(self, event, payload):
		# Return if not enabled
		if not self._settings.get(['enabled']):
			self._logger.info("Not enabled, will not send.")
			return

		# Handle events
		# Image numbers; 1: OK, 2: ERROR, 3: INFO, 4: PAUSE
		if event == 'Connected':
			if self._settings.get(['notify','printerconnected']):
				self.sendInformer("Printer Connected","Connected to Printer","A connection has been established with the printer","3")
				return
		if event == 'Disconnected':
			if self._settings.get(['notify','printerdisconnected']):
				self.sendInformer("Printer Disconnected","Disconnected from Printer","The connection to the printer has been disconnected","3")
				return
		if event == 'Error':
			if self._settings.get(['notify','printererror']):
				self.sendInformer("Printer Error","Communication error with Printer","{error}","2")
				return
		if event == 'PrintStarted':
			if self._settings.get(['notify','printstart']):
				self.sendInformer("Printing started","Printng has started","Printing has started","3")
				return
		if event == 'PrintFailed':
			if self._settings.get(['notify','printfailed']):
				self.sendInformer("Printing failed","Printng has failed","Printing has Failed","2")
				return
		if event == 'PrintDone':
			if self._settings.get(['notify','printdone']):
				self.sendInformer("Printing finished","Printng has finished","Printing has finished","1")
				return
		if event == 'PrintCancelled':
			if self._settings.get(['notify','printcancel']):
				self.sendInformer("Printing cancleed","Printng has been canceled","Printing has been cacnceled by user","2")
				return
		if event == 'PrintPaused':
			if self._settings.get(['notify','printpause']):
				self.sendInformer("Printing paused","Printng has been paused","Printing has been paused","4")
				return
		if event == 'PrintResumed':
			if self._settings.get(['notify','printresume']):
				self.sendInformer("Printing resumed","Printng has been resumed","Printing has been resumed","1")
				return
		if event == 'MovieRendering':
			if self._settings.get(['notify','timelapsestart']):
				self.sendInformer("Timelapse started","Timelapse rendering has stared","Timelapse rendering has started","3")
				return
		if event == 'MovieDone':
			if self._settings.get(['notify','timelapsefinish']):
				self.sendInformer("Timelapse finshed","Timelapse rendering has finished","Timelapse rendering has finished","1")
				return
		if event == 'MovieFailed':
			if self._settings.get(['notify','timelapsefailed']):
				self.sendInformer("Timelapse failed","Timelapse rendering has failed","{error}","2")
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
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

