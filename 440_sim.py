import warnings
import os
import re
import numpy as np
import pandas as pd
from statsbombpy import sb

warnings.filterwarnings("ignore")

# SETTINGS

FIRST_SEASON = 2003
LAST_SEASON = 2018

SHORT_CORNER_LENGTH = 15
ANOTHER_CORNER_SECONDS = 30

# StatsBomb will use whatever seasons are actually available
# between 2003/04 and 2018/19.
LEAGUES = [
    "Champions League",
    "La Liga",
    "Premier League",
    "1. Bundesliga",
    "Serie A",
]

GK_POSSESSION = [
    "Collected",
    "Smother",
    "Claim",
    "Keeper Sweeper"
]

ON_TARGET = [
    "Goal",
    "Saved",
    "Saved to Post"
]

# Events considered a "touch" when finding the first touch
# after the corner.
TOUCH_TYPES = [
    "Ball Receipt*",
    "Clearance",
    "Duel",
    "Interception",
    "Block",
    "Ball Recovery",
    "Miscontrol",
    "Goal Keeper",
    "Shot",
    "Pass",
    "Carry",
    "Dribble",
    "Foul Committed",
    "Foul Won"
]

# Columns used by the analysis.
# Missing columns are automatically created as NaN 
NEEDED = [
    "pass_type",
    "pass_technique",
    "pass_height",
    "pass_body_part",
    "pass_end_location",
    "pass_length",
    "pass_recipient",
    "pass_outcome",
    "pass_cross",
    "pass_aerial_won",
    "pass_angle",

    "shot_outcome",
    "shot_statsbomb_xg",
    "shot_body_part",
    "shot_type",

    "foul_committed_penalty",
    "foul_won_penalty",

    "goalkeeper_type",

    "location",
    "player",
    "team",

    "possession",
    "period",
    "minute",
    "second",
    "index",
    "type"
]

# BASIC HELPERS

def xy(value):
    """
    Extract x and y coordinates from a StatsBomb location.
    """

    if (
        isinstance(value, (list, tuple, np.ndarray))
        and len(value) >= 2
    ):
        return value[0], value[1]

    return np.nan, np.nan


def dist_to_goal(x, y):
    """
    Distance from a location to the center of the goal.

    StatsBomb pitch:
        x = 0 to 120
        y = 0 to 80

    Goal center:
        (120, 40)
    """

    if pd.isna(x) or pd.isna(y):
        return np.nan

    return float(
        np.hypot(
            120 - x,
            40 - y
        )
    )


def safe_filename(name):
    """
    Convert competition name to safe Excel filename.
    """

    name = re.sub(
        r"[^\w\s-]",
        "",
        str(name)
    )

    name = re.sub(
        r"\s+",
        "_",
        name.strip()
    )

    return name


def get_start_year(season_name):
    """
    Examples:

        2003/2004 -> 2003
        2018/2019 -> 2018
        2018      -> 2018
    """

    try:
        return int(str(season_name)[:4])

    except Exception:
        return np.nan


def text_matches(series, value):
    """
    Case-insensitive partial matching helper.
    """

    return (
        series
        .astype(str)
        .str.strip()
        .str.casefold()
        .str.contains(
            str(value).strip().casefold(),
            regex=False,
            na=False
        )
    )

# CORNER CLASSIFICATION

def delivery_type(length, end_x, end_y):
    """
    Classify corner as:

        Short
        Into the box
        Outside the box
        Not recorded
    """

    if pd.isna(end_x) or pd.isna(end_y):
        return "Not recorded"

    if (
        pd.notna(length)
        and length < SHORT_CORNER_LENGTH
    ):
        return "Short"

    if (
        end_x >= 102
        and 18 <= end_y <= 62
    ):
        return "Into the box"

    return "Outside the box"


def delivery_depth(end_x):
    """
    Classify how deep the delivery went.
    """

    if pd.isna(end_x):
        return "Not recorded"

    if end_x >= 114:
        return "Six-yard box"

    if end_x >= 102:
        return "Penalty area"

    return "Outside penalty area"


def delivery_zone(start_y, end_x, end_y):
    """
    Classify delivery as:

        Near post
        Central
        Far post
        Outside box

    """

    if (
        pd.isna(start_y)
        or pd.isna(end_x)
        or pd.isna(end_y)
    ):
        return "Not recorded"

    if (
        end_x < 102
        or end_y < 18
        or end_y > 62
    ):
        return "Outside box"

    if start_y < 40:
        distance_from_taker_side = end_y
    else:
        distance_from_taker_side = 80 - end_y

    if distance_from_taker_side < 36:
        return "Near post"

    if distance_from_taker_side <= 44:
        return "Central"

    return "Far post"


def corner_side(start_y):
    """
    Which side of the field the corner was taken from.
    """

    if pd.isna(start_y):
        return "Not recorded"

    if start_y < 40:
        return "y=0 side"

    return "y=80 side"


# AVAILABLE STATSBOMB SEASONS

def get_available_league_seasons():
    """
    Find available StatsBomb seasons for our five competitions
    between 2003/04 and 2018/19.
    """

    comps = sb.competitions().copy()

    comps["start_year"] = (
        comps["season_name"]
        .apply(get_start_year)
    )

    comps = comps[
        comps["competition_name"].isin(LEAGUES)
        &
        comps["start_year"].between(
            FIRST_SEASON,
            LAST_SEASON,
            inclusive="both"
        )
    ].copy()

    return comps


# EXTRACT CORNERS FROM ONE MATCH

def extract_match_corners(
    events,
    match,
    season_name,
    league_name
):

    rows = []

    ev = events.copy()

    # Add missing columns

    for col in NEEDED:

        if col not in ev.columns:
            ev[col] = np.nan

    ev = (
        ev.sort_values("index")
        .reset_index(drop=True)
    )

    # Find corners

    corners = ev[
        (ev["type"] == "Pass")
        &
        (ev["pass_type"] == "Corner")
    ]

    # Process each corner

    for _, c in corners.iterrows():

        # GAME INFORMATION

        is_home = (
            c["team"]
            == match["home_team"]
        )

        if is_home:

            goals_for = (
                match["home_score"]
            )

            goals_against = (
                match["away_score"]
            )

        else:

            goals_for = (
                match["away_score"]
            )

            goals_against = (
                match["home_score"]
            )

        if goals_for > goals_against:
            game_result = "Win"

        elif goals_for < goals_against:
            game_result = "Loss"

        else:
            game_result = "Draw"

        # CORNER START / END LOCATION

        start_x, start_y = xy(
            c["location"]
        )

        end_x, end_y = xy(
            c["pass_end_location"]
        )

        # SAME POSSESSION AFTER CORNER

        possession = ev[
            (ev["possession"] == c["possession"])
            &
            (ev["index"] >= c["index"])
        ]

        attacking_possession = possession[
            possession["team"]
            == c["team"]
        ]

        shots = attacking_possession[
            attacking_possession["type"]
            == "Shot"
        ]

        goals = shots[
            shots["shot_outcome"]
            == "Goal"
        ]

        goalkeeper_events = possession[
            possession["type"]
            == "Goal Keeper"
        ]

        if len(shots) > 0:
            first_shot = shots.iloc[0]

        else:
            first_shot = None

        # FIRST TOUCH AFTER CORNER

        after_corner = ev[
            (ev["index"] > c["index"])
            &
            (ev["period"] == c["period"])
            &
            (ev["type"].isin(TOUCH_TYPES))
        ]

        if len(after_corner) > 0:

            first_touch = (
                after_corner.iloc[0]
            )

            ft_x, ft_y = xy(
                first_touch["location"]
            )

            ft_type = (
                first_touch["type"]
            )

            ft_player = (
                first_touch["player"]
            )

            ft_team = (
                first_touch["team"]
            )

            first_touch_by_attackers = int(
                ft_team == c["team"]
            )

        else:

            ft_x = np.nan
            ft_y = np.nan

            ft_type = np.nan
            ft_player = np.nan
            ft_team = np.nan

            first_touch_by_attackers = (
                np.nan
            )

       # MAIN CORNER CHARACTERISTICS

        if pd.notna(
            c["pass_technique"]
        ):

            swing = (
                c["pass_technique"]
            )

        else:

            swing = "Not recorded"

        if pd.notna(
            c["pass_height"]
        ):

            height = (
                c["pass_height"]
            )

        else:

            height = "Not recorded"

        if pd.notna(
            c["pass_body_part"]
        ):

            foot = (
                c["pass_body_part"]
            )

        else:

            foot = "Not recorded"

        d_type = delivery_type(
            c["pass_length"],
            end_x,
            end_y
        )

        d_zone = delivery_zone(
            start_y,
            end_x,
            end_y
        )

        d_depth = delivery_depth(
            end_x
        )

        # SAVE CORNER

        rows.append({

            # LEAGUE / SEASON

            "league":
                league_name,

            "season":
                season_name,

            # TEAM / PLAYER

            "team":
                c["team"],

            "taker":
                c["player"],

            # MAIN CORNER METHOD VARIABLES

            "swing_type":
                swing,

            "delivery_zone":
                d_zone,

            "delivery_type":
                d_type,

            "delivery_depth":
                d_depth,

            "height":
                height,

            "foot":
                foot,

            "corner_side":
                corner_side(start_y),

            # PASS / DELIVERY INFORMATION

            "pass_length":
                c["pass_length"],

            "pass_angle":
                c["pass_angle"],

            "pass_cross":
                c["pass_cross"],

            "pass_aerial_won":
                c["pass_aerial_won"],

            "end_x":
                end_x,

            "end_y":
                end_y,

            "end_distance_to_goal":
                dist_to_goal(
                    end_x,
                    end_y
                ),

            # PLAYER DELIVERY REACHED

            "reached_player":
                c["pass_recipient"],

            "delivery_completed":
                int(
                    pd.isna(
                        c["pass_outcome"]
                    )
                ),

            # FIRST TOUCH

            "first_touch_type":
                ft_type,

            "first_touch_player":
                ft_player,

            "first_touch_team":
                ft_team,

            "first_touch_by_attackers":
                first_touch_by_attackers,

            "first_touch_x":
                ft_x,

            "first_touch_y":
                ft_y,

            "first_touch_distance_to_goal":
                dist_to_goal(
                    ft_x,
                    ft_y
                ),

            # PRIMARY OUTCOME

            "goal":
                int(
                    len(goals) > 0
                ),

            # EXTRA OUTCOMES

            "shot":
                int(
                    len(shots) > 0
                ),

            "shot_on_goal":
                int(
                    shots[
                        "shot_outcome"
                    ]
                    .isin(ON_TARGET)
                    .any()
                ),

            "shot_xg":
                float(
                    shots[
                        "shot_statsbomb_xg"
                    ]
                    .fillna(0)
                    .sum()
                ),

            "shooter":
                (
                    first_shot["player"]
                    if first_shot
                    is not None
                    else np.nan
                ),

            "shot_header":
                int(
                    first_shot
                    is not None
                    and
                    first_shot[
                        "shot_body_part"
                    ] == "Head"
                ),

            # OTHER OUTCOMES

            "goalie_action":
                int(
                    len(
                        goalkeeper_events
                    ) > 0
                ),

            "goalie_possession":
                int(
                    goalkeeper_events[
                        "goalkeeper_type"
                    ]
                    .isin(
                        GK_POSSESSION
                    )
                    .any()
                ),

            "out_of_bounds":
                int(
                    (
                        possession[
                            "pass_outcome"
                        ] == "Out"
                    ).any()
                ),

            "penalty":
                int(
                    (
                        possession[
                            "shot_type"
                        ] == "Penalty"
                    ).any()

                    or

                    (
                        possession[
                            "foul_committed_penalty"
                        ] == True
                    ).any()

                    or

                    (
                        possession[
                            "foul_won_penalty"
                        ] == True
                    ).any()
                ),

            # MATCH INFORMATION

            "match_id":
                match["match_id"],

            "match_date":
                match["match_date"],

            "period":
                c["period"],

            "time_sec":
                (
                    c["minute"] * 60
                    + c["second"]
                ),

            "home_or_away":
                (
                    "Home"
                    if is_home
                    else "Away"
                ),

            # GAME RESULT

            "game_score":
                (
                    f"{match['home_team']} "
                    f"{int(match['home_score'])}"
                    " - "
                    f"{int(match['away_score'])} "
                    f"{match['away_team']}"
                ),

            "game_score_for":
                goals_for,

            "game_score_against":
                goals_against,

            "game_result":
                game_result,

            "team_won_game":
                int(
                    game_result
                    == "Win"
                ),
        })

    return rows


# ADD CONVERSION RATES 

def add_statistics(df):

    if df.empty:
        return df

    df = df.copy()

    # SORT CHRONOLOGICALLY

    df = (
        df.sort_values(
            [
                "match_id",
                "period",
                "time_sec"
            ]
        )
        .reset_index(drop=True)
    )

    # ANOTHER CORNER

    grouped = df.groupby(
        [
            "match_id",
            "period"
        ]
    )

    next_time = (
        grouped["time_sec"]
        .shift(-1)
    )

    next_team = (
        grouped["team"]
        .shift(-1)
    )

    df["another_corner"] = (

        (
            (
                next_time
                - df["time_sec"]
            )
            <= ANOTHER_CORNER_SECONDS
        )

        &

        (
            next_team
            == df["team"]
        )
    )

    df["another_corner"] = (
        df["another_corner"]
        .fillna(False)
        .astype(int)
    )

    # METHOD LABEL

    df["corner_method"] = (

        df["swing_type"]
        .astype(str)

        + " | "

        + df["height"]
        .astype(str)

        + " | "

        + df["delivery_type"]
        .astype(str)

        + " | "

        + df["delivery_zone"]
        .astype(str)

        + " | "

        + df["delivery_depth"]
        .astype(str)

        + " | "

        + df["foot"]
        .astype(str)
    )

    # METHOD CONVERSION

    df["method_corners"] = (
        df.groupby(
            "corner_method"
        )["goal"]
        .transform("size")
    )

    df["method_goals"] = (
        df.groupby(
            "corner_method"
        )["goal"]
        .transform("sum")
    )

    df[
        "method_conversion_rate"
    ] = (
        df.groupby(
            "corner_method"
        )["goal"]
        .transform("mean")
    )

    # TEAM CONVERSION

    df["team_corners"] = (
        df.groupby(
            "team"
        )["goal"]
        .transform("size")
    )

    df["team_goals"] = (
        df.groupby(
            "team"
        )["goal"]
        .transform("sum")
    )

    df[
        "team_conversion_rate"
    ] = (
        df.groupby(
            "team"
        )["goal"]
        .transform("mean")
    )

    # CORNER TAKER CONVERSION

    df["taker_corners"] = (
        df.groupby(
            "taker"
        )["goal"]
        .transform("size")
    )

    df["taker_goals"] = (
        df.groupby(
            "taker"
        )["goal"]
        .transform("sum")
    )

    df[
        "taker_conversion_rate"
    ] = (
        df.groupby(
            "taker"
        )["goal"]
        .transform("mean")
    )

    return df


# COLUMN ORDER FOR EXCEL

def reorder_columns(df):

    order = [

        # IDENTIFICATION

        "league",
        "season",

        "team",
        "taker",

        # MAIN PROJECT VARIABLES

        "swing_type",

        "delivery_zone",

        "delivery_type",

        "first_touch_distance_to_goal",

        "reached_player",

        # OTHER IMPORTANT METHOD VARIABLES

        "height",

        "foot",

        "delivery_depth",

        "corner_side",

        "corner_method",

        # PRIMARY OUTCOME

        "goal",

        # METHOD CONVERSION

        "method_corners",
        "method_goals",
        "method_conversion_rate",

        # TEAM CONVERSION

        "team_corners",
        "team_goals",
        "team_conversion_rate",

        # CORNER TAKER CONVERSION

        "taker_corners",
        "taker_goals",
        "taker_conversion_rate",

        # WINNING / GAME RESULT

        "game_score",
        "game_result",
        "team_won_game",

        # MATCH INFO

        "match_date",
        "match_id",

        "period",
        "time_sec",

        "home_or_away",

        # DELIVERY DETAILS

        "pass_length",
        "pass_angle",
        "pass_cross",
        "pass_aerial_won",

        "end_x",
        "end_y",

        "end_distance_to_goal",

        "delivery_completed",

        # FIRST TOUCH DETAILS

        "first_touch_type",

        "first_touch_player",

        "first_touch_team",

        "first_touch_by_attackers",

        "first_touch_x",

        "first_touch_y",

        # EXTRA OUTCOMES

        "shot",

        "shot_on_goal",

        "shot_xg",

        "shooter",

        "shot_header",

        "another_corner",

        "goalie_action",

        "goalie_possession",

        "out_of_bounds",

        "penalty",

        # SCORE

        "game_score_for",

        "game_score_against",
    ]

    existing = [
        column
        for column in order
        if column in df.columns
    ]

    return df[existing]


# COLLECT ONE LEAGUE

def collect_league(
    competition_rows,
    league_name
):

    rows = []

    league_seasons = (
        competition_rows[
            competition_rows[
                "competition_name"
            ]
            == league_name
        ]
        .copy()
    )

    if league_seasons.empty:
        return pd.DataFrame()

    for _, season in (
        league_seasons.iterrows()
    ):

        try:

            matches = sb.matches(

                competition_id=
                    season[
                        "competition_id"
                    ],

                season_id=
                    season[
                        "season_id"
                    ]
            )

        except Exception:

            continue

        for _, match in (
            matches.iterrows()
        ):

            try:

                events = sb.events(
                    match_id=
                        match["match_id"]
                )

            except Exception:

                continue

            match_rows = (
                extract_match_corners(

                    events=
                        events,

                    match=
                        match,

                    season_name=
                        season[
                            "season_name"
                        ],

                    league_name=
                        league_name
                )
            )

            rows.extend(
                match_rows
            )

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        return df

    df = add_statistics(
        df
    )

    df = reorder_columns(
        df
    )

    return df

# SAVE EACH LEAGUE TO ITS OWN EXCEL FILE

def save_league(
    df,
    league_name
):

    filename = (
        safe_filename(
            league_name
        )
        + "_corners.xlsx"
    )

    with pd.ExcelWriter(
        filename,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Corners",
            index=False
        )

        sheet = (
            writer.sheets[
                "Corners"
            ]
        )

        sheet.freeze_panes = "A2"

        sheet.auto_filter.ref = (
            sheet.dimensions
        )

    return filename


# BUILD ALL FIVE DATABASES

def build_database():

    competitions = (
        get_available_league_seasons()
    )

    league_data = {}

    for league in LEAGUES:

        df = collect_league(
            competitions,
            league
        )

        league_data[
            league
        ] = df

        if not df.empty:

            filename = save_league(
                df,
                league
            )

            # Minimal console printing
            print(
                f"{league}: "
                f"{len(df):,} corners -> "
                f"{filename}"
            )

        else:

            print(
                f"{league}: "
                "no available data"
            )

    return league_data


# LOAD THE FIVE SAVED FILES

def load_saved_leagues():

    frames = []

    for league in LEAGUES:

        filename = (
            safe_filename(
                league
            )
            + "_corners.xlsx"
        )

        if os.path.exists(
            filename
        ):

            temp = pd.read_excel(
                filename
            )

            frames.append(
                temp
            )

    if not frames:

        return pd.DataFrame()

    return pd.concat(
        frames,
        ignore_index=True
    )


# BASIC DATABASE SEARCH

def search_corners(
    df,
    league=None,
    season=None,
    team=None,
    corner_taker=None,
    reached_player=None
):

    result = df.copy()

    if league is not None:

        result = result[
            text_matches(
                result["league"],
                league
            )
        ]

    if season is not None:

        result = result[
            text_matches(
                result["season"],
                season
            )
        ]

    if team is not None:

        result = result[
            text_matches(
                result["team"],
                team
            )
        ]

    if corner_taker is not None:

        result = result[
            text_matches(
                result["taker"],
                corner_taker
            )
        ]

    if reached_player is not None:

        result = result[
            text_matches(
                result[
                    "reached_player"
                ],
                reached_player
            )
        ]

    return result.copy()


# CONDITIONAL GOAL PROBABILITY

def conditional_goal_probability(
    df,

    # General
    league=None,
    season=None,
    team=None,

    # Player variables
    corner_taker=None,
    reached_player=None,

    # Main corner characteristics
    swing_type=None,
    delivery_zone=None,
    delivery_type=None,

    # Additional characteristics
    height=None,
    foot=None,
    delivery_depth=None,

    # First-touch distance
    min_first_touch_distance=None,
    max_first_touch_distance=None
):

    subset = search_corners(

        df,

        league=
            league,

        season=
            season,

        team=
            team,

        corner_taker=
            corner_taker,

        reached_player=
            reached_player
    )

    # SWING

    if swing_type is not None:

        subset = subset[
            text_matches(
                subset[
                    "swing_type"
                ],
                swing_type
            )
        ]

    # DELIVERY ZONE

    if delivery_zone is not None:

        subset = subset[
            text_matches(
                subset[
                    "delivery_zone"
                ],
                delivery_zone
            )
        ]

    # SHORT / INTO BOX

    if delivery_type is not None:

        subset = subset[
            text_matches(
                subset[
                    "delivery_type"
                ],
                delivery_type
            )
        ]

    # HEIGHT

    if height is not None:

        subset = subset[
            text_matches(
                subset[
                    "height"
                ],
                height
            )
        ]

    # FOOT

    if foot is not None:

        subset = subset[
            text_matches(
                subset[
                    "foot"
                ],
                foot
            )
        ]

    # DELIVERY DEPTH

    if delivery_depth is not None:

        subset = subset[
            text_matches(
                subset[
                    "delivery_depth"
                ],
                delivery_depth
            )
        ]

    # FIRST TOUCH DISTANCE

    if (
        min_first_touch_distance
        is not None
    ):

        subset = subset[
            subset[
                "first_touch_distance_to_goal"
            ]
            >= min_first_touch_distance
        ]

    if (
        max_first_touch_distance
        is not None
    ):

        subset = subset[
            subset[
                "first_touch_distance_to_goal"
            ]
            <= max_first_touch_distance
        ]

    # CONDITIONAL PROBABILITY

    matching_corners = len(
        subset
    )

    if matching_corners == 0:

        return {

            "matching_corners":
                0,

            "goals":
                0,

            "goal_probability":
                np.nan,

            "goal_percentage":
                np.nan,

            "matching_data":
                subset
        }

    goals = int(
        subset["goal"].sum()
    )

    probability = (
        goals
        /
        matching_corners
    )

    return {

        "matching_corners":
            matching_corners,

        "goals":
            goals,

        "goal_probability":
            probability,

        "goal_percentage":
            probability * 100,

        "matching_data":
            subset
    }


# RANK TEAMS BY CORNER CONVERSION

def rank_teams(
    df,
    min_corners=20
):

    if df.empty:
        return pd.DataFrame()

    # TEAM RESULTS

    team_summary = (

        df.groupby("team")

        .agg(

            corners=
                ("goal", "size"),

            goals=
                ("goal", "sum")
        )

        .reset_index()
    )

    team_summary[
        "conversion_rate"
    ] = (

        team_summary[
            "goals"
        ]

        /

        team_summary[
            "corners"
        ]
    )

    team_summary[
        "conversion_percentage"
    ] = (

        team_summary[
            "conversion_rate"
        ]

        * 100
    )

    # PREFERRED METHOD

    preferred = (

        df.groupby(
            [
                "team",
                "corner_method"
            ]
        )

        .size()

        .reset_index(
            name="times_used"
        )

        .sort_values(
            [
                "team",
                "times_used"
            ],
            ascending=[
                True,
                False
            ]
        )

        .drop_duplicates(
            "team"
        )
    )

    preferred = (

        preferred[
            [
                "team",
                "corner_method",
                "times_used"
            ]
        ]

        .rename(
            columns={

                "corner_method":
                    "preferred_method",

                "times_used":
                    "preferred_method_uses"
            }
        )
    )

    team_summary = (
        team_summary.merge(
            preferred,
            on="team",
            how="left"
        )
    )

    team_summary = (
        team_summary[
            team_summary[
                "corners"
            ]
            >= min_corners
        ]
    )

    return (

        team_summary

        .sort_values(
            [
                "conversion_rate",
                "goals"
            ],
            ascending=False
        )

        .reset_index(
            drop=True
        )
    )


# RANK CORNER TAKERS

def rank_players(
    df,
    min_corners=10
):

    if df.empty:
        return pd.DataFrame()

    player_summary = (

        df.groupby(
            "taker"
        )

        .agg(

            corners=
                ("goal", "size"),

            goals=
                ("goal", "sum")
        )

        .reset_index()
    )

    player_summary[
        "conversion_rate"
    ] = (

        player_summary[
            "goals"
        ]

        /

        player_summary[
            "corners"
        ]
    )

    player_summary[
        "conversion_percentage"
    ] = (

        player_summary[
            "conversion_rate"
        ]

        * 100
    )

    # PLAYER'S PREFERRED METHOD

    preferred = (

        df.groupby(
            [
                "taker",
                "corner_method"
            ]
        )

        .size()

        .reset_index(
            name="times_used"
        )

        .sort_values(
            [
                "taker",
                "times_used"
            ],
            ascending=[
                True,
                False
            ]
        )

        .drop_duplicates(
            "taker"
        )
    )

    preferred = (

        preferred[
            [
                "taker",
                "corner_method",
                "times_used"
            ]
        ]

        .rename(
            columns={

                "corner_method":
                    "preferred_method",

                "times_used":
                    "preferred_method_uses"
            }
        )
    )

    player_summary = (
        player_summary.merge(
            preferred,
            on="taker",
            how="left"
        )
    )

    player_summary = (
        player_summary[
            player_summary[
                "corners"
            ]
            >= min_corners
        ]
    )

    return (

        player_summary

        .sort_values(
            [
                "conversion_rate",
                "goals"
            ],
            ascending=False
        )

        .reset_index(
            drop=True
        )
    )


# RANK CORNER METHODS

def rank_corner_methods(
    df,
    min_corners=20
):
    """
    Rank combinations by:

        P(GOAL | METHOD)
    """

    features = [

        "swing_type",

        "delivery_zone",

        "delivery_type",

        "height",

        "foot",

        "delivery_depth"
    ]

    result = (

        df.groupby(
            features,
            dropna=False
        )

        .agg(

            corners=
                ("goal", "size"),

            goals=
                ("goal", "sum")
        )

        .reset_index()
    )

    result[
        "goal_probability"
    ] = (

        result["goals"]
        /
        result["corners"]
    )

    result[
        "goal_percentage"
    ] = (

        result[
            "goal_probability"
        ]

        * 100
    )

    result = result[
        result["corners"]
        >= min_corners
    ]

    return (

        result

        .sort_values(
            [
                "goal_probability",
                "goals"
            ],
            ascending=False
        )

        .reset_index(
            drop=True
        )
    )

# TEAM CONSISTENCY ACROSS SEASONS

def team_season_consistency(
    df,
    min_corners_per_season=10
):
    """
    Helps answer:

        Are there teams that consistently score
        from corners?
    """

    result = (

        df.groupby(
            [
                "league",
                "team",
                "season"
            ]
        )

        .agg(

            corners=
                ("goal", "size"),

            goals=
                ("goal", "sum")
        )

        .reset_index()
    )

    result[
        "conversion_rate"
    ] = (

        result["goals"]
        /
        result["corners"]
    )

    result[
        "conversion_percentage"
    ] = (

        result[
            "conversion_rate"
        ]

        * 100
    )

    result = result[
        result["corners"]
        >= min_corners_per_season
    ]

    return (

        result

        .sort_values(
            [
                "team",
                "season"
            ]
        )

        .reset_index(
            drop=True
        )
    )

# CORNER SUCCESS AND WINNING

def corner_success_vs_winning(
    df
):
    """
    Match-level dataset for examining the relationship between
    scoring from corners and winning.

    One row = one team in one match.

    This is better than simply correlating every individual
    corner with the same repeated match result.
    """

    result = (

        df.groupby(
            [
                "league",
                "season",
                "match_id",
                "team"
            ]
        )

        .agg(

            corners=
                ("goal", "size"),

            corner_goals=
                ("goal", "sum"),

            won_game=
                (
                    "team_won_game",
                    "first"
                )
        )

        .reset_index()
    )

    result[
        "corner_conversion_rate"
    ] = (

        result[
            "corner_goals"
        ]

        /

        result[
            "corners"
        ]
    )

    return result

# INTERACTIVE USER INPUT

def interactive_goal_query(
    df
):
    """
    USER INPUT SYSTEM

    Calculates:

        P(GOAL | selected characteristics)

    Every question is optional.

    Press Enter to skip anything you do not want to filter.
    """

    print(
        "\n========================================"
    )

    print(
        "       CORNER GOAL PROBABILITY"
    )

    print(
        "========================================"
    )

    print(
        "Press Enter to skip any filter.\n"
    )

    # GENERAL

    league = input(
    "League (e.g. Champions League / La Liga / Premier League / "
    "1. Bundesliga / Serie A; Enter = any): "
    ).strip()

    season = input(
    "Season (e.g. 2015/2016; Enter = any): "
    ).strip()

    team = input(
    "Team (exact team name, e.g. Barcelona / Real Madrid; Enter = any): "
    ).strip()

    corner_taker = input(
    "Corner taker (exact player name; Enter = any): "
    ).strip()

    swing_type = input(
    "Swing type (Inswinging / Outswinging / Not recorded; Enter = any): "
        ).strip()

    delivery_zone = input(
    "Delivery zone (Near post / Central / Far post / Outside box / "
    "Not recorded; Enter = any): "
    ).strip()

    delivery_type = input(
    "Delivery type (Short / Into the box / Outside the box / "
    "Not recorded; Enter = any): "
    ).strip()

    height = input(
    "Height (Ground Pass / Low Pass / High Pass / Not recorded; "
    "Enter = any): "
    ).strip()

    foot = input(
    "Foot (Left Foot / Right Foot / Not recorded; Enter = any): "
    ).strip()

    min_distance = input(
    "Minimum first-touch distance from goal "
    "(number, e.g. 5 or 10.5; Enter = no minimum): "
    ).strip()

    max_distance = input(
    "Maximum first-touch distance from goal "
    "(number, e.g. 15 or 25.5; Enter = no maximum): "
    ).strip()

    reached_player = input(
    "Player delivery reached (exact player name; Enter = any): "
    ).strip()

    # BLANK = NO FILTER

    league = (
        league or None
    )

    season = (
        season or None
    )

    team = (
        team or None
    )

    corner_taker = (
        corner_taker or None
    )

    swing_type = (
        swing_type or None
    )

    delivery_zone = (
        delivery_zone
        or None
    )

    delivery_type = (
        delivery_type
        or None
    )

    height = (
        height or None
    )

    foot = (
        foot or None
    )

    reached_player = (
        reached_player
        or None
    )

    # DISTANCE VALIDATION

    try:

        min_distance = (
            float(
                min_distance
            )
            if min_distance
            else None
        )

    except ValueError:

        min_distance = None

    try:

        max_distance = (
            float(
                max_distance
            )
            if max_distance
            else None
        )

    except ValueError:

        max_distance = None

    # CALCULATE CONDITIONAL PROBABILITY

    result = (
        conditional_goal_probability(

            df,

            league=
                league,

            season=
                season,

            team=
                team,

            corner_taker=
                corner_taker,

            reached_player=
                reached_player,

            swing_type=
                swing_type,

            delivery_zone=
                delivery_zone,

            delivery_type=
                delivery_type,

            height=
                height,

            foot=
                foot,

            min_first_touch_distance=
                min_distance,

            max_first_touch_distance=
                max_distance
        )
    )

    # MINIMAL CONSOLE OUTPUT

    print(
        "\nRESULT"
    )

    print(
        "Matching corners:",
        result[
            "matching_corners"
        ]
    )

    print(
        "Goals:",
        result[
            "goals"
        ]
    )

    if pd.isna(
        result[
            "goal_probability"
        ]
    ):

        print(
            "P(Goal | selected characteristics): "
            "No matching data"
        )

    else:

        print(
            "P(Goal | selected characteristics): "
            f"{result['goal_percentage']:.2f}%"
        )

    return result


# MAIN

if __name__ == "__main__":

    print("Loading saved Excel data...")

    all_corners = load_saved_leagues()

    if all_corners.empty:
        print("No saved Excel files were found.")
    else:
        print(f"Loaded {len(all_corners):,} corners.")

        goal_corners = all_corners[
            all_corners["goal"] == 1
        ].copy()

        print(f"Loaded {len(goal_corners):,} goal-scoring corners.")

        # Query the saved data
        interactive_goal_query(all_corners)