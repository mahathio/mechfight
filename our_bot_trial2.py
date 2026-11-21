import math, heapq
import mechfight as mf

class Bot:
    name = "elite-algo-py"

    def __init__(self, hello: mf.Hello):
        self.reach = hello["config"]["loot"]["pickup_radius"]
        self.last_enemy_pos, self.waypoint, self.last_path_tick = {}, None, -100

    def act(self, obs: mf.Observation) -> mf.Action:
        me, (x, y, z), tick, goal = obs["self"], obs["self"]["pos"], obs["tick"], obs["zone"]["next_center"]
        act: mf.Action = {"tick": tick, **({"pick": 0} if obs["offer"] else {})}

        # 1. COMBAT TARGETING & VELOCITY
        mechs = [m for m in obs["mechs"] if m["kind"] == "mech"]
        enemy = min(mechs, key=lambda m: (m.get("hp", 100), math.dist(m["pos"], (x, y, z)))) if mechs else None
        
        evx, evy, dist = 0, 0, float('inf')
        if enemy:
            eid, t = enemy["id"], enemy["pos"]
            evx, evy = t[0] - self.last_enemy_pos.get(eid, t)[0], t[1] - self.last_enemy_pos.get(eid, t)[1]
            self.last_enemy_pos[eid], dist = t, math.dist(t[:2], (x, y))

        if tick % 60 == 0: 
            self.last_enemy_pos = {m["id"]: self.last_enemy_pos[m["id"]] for m in mechs if m["id"] in self.last_enemy_pos}

        # 2. EMERGENCY LOOTING
        near = [p for p in obs["pickups"] if math.dist(p["pos"][:2], (x, y)) < self.reach]
        if near and (not me["weapons"][1] or me["hp"] < 50): act["take"] = near[0]["id"]

        # 3. DECISION TREE (Juking vs Retreat vs Pathing)
        is_critical = me["hp"] < 30 # Elite mechanic: Retreat if nearly dead
        
        if enemy and dist < 250 and not is_critical:
            # Elite mechanic: Zig-zag strafing to break enemy predictive aiming
            juke_dir = 1 if tick % 40 < 20 else -1
            syaw = math.atan2(t[1]-y, t[0]-x) + (juke_dir * math.pi/2)
            gyaw = math.atan2(goal[1]-y, goal[0]-x)
            
            px, py = t[0] + evx * (dist/50.0), t[1] + evy * (dist/50.0)
            
            act.update(
                move=[math.cos(syaw)*0.8 + math.cos(gyaw)*0.2, math.sin(syaw)*0.8 + math.sin(gyaw)*0.2],
                aim=[math.atan2(py-y, px-x), math.atan2(t[2]-z-2.5, math.dist([px, py], (x, y)))],
                fire=[True, True], boost=not me["in_zone"], jump=tick % 30 == 0
            )
            mf.draw.line([x, y, z + 7], [px, py, t[2] + 4.5], "#ff5040")
        else:
            if tick - self.last_path_tick > 20 or not self.waypoint or math.dist((x,y), self.waypoint) < 20:
                nodes = {**{f"p{i}": p["pos"][:2] for i, p in enumerate(sorted(obs["pickups"], key=lambda p: math.dist(p["pos"][:2], (x,y)))[:10])}, "me": (x, y), "goal": goal[:2]}
                graph = {k1: [(k2, math.dist(p1, p2)) for k2, p2 in nodes.items() if k1 != k2 and math.dist(p1, p2) < 400] for k1, p1 in nodes.items()}
                
                q, seen, mins, path = [(0, "me", [])], set(), {"me": 0}, []
                while q:
                    c, n, p = heapq.heappop(q)
                    if n == "goal": path = p + [n]; break
                    if n not in seen:
                        seen.add(n)
                        for nx, w in graph.get(n, []):
                            if c + w < mins.get(nx, float('inf')):
                                mins[nx] = c + w
                                heapq.heappush(q, (c + w, nx, p + [n]))
                                
                self.waypoint, self.last_path_tick = nodes[path[1]] if len(path) > 1 else goal[:2], tick

            yaw = math.atan2(self.waypoint[1] - y, self.waypoint[0] - x)
            act.update(move=[math.cos(yaw), math.sin(yaw)], aim=[yaw, 0.0], boost=(not me["in_zone"] or is_critical), jump=tick % 40 == 0)
            mf.draw.point([self.waypoint[0], self.waypoint[1], z], "#40c0ff", 6)

        return act

mf.run(Bot)