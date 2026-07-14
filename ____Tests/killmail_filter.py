from datetime import date, timedelta
from pathlib import Path
import tarfile
import json
from tqdm import tqdm

download_dir = Path("killmails")

start_date = date(2007, 12, 5)
end_date = date.today() - timedelta(days=2)

# key -> first seen date (as string)
key_timeline = {}

def process_json(obj, seen_date: str):
    """
    Recursively walk JSON and register all keys.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k not in key_timeline:
                key_timeline[k] = seen_date
            process_json(v, seen_date)

    elif isinstance(obj, list):
        item = obj[0]
        process_json(item, seen_date)

def filter_mails():
    total_days = (end_date - start_date).days + 1

    for i in tqdm(range(total_days)):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")

        archive_path = download_dir / str(current_date.year) / f"killmails-{date_str}.tar.bz2"

        if not archive_path.exists():
            continue

        try:
            with tarfile.open(archive_path, "r:bz2") as tar:
                for member in tar:
                    if not member.isfile():
                        continue

                    f = tar.extractfile(member)
                    if f is None:
                        continue

                    try:
                        data = json.load(f)
                        process_json(data, date_str)
                        break
                    except Exception:
                        continue

        except Exception as e:
            tqdm.write(f"Failed archive {archive_path}: {e}")

        # periodic checkpoint save (important for long runs)
        if i % 50 == 0:
            with open("key_timeline.json", "w") as out:
                json.dump(key_timeline, out)

    # final save
    with open(download_dir / "key_timeline.json", "w") as out:
        json.dump(key_timeline, out)

    print("Done.")
    print(f"Total unique keys tracked: {len(key_timeline)}")
    for k,v in key_timeline.items():
        print(f"{k} : {v}")


if __name__ == "__main__":
    filter_mails()
    