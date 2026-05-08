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

        ball_pattern = re.compile(
            r"\(\(b\)\s+"
            r"([-\d\.]+)\s+"
            r"([-\d\.]+)\s+"
            r"([-\d\.]+)\s+"
            r"([-\d\.]+)"
            r"\)"
        )

        for match in ball_pattern.finditer(msg):

            result["objects"].append({

                "object_type": "ball",

                "distance": float(match.group(1)),
                "direction": float(match.group(2)),

                "distance_change": float(match.group(3)),
                "direction_change": float(match.group(4))
            })

        player_pattern = re.compile(
            r'\(\(p\s+"([^"]+)"\s+(\d+)\)\s+'
            r'([-\d\.]+)\s+'
            r'([-\d\.]+)\s+'
            r'([-\d\.]+)\s+'
            r'([-\d\.]+)\s+'
            r'([-\d\.]+)\s+'
            r'([-\d\.]+)'
            r'\)'
        )

        for match in player_pattern.finditer(msg):

            result["players"].append({

                "team_name": match.group(1),

                "uniform_number": int(match.group(2)),

                "goalie": False,

                "distance": float(match.group(3)),
                "direction": float(match.group(4)),

                "distance_change": float(match.group(5)),
                "direction_change": float(match.group(6)),

                "body_direction": float(match.group(7)),
                "head_direction": float(match.group(8))
            })

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