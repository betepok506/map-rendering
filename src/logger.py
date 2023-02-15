import logging


class LoggerFormating(logging.Formatter):
    format = '%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'

    FORMATS = {logging.INFO: format}

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)