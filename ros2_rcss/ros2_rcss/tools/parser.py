import re


OBJECT_PREFIXES = {"b": "ball", "g": "goal", "f": "flag", "l": "line"}


def object_name(raw: str) -> str:
    """Convert a raw object token like '(g r)' or '(f c t)' to 'goal r' / 'flag c t'."""
    tokens = raw.strip("()").split()
    if not tokens:
        return ""
    tokens[0] = OBJECT_PREFIXES.get(tokens[0], tokens[0])
    return " ".join(tokens)


class Parser:
    def parse_message(self, msg: str):
        if msg.startswith("(see"):
            return self.parse_see(msg)

        elif msg.startswith("(hear"):
            return self.parse_hear(msg)

        elif msg.startswith("(sense_body"):
            return self.parse_body(msg)

        return None

    def parse_see(self, msg: str):
        result = {
            "type": "see",
            "cycle": 0,
            "objects": [],
            "players": []
        }

        cycle_match = re.match(r"\(see\s+(\d+)", msg)
        if cycle_match:
            result["cycle"] = int(cycle_match.group(1))

        obj_pattern = re.compile(r'\((\([^)]+\))\s+([^)]*)\)')

        for match in obj_pattern.finditer(msg):
            obj_name_raw = match.group(1).strip()
            fields_raw   = match.group(2).strip()

            nums = []
            for token in fields_raw.split():
                try:
                    nums.append(float(token))
                except ValueError:
                    pass

            if obj_name_raw == "(b)":
                obj = {"object_type": "ball", "name": "ball"}
                keys = ["distance", "direction", "distance_change", "direction_change"]
                for k, v in zip(keys, nums):
                    obj[k] = v
                result["objects"].append(obj)

            elif obj_name_raw.startswith("(p"):
                # Parse team name, uniform number, goalie flag from the name token
                team_match = re.match(
                    r'\(p(?:\s+"([^"]+)"(?:\s+(\d+)(?:\s+(goalie))?)?)?\)',
                    obj_name_raw
                )
                player = {
                    "object_type": "player",
                    "team_name":       team_match.group(1) if team_match else None,
                    "uniform_number":  int(team_match.group(2)) if (team_match and team_match.group(2)) else None,
                    "goalie":          team_match.group(3) == "goalie" if team_match else False,
                }
                keys = ["distance", "direction", "distance_change",
                        "direction_change", "body_direction", "head_direction"]
                for k, v in zip(keys, nums):
                    player[k] = v
                result["players"].append(player)

            elif obj_name_raw.startswith("(g"):
                obj = {"object_type": "goal", "which": obj_name_raw,
                       "name": object_name(obj_name_raw)}
                keys = ["distance", "direction", "distance_change", "direction_change"]
                for k, v in zip(keys, nums):
                    obj[k] = v
                result["objects"].append(obj)

            elif obj_name_raw.startswith("(f") or obj_name_raw.startswith("(l"):
                obj = {"object_type": "flag", "which": obj_name_raw,
                       "name": object_name(obj_name_raw)}
                keys = ["distance", "direction", "distance_change", "direction_change"]
                for k, v in zip(keys, nums):
                    obj[k] = v
                result["objects"].append(obj)

        return result

    def parse_hear(self, msg: str):
        result = {
            "type": "hear",
            "cycle": 0,
            "sender": "",
            "direction": 0.0,
            "message": ""
        }

        # Formats (protocol v15):
        #   (hear T referee play_mode)      (hear T self "msg")
        #   (hear T DIR our UNUM "msg")     (hear T DIR opp "msg")
        #   (hear T online_coach_left "msg")
        match = re.match(r"\(hear\s+(\d+)\s+(.*)\)$", msg, re.S)
        if not match:
            return result

        result["cycle"] = int(match.group(1))
        rest = match.group(2).strip()

        player = re.match(
            r'(-?[\d.]+)\s+(?:(our)\s+(\d+)|(opp))\s*(.*)$', rest, re.S
        )
        if player:
            result["direction"] = float(player.group(1))
            if player.group(2):
                result["sender"] = f"our {player.group(3)}"
            else:
                result["sender"] = "opp"
            result["message"] = player.group(5).strip().strip('"')
        else:
            sender, _, message = rest.partition(" ")
            result["sender"] = sender
            result["message"] = message.strip().strip('"')

        return result

    def parse_body(self, msg: str):
        result = {
            "type": "body",
            "cycle": 0,

            "stamina": 0.0,
            "effort": 0.0,

            "speed": 0.0,
            "speed_direction": 0.0,

            "neck_direction": 0.0,

            "view_mode": ""
        }

        cycle_match = re.match(
            r"\(sense_body\s+(\d+)",
            msg
        )

        if cycle_match:
            result["cycle"] = int(
                cycle_match.group(1)
            )

        stamina_match = re.search(
            r"\(stamina\s+([-\d\.]+)\s+([-\d\.]+)",
            msg
        )

        if stamina_match:

            result["stamina"] = float(
                stamina_match.group(1)
            )

            result["effort"] = float(
                stamina_match.group(2)
            )

        speed_match = re.search(
            r"\(speed\s+([-\d\.]+)\s+([-\d\.]+)\)",
            msg
        )

        if speed_match:

            result["speed"] = float(
                speed_match.group(1)
            )

            result["speed_direction"] = float(
                speed_match.group(2)
            )

        neck_match = re.search(
            r"\((?:head_angle|neck)\s+([-\d\.]+)\)",
            msg
        )

        if neck_match:

            result["neck_direction"] = float(
                neck_match.group(1)
            )

        view_match = re.search(r"\(view_mode\s+(\w+)\s+(\w+)\)", msg)

        if view_match:
            result["view_mode"] = f"{view_match.group(1)} {view_match.group(2)}"

        return result