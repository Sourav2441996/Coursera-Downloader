from selenium import webdriver
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, StaleElementReferenceException) 
import time, requests
from bs4 import BeautifulSoup
import sys, os, re, argparse


class EndOfCourseException(Exception):
	def __init__(self, args):
		self.args = args

class CourseraDownloader:
	def __init__(self, folder=''):
		self.browser = webdriver.Chrome()
		self.wait = WebDriverWait(self.browser, 10)
		self.folder = folder
		self.courses =[]
		self.coursebase=''
		self.weekurls ={}
		self.lastweekno = 0


	def login(self, myemail, mypassword):
		print('Getting coursera...')
		self.browser.get('http://www.coursera.org/?authMode=login')
		for i in range(4):
			try: 
				email = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-courselenium ="email-field"]')))
				password = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-courselenium="password-field"]')))
				loginBtn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-courselenium="login-form-submit-button"]')))
				break
			except (TimeoutException, StaleElementReferenceException):
				print('Webdriver timeout or recovering from staleness...trying again')
		else:
			print("Please restart program")
			sys.exit(1)

		print('Logging in...')
		email.send_keys(myemail)
		password.send_keys(mypassword)
		loginBtn.click()
		self.cookies = self.browser.get_cookies()


	def getCookies(self):
		toSendCookie ={}
		for cookie in self.cookies:
			toSendCookie[cookie['name']] = cookie['value']
		return toSendCookie



	def retrieveCourseLists(self):
		for i in range(4):
			try:
				self.courses =[]
				courseList = self.wait.until(EC.presence_of_all_elements_located((By.XPATH,'//div[@data-courselenium="course-name"]/div')))
				for course  in courseList:
					self.courses.append(course.text)
				retrieved = True
				break
			except (TimeoutException,StaleElementReferenceException):
				print('Trying to recover from staleness or timeout...')
		else:
			print("Failed to recover. Restart program")
			sys.exit(1)

		if retrieved:
			print('\nYour course list\n\n')
			for index, course in enumerate(self.courses):
				print('[', index,'] ', course)
			print('\n\n')
		else:
			print('Could not recover...try running again')
			sys.exit(1)


	def goToCourse(self, index):
		courseName = self.courses[index]
		if self.folder == '':
			self.folder = courseName

		xpath = '//div[text()=\"'+ courseName+ '\"]/../../following-sibling::div/a[text()]'
		print('Going to course...')
		for i in range(4):
			try:
				anchor = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
				anchor.click()

				self.coursebase = os.path.dirname(self.browser.current_url)
				break
			except (TimeoutException, StaleElementReferenceException):
				print("Could not go to course. Trying again...")
		else: 
			print('Could not recover..try running the program again')
			sys.exit(1)

		for i in range(4):
			try:
				weeknoXpath = '//a[@data-track-component="syllabus_week"]/div/div/div/h4/span'
				navweekno = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, weeknoXpath)))
				self.lastweekno = len(navweekno)
				print('Total number of weeks to fetch: ', self.lastweekno)
				break
			except (TimeoutException, StaleElementReferenceException):
				print('Could not get total number of weeks. Trying again...')
		else:
			print('Failed to get total number of weeks. Restart program')
			sys.exit(1)



	def toVisitInWeek(self, weekno):
		if weekno > self.lastweekno:
			raise EndOfCourseException("You have reaced the end of course")
		self.browser.get(self.coursebase+'/week/'+str(weekno))
		
		
		print('Visiting week '+ str(weekno))
		xpath = '//span[contains(concat(" ", normalize-space(@class), " ")," play ")]/../../../../..|//i[contains(concat(" ", normalize-space(@class), " "), "cif-item-video")]/../../../../..'


		for i in range(4):
			downloadLinks = []
			tovisit =[]
			try:
				links = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, xpath)))
				for link in links:
					tovisit.append(link.get_attribute('href'))
				break
			except (TimeoutException, StaleElementReferenceException):
				print('Trying to recover from staleness...')
		else:
			print('Could not fetch link. Try running the program again...')
			sys.exit(1)		

		
		print('\n\n\n')
		for link in tovisit:
			print('Fetching ', link)
			self.browser.get(link)
			videoxpath = '//source[@type="video/mp4"]'
			for i in range(4):
				try:
					video = self.wait.until(EC.presence_of_element_located((By.XPATH, videoxpath)))
					src = video.get_attribute('src')
					break
				except (TimeoutException, StaleElementReferenceException):
					print('Timeout or elements have gone stale. Trying again...')
			else:
				print('Could not fetch video source. Try restarting the program')
				sys.exit(1)

			
			title=self.browser.title
			title = title.split(" | ")[0].split(" - ")[0]
			downloadLinks.append({"src": src, "title": title})
			

		self.weekurls["Week-"+str(weekno)] = downloadLinks
		#print(self.weekurls)

	def downloadVideos(self):
		for (week, urlList) in self.weekurls.items():
			os.makedirs(self.folder+'/'+week, exist_ok=True)
			counter = 1
			for link in urlList:
				print('Downloading video with title: ', link['title'],'...')
				filename = self.folder+'/'+week+'/'+str(counter)+'. '+link['title']
				filename = re.sub(r'[.,!?]', '', filename)
				videoFile = open(filename+'.mp4', 'wb')
				resp = requests.get(link['src'])
				for chunk in resp.iter_content(100000):
					videoFile.write(chunk)
				counter+=1
				videoFile.close()


	def scrape(self, index):
		self.goToCourse(index)
		weekno = 1
		while True:
			try:
				self.toVisitInWeek(weekno)
				weekno+=1
			except EndOfCourseException:
				print('\n\nAll the videos of the course have been fetched. Will start downloading...\n\n')
				self.browser.close()
				self.downloadVideos()
				print('\n\n\nDone!\n\n')
				break


	def closeBrowser(self):
		self.browser.close()


def main():

	parser = argparse.ArgumentParser()
	parser.add_argument('--folder', '-f', help="Enter the name of folder")
	parser.add_argument('--email', '-e', help="The email address to login with", required=True)
	parser.add_argument('--passwd', '-p', help="The password to login with", required=True)
	args = parser.parse_args()

	if args.folder:
		downloader = CourseraDownloader(folder = args.folder)
	else:
		downloader = CourseraDownloader()
	

	downloader.login(args.email, args.passwd)
	downloader.retrieveCourseLists()
	entered= False
	while entered == False:
		courseNum = input('Enter the index of course you wish to download: ')
		try:
			courseNum = int(courseNum)
			entered=True
		except:
			print('Only integer numbers')
		

	downloader.scrape(courseNum)
	time.sleep(20)

	
if __name__=='__main__':
	main()