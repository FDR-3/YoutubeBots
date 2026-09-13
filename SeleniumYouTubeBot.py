from email.mime import message
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
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

TIME_OUT = 0.5 #time out in seconds
READ_TRANSCRIPT_MAX_TRY_COUNT = 4
EXPAND_DESCRIPTION_MAX_TRY_COUNT = 4
SHOW_TRANSCRIPT_MAX_TRY_COUNT = 4

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
    oldestVideosButton = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Oldest']")
    oldestVideosButton.click()
    print("Performing search backwards")
    waitForDocumentReadyState()

  #videoThumbnails = WebDriverWait(driver, TIME_OUT).until(EC.presence_of_all_elements_located(thumbNailLocator))
  videoThumbnails = driver.find_elements(By.CSS_SELECTOR, thumbNailId)

  currentNumberOfVisibleThumbnails = len(videoThumbnails)
  currentBottomOfPageHeight = driver.execute_script("return window.pageYOffset + window.innerHeight")
 
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
        videoThumbnails = driver.find_elements(
                By.CSS_SELECTOR,
                "ytd-rich-item-renderer a.ytLockupViewModelContentImage"
              )
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
      nextThumbNail = driver.find_element(
        By.XPATH,
        f"//ytd-rich-item-renderer[{nextVideoToCheck}]//a[contains(@class, 'ytLockupViewModelContentImage')]"
      )

      if nextThumbNail:
        #Open the link in a new tab using Ctrl+Click (or Command+Click on macOS)
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).click(nextThumbNail).key_up(Keys.CONTROL).perform() #for windows and linux
        #actions.key_down(Keys.COMMAND).click(button).key_up(Keys.COMMAND).perform() #for Mac OS
        clicked = True
    except Exception as errorMessage:
      print(f"Error: {errorMessage}")
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
    ageRestrictionProperty = driver.find_elements(By.XPATH, "//meta[@property='og:restrictions:age']")
    if ageRestrictionProperty:
      with open(noTranscriptFoundFile, "a") as file:
        print("Age restricted video. No transcript. Skipping video.")
        file.write(f"Video Number: {nextVideoToCheck}" + "\n")
        file.write(driver.current_url + "\n")
        nextVideoToCheck += 1
        closeVideoAndSwitchBackToMainTab()
      return
  except Exception as message:
    print(f"Error: {message}")
    pass
    
  searched = False
  readTranscriptTryCount = 0
  while searched == False:
    if readTranscriptTryCount <= READ_TRANSCRIPT_MAX_TRY_COUNT:
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
        dismissPopupButton = driver.find_elements(By.CSS_SELECTOR, "#dismiss-button > yt-button-shape > button")
        if dismissPopupButton:
          if dismissPopupButton[0].is_displayed():
            dismissPopupButton[0].click()
            print("Killed pop up!")
      except Exception:
        pass

      #Expand More Video Info
      clicked = False
      expandDescriptionTryCount = 0
      while clicked == False:
        try:
          element_locator = By.CSS_SELECTOR, "#description-inline-expander > #expand"
          expandMoreVideoInfoButton = WebDriverWait(driver, 4).until(EC.presence_of_element_located(element_locator))
          if expandMoreVideoInfoButton.is_displayed():
            expandMoreVideoInfoButton.click()
            clicked = True
        except Exception as message:
          print(f"Error: {message}")
          checkForSomethingWentWrongMessage()
          if expandDescriptionTryCount >= EXPAND_DESCRIPTION_MAX_TRY_COUNT:
            recordSkippedVideoAndMoveOn()
            return
          expandDescriptionTryCount += 1
          print(f"Failed to click Expand Description button. Retry {expandDescriptionTryCount} of {EXPAND_DESCRIPTION_MAX_TRY_COUNT}")

      #Show Transcript
      clicked = False
      showTranscriptTryCount = 0
      #element_locator = By.CSS_SELECTOR, "#structured-description > :nth-child(2) > ytd-video-description-transcript-section-renderer.style-scope > #button-container > #primary-button > .style-scope > yt-button-shape > .yt-spec-button-shape-next"
      while clicked == False:
        try:
          #element = WebDriverWait(driver, TIME_OUT).until(EC.presence_of_element_located(element_locator))
          element_locator = By.XPATH, '//*[@id="primary-button"]/ytd-button-renderer/yt-button-shape/button/yt-touch-feedback-shape/div[2]'
          showTranscriptButton = WebDriverWait(driver, 4).until(EC.presence_of_element_located(element_locator))
          #showTranscriptButton = driver.find_element(By.XPATH, '//*[@id="primary-button"]/ytd-button-renderer/yt-button-shape/button/yt-touch-feedback-shape/div[2]')

          #showTranscriptButton.click()
          # 3. Execute JavaScript click directly on the element
          driver.execute_script("arguments[0].click();", showTranscriptButton)
          clicked = True
        except Exception as message:
          print(f"Error: {message}")
          checkForSomethingWentWrongMessage()
          if showTranscriptTryCount >= SHOW_TRANSCRIPT_MAX_TRY_COUNT:
            recordSkippedVideoAndMoveOn()
            return
          showTranscriptTryCount += 1
          print(f"Failed to click Show Transcript button. Retry {showTranscriptTryCount} of {SHOW_TRANSCRIPT_MAX_TRY_COUNT}")

      #Search Transcript
      cssSelector = "transcript-segment-view-model"
      element_locator = By.CSS_SELECTOR, cssSelector
      try:
        transcriptLines = WebDriverWait(driver, 4).until(EC.presence_of_all_elements_located(element_locator))
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
      except Exception:
        readTranscriptTryCount += 1
        if readTranscriptTryCount > READ_TRANSCRIPT_MAX_TRY_COUNT:
          recordSkippedVideoAndMoveOn()
          return
        print(f"Transcript not readabled. Reloading page and trying again. Retry {readTranscriptTryCount} of {READ_TRANSCRIPT_MAX_TRY_COUNT}")
        driver.refresh()#Reload page since transcript probably says "No Results Found" and try all the steps again starting back at the "#Pause Video" step  
    else:
      recordSkippedVideoAndMoveOn()
      return
    
  #Print out video parse time
  videoParseEndTime = time.time()
  videoParseTime = videoParseEndTime - videoParseStartTime
  print(f"Video took {videoParseTime} seconds to parse.")

  closeVideoAndSwitchBackToMainTab()

def recordSkippedVideoAndMoveOn():
  global nextVideoToCheck
  with open(noTranscriptFoundFile, "a") as file:
    print("Couldn't read transcript. Recording URL and skipping video.")
    file.write(f"Video Number: {nextVideoToCheck}" + "\n")
    file.write(driver.current_url + "\n")
    nextVideoToCheck += 1
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
  except Exception:
    pass
  
channelVideosURL = "https://www.youtube.com/@kagethedon001/videos"

videoStartNumber = 1 # Start the search from this video number from the top down on the youtube channel
#videoStartNumber = 7433 #Start the search from this video number from the top down on the youtube channel
videoStopNumber = -1 #-1 if unused
searchStringList = ["Lock in", "On business"]
backwardsSearch = False

searchChannelForString(channelVideosURL, searchStringList, videoStartNumber, videoStopNumber, backwardsSearch)