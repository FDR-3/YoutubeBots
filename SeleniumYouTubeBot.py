import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException, TimeoutException, NoSuchElementException, ElementNotInteractableException
#from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

matchFoundFile = "SeleniumYoutubeBotMatches.txt"
noTranscriptFoundFile = "SeleniumYoutubeBotNoTranscripts.txt"
progressSavedFile = "SeleniumYoutubeBotSavedProgress.txt"
thumbNailId = "#thumbnail"

TIME_OUT = 1 #time out in seconds
SHOW_TRANSCRIPT_MAX_TRY_COUNT = 20

brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" #Replace with your actual path

#Configure ChromeOptions to use the Brave executable
brave_options = ChromeOptions()
brave_options.binary_location = brave_path

#Initialize the Chrome WebDriver with the Brave options
driver = webdriver.Chrome(options=brave_options)
#driver = webdriver.Chrome()

def searchChannelForString(channelVideosURL, searchStringList, videoStartNumber, videoStopNumber, backwardsSearch):
  global nextVideoToCheck
  nextVideoToCheck = videoStartNumber

  global searchStartTime
  searchStartTime = time.time()

  if os.path.exists(matchFoundFile):
    os.remove(matchFoundFile)  #Delete the file if it exists
    print(f"Existing file '{matchFoundFile}' deleted.")

  if os.path.exists(noTranscriptFoundFile):
    os.remove(noTranscriptFoundFile)  #Delete the file if it exists
    print(f"Existing file '{noTranscriptFoundFile}' deleted.")

  driver.get(channelVideosURL)

  waitForDocumentReadyState()

  if backwardsSearch:
    oldestVideosButton = driver.find_element(By.CSS_SELECTOR, ":nth-child(3) > #chip-container > #text")
    if oldestVideosButton.is_displayed():
      oldestVideosButton.click()
      print("Performing search backwards")
      waitForDocumentReadyState()

  #videoThumbnails = WebDriverWait(driver, TIME_OUT).until(EC.presence_of_all_elements_located(thumbNailLocator))
  videoThumbnails = driver.find_elements(By.CSS_SELECTOR, thumbNailId)

  currentNumberOfVisibleThumbnails = len(videoThumbnails)
  currentBottomOfPageHeight = driver.execute_script("return window.pageYOffset + window.innerHeight")
  allVideosSearched = False
 
  try:
    allVideosSearched = False
    while allVideosSearched == False:
      global videoParseStartTime
      videoParseStartTime = time.time()

      if (videoStopNumber != -1) and (nextVideoToCheck > videoStopNumber):
        allVideosSearched = True
      elif (nextVideoToCheck < currentNumberOfVisibleThumbnails):
        searchNextVideoThumbNail(searchStringList, backwardsSearch)
      else:
        #Scroll to the bottom, update what the new page bottom value is, and wait
        scrollToBottomOfPage()
        time.sleep(TIME_OUT)

        heightAfterScrollDown = driver.execute_script("return window.pageYOffset + window.innerHeight")

        #videoThumbnails = WebDriverWait(driver, TIME_OUT).until(EC.presence_of_all_elements_located(thumbNailLocator))
        videoThumbnails = driver.find_elements(By.CSS_SELECTOR, thumbNailId)
        currentNumberOfVisibleThumbnails = len(videoThumbnails)

        #Check if there aren't more video thumbnails to click on after scrolling down
        if nextVideoToCheck > currentNumberOfVisibleThumbnails:
          #Check if we hit the bottom of the youtube channel after the no new videos check, if so, get the fuck out of here!
          if currentBottomOfPageHeight == heightAfterScrollDown:
            allVideosSearched = True
            
          else:
            #Scroll to the bottom and update the current page bottom value, update what the new page bottom value is, and wait
            scrollToBottomOfPage()
            time.sleep(TIME_OUT)

            currentBottomOfPageHeight = driver.execute_script("return window.pageYOffset + window.innerHeight")
            
        else:
          searchNextVideoThumbNail(searchStringList, backwardsSearch)
   
  finally:
    searchEndTime = time.time()
    executionTime = searchEndTime - searchStartTime

    #Convert seconds into hours, minutes, and left over seconds
    hours = int(executionTime // 3600) #Divide by 3600 (seconds in an hour)
    minutes = int((executionTime % 3600) // 60) #Get the remainder and divide by 60
    seconds = int(executionTime % 60) #Get the remainder after dividing by 60

    print(f"The script ran for {hours} hours, {minutes} minutes, and {seconds} seconds.")

    driver.quit()
      
def searchNextVideoThumbNail(searchStringList, backwardsSearch):
  global nextVideoToCheck
  
  #Open next thumbnail in new tab
  clicked = False
  while clicked == False:
    try:
      nextThumbNail = driver.find_element(By.XPATH, f"//ytd-rich-item-renderer[{nextVideoToCheck}]//a[@id='thumbnail']")

      if nextThumbNail:
        #Open the link in a new tab using Ctrl+Click (or Command+Click on macOS)
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).click(nextThumbNail).key_up(Keys.CONTROL).perform() #for windows and linux
        #actions.key_down(Keys.COMMAND).click(button).key_up(Keys.COMMAND).perform() #for Mac OS
        clicked = True
    except Exception as errorMessage:
      print(errorMessage)
      print("Thumbnail not reachable. Attemping to scroll down.")
      #Scroll to the bottom incase we can't reach the video
      scrollToBottomOfPage()
      time.sleep(TIME_OUT)

  #Switch to the new tab
  new_window = driver.window_handles[-1]  #Get the handle of the last opened tab
  driver.switch_to.window(new_window)

  waitForDocumentReadyState()

  #Skip age restricted videos that don't have transcripts
  try:
    ageRestrictionProperty = driver.find_element(By.XPATH, "//meta[@property='og:restrictions:age']")
    if ageRestrictionProperty:
      with open(noTranscriptFoundFile, "a") as file:
        print("Age restricted video. No transcript. Skipping video.")
        file.write(f"Video Number: {nextVideoToCheck}" + "\n")
        file.write(driver.current_url + "\n")
        nextVideoToCheck += 1
        closeVideoAndSwitchBackToMainTab()
      return
  except NoSuchElementException:
    pass
    
  searched = False
  while searched == False:
    '''
    #Pause Video
    clicked = False
    #element_locator = By.CLASS_NAME, "ytp-play-button"
    while clicked == False:
      try:
        #element = WebDriverWait(driver, TIME_OUT).until(EC.presence_of_element_located(element_locator))
        element = driver.find_element(By.CLASS_NAME, "ytp-play-button")
        if element.is_displayed():
          element.click()
          clicked = True
      except StaleElementReferenceException:
        print("The element is stale. Trying to pause video again.")
    '''
    #Dismiss Popup if it's there
    #element_locator = By.CSS_SELECTOR, "#dismiss-button > yt-button-shape > button"
    try:
      #element = WebDriverWait(driver, TIME_OUT).until(EC.presence_of_element_located(element_locator))
      dismissPopupButton = driver.find_element(By.CSS_SELECTOR, "#dismiss-button > yt-button-shape > button")
      if dismissPopupButton.is_displayed():
        dismissPopupButton.click()
        print("Killed pop up!")
    except (StaleElementReferenceException, NoSuchElementException):
      pass

    #Expand More Video Info
    clicked = False
    #element_locator = By.CSS_SELECTOR, "#description-inline-expander > #expand"
    while clicked == False:
      try:
        #element = WebDriverWait(driver, TIME_OUT).until(EC.presence_of_element_located(element_locator))
        expandMoreVideoInfoButton = driver.find_element(By.CSS_SELECTOR, "#description-inline-expander > #expand")
        if expandMoreVideoInfoButton.is_displayed():
          expandMoreVideoInfoButton.click()
          clicked = True
      except (StaleElementReferenceException, ElementClickInterceptedException, NoSuchElementException):
        print("The expandMoreVideoInfoButton is stale. Trying to expand more info again.")
        checkForSomethingWentWrongMessage()

    #Show Transcript
    clicked = False
    showTranscriptTryCount = 0
    #element_locator = By.CSS_SELECTOR, "#structured-description > :nth-child(2) > ytd-video-description-transcript-section-renderer.style-scope > #button-container > #primary-button > .style-scope > yt-button-shape > .yt-spec-button-shape-next"
    while clicked == False:
      try:
        if showTranscriptTryCount < SHOW_TRANSCRIPT_MAX_TRY_COUNT:
          #element = WebDriverWait(driver, TIME_OUT).until(EC.presence_of_element_located(element_locator))
          #showTranscriptButton = driver.find_element(By.CSS_SELECTOR, "#structured-description > :nth-child(2) > ytd-video-description-transcript-section-renderer.style-scope > #button-container > #primary-button > .style-scope > yt-button-shape > .yt-spec-button-shape-next")
          showTranscriptButton = driver.find_element(By.XPATH, '//*[@id="primary-button"]/ytd-button-renderer/yt-button-shape/button/yt-touch-feedback-shape/div[2]')

          #showTranscriptButton.click()
          # 3. Execute JavaScript click directly on the element
          driver.execute_script("arguments[0].click();", showTranscriptButton)
          clicked = True
        else:
          with open(noTranscriptFoundFile, "a") as file:
            print("No transcript button found. Skipping video.")
            file.write(f"Video Number: {nextVideoToCheck}" + "\n")
            file.write(driver.current_url + "\n")
            nextVideoToCheck += 1
            closeVideoAndSwitchBackToMainTab()
          return
      except (StaleElementReferenceException, ElementClickInterceptedException, NoSuchElementException, ElementNotInteractableException) as message:
        print(message)
        print("The element is stale. Trying to show transcript again.")
        checkForSomethingWentWrongMessage()
        showTranscriptTryCount += 1

    #Search Transcript
    cssSelector = "#segments-container > ytd-transcript-segment-renderer"
    element_locator = By.CSS_SELECTOR, cssSelector
    try:
      transcriptLines = WebDriverWait(driver, TIME_OUT).until(EC.presence_of_all_elements_located(element_locator))
      #elements = driver.find_elements(By.CSS_SELECTOR, cssSelector) This doesn't return any of them
      print("transcript lines: ", len(transcriptLines))

      found = False
      for transcriptLine in transcriptLines:
        if found == True:
          break
        for searchString in searchStringList:
          if searchString.lower() in transcriptLine.text.lower():
            #If match found, append it to MatchFoundFile
            with open(matchFoundFile, "a") as file:
              print("Found string!")
              file.write(f"Video Number: {nextVideoToCheck}" + "\n")
              file.write(driver.current_url + "\n")
            found = True
            break
      #Create/overwrite progress file to save the last video number and url that was checked in case of restarts
      with open(progressSavedFile, "w") as file:
        global searchStartTime
        saveTime = time.time()
        checkPointTime = saveTime - searchStartTime

        #Convert seconds into hours, minutes, and remaining seconds
        hours = int(checkPointTime // 3600)  #Divide by 3600 (seconds in an hour)
        minutes = int((checkPointTime % 3600) // 60)  #Get the remainder and divide by 60
        seconds = int(checkPointTime % 60)  #Get the remainder after dividing by 60

        file.write(f"Backwards Search: {backwardsSearch}" + "\n")
        file.write(f"Last Video Number Checked: {nextVideoToCheck}" + "\n")
        file.write(f"URL: {driver.current_url}" + "\n")
        file.write(f"Current run time: {hours} hours, {minutes} minutes, and {seconds} seconds")

      searched = True
      nextVideoToCheck += 1
    except (StaleElementReferenceException, ElementClickInterceptedException, TimeoutException):
      print("Transcript not readabled. Reloading page and trying again.")
      driver.refresh()#Reload page since transcript probably says "No Results Found" and try all the steps again starting back at the "#Pause Video" step

  #Print out video parse time
  videoParseEndTime = time.time()
  videoParseTime = videoParseEndTime - videoParseStartTime
  print(f"Video took {videoParseTime} seconds to parse.")

  closeVideoAndSwitchBackToMainTab()
  
def waitForDocumentReadyState():
  while driver.execute_script("return document.readyState") != "complete":
    pass

def scrollToBottomOfPage():
  html = driver.find_element(By.TAG_NAME, "html")
  html.send_keys(Keys.END)

def closeVideoAndSwitchBackToMainTab():
  driver.close()
  mainWindow = driver.window_handles[0]
  driver.switch_to.window(mainWindow)

def checkForSomethingWentWrongMessage():
  try:
    driver.find_element(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'something went wrong. refresh or try again later.')]")
    print("Something went wrong message, reloading video")
    driver.refresh()
  except NoSuchElementException:
    pass
  
channelVideosURL = "https://www.youtube.com/@SecularTalk/videos"

videoStartNumber = 1 # Start the search from this video number from the top down on the youtube channel
#videoStartNumber = 7433 #Start the search from this video number from the top down on the youtube channel
videoStopNumber = -1 #-1 if unused
searchStringList = ["Jiggly Puff", "JigglyPuff"]
backwardsSearch = False

searchChannelForString(channelVideosURL, searchStringList, videoStartNumber, videoStopNumber, backwardsSearch)