import sys
import ruamel.yaml


class Item:
    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value

    @classmethod
    def from_yaml(cls, constructor, node):
        for m in constructor.construct_yaml_map(node):
            pass
        return cls(m['Name'], m['Value'])

    def __repr__(self):
        return 'Item(name={.name}, value={.value})'.format(self, self)

class Message:
    def __init__(self, name=None, DLC=None, object=None, signals=None):
        self.name = name
        self.dlc = DLC
        self.object = object
        self.signals = [] if signals is None else signals

    @classmethod
    def from_yaml(cls, constructor, node):
        for m in constructor.construct_yaml_map(node):
            pass
        if 'Name' in m:
            name = m['Name']
        elif 'name' in m:
            name = m['name']
        else:
            name = None
        object = m['object'] if 'object' in m else None
        if 'DLC' in m:
            dlc = m['DLC']
        else:
            dlc = None
        if 'signals' in m:
            signals = m['signals']
        elif 'Signal1' in m:
            x = 1
            signals = []
            while True:
                name = "Signal{}".format(x)
                try:
                    signals.append(m[name])
                except KeyError:
                    break
                x += 1
        else:
            signals = None
        return cls(name, dlc, object, signals)

    def __repr__(self):
        return 'Message(name={}, DLC={}, object={}, signals{})'.format(
            self.name, self.dlc, self.object, '[...]' if self.signals else '[]',
        )


yaml = ruamel.yaml.YAML(typ='safe')
yaml.register_class(Item)
yaml.register_class(Message)
with open('input.yaml') as fp:
    data = yaml.load(fp)
print(data)