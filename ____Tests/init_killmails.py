

from src.killmail_downloader import *
from src.killmail_filter import *


if __name__ == "__main__":
    download_all_killsmails()
    filter_mails()