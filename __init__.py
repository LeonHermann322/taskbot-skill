from datetime import date, timedelta, datetime

import dotenv
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler
from mycroft.audio import wait_while_speaking
import os
import random
import requests
import time
import subprocess
import openai
from dotenv import load_dotenv
from flair.models import TextClassifier
from flair.data import Sentence

class Taskbot(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        load_dotenv()

        self.scoreFile = "./scoreFile.txt"
        if not os.path.exists(self.scoreFile):
            self.setScore(1100)

        self.labeling_folder = "/tmp/random_pictures"
        if not os.path.exists(self.labeling_folder):
            os.mkdir(self.labeling_folder)

        self.animal_dataset = "/opt/mycroft/skills/taskbot-skill/animal_dataset/raw-img"
        self.utterances = "./utterances.txt"
        self.sentiments = "./sentiments.txt"

        self.classifier = TextClassifier.load('en-sentiment')

        self.sentiment_score = 0

        openai.api_key = os.getenv("OPENAI_API_KEY")

    def initialize(self):
        self.schedule_repeating_event(self.check_utterances, datetime.now(), 50, name='utterances')

    def check_utterances(self):
        with open(self.utterances) as file:
            lines = file.readlines()
        lines.reverse()
        dialog_list = []
        now_time = datetime.now()
        current_dialog = ""
        current_dialog_time = datetime.strptime(lines[1].split(',')[1], "%d.%m.%Y %H:%M:%S")
        if now_time - timedelta(seconds=60) > current_dialog_time:
            self.log.info("Last utterance too long ago")
            return
        for line in lines:
            line_arr = line.split(',')
            utterance_time = datetime.strptime(line_arr[1], "%d.%m.%Y %H:%M:%S")
            if current_dialog_time - timedelta(seconds=15)  <= utterance_time:
                current_dialog = line_arr[0] + ". " + current_dialog
            else:
                if now_time - timedelta(seconds=60) > utterance_time:
                    break
                dialog_list.append(current_dialog)
                current_dialog = line_arr[0]
                current_dialog_time = utterance_time

        dialog_analysis = []
        sentiment_file = open(self.sentiments, "a")
        for dialog in dialog_list:
            sentence = Sentence(dialog)
            self.classifier.predict(sentence)
            dialog_analysis.append(sentence.labels) 

            if "NEGATIVE" in str(sentence.labels[0]):
                self.sentiment_score -= 1
            else:
                self.sentiment_score += 1

            sentiment_file.write(dialog + "," + str(sentence.labels) + '\n')
        sentiment_file.close()
        self.log.info(self.sentiment_score)

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
        tasks = [self.voice_task]#self.classify_task, self.verify_task, 
        task = random.choice(tasks)
        task(message)

    @intent_handler(IntentBuilder('noise').require('Noise'))
    def handle_noise(self, message):
        self.log.info("peter")
        response = openai.Completion.create(engine="text-davinci-001", prompt="Write a statement that it is too loud or too noisy. Or tell me to be quiet. And maybe add a threat that there will be consequences.", temperature=0.7)
        self.speak(response["choices"][0]["text"])
        wait_while_speaking()

    def voice_task(self, message):
        response = openai.Completion.create(engine="text-davinci-001", prompt="Write something angry.", temperature=0.9)
        self.speak(response["choices"][0]["text"])

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
