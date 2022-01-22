import shutil

from numpy import imag
from mycroft import MycroftSkill, intent_handler
from adapt.intent import IntentBuilder
import os
import random
from PIL import Image
import requests
import time
import subprocess
class Taskbot(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.scoreFile = "./scoreFile.txt"
        if not os.path.exists(self.scoreFile):
            self.setScore(1100)

        self.labeling_folder = "/tmp/random_pictures"
        if not os.path.exists(self.labeling_folder):
            os.mkdir(self.labeling_folder)

        self.animal_dataset = "/opt/mycroft/skills/taskbot-skill/animal_dataset/raw-img"

    def getScore(self):
        scoreFile = open(self.scoreFile, "r")
        points = int(scoreFile.read())
        scoreFile.close()
        return points

    def setScore(self, points):
        scoreFile = open(self.scoreFile, "w+")
        scoreFile.write(str(points))
        scoreFile.close()

    @intent_handler(IntentBuilder('score').require('Score'))
    def handle_score(self, message):
        points = self.getScore()
        self.speak(f"Your score is {points}")

    @intent_handler(IntentBuilder('deny').require('Deny'))
    def handle_deny(self, message):
        points = self.getScore()
        answer = self.get_response('serviceDenied')
        if self.voc_match(answer, 'yes', self.lang):
            self.handle_task(message)
        elif self.voc_match(answer, 'no', self.lang):
            self.speak("Okay")
    
    @intent_handler(IntentBuilder('task').require('Task'))
    def handle_task(self, message):
        tasks = [self.classify_task, self.verify_task]
        task = random.choice(tasks)
        task(message)

    def verify_task(self, message):
        animal_list = ["dog", "elephant", "cat", "chicken"]
        current_animal = random.choice(animal_list)
        folder_path = os.path.join(self.animal_dataset, current_animal)
        picture_list = []
        for file in os.listdir(folder_path):
            picture_list.append(file)
        picture_path = os.path.join(folder_path, random.choice(picture_list))
        viewer = subprocess.Popen(['eog', picture_path])
        answer = self.get_response("What animal do you see ?")
        viewer.terminate()
        if answer == current_animal:
            self.speak("You are correct. Score increased")
            self.setScore(self.getScore() + 5)
        else:
            self.speak(f"Are you kidding me? This clearly was a {current_animal}. Your Score has been decreased")
            self.setScore(self.getScore() - 20)

    def download_save_image(self, curr_time):
        path = "https://picsum.photos/800/480.jpg"
        res = requests.get(path)

        file_path = f"{self.labeling_folder}/{curr_time}.jpg"
        if res.status_code == 200:
            with open(file_path, "wb") as image_file:
                image_file.write(res.content)

        return file_path
        
    def classify_task(self, message):
        t = time.localtime()
        current_time = time.strftime("%Y%m%d%H%M%S", t)
        file_path = self.download_save_image(current_time)

        viewer = subprocess.Popen(['eog', file_path])
        answer = self.get_response("What do you see?")
        if answer:
            self.speak("Thank you for your work!")
            viewer.terminate()
            self.setScore(self.getScore() + 5)
        else:
            self.speak("I would like an answer please!")
            return
        
        with open(self.labeling_folder + "/labels.csv", 'a') as label_file:
            label_file.write(f"{current_time}.jpg,{answer}\n")

def create_skill():
    return Taskbot()
