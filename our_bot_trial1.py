import math, heapq
import mechfight as mf

class Bot:
    name = "short-algo-py"

    def __init__(self, hello: mf.Hello):
        self.reach = hello["config"]["loot"]["pickup_radius"]

    def act(self, obs: mf.Observation) -> mf.Action:
        me, (x, y, z) = obs["self"], obs["self"]["pos"]
        goal = obs["zone"]["next_center"]
        act: mf.Action = {"tick": obs["tick"]}
        
        if obs["offer"]: act["pick"] = 0

        # 1. GRAPH SETUP
        nodes = {**{f"p{i}": p["pos"][:2] for i, p in enumerate(obs["pickups"])}, "me": (x, y), "goal": goal[:2]}
        graph = {k1: [(k2, math.dist(p1, p2)) for k2, p2 in nodes.items() if k1 != k2 and math.dist(p1, p2) < 400] for k1, p1 in nodes.items()}

        # 2. GRAPH TRAVERSAL (DFS - Compacted)
        visited = set()
        def dfs(n): visited.add(n); [dfs(nx) for nx, _ in graph[n] if nx not in visited]
        dfs("me")

        # 3. DIJKSTRA'S ALGORITHM (Compacted)
        queue, seen, mins, path = [(0, "me", [])], set(), {"me": 0}, []
        while queue:
            cost, node, p = heapq.heappop(queue)
            if node == "goal": path = p + [node]; break
            if node not in seen:
                seen.add(node)
                for nxt, w in graph[node]:
                    if cost + w < mins.get(nxt, float('inf')):
                        mins[nxt] = cost + w
                        heapq.heappush(queue, (cost + w, nxt, p + [node]))

        # Pathing execution
        tg = nodes[path[1]] if len(path) > 1 else goal
        yaw = math.atan2(tg[1] - y, tg[0] - x)
        act.update(move=[math.cos(yaw), math.sin(yaw)], aim=[yaw, 0.0], boost=not me["in_zone"], jump=obs["tick"] % 40 == 0)

        # Looting
        near = [p for p in obs["pickups"] if math.dist(p["pos"][:2], (x, y)) < self.reach]
        if me["weapons"][1] is None and near and near[0]["kind"] != "gun": act["take"] = near[0]["id"]

        # 4. GREEDY ALGORITHM (Combat)
        mechs = [m for m in obs["mechs"] if m["kind"] == "mech"]
        enemy = min(mechs, key=lambda m: math.dist(m["pos"], (x, y, z))) if mechs else None

        if enemy:
            t = enemy["pos"]
            act.update(aim=[math.atan2(t[1]-y, t[0]-x), math.atan2(t[2]-z-2.5, math.dist(t[:2], (x,y)))], fire=[True, True])
            mf.draw.line([x, y, z + 7], [t[0], t[1], t[2] + 4.5], "#ff5040")

        return act

mf.run(Bot)