import json


# class WORKER_CONFIG(object):
#     def __init__(self, d):
#         if type(d) is str:
#             d = json.loads(d)
#         self.convert_json(d)

#     def convert_json(self, d):
#         self.__dict__ = {}
#         for key, value in d.items():
#             if type(value) is dict:
#                 value = WORKER_CONFIG(value)
#             self.__dict__[key] = value

#     def __setitem__(self, key, value):
#         self.__dict__[key] = value

#     def __getitem__(self, key):
#         return self.__dict__[key]
