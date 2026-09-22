import pandas as pd
from statsbombpy import sb


# ============================================================
# 1. FIND THE 2012 CHAMPIONS LEAGUE FINAL
# ============================================================

COMPETITION_ID = 16   # UEFA Champions League
SEASON_ID = 23        # 2011/12 season = 2012 final

print("Loading Champions League matches...")

matches = sb.matches(
    competition_id=COMPETITION_ID,
    season_id=SEASON_ID
)

# Find Bayern Munich vs Chelsea
final = matches[
    (
        matches["home_team"].astype(str).str.contains(
            "Bayern", case=False, na=False
        )
        &
        matches["away_team"].astype(str).str.contains(
            "Chelsea", case=False, na=False
        )
    )
    |
    (
        matches["home_team"].astype(str).str.contains(
            "Chelsea", case=False, na=False
        )
        &
        matches["away_team"].astype(str).str.contains(
            "Bayern", case=False, na=False
        )
    )
]

if final.empty:
    print("Could not find Bayern vs Chelsea.")
    print(matches[["match_id", "home_team", "away_team"]].to_string())
    raise SystemExit

match = final.iloc[0]

match_id = match["match_id"]
home_team = match["home_team"]
away_team = match["away_team"]

print()
print("2012 Champions League Final")
print("----------------------------")
print(f"{home_team} vs {away_team}")
print(f"Match ID: {match_id}")
print()


# ============================================================
# 2. GET ALL EVENT DATA
# ============================================================

print("Downloading event data...")

events = sb.events(match_id=match_id)

# Sort chronologically
if "index" in events.columns:
    events = events.sort_values("index").reset_index(drop=True)

print(f"Total events: {len(events)}")


# ============================================================
# 3. FIND ALL CORNERS
# ============================================================

corners = events[
    (events["type"] == "Pass") &
    (events["pass_type"] == "Corner")
].copy()

print(f"Total corners: {len(corners)}")
print()


# ============================================================
# 4. SAFE VALUE FUNCTION
# ============================================================

def get_value(row, column):
    """
    Safely retrieve a StatsBomb field.

    This is important because StatsBomb locations are stored
    as lists such as [120.0, 5.0]. Calling pd.notna() directly
    on those lists causes the 'truth value of an array is
    ambiguous' error.
    """

    if column not in row.index:
        return None

    value = row[column]

    # Missing value
    if value is None:
        return None

    # StatsBomb coordinate lists, e.g. [120.0, 5.0]
    if isinstance(value, (list, tuple)):
        return value

    # Safely check scalar values for NaN
    try:
        if pd.isna(value):
            return None
    except (ValueError, TypeError):
        pass

    return value


# ============================================================
# 5. FORMAT LOCATIONS
# ============================================================

def format_location(location):
    """
    Convert StatsBomb [x, y] coordinates into readable text.
    """

    if location is None:
        return "Not recorded"

    if isinstance(location, (list, tuple)) and len(location) >= 2:
        return f"({location[0]:.1f}, {location[1]:.1f})"

    return str(location)


# ============================================================
# 6. DETERMINE CORNER TYPE
# ============================================================

def get_corner_type(technique):
    """
    StatsBomb may record corner technique information.

    Depending on the match/event data, this can sometimes
    be missing.
    """

    if technique is None:
        return "Not recorded"

    technique_string = str(technique).lower()

    if "inswing" in technique_string:
        return "Inswinging"

    if "outswing" in technique_string:
        return "Outswinging"

    if "straight" in technique_string:
        return "Straight"

    return str(technique)


# ============================================================
# 7. GET EVENTS AFTER EACH CORNER
# ============================================================

def get_following_events(corner_index, number_of_events=20):
    """
    Return the next events after a corner.

    We use StatsBomb's event index when available.
    """

    if "index" not in events.columns:
        return pd.DataFrame()

    corner_event_index = get_value(corners.loc[corner_index], "index")

    if corner_event_index is None:
        return pd.DataFrame()

    following = events[
        events["index"] > corner_event_index
    ].sort_values("index").head(number_of_events)

    return following


# ============================================================
# 8. ANALYZE EACH CORNER
# ============================================================

corner_data = []

for corner_number, (corner_index, corner) in enumerate(
    corners.iterrows(),
    start=1
):

    # --------------------------------------------------------
    # Basic corner information
    # --------------------------------------------------------

    minute = get_value(corner, "minute")
    second = get_value(corner, "second")

    team = get_value(corner, "team")
    player = get_value(corner, "player")

    start_location = get_value(corner, "location")
    end_location = get_value(corner, "pass_end_location")

    technique = get_value(corner, "pass_technique")
    pass_outcome = get_value(corner, "pass_outcome")
    pass_height = get_value(corner, "pass_height")

    # --------------------------------------------------------
    # Corner type
    # --------------------------------------------------------

    corner_type = get_corner_type(technique)

    # --------------------------------------------------------
    # Following events
    # --------------------------------------------------------

    following_events = get_following_events(
        corner_index,
        number_of_events=20
    )

    first_event = None
    first_event_player = None

    shot_occurred = False
    shot_player = None
    shot_outcome = None
    shot_xg = None

    goal_occurred = False

    # --------------------------------------------------------
    # Look through subsequent events
    # --------------------------------------------------------

    if not following_events.empty:

        for _, event in following_events.iterrows():

            event_type = get_value(event, "type")
            event_player = get_value(event, "player")

            # Save first event after corner
            if first_event is None:
                first_event = event_type

                if event_player is not None:
                    first_event_player = event_player

            # ------------------------------------------------
            # Shot
            # ------------------------------------------------

            if event_type == "Shot":

                shot_occurred = True

                if shot_player is None:
                    shot_player = event_player

                outcome = get_value(event, "shot_outcome")

                if outcome is not None:
                    shot_outcome = outcome

                xg = get_value(event, "shot_statsbomb_xg")

                if xg is not None:
                    shot_xg = xg

                # A goal is a shot with outcome "Goal"
                if str(outcome).lower() == "goal":
                    goal_occurred = True

                # Stop once we've found the shot
                break

    # --------------------------------------------------------
    # Direct shot-assist information
    # --------------------------------------------------------

    assisted_shot_id = get_value(
        corner,
        "pass_assisted_shot_id"
    )

    direct_shot = None
    direct_shot_outcome = None
    direct_shot_xg = None
    direct_shot_player = None

    if assisted_shot_id is not None:

        matching_shots = events[
            events["id"].astype(str) ==
            str(assisted_shot_id)
        ]

        if not matching_shots.empty:

            direct_shot = matching_shots.iloc[0]

            direct_shot_player = get_value(
                direct_shot,
                "player"
            )

            direct_shot_outcome = get_value(
                direct_shot,
                "shot_outcome"
            )

            direct_shot_xg = get_value(
                direct_shot,
                "shot_statsbomb_xg"
            )

    # --------------------------------------------------------
    # Determine result description
    # --------------------------------------------------------

    if direct_shot is not None:

        result = "Direct shot from corner"

        if str(direct_shot_outcome).lower() == "goal":
            result = "GOAL from corner"

    elif goal_occurred:

        result = "Goal in subsequent events"

    elif shot_occurred:

        result = "Shot in subsequent events"

    elif first_event is not None:

        result = f"First event: {first_event}"

    else:

        result = "No subsequent event found"

    # --------------------------------------------------------
    # Save information
    # --------------------------------------------------------

    corner_data.append({

        "Corner #": corner_number,

        "Minute": minute,

        "Second": second,

        "Team": team,

        "Player": player,

        "Taken From": format_location(start_location),

        "Sent To": format_location(end_location),

        "Corner Type": corner_type,

        "Technique": technique,

        "Pass Height": pass_height,

        "Pass Outcome": pass_outcome,

        "First Event After Corner": first_event,

        "First Event Player": first_event_player,

        "Shot Occurred": "Yes" if shot_occurred else "No",

        "Shot Player": shot_player,

        "Shot Outcome": shot_outcome,

        "Shot xG": shot_xg,

        "Direct Shot From Corner": (
            "Yes" if direct_shot is not None else "No"
        ),

        "Direct Shot Player": direct_shot_player,

        "Direct Shot Outcome": direct_shot_outcome,

        "Direct Shot xG": direct_shot_xg,

        "Goal From Corner": (
            "Yes"
            if (
                direct_shot is not None
                and str(direct_shot_outcome).lower() == "goal"
            )
            else "No"
        ),

        "Result": result
    })


# ============================================================
# 9. CREATE CLEAN DATAFRAME
# ============================================================

corner_table = pd.DataFrame(corner_data)


# ============================================================
# 10. PRINT TABLE
# ============================================================

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 30)

print()
print("=" * 100)
print("CORNER KICK ANALYSIS")
print("=" * 100)
print()

print(corner_table.to_string(index=False))


# ============================================================
# 11. SUMMARY
# ============================================================

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)

print(f"Total corners: {len(corner_table)}")

if len(corner_table) > 0:

    print()
    print("Corners by team:")

    print(
        corner_table["Team"]
        .value_counts()
        .to_string()
    )

    print()
    print("Corner types:")

    print(
        corner_table["Corner Type"]
        .value_counts()
        .to_string()
    )

    print()
    print(
        f"Shots after corners: "
        f"{(corner_table['Shot Occurred'] == 'Yes').sum()}"
    )

    print(
        f"Direct shots from corners: "
        f"{(corner_table['Direct Shot From Corner'] == 'Yes').sum()}"
    )

    print(
        f"Goals directly from corners: "
        f"{(corner_table['Goal From Corner'] == 'Yes').sum()}"
    )


# ============================================================
# 12. SAVE TO CSV
# ============================================================

output_file = "2012_champions_league_final_corners.csv"

corner_table.to_csv(
    output_file,
    index=False
)

print()
print(f"Saved corner analysis to:")
print(output_file)
print()


# ============================================================
# 13. SAVE TO EXCEL
# ============================================================

excel_file = "2012_champions_league_final_corners.xlsx"

corner_table.to_excel(
    excel_file,
    index=False
)

print(f"Saved Excel version to:")
print(excel_file)
print()