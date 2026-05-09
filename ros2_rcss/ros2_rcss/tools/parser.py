import re


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
                obj = {"object_type": "ball"}
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
                obj = {"object_type": "goal", "which": obj_name_raw}
                keys = ["distance", "direction", "distance_change", "direction_change"]
                for k, v in zip(keys, nums):
                    obj[k] = v
                result["objects"].append(obj)

            elif obj_name_raw.startswith("(f") or obj_name_raw.startswith("(l"):
                obj = {"object_type": "flag", "which": obj_name_raw}
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

        pattern = re.compile(
            r"\(hear\s+(\d+)\s+([^\s]+)\s+(.+)\)"
        )

        match = pattern.match(msg)

        if match:

            result["cycle"] = int(match.group(1))

            result["sender"] = match.group(2)

            result["message"] = match.group(3)

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
            r"\(stamina\s+([-\d\.]+)\s+([-\d\.]+)\)",
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
            r"\(neck\s+([-\d\.]+)\)",
            msg
        )

        if neck_match:

            result["neck_direction"] = float(
                neck_match.group(1)
            )

        return result