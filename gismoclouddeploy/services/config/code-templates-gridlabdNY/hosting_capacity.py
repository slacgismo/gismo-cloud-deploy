import os, sys
import gridlabd
import timeit

DER_value = None
loads = []
nodes = []
links = []
timer = timeit.default_timer()


def on_init(*args, **kwargs):

    #
    # Copy DER value from GLM global DER_VALUE to load objects
    #
    global DER_value
    DER_value = gridlabd.get_global("DER_VALUE")[1:-1]

    global loads
    loads = [
        obj
        for obj in gridlabd.get("objects")
        if gridlabd.get_value(obj, "class") == "load"
    ]

    global nodes
    nodes = [
        obj
        for obj in gridlabd.get("objects")
        if "DER_value" in gridlabd.get_object(obj).keys()
    ]

    global links
    links = [
        obj
        for obj in gridlabd.get("objects")
        if "power_losses" in gridlabd.get_object(obj).keys()
    ]

    for obj in loads:
        gridlabd.set_value(obj, "DER_value", DER_value)

    return 1


def on_term(*args, **kwargs):

    with open("hosting_capacity.csv", "at") as fh:
        print(
            f'{gridlabd.get_global("modelname")},{DER_value},{len(nodes)},{len(links)},{len(loads)},{round(timeit.default_timer()-timer,3)}',
            file=fh,
        )

    return 0
