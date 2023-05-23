import logging as logger
import os


# noinspection PyArgumentList
def config_logger(use_stream_handler, filename="debug.log"):
    """
    Configures logger module
    if use stream handler = true -> output to BOTH log file and std out
    :param use_stream_handler - built-in param for pytest info
    :param filename - file to store logs
    """
    '''
    # relative to source directory
    fullpath = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), filename)
    '''
    # relative to working directory
    fullpath = '/'.join([os.getcwd(), filename])
    if use_stream_handler:
        # Configure logger module to log to file AND print out to STD out
        # noinspection PyArgumentList
        logger.basicConfig(level=logger.INFO,
                           format='%(asctime)s - %(message)s',
                           datefmt='%d-%b-%y %H:%M:%S',
                           handlers=[
                               logger.FileHandler(fullpath, mode='a'),
                               logger.StreamHandler()
                           ])
    else:
        # Configure logger module to log to file ONLY
        logger.basicConfig(level=logger.INFO,
                           format='%(asctime)s - %(message)s',
                           datefmt='%d-%b-%y %H:%M:%S',
                           handlers=[
                               logger.FileHandler(fullpath, mode='a'),
                           ])
