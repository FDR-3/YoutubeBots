import os
import time
import scrapetube
from youtube_transcript_api import YouTubeTranscriptApi

matchFoundFile = "APIYoutubeBotMatches.txt"
noTranscriptFoundFile = "APIYoutubeBotNoTranscripts.txt"
progressSavedFile = "APIYoutubeBotSavedProgress.txt"

def searchChannelForString(channelID, searchTerms, videoStartNumber):
  searchStartTime = time.time()

  if os.path.exists(matchFoundFile):
    os.remove(matchFoundFile) #Delete the file if it exists
    print(f"Existing file '{matchFoundFile}' deleted.")

  if os.path.exists(noTranscriptFoundFile):
    os.remove(noTranscriptFoundFile)  #Delete the file if it exists
    print(f"Existing file '{noTranscriptFoundFile}' deleted.")

  videos = scrapetube.get_channel(channelID)
  videoCount = 1

  for video in videos:

    if videoStartNumber > videoCount:
      print(f"Skipping Video Number {videoCount}")
      videoCount += 1
      continue

    print(f"Parsing Video Number {videoCount}")
    videoParseStartTime = time.time()
    videoId = video['videoId']
    videoPostTime = video['publishedTimeText']
    yttAPI = YouTubeTranscriptApi()

    try:
      transcriptLines = yttAPI.fetch(videoId)
      print("transcript lines: ", len(transcriptLines))

      found = False
      for transcriptLine in transcriptLines:
        if found == True:
          break
        for searchTerm in searchTerms:
          if searchTerm.lower() in transcriptLine.text.lower():
            with open(matchFoundFile, "a") as file:
              print("Found string!")
              file.write(f"Video Number: {videoCount}" + "\n")
              file.write("https://www.youtube.com/watch?v=" + videoId + "\n")
            found = True
            break
            
      printVideoParseTime(videoParseStartTime)
      saveSearchProgress(searchStartTime, videoCount, videoId, videoPostTime)
      videoCount += 1

    except Exception as error:
      #print(f"An error occurred: {error}")
      print("No transcript found. Skipping video.")
      with open(noTranscriptFoundFile, "a") as file:
        file.write(f"Video Number: {videoCount}" + "\n")
        file.write("https://www.youtube.com/watch?v=" + videoId + "\n")
      videoCount += 1
  
  searchEndTime = time.time()
  executionTime = searchEndTime - searchStartTime

  #Convert seconds into hours, minutes, and remaining seconds
  hours = int(executionTime // 3600) #Divide by 3600 (seconds in an hour)
  minutes = int((executionTime % 3600) // 60) #Get the remainder and divide by 60
  seconds = int(executionTime % 60) #Get the remainder after dividing by 60

  print(f"The script took {hours} hours, {minutes} minutes, and {seconds} seconds to run.")

def printVideoParseTime(videoParseStartTime):
  videoParseEndTime = time.time()
  videoParseTime = videoParseEndTime - videoParseStartTime
  print(f"Video took {videoParseTime} seconds to parse.")

def saveSearchProgress(searchStartTime, videoCount, videoId, videoPostTime):
  with open(progressSavedFile, "w") as file:
    saveTime = time.time()
    checkPointTime = saveTime - searchStartTime

    #Convert seconds into hours, minutes, and remaining seconds
    hours = int(checkPointTime // 3600) #Divide by 3600 (seconds in an hour)
    minutes = int((checkPointTime % 3600) // 60) #Get the remainder and divide by 60
    seconds = int(checkPointTime % 60) #Get the remainder after dividing by 60

    file.write(f"Last Video Number Checked: {videoCount}" + "\n")
    file.write(f"URL: https://www.youtube.com/watch?v=" + videoId + "\n")
    file.write(f"Video Post Time: {videoPostTime}" + "\n")
    file.write(f"Current run time: {hours} hours, {minutes} minutes, and {seconds} seconds")

channelID = "UCldfgbzNILYZA4dmDt4Cd6A"
searchTerms = ["JigglyPuff", "Jiggly Puff"]
videoStartNumber = 1
#videoStartNumber = 11384

searchChannelForString(channelID, searchTerms, videoStartNumber)