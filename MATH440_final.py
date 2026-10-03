import warnings
import numpy as np
import pandas as pd
from statsbombpy import sb
 
warnings.filterwarnings("ignore")
 
# ------------------------------------------------------------
# Settings
# ------------------------------------------------------------
FIRST_SEASON, LAST_SEASON = 2003, 2018          # 2003/04 through 2018/19
SHORT_CORNER_LENGTH = 15                        # pass shorter than this (yards) = short corner
ANOTHER_CORNER_SECONDS = 30                     # next corner by same team within this = "another corner"
 
GK_POSSESSION = ["Collected", "Smother", "Claim", "Keeper Sweeper"]
ON_TARGET = ["Goal", "Saved", "Saved to Post"]
 
# events that count as "a touch" when finding the first touch after the corner
TOUCH_TYPES = ["Ball Receipt*", "Clearance", "Duel", "Interception", "Block",
               "Ball Recovery", "Miscontrol", "Goal Keeper", "Shot", "Pass",
               "Carry", "Dribble", "Foul Committed", "Foul Won"]
 
NEEDED = ["pass_technique", "pass_height", "pass_body_part", "pass_end_location",
          "pass_length", "pass_recipient", "pass_outcome", "shot_outcome",
          "shot_statsbomb_xg", "shot_body_part", "shot_type", "foul_committed_penalty",
          "foul_won_penalty", "goalkeeper_type", "location", "player", "team"]
 
 
# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def xy(v):
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return v[0], v[1]
    return np.nan, np.nan
 
 
def dist_to_goal(x, y):
    # goal center is (120, 40) on StatsBomb's 120 x 80 pitch (units = yards)
    if pd.isna(x) or pd.isna(y):
        return np.nan
    return float(np.hypot(120 - x, 40 - y))
 
 
def delivery_type(length, x, y):
    if pd.isna(x) or pd.isna(y):
        return "Not recorded"
    if pd.notna(length) and length < SHORT_CORNER_LENGTH:
        return "Short"
    if x >= 102 and 18 <= y <= 62:
        return "Into the box"
    return "Outside the box"
 
 
def delivery_depth(x):
    if pd.isna(x):
        return "Not recorded"
    if x >= 114:
        return "Six-yard box"
    if x >= 102:
        return "Penalty area"
    return "Outside penalty area"
 
 
def delivery_zone(start_y, end_x, end_y):
    # near post = side of the goal closest to the corner taker
    if pd.isna(end_x) or pd.isna(end_y) or pd.isna(start_y):
        return "Not recorded"
    if end_x < 102 or end_y < 18 or end_y > 62:
        return "Outside box"
    d = end_y if start_y < 40 else 80 - end_y     # distance from the taker's side
    if d < 36:
        return "Near post"
    if d <= 44:
        return "Central"
    return "Far post"
 
 
# ------------------------------------------------------------
# 1. Champions League seasons
# ------------------------------------------------------------
comps = sb.competitions()
ucl = comps[comps["competition_name"] == "Champions League"].copy()
ucl["start_year"] = ucl["season_name"].str[:4].astype(int)
ucl = ucl[(ucl["start_year"] >= FIRST_SEASON) & (ucl["start_year"] <= LAST_SEASON)]
 
rows = []
 
# ------------------------------------------------------------
# 2. Every match, every corner kick
# ------------------------------------------------------------
for _, s in ucl.iterrows():
    matches = sb.matches(competition_id=s["competition_id"], season_id=s["season_id"])
    print("Season", s["season_name"], "-", len(matches), "matches")
 
    for _, m in matches.iterrows():
        try:
            ev = sb.events(match_id=m["match_id"])
        except Exception:
            continue
 
        for col in NEEDED:
            if col not in ev.columns:
                ev[col] = np.nan
        ev = ev.sort_values("index").reset_index(drop=True)
 
        corners = ev[(ev["type"] == "Pass") & (ev["pass_type"] == "Corner")]
 
        for _, c in corners.iterrows():
            # ---------- game info ----------
            is_home = c["team"] == m["home_team"]
            mine = m["home_score"] if is_home else m["away_score"]
            theirs = m["away_score"] if is_home else m["home_score"]
            game_result = "Win" if mine > theirs else ("Loss" if mine < theirs else "Draw")
 
            # ---------- corner kick characteristics ----------
            start_x, start_y = xy(c["location"])
            end_x, end_y = xy(c["pass_end_location"])
 
            # ---------- play after the corner (same possession) ----------
            poss = ev[ev["possession"] == c["possession"]]
            shots = poss[(poss["type"] == "Shot") & (poss["team"] == c["team"])]
            gk = poss[poss["type"] == "Goal Keeper"]
            first_shot = shots.iloc[0] if len(shots) else None
 
            # ---------- first touch after the corner ----------
            after = ev[(ev["index"] > c["index"]) & (ev["period"] == c["period"])
                       & (ev["type"].isin(TOUCH_TYPES))]
            if len(after):
                ft = after.iloc[0]
                ft_x, ft_y = xy(ft["location"])
                ft_type, ft_player, ft_team = ft["type"], ft["player"], ft["team"]
            else:
                ft_x = ft_y = np.nan
                ft_type = ft_player = ft_team = np.nan
 
            rows.append({
                # --- game ---
                "season": s["season_name"],
                "match_id": m["match_id"],
                "match_date": m["match_date"],
                "period": c["period"],
                "time_sec": c["minute"] * 60 + c["second"],
                # --- who took it ---
                "team": c["team"],
                "taker": c["player"],
                "home_or_away": "Home" if is_home else "Away",
                # --- corner kick method ---
                "swing_type": c["pass_technique"] if pd.notna(c["pass_technique"]) else "Not recorded",
                "height": c["pass_height"],
                "foot": c["pass_body_part"],
                "corner_side": "y=0 side" if start_y < 40 else "y=80 side",
                "delivery_type": delivery_type(c["pass_length"], end_x, end_y),
                "delivery_zone": delivery_zone(start_y, end_x, end_y),
                "delivery_depth": delivery_depth(end_x),
                "pass_length": c["pass_length"],
                "end_x": end_x,
                "end_y": end_y,
                "end_distance_to_goal": dist_to_goal(end_x, end_y),
                # --- who the delivery reached ---
                "reached_player": c["pass_recipient"],
                "delivery_completed": int(pd.isna(c["pass_outcome"])),
                # --- first touch after the corner ---
                "first_touch_type": ft_type,
                "first_touch_player": ft_player,
                "first_touch_by_attackers": (int(ft_team == c["team"]) if pd.notna(ft_team) else np.nan),
                "first_touch_x": ft_x,
                "first_touch_y": ft_y,
                "first_touch_distance_to_goal": dist_to_goal(ft_x, ft_y),
                # --- result of the corner (1 = yes, 0 = no) ---
                "shot": int(len(shots) > 0),
                "shot_on_goal": int(shots["shot_outcome"].isin(ON_TARGET).any()),
                "goal": int((shots["shot_outcome"] == "Goal").any()),
                "shot_xg": float(shots["shot_statsbomb_xg"].sum()),
                "shooter": first_shot["player"] if first_shot is not None else np.nan,
                "shot_header": int(first_shot is not None and first_shot["shot_body_part"] == "Head"),
                "goalie_action": int(len(gk) > 0),
                "goalie_possession": int(gk["goalkeeper_type"].isin(GK_POSSESSION).any()),
                "out_of_bounds": int((poss["pass_outcome"] == "Out").any()),
                "penalty": int((poss["shot_type"] == "Penalty").any()
                               or (poss["foul_committed_penalty"] == True).any()
                               or (poss["foul_won_penalty"] == True).any()),
                # --- game outcome for the team that took the corner ---
                "game_score": f"{m['home_team']} {int(m['home_score'])} - {int(m['away_score'])} {m['away_team']}",
                "game_score_for": mine,
                "game_score_against": theirs,
                "game_result": game_result,
                "team_won_game": int(game_result == "Win"),
            })
 
df = pd.DataFrame(rows)
 
# ------------------------------------------------------------
# 3. Another corner: same team takes the next corner shortly after
# ------------------------------------------------------------
df = df.sort_values(["match_id", "period", "time_sec"]).reset_index(drop=True)
g = df.groupby(["match_id", "period"])
df["another_corner"] = (((g["time_sec"].shift(-1) - df["time_sec"]) <= ANOTHER_CORNER_SECONDS)
                        & (g["team"].shift(-1) == df["team"])).astype(int)
 
# ------------------------------------------------------------
# 4. Hypothesis flag: high, outswinging corner sent to the center of the box
# ------------------------------------------------------------
df["hypothesis_corner"] = ((df["height"] == "High Pass")
                           & (df["swing_type"] == "Outswinging")
                           & (df["delivery_zone"] == "Central")).astype(int)
 
# ------------------------------------------------------------
# 5. Method label and conversion rates (conversion rate = goals / corners)
# ------------------------------------------------------------
df["corner_method"] = (df["swing_type"].astype(str) + " | " + df["height"].astype(str) + " | "
                       + df["delivery_type"].astype(str) + " | " + df["delivery_zone"].astype(str))
 
for name, col in [("method", "corner_method"), ("team", "team"), ("taker", "taker")]:
    df[name + "_corners"] = df.groupby(col)["goal"].transform("size")
    df[name + "_conversion_rate"] = df.groupby(col)["goal"].transform("mean")
 
# ------------------------------------------------------------
# 6. One sheet (most important variables first)
# ------------------------------------------------------------
order = [
    # --- the key variables ---
    "season", "team", "taker",
    "swing_type",                       # inswinging / outswinging / straight
    "delivery_zone",                    # near post / central / far post
    "delivery_type",                    # short or into the box
    "first_touch_distance_to_goal",     # how far from goal the first touch was made
    "reached_player",                   # which player the delivery reached
    "corner_method",                    # swing | height | short/box | zone
    "goal", "shot", "shot_on_goal",     # result of the corner
    "method_corners", "method_conversion_rate",
    "team_corners", "team_conversion_rate",
    "taker_corners", "taker_conversion_rate",
    "game_score", "game_result", "team_won_game",
    # --- extra detail ---
    "match_date", "home_or_away", "height", "foot", "corner_side", "delivery_depth",
    "pass_length", "end_x", "end_y", "end_distance_to_goal", "delivery_completed",
    "first_touch_type", "first_touch_player", "first_touch_by_attackers",
    "first_touch_x", "first_touch_y",
    "shot_xg", "shooter", "shot_header",
    "another_corner", "goalie_action", "goalie_possession", "out_of_bounds", "penalty",
    "game_score_for", "game_score_against",
    "hypothesis_corner",
]
df = df[order]
 
with pd.ExcelWriter("ucl_corners.xlsx", engine="openpyxl") as w:
    df.to_excel(w, sheet_name="Corners", index=False)
    w.sheets["Corners"].freeze_panes = "A2"
 
print("Saved ucl_corners.xlsx with", len(df), "corner kicks")