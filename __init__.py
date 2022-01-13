from mycroft import MycroftSkill, intent_handler
from adapt.intent import IntentBuilder
import os


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


    @intent_handler(IntentBuilder('score').require('Score'))
    def handle_score(self, message):
        points = self.getScore()
        self.log.info("Calculating response")
        self.speak(f"Your score is {points}")

    @intent_handler(IntentBuilder('deny').require('Deny'))
    def handle_deny(self, message):
        points = self.getScore()
        self.speak(f"""Service denied, your score is too low. 
        Currently at {points} points.
        Solve some tasks to increase your score.
        """)

    @intent_handler(IntentBuilder('task').require('Task'))
    def handle_task(self, message):
        answer = self.get_response('askMathTask')
        if self.voc_match(answer, 'yes', self.lang):
            self.speak("Your score has been increased")
        else:
            self.speak("Fuck you the answer is wrong")


def create_skill():
    return Taskbot()
