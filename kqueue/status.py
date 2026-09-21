################################################################################
## Status

class Status():

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):

        if isinstance(other, str):
            return self.name == other

        if not isinstance(other, Status):
            return False

        return self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self.name

RENDERING = Status('RENDERING')
READY_TO_RENDER = Status('READY_TO_RENDER')
RENDERING_STOPPING = Status('RENDERING_STOPPING')
RENDERING_FINISHED = Status('RENDERING_FINISHED')
