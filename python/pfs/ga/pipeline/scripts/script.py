import os
import logging
from argparse import ArgumentParser

class Script():
    """
    Implements generic function for pipeline command-line scripts.
    """

    def __init__(self):
        self.__debug = False
        self.__loglevel = logging.INFO

        self.__parser = ArgumentParser()

    def __get_debug(self):
        return self.__debug
    
    debug = property(__get_debug)

    def __get_loglevel(self):
        return self.__loglevel
    
    loglevel = property(__get_loglevel)

    def __parse_args(self):
        self.__args = self.__parser.parse_args().__dict__

    def _add_arg(self, *args, **kwargs):
        self.__parser.add_argument(*args, **kwargs)

    def _get_arg(self, name, args=None, default=None):
        args = args if args is not None else self.__args

        if name in args and args[name] is not None and args[name] != '':
            return args[name]
        else:
            return default
        
    def _add_args(self):
        self._add_arg('--debug', action='store_true', help='Enable debug mode')

    def _init_from_args(self, args):
        self.__debug = self._get_arg('debug', args, self.__debug)

    def execute(self):
        self._add_args()
        self.__parse_args()
        self._init_from_args(self.__args)
        self.run()

    def run(self):
        raise NotImplementedError()