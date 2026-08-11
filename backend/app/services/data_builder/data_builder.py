
from pathlib import Path

dataset_dir = Path("static/datasets")
dataset_dir.mkdir(exist_ok=True)

class DataBuilder:
    _allowed_permutes = [ # No function yet, will be added later
        "drop", # R
        "all",  # Include all permutations of the battles
    ]

    _allowed_synthetics = [ # No function yet, will be added later
        "None",
        "all"  
    ]
    def __init__(
            self,
            max_time : float,
            max_distance : float,
            team_size : int,
            permute_data : list[str]|None = None,
            synthetic_data : list[str]|None = None,
        ):
        self.max_time = max_time
        self.max_distance = max_distance
        self.team_size = team_size

        if type(permute_data) == list:
            for val in permute_data:
                if type(val) != str or not val in DataBuilder._allowed_permutes:
                    raise ValueError("Faulty Permutation Setting")            
        self.permute_data = permute_data

        if type(synthetic_data) == list:
            for val in synthetic_data:
                if type(val) != str or not val in DataBuilder._allowed_synthetics:
                    raise ValueError("Faulty Synthetic Data Setting")
        self.synthetic_data = synthetic_data
        return

    def create(self) ->tuple[bool, str]:
        return True, ""
    
    def _save():
        return
    