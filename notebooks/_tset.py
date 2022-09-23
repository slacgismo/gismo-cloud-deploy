


# from transitions import Machine
# import random


# import enum  # Python 2.7 users need to have 'enum34' installed
# # from transitions import Machine

# class States(enum.Enum):
#     ERROR = 0
#     RED = 1
#     YELLOW = 2
#     GREEN = 3

# transitions = [['proceed', States.RED, States.YELLOW],
#                ['proceed', States.YELLOW, States.GREEN],
#                ['error', '*', States.ERROR]]


# m = Machine(states=States, transitions=transitions, initial=States.RED)
# assert m.is_RED()
# assert m.state is States.RED
# state = m.get_state(States.RED)  # get transitions.State object
# print(state.name)  # >>> RED
# m.proceed()
# m.proceed()
# assert m.is_GREEN()
# m.error()
# assert m.state is States.ERROR

# class GismoCloudDeploy(object):
#     states = [
#             'idle', 
#             'load_config', 
#             'verify_config', 
#             'build_images', 
#             'aws_tag_and_push_to_ecr',
#             'aws_scale_eks', 
#             'get_pods_info', 
#             'send_command',
#             'long_pulling_sqs',
#             'analyze_logs',
#             'close_k8s_sqs_services',
#             'aws_scaledown_eks',
#             'error'
#         ]

#     def __init__(self, config_file):
#         self.config_file = config_file
#         # repeat index
#         self.repeat_index = 0
#         # Initialize the state machine
#         self.machine = Machine(model=self, states=GismoCloudDeploy.states, initial='idle')
#         self.machine.add_transition('start', 'idle', 'load_config',
#                          before='hello_world')

#     def hello_world(self,name, test):
#         print(f"hello world {name}")
#         test = test +5
#         print(test)

# gcd = GismoCloudDeploy("config.yaml")
# print(gcd.state)
# gcd.start("jimmy",test=6)
# print(gcd.state)

# class NarcolepticSuperhero(object):

#     # Define some states. Most of the time, narcoleptic superheroes are just like
#     # everyone else. Except for...
#     states = ['asleep', 'hanging out', 'hungry', 'sweaty', 'saving the world']
    
#     def __init__(self, name):

#         # No anonymous superheroes on my watch! Every narcoleptic superhero gets
#         # a name. Any name at all. SleepyMan. SlumberGirl. You get the idea.
#         self.name = name

#         # What have we accomplished today?
#         self.kittens_rescued = 0




#         # Initialize the state machine
#         self.machine = Machine(model=self, states=NarcolepticSuperhero.states, initial='asleep')

#         # Add some transitions. We could also define these using a static list of
#         # dictionaries, as we did with states above, and then pass the list to
#         # the Machine initializer as the transitions= argument.

#         # At some point, every superhero must rise and shine.
#         self.machine.add_transition(trigger='wake_up', source='asleep', dest='hanging out')

#         # Superheroes need to keep in shape.
#         self.machine.add_transition('work_out', 'hanging out', 'hungry')

#         # Those calories won't replenish themselves!
#         self.machine.add_transition('eat', 'hungry', 'hanging out')

#         # Superheroes are always on call. ALWAYS. But they're not always
#         # dressed in work-appropriate clothing.
#         self.machine.add_transition('distress_call', '*', 'saving the world',
#                          before='change_into_super_secret_costume')

#         # When they get off work, they're all sweaty and disgusting. But before
#         # they do anything else, they have to meticulously log their latest
#         # escapades. Because the legal department says so.
#         self.machine.add_transition('complete_mission', 'saving the world', 'sweaty',
#                          after='update_journal')

#         # Sweat is a disorder that can be remedied with water.
#         # Unless you've had a particularly long day, in which case... bed time!
#         self.machine.add_transition('clean_up', 'sweaty', 'asleep', conditions=['is_exhausted'])
#         self.machine.add_transition('clean_up', 'sweaty', 'hanging out')

#         # Our NarcolepticSuperhero can fall asleep at pretty much any time.
#         self.machine.add_transition('nap', '*', 'asleep')

#     def update_journal(self):
#         """ Dear Diary, today I saved Mr. Whiskers. Again. """
#         self.kittens_rescued += 1

#     @property
#     def is_exhausted(self):
#         """ Basically a coin toss. """
#         return random.random() < 0.5

#     def change_into_super_secret_costume(self):
#         print("Beauty, eh?")


# batman = NarcolepticSuperhero("Batman")
# print(batman.state)

# batman.wake_up()
# print(batman.state)

# batman.distress_call()

# Singleton
# import os
# import yaml
# from functools import reduce

# class Config(object):
#     __env = None
    
#     # constant values which should same for envs
#     SERVER = "abc"
    

#     def __new__(cls, env: str):
#         if not hasattr(cls, 'instance') or cls.instance.__env != env:
#             cls.instance = super(Config, cls).__new__(cls)
#             cls.instance.load(env)
#         return cls.instance


#     def load(self, env):
#         self.__env = env
#         with open(f"{env}.yaml", "r") as f:
#             self._data = yaml.load(f, Loader=yaml.FullLoader)

#     def get(self, key):
#         if "." not in key:
#             return self._data.get(key, None)
#         else:
#             keys = key.split(".")
#             return reduce(lambda data, key: data[key], keys, self._data)
