import sys
from gi.repository import Gtk
import requests
from bs4 import BeautifulSoup as bs
import os
import ConfigParser
import base64
import time

class HellowWorldGTK:
	global courses
	courses = None
	global directory
	directory = ""
	global session
	session = None
	global config
	config = ConfigParser.RawConfigParser()
	
	if os.path.exists("moodleset.cfg"):
		if(open("moodleset.cfg","r").read()):
			config.read("moodleset.cfg")
			directory = config.get("Login","dir")
			
	def download_file(self,url,name,session):
		tries = 0
		try:
    			r = session.get(url, stream=True)
    			if os.path.exists(name):
    				return ""
    			with open(name, 'wb') as f:
        			for chunk in r.iter_content(chunk_size=1024): 
            				if chunk:
                				f.write(chunk)
                	time.sleep(1)
    			return name
    		except:
    			print "Exception"
    			if not (tries is 5):
    				self.download_file(url,name,session)

	def getdata(self,textbuffer,course,name,session):
		data = session.get(course).text
		data = data.encode('utf-8')
		if "403 Forbidden" in data:
			print "Session expired"
			return
		if os.path.exists(directory+name+"/last_mod.txt"):
			lmod = open(directory+name+"/last_mod.txt","r")
			if len(data) == len(lmod.read()):
				end_iter = textbuffer.get_end_iter()
				textbuffer.insert(end_iter, name+"\t:\tNo updates\n")
				self.tupdate()
				return
			else:
				lmod = open(directory+name+"/last_mod.txt","w")
				end_iter = textbuffer.get_end_iter()
				textbuffer.insert(end_iter, name+"\t:\tUpdated\n")
				self.tupdate()
		else:
			lmod = open(directory+name+"/last_mod.txt","w")
			lmod.write(data)
			lmod.close()
		soup = bs(data,'html.parser')
		divs = soup.find_all("div",class_="activityinstance")
		links = {}
		if divs:
			for div in divs:
				links[div.a["href"]] = div.a.span.text
			resources = {}
			folders = {}
			for link in links.keys():
				if "resource" in link:
					resources[link] = links[link]
			for link in links:
				if "folder" in link:
					folders[link] = links[link]
			for resource in resources.keys():
				retval = self.download_file(resource,directory+name+"/"+resources[resource],session)
				end_iter = textbuffer.get_end_iter()
				textbuffer.insert(end_iter, name+"\t:\t"+resources[resource]+"\n")
				self.tupdate()
			for folder in folders.keys():
				self.getfolder(textbuffer,folder,directory+name+"/"+folders[folder],session)
		else:
			self.getfolder(textbuffer,course,directory+name,session)
		lmod.write(data)
		lmod.close()

	
	def getfolder(self,textbuffer,folder,foldername,session):
		data = session.get(folder).text
		soup = bs(data,'html.parser')
		spans = soup.find_all("span",class_="fp-filename-icon")
		links = {}
		for span in spans:
			if span.a:
				links[span.a["href"]]=span.find("span",class_="fp-filename").text
		for link in links.keys():
			if not os.path.exists(foldername):
    				os.makedirs(foldername)
			retval = self.download_file(link,foldername+"/"+links[link],session)
			end_iter = textbuffer.get_end_iter()
			textbuffer.insert(end_iter, foldername+"\t-\t"+link+"\t:\t"+retval+"\n")
			self.tupdate()

	
	def __init__(self):
		global config,session
        	self.glade = Gtk.Builder()
        	self.glade.add_from_file("moodln.glade")
        	loginwin = self.glade.get_object("loginwin")
		loginwin.show_all()
		button = self.glade.get_object("loginbtn")
		button.connect("clicked",self.login,loginwin)
        	if(config.has_section("Login")):
        		encusern = config.get("Login","username")
			encpass = config.get("Login","password")
			if(encusern and encpass):
				moods = requests.Session()
				username = base64.b64decode(encusern)
				password = base64.b64decode(encpass)
				login_data = {"username": username,"password":password}
				moodle = moods.post("https://courses.iitm.ac.in/login/index.php",login_data)
				courses = moods.get("https://courses.iitm.ac.in/my/")
				soup = bs(courses.text,'html.parser')
				mcourses = soup.find_all("p",class_="tree_item branch")
				if(mcourses):
					session = moods
					loginwin.destroy()
					self.cfolder(mcourses)
					
	def tupdate(self):
		while Gtk.events_pending():
  			Gtk.main_iteration()
		
			
	def login(self,button,loginwin):
		global mcourses,session	
		userwin = self.glade.get_object("username")
		username = userwin.get_text()
		passwin = self.glade.get_object("password")
		password = passwin.get_text()
		moods = requests.Session()
		login_data = {"username": username,"password":password}
		moodle = moods.post("https://courses.iitm.ac.in/login/index.php",login_data)
		courses = moods.get("https://courses.iitm.ac.in/my/")
		soup = bs(courses.text,'html.parser')
		mcourses = soup.find_all("p",class_="tree_item branch")
		if(mcourses):
			session = moods
			encuser = base64.b64encode(username)
			encpas = base64.b64encode(password)
			config.add_section("Login")
			config.set("Login","username",encuser)
			config.set("Login","password",encpas)
			self.cfolder(mcourses)
			loginwin.destroy()
		else:
			print "Invalid"
			return
			
		
	def cfolder(self,mcourses):
		global directory
		if(directory):
			self.getinfo()
		else:
			chooser = self.glade.get_object("filechooserdialog1")
			select = self.glade.get_object("select")
			select.connect("clicked",self.chosen,chooser,mcourses)
			chooser.show_all()
		
	def chosen(self,button,chooser,mcourses):
		global directory,config
		dirpath = chooser.get_filename()
		if(os.path.isdir(dirpath)):
			chooser.destroy()
			directory = dirpath+"/"
			config.set("Login","dir",directory)
			self.getcourses(button,mcourses)
		else:
			self.cfolder(mcourses)
		
	def getcourses(self,button,mcourses):
		global courses
		if not directory:
			self.getflder(mcourses)
		coursewin = self.glade.get_object("courseswin")
		treeleft = self.glade.get_object("treeviewleft")
		treeright = self.glade.get_object("treeviewright")
		add = self.glade.get_object("add")
		remove = self.glade.get_object("remove")
		done = self.glade.get_object("done")
		lstore = self.glade.get_object("liststoreleft")
		rstore = self.glade.get_object("liststoreright")
		courses = {}
		for mcourse in mcourses:
			if mcourse.a:
				course = mcourse.a.contents[0]
				link = mcourse.a["href"]
				name = course.split(":")[0]
				courses[name] = link
				lstore.append([name])
		coursewin.show_all()
		add.connect("clicked",self.changecourses,treeleft.get_selection(),lstore,rstore)
		remove.connect("clicked",self.changecourses,treeright.get_selection(),rstore,lstore)
		done.connect("clicked",self.retcourses,coursewin,rstore)
	
	def changecourses(self,button,selection,store1,store2):
		model,path = selection.get_selected_rows()
		if(path):
			for p in path:
				row = model.get_iter(path)
				store2.append(store1[row][:])
				store1.remove(row)
				
	def retcourses(self,button,coursewin,store):
		global session,courses,config
		coursewin.destroy()
		final = self.glade.get_object("final")
		final.connect("destroy", Gtk.main_quit)
		textbuffer = self.glade.get_object("textbuffer")
		final.show_all()
		iterator = store.get_iter_first()
		crs = []
		config.add_section("Courses")
		while(iterator!=None):
			crs.append(store[iterator][:][0])
			iterator = store.iter_next(iterator)
		for crsid in crs:
			if not os.path.exists(directory+crsid):
    				os.makedirs(directory+crsid)
    			config.set("Courses",crsid,courses[crsid])
			self.getdata(textbuffer,courses[crsid],crsid,session)
		with open('moodleset.cfg', 'wb') as configfile:
    			config.write(configfile)
    					
	def getinfo(self):
		global session,config
		final = self.glade.get_object("final")
		textbuffer = self.glade.get_object("textbuffer")
		final.show_all()
		final.connect("destroy", Gtk.main_quit)
		courses = config.items("Courses")
		for course in courses:
			if not os.path.exists(directory+course[0].upper()):
    				os.makedirs(directory+course[0].upper())
    			self.getdata(textbuffer,course[1],course[0].upper(),session)
    			time.sleep(2)
    		end_iter = textbuffer.get_end_iter()
		textbuffer.insert(end_iter, "\n\n\t---\tDONE\t---\n")
		self.tupdate()
    		
		
		

if __name__ == "__main__":
	hwg = HellowWorldGTK()
	Gtk.main()
	exit()
