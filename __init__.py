from mycroft import MycroftSkill, intent_handler
from adapt.intent import IntentBuilder
import os
import random
from PIL import Image
import requests
import time
import glob
import subprocess
class Taskbot(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.scoreFile = "/home/leonhermann/.config/mycroft/skills/Judgealexa/scoreFile.txt"
        if not os.path.exists(self.scoreFile):
            self.setScore(1000)

    def getScore(self):
        scoreFile = open(self.scoreFile, "r")
        points = int(scoreFile.read())
        scoreFile.close()
        return points

    def setScore(self, points):
        scoreFile = open(self.scoreFile, "w+")
        scoreFile.write(str(points))
        scoreFile.close()
    
    def ask_mask_task(self):
        answer = self.get_response('askMathTask')
        if self.voc_match(answer, 'yes', self.lang):
            self.speak("Your answer is correct. Your score has been increased")
            self.setScore(self.getScore() + 5)
        else:
            self.speak("Fuck you the answer is wrong")
            self.setScore(self.getScore() - 5)


    @intent_handler(IntentBuilder('score').require('Score'))
    def handle_score(self, message):
        points = self.getScore()
        self.log.info("Calculating response")
        self.speak(f"Your score is {points}")

    @intent_handler(IntentBuilder('deny').require('Deny'))
    def handle_deny(self, message):
        points = self.getScore()
        answer = self.get_response('serviceDenied')
        if self.voc_match(answer, 'yes', self.lang):
            self.ask_mask_task()
        elif self.voc_match(answer, 'no', self.lang):
            self.speak("okay, loser")

    @intent_handler(IntentBuilder('mathTask').require('MathTask'))
    def handle_math_task(self, message):
        self.askMathTask()

    
    @intent_handler(IntentBuilder('animalTask').require('AnimalTask'))
    def handle_animal_task(self, message):
        self.classify_task()

   
            
    def verify_task(self):
        animal_list = ["dog", "elephant", "cat", "chicken"]
        current_animal = random.choice(animal_list)
        folder_path = f"/home/leonhermann/animal_dataset/raw-img/{current_animal}"
        picture_list = []
        for file in os.listdir(folder_path):
            picture_list.append(file)
        picture = Image.open(folder_path + "/" + random.choice(picture_list))
        picture.show()
        answer = self.get_response("What animal do you see ?")
        if answer == current_animal:
            self.speak("You are correct. Score increased")
            self.setScore(self.getScore() + 5)
        else:
            self.speak(f"Are you kidding me? This clearly was a {current_animal}. Your Score has been decreased")
            self.setScore(self.getScore() - 20)
        picture.close()
        
    def classify_task(self):
        folder_path = "/home/leonhermann/random_pictures"
        path = "https://picsum.photos/800/480.jpg"
        img = requests.get(path)
        t = time.localtime()
        current_time = time.strftime("%Y%m%d%H%M%S", t)
        file_path = f"{folder_path}/{current_time}.jpg"

        with open(f"{folder_path}/{current_time}.jpg", "wb") as fd:
            fd.write(img.content)
        #picture = 

        for infile in glob.glob(file_path):
            viewer = subprocess.Popen(['eog', infile])
            answer = self.get_response("What do you see?")
            if answer:
                self.speak("thank you for your work")
                viewer.terminate()
                viewer.kill()
        
        with open(folder_path + "/labels.csv", 'a') as fd:
            fd.write(f"{current_time}.jpg,{answer} \n")
        
        
def create_skill():
    return Taskbot()
