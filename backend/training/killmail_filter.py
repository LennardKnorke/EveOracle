

class BattleReport:
    def __init__(self, filter_time : int = 60, filter_distance : float = 100.0):
        self.fleet0 = []
        self.fleet1 = []
        self.unknown_pilots = []
        self.isklost0 = 0
        self.isklost1 = 0
        self.shipslost0 = 0
        self.shipslost0 = 0

class RunningPlayerStats:
    def __init__(self, character_id : int|str):
        if type(character_id) == str:
            if character_id.isdigit():
                character_id = int(character_id)
            else:
                raise ValueError("Faulty Character_ID provided")
        self.character_id = character_id

def scan_killmails(
        filter_time : int,
        filter_distance : float,
        fleet_size : int
):
    
    
    return