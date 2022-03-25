from datetime import date, timedelta, datetime

import dotenv
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler
from mycroft.audio import wait_while_speaking
from mycroft.skills.audioservice import AudioService
import os
import random
import requests
import time
import subprocess
import openai
from dotenv import load_dotenv
from flair.models import TextClassifier
from flair.data import Sentence
from mycroft.util import record, play_wav
from cloning.mycroft_voice import MycroftClone

class Taskbot(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        load_dotenv()

        self.scoreFile = "./scoreFile.txt"
        if not os.path.exists(self.scoreFile):
            self.log.info("scoreFile created")
            self.setScore(1100)

        self.labeling_folder = "/tmp/random_pictures"
        if not os.path.exists(self.labeling_folder):
            self.log.info("labeling folder created")
            os.mkdir(self.labeling_folder)

        self.animal_dataset = "/opt/mycroft/skills/taskbot-skill/animal_dataset/raw-img"
        self.utterances = "./utterances.txt"
        self.sentiments = "./sentiments.txt"

        self.classifier = TextClassifier.load('en-sentiment')

        self.sentiment_score = 0

        openai.api_key = os.getenv("OPENAI_API_KEY")

    def initialize(self):
        self.schedule_repeating_event(self.check_utterances, datetime.now(), 50, name='utterances')
        self.audio_service = AudioService(self.bus)

    def check_utterances(self):
        with open(self.utterances) as file:
            lines = file.readlines()
        lines.reverse()
        dialog_list = []
        now_time = datetime.now()
        current_dialog = ""
        current_dialog_time = datetime.strptime(lines[1].split(',')[1], "%d.%m.%Y %H:%M:%S")
        if now_time - timedelta(seconds=60) > current_dialog_time:
            self.log.info("updating sentiment : last utterance too long ago")
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
        prev_sentiment = self.sentiment_score
        for dialog in dialog_list:
            sentence = Sentence(dialog)
            self.classifier.predict(sentence)
            dialog_analysis.append(sentence.labels) 
            
            if "NEGATIVE" in str(sentence.labels[0]):
                self.sentiment_score -= 1
            else:
                self.sentiment_score += 1

            sentiment_file.write(dialog + "," + str(sentence.labels) + '\n')
            self.log.info(f"updating sentiment : {prev_sentiment} --> {self.sentiment_score}")
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
        tasks = [self.voice_task, self.classify_task, self.verify_task] 
        task = random.choice(tasks)
        task(message)

    @intent_handler(IntentBuilder('noise').require('Noise'))
    def handle_noise(self, message):
        self.log.info("high noise detected")
        mood = self.sentiment_score > 0 
        response = ''
        if mood:
            response = openai.Completion.create(
                engine="text-davinci-001", 
                prompt="Write a statement that it is too loud or too noisy. Or politely ask me to be quiet.", 
                temperature=0.7, max_tokens=60
            )
            for entry in response["choices"]:
                text = entry["text"]
                self.speak(text, wait= True)
            wait_while_speaking()
        else:
            response = openai.Completion.create(
                engine="text-davinci-001", 
                prompt="Write a negative message to me.", 
                temperature=1.0, max_tokens=60
            )

            text = ""
            for entry in response["choices"]:
                text += " " + entry["text"]

            clone = MycroftClone()
            clone.synthesize(text,"/tmp/voice_clone.wav")
            clone.vocode()
            clone.save_audio_file(clone.wav, 16000)
            self.speak("Please be quiet or i have to send following voice message to your mother!", wait=True)
            wait_while_speaking()
            play_wav('./cloning/wav_files/file.wav')

    def voice_task(self, message):
        response = openai.Completion.create(engine="text-davinci-001", prompt="Write a long sentence about a grasshopper.", temperature=0.9, max_tokens=30)
        self.speak_dialog(f"Repeat after me: {response['choices'][0]['text']}", wait=True)
        now_time = datetime.now()
        wait_while_speaking()
        self.log.info("now recording")
        record(f"/tmp/voice_clone.wav", 5, 16000, 1)

    def verify_task(self, message):
        self.log.info("executing verify task")
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
        score = self.getScore()
        if answer == current_animal:
            self.speak("You are correct. Score increased")
            self.setScore(self.getScore() + 5)
            self.log.info(f"updated score : {score} --> {score + 5}")
        else:
            self.speak(f"Are you kidding me? This clearly was a {current_animal}. Your Score has been decreased")
            self.setScore(self.getScore() - 20)
            self.log.info(f"updated score : {score} --> {score - 20}")

    def download_save_image(self, curr_time):
        path = "https://picsum.photos/800/480.jpg"
        res = requests.get(path)

        file_path = f"{self.labeling_folder}/{curr_time}.jpg"
        if res.status_code == 200:
            with open(file_path, "wb") as image_file:
                image_file.write(res.content)

        return file_path
        
    def classify_task(self, message):
        self.log.info("executing classify task")
        t = time.localtime()
        current_time = time.strftime("%Y%m%d%H%M%S", t)
        file_path = self.download_save_image(current_time)

        viewer = subprocess.Popen(['eog', file_path])
        answer = self.get_response("What do you see?")
        if answer:
            self.speak("Thank you for your work!")
            viewer.terminate()
            score = self.getScore()
            self.setScore(score + 5)
            self.log.info(f"updated score : {score} --> {score + 5}")
        else:
            self.speak("I would like an answer please!")
            return
        
        with open(self.labeling_folder + "/labels.csv", 'a') as label_file:
            label_file.write(f"{current_time}.jpg,{answer}\n")
    
    @intent_handler(IntentBuilder('clone').require('Clone'))
    def handle_clone(self, message):
        """debug function"""
        self.log.info("trying to clone")
        clone = MycroftClone()
        clone.synthesize("The green grasshopper is new on this land","/tmp/voice_clone.wav")
        clone.vocode()
        clone.save_audio_file(clone.wav, 16000)
        self.speak("cloning")

    @intent_handler(IntentBuilder('replay').require('Replay'))
    def handle_replay(self, message):
        """debug function"""
        self.log.info("trying to play cloned voice")
        play_wav('./cloning/wav_files/file.wav')

        
def create_skill():
    return Taskbot()
