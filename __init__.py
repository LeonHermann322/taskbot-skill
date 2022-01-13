from mycroft import MycroftSkill, intent_file_handler


class Taskbot(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('taskbot.intent')
    def handle_taskbot(self, message):
        self.speak_dialog('taskbot')


def create_skill():
    return Taskbot()

