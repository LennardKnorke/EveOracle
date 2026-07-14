from datetime import date, timedelta
import os
from pathlib import Path
import random
import time
from urllib.request import urlretrieve
from urllib.error import HTTPError


from tqdm import tqdm

killmail_url = "https://data.everef.net/killmails"

MIN_DELAY = 0.8
MAX_DELAY = 2.0
def rate_limit():
    """
    Amateur rate limit but works
    """
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


start_date = date(2007, 12, 5)
end_date = date.today() - timedelta(days=2)


download_dir = Path("esi_killmail_history")
download_dir.mkdir(exist_ok=True)


def download(d : date, filename : str):
    rate_limit()

    # URL + TARGET PATH
    url = killmail_url + f"/{d.year}/" + filename
    filepath = download_dir/str(d.year)/filename

    # RETRIEVE
    try:
        urlretrieve(url, filepath)
    except HTTPError as e:
        if e.code == 404:
            tqdm.write(f"Missing: {filename}")
        else:
            tqdm.write(f"HTTP {e.code}: {filename}")
    except Exception as e:
        tqdm.write(f"Failed {filename}: {e}")
    return


def download_all_killsmails():
    r = tqdm(range((end_date - start_date).days + 1))
    for i in r:
        current_date = start_date + timedelta(days=i)
        filename = f"killmails-{current_date:%Y-%m-%d}.tar.bz2"
        os.makedirs(f"{download_dir}/{current_date.year}", exist_ok=True)


        if os.path.exists(f"{download_dir}/{current_date.year}/{filename}"):
            continue
        else:
            download(current_date, filename)
    return


if __name__ == "__main__":
    download_all_killsmails()