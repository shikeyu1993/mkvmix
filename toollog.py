import logging
import os
TAG = 'mkvmix'
TOOLLOGPATH = f'{os.getcwd()}\\mkvmix.log'
LOGLEVEL = logging.INFO

log_level = LOGLEVEL
logging.basicConfig(level=log_level,
                    format='%(asctime)s %(name)-8s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S',
                    filename=TOOLLOGPATH,
                    filemode='w')
console = logging.StreamHandler()
console.setLevel(log_level)
formatter = logging.Formatter(
    '%(asctime)s %(name)-8s %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
logger = logging.getLogger(TAG)