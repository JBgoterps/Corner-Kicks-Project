# Soccer Corner-Kick Goal Probability Analysis

## Project Overview

This project analyzes soccer corner kicks using StatsBomb event data.

The main goal is to study which corner-kick characteristics are associated with scoring goals. The primary quantity calculated by the program is:

**P(Goal | selected corner characteristics)**

This is the conditional probability that a corner results in a goal given the characteristics selected by the user.

For example, the program can be used to investigate questions such as:

- Which teams have the highest corner-kick goal conversion rates?
- Which players are most successful when taking corners?
- Are inswinging or outswinging corners more successful?
- Are near-post, central, or far-post deliveries more successful?
- Are short corners or corners delivered into the box more successful?
- Does delivery height or foot used affect goal conversion?
- How does the location of the first touch relate to corner success?
- Which players are being reached by corner deliveries?
- Do certain combinations of corner characteristics have higher goal probabilities?
- Are teams that are more successful from corners also more likely to win?

The program stores individual corner kicks in a dataset, adds derived corner characteristics, calculates conversion statistics, and allows the user to query the dataset interactively.

---

# Data Source

The project uses event data available through the Python `statsbombpy` package.

The code is configured to work with the following competitions when data is available:

- Champions League
- La Liga
- Premier League
- 1. Bundesliga
- Serie A

The configured season range is based on seasons beginning from 2003 through 2018. The program does not assume that StatsBomb has every season available for every competition. It first checks which competition/season combinations are actually available.

---

# Required Python Packages

The project uses:

```python
numpy
pandas
statsbombpy
openpyxl
```

They can be installed from a terminal with:

```bash
pip install numpy pandas statsbombpy openpyxl
```

or:

```bash
pip3 install numpy pandas statsbombpy openpyxl
```

---

# Main Program

The main analysis code is contained in:

```text
440_sim.py
```

The program performs several major tasks:

1. Finds available StatsBomb competitions and seasons.
2. Downloads match and event data when the database is intentionally built.
3. Identifies corner kicks.
4. Extracts information about each corner.
5. Classifies the delivery.
6. Determines what happened after the corner.
7. Determines whether the corner possession resulted in a goal.
8. Calculates team, player, and corner-method conversion statistics.
9. Saves league datasets to Excel.
10. Loads previously generated Excel datasets for later analysis.
11. Allows the user to filter the database.
12. Calculates conditional goal probabilities from the selected filters.

---

# Saved Data Files

When the database is built, each competition is saved separately.

The expected files are:

```text
Champions_League_corners.xlsx
La_Liga_corners.xlsx
Premier_League_corners.xlsx
1_Bundesliga_corners.xlsx
Serie_A_corners.xlsx
```

Each file contains a `Corners` sheet.

Once these files have already been generated, they can be loaded for analysis without downloading every StatsBomb match again.

This is important because downloading and processing all available match event data can take a significant amount of time.

---

# Primary Outcome: Goal

The primary outcome used by this project is:

```text
goal
```

A value of:

```text
1
```

means that the attacking team scored during the possession associated with the corner.

A value of:

```text
0
```

means that the possession did not result in a goal.

Although the dataset also contains information about shots, shots on goal, expected goals, goalkeeper actions, and other outcomes, those variables are additional descriptive information.

The primary conditional probability calculation is based on **goals**.

---

# Conditional Probability

The main analysis calculates:

**P(Goal | selected characteristics)**

The calculation is:

```text
number of goals from matching corners
--------------------------------------
total number of matching corners
```

For example, suppose the user selects:

```text
League: Champions League
Swing type: Inswinging
Delivery zone: Near post
```

and the database contains:

```text
80 matching corners
4 goals
```

Then:

```text
P(Goal | Champions League, Inswinging, Near post)
= 4 / 80
= 0.05
= 5%
```

The program reports the number of matching corners, the number of goals, and the resulting probability.

---

# Interactive User Input

The interactive query allows the user to select characteristics of the corners they want to analyze.

**Every filter is optional.**

If the user presses **Enter** without typing anything, that filter is ignored.

For example:

```text
League:
```

Pressing Enter means:

```text
Use any league.
```

---

# Partial Text Matching

Text searches are:

- case-insensitive
- partial-match enabled

This means the user usually does not need to type the entire stored value.

Examples:

```text
champ
```

can match:

```text
Champions League
```

and:

```text
barca
```

can match:

```text
Barcelona
```

Similarly:

```text
near
```

can match:

```text
Near post
```

and:

```text
high
```

can match:

```text
High Pass
```

Capitalization does not matter.

For example:

```text
CHAMP
champ
Champ
```

are treated the same way.

Partial matching is **not fuzzy spelling correction**. A misspelled word is not automatically corrected.

For example:

```text
Champions
```

can match `Champions League`, but:

```text
Champision
```

will not necessarily match because that misspelled string is not contained in `Champions League`.

---

# Interactive Prompts

## 1. League

The program asks for a league/competition.

Expected options include:

```text
Champions League
La Liga
Premier League
1. Bundesliga
Serie A
```

Examples of valid partial searches:

```text
champ
liga
premier
bundes
serie
```

Press Enter to include all leagues.

---

## 2. Season

The program asks for a season.

The value should correspond to a season actually present in the loaded StatsBomb dataset.

Example:

```text
2015/2016
```

The exact available season labels depend on the saved data.

Press Enter to include all available seasons.

---

## 3. Team

The program asks for the team taking the corner.

Example:

```text
Barcelona
```

Because partial matching is enabled, something such as:

```text
barca
```

may be used if it uniquely matches the desired stored team name.

Press Enter to include all teams.

---

## 4. Corner Taker

This is the player who took the corner kick.

Example input:

```text
Messi
```

Partial player names are allowed.

This field is different from the player who receives the delivery.

Press Enter to include all corner takers.

---

## 5. Swing Type

This describes the direction/spin of the corner delivery when StatsBomb records it.

Possible stored values can include:

```text
Inswinging
Outswinging
Not recorded
```

Example inputs:

```text
inswing
```

or:

```text
outswing
```

Press Enter to include any swing type.

---

## 6. Delivery Zone

The project classifies the corner endpoint into the following categories:

```text
Near post
Central
Far post
Outside box
Not recorded
```

Example inputs:

```text
near
central
far
outside
```

Press Enter to include any delivery zone.

### Meaning of the zones

Near-post and far-post classifications are defined relative to the side from which the corner was taken.

If the required coordinates are unavailable, the delivery is classified as:

```text
Not recorded
```

---

## 7. Delivery Type

The project classifies the overall delivery as:

```text
Short
Into the box
Outside the box
Not recorded
```

Example inputs:

```text
short
into
outside
```

Press Enter to include any delivery type.

### Short corner

A corner is classified as `Short` when its recorded pass length is below the configured short-corner threshold.

The current threshold is:

```text
15
```

StatsBomb pitch units.

### Into the box

A non-short delivery whose endpoint falls inside the program's defined penalty-area region is classified as:

```text
Into the box
```

### Outside the box

Other recorded non-short deliveries are classified as:

```text
Outside the box
```

---

## 8. Height

The height of the corner delivery comes from the StatsBomb pass-height field.

Values may include:

```text
Ground Pass
Low Pass
High Pass
Not recorded
```

Example inputs:

```text
ground
low
high
```

Press Enter to include all delivery heights.

---

## 9. Foot

This describes the recorded body part/foot used to take the corner.

Typical values include:

```text
Left Foot
Right Foot
Not recorded
```

Example inputs:

```text
left
right
```

Press Enter to include either foot.

---

## 10. Minimum First-Touch Distance From Goal

The program identifies the first relevant recorded touch after the corner and calculates its distance from the center of the goal.

This prompt expects a **number**, not text.

Example:

```text
5
```

or:

```text
10.5
```

If the user enters:

```text
10
```

only corners whose first-touch distance is at least 10 StatsBomb pitch units are retained.

Press Enter for no minimum.

---

## 11. Maximum First-Touch Distance From Goal

This is also a numeric input.

Example:

```text
20
```

If the user enters:

```text
20
```

only corners whose first-touch distance is at most 20 StatsBomb pitch units are retained.

The minimum and maximum can be combined.

For example:

```text
Minimum: 5
Maximum: 15
```

selects first touches whose recorded distance from goal is between 5 and 15 units.

Press Enter for no maximum.

---

## 12. Player Delivery Reached

This filters by the recorded player receiving the corner pass.

Example:

```text
Ronaldo
```

Partial player names are allowed.

This variable is separate from:

```text
Corner taker
```

The corner taker is the player delivering the corner.

The reached player is the recorded recipient of that delivery.

Press Enter to include all recipients.

---

# Example Interactive Query

Suppose the user wants to examine high, inswinging, near-post Champions League corners.

The inputs could look like:

```text
League: champ
Season:
Team:
Corner taker:
Swing type: inswing
Delivery zone: near
Delivery type:
Height: high
Foot:
Minimum first-touch distance from goal:
Maximum first-touch distance from goal:
Player delivery reached:
```

Blank responses mean that those variables are not used as filters.

The query therefore asks approximately:

**What is P(Goal | Champions League, Inswinging, Near Post, High Pass)?**

---

# Query Output

The program returns information in the following general form:

```text
RESULT
Matching corners: 100
Goals: 4
P(Goal | selected characteristics): 4.00%
```

### Matching corners

This is the denominator.

It tells the user how many corners in the dataset satisfy **all** selected filters.

### Goals

This is the numerator.

It tells the user how many of those matching corners resulted in goals.

### Goal probability

This is:

```text
Goals / Matching corners
```

expressed as a conditional probability or percentage.

---

# Zero Matching Corners

A query can return:

```text
Matching corners: 0
Goals: 0
```

This does not necessarily mean that the program failed.

Possible reasons include:

- the selected combination does not exist;
- a player/team name was misspelled;
- the requested season is not available;
- too many restrictive filters were combined;
- the requested value is not represented in the StatsBomb data.

A useful troubleshooting strategy is to remove filters one at a time.

For example, instead of immediately querying:

```text
Champions League
Barcelona
Inswinging
Near post
High Pass
Left Foot
specific player
specific distance range
```

start with:

```text
Champions League
```

and gradually add conditions.

---

# Main Dataset Variables

Important columns produced by the program include:

## Identification

```text
league
season
team
taker
```

## Main corner characteristics

```text
swing_type
delivery_zone
delivery_type
delivery_depth
height
foot
corner_side
corner_method
```

## Delivery information

```text
pass_length
pass_angle
pass_cross
pass_aerial_won
end_x
end_y
end_distance_to_goal
reached_player
delivery_completed
```

## First-touch information

```text
first_touch_type
first_touch_player
first_touch_team
first_touch_by_attackers
first_touch_x
first_touch_y
first_touch_distance_to_goal
```

## Primary outcome

```text
goal
```

## Additional outcomes

```text
shot
shot_on_goal
shot_xg
shooter
shot_header
another_corner
goalie_action
goalie_possession
out_of_bounds
penalty
```

## Match information

```text
match_id
match_date
period
time_sec
home_or_away
game_score
game_score_for
game_score_against
game_result
team_won_game
```

---

# Corner Method

The program also creates a combined `corner_method` variable.

It combines:

```text
swing type
height
delivery type
delivery zone
delivery depth
foot
```

This makes it possible to compare complete corner methods rather than only one characteristic at a time.

A conceptual example is:

```text
Inswinging | High Pass | Into the box | Near post | Penalty area | Left Foot
```

---

# Conversion Statistics

The program calculates several conversion-rate variables.

## Method Conversion Rate

For each corner method:

```text
method_corners
method_goals
method_conversion_rate
```

The conversion rate is:

```text
goals using that method
-----------------------
corners using that method
```

---

## Team Conversion Rate

For each team:

```text
team_corners
team_goals
team_conversion_rate
```

The conversion rate is:

```text
team goals from corners
-----------------------
team corners
```

---

## Corner-Taker Conversion Rate

For each corner taker:

```text
taker_corners
taker_goals
taker_conversion_rate
```

This allows the project to compare the observed goal conversion associated with different corner takers.

---

# Additional Analysis Functions

The main code also contains helper functions intended for broader analysis.

These include functions for:

- ranking teams;
- ranking corner takers/players;
- ranking corner methods;
- examining team-season consistency; and
- examining corner success in relation to winning.

These analyses are useful for questions beyond one interactive conditional-probability query.

---

# Team and Player Rankings

Ranking functions can be used to compare teams or players by their observed corner conversion rates.

Minimum-corner thresholds should be used when interpreting these rankings.

For example, a player with:

```text
1 goal from 1 corner
```

would technically have:

```text
100% conversion
```

but this is not meaningful evidence that the player is the best corner taker.

A larger sample provides a more useful comparison.

---

# Corner Success and Winning

The dataset stores:

```text
game_result
team_won_game
```

This allows the project to investigate whether teams with successful corner outcomes are also more likely to win matches.

This should be interpreted as an observed relationship in the dataset rather than proof that corner success causes winning.

---

# First-Touch Distance

StatsBomb uses a pitch coordinate system with approximately:

```text
x = 0 to 120
y = 0 to 80
```

The attacking goal center used by this project is:

```text
(120, 40)
```

The program calculates Euclidean distance from a recorded location to that goal center.

Therefore:

```text
first_touch_distance_to_goal
```

measures how far the first relevant recorded touch following the corner occurred from the goal center in StatsBomb pitch-coordinate units.

---

# Other Derived Outcomes

The dataset retains several additional variables even though they are not the primary conditional outcome.

Examples include:

### Shot

Whether the attacking possession contained a shot.

### Shot on goal

Whether an associated shot had an on-target outcome as defined by the code.

### Shot xG

The sum of the recorded StatsBomb expected-goal values for shots in the attacking possession.

### Header

Whether the first associated shot was recorded as a header.

### Goalkeeper action

Whether the possession contained a goalkeeper event.

### Goalkeeper possession

Whether a goalkeeper event represented one of the possession/collection types recognized by the program.

### Another corner

Whether another corner by the same team occurred within the configured time threshold.

The current threshold is:

```text
30 seconds
```

### Penalty

Whether the possession contains an event identified by the code as a penalty-related event.

---

# Using the Saved Data Instead of Downloading Again

After the Excel files have been generated, the recommended workflow is to load them using:

```python
all_corners = load_saved_leagues()
```

rather than calling:

```python
build_database()
```

every time.

`build_database()` contacts StatsBomb and processes event data for many matches, so it can take much longer.

For normal querying and analysis, use the saved files.

---

# Running the Project in Jupyter Notebook

A Jupyter Notebook can be used as the easy interface for this project.

The notebook should be placed in the same project folder as:

```text
440_sim.py
Champions_League_corners.xlsx
La_Liga_corners.xlsx
Premier_League_corners.xlsx
1_Bundesliga_corners.xlsx
Serie_A_corners.xlsx
```

## Step 1: Open the project folder

In VS Code:

1. Open the `MATH 440` project folder.
2. Make sure the Python and Jupyter extensions are installed.
3. Create a new Jupyter Notebook (`.ipynb`).
4. Select the Python environment/kernel containing the required packages.

---

## Step 2: Install packages if necessary

In a notebook cell:

```python
%pip install pandas numpy statsbombpy openpyxl
```

Run this only if the packages are not already installed.

---

## Step 3: Load the main Python file

Because the main source file is named:

```text
440_sim.py
```

it cannot be imported using the ordinary:

```python
import 440_sim
```

syntax because Python module identifiers cannot begin with a number.

Use:

```python
import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    "corner_analysis",
    "440_sim.py"
)

analysis = importlib.util.module_from_spec(spec)
sys.modules["corner_analysis"] = analysis
spec.loader.exec_module(analysis)
```

The variable:

```python
analysis
```

now represents the code in `440_sim.py`.

---

## Step 4: Load the saved corner data

Run:

```python
all_corners = analysis.load_saved_leagues()

print(f"Loaded {len(all_corners):,} corners.")
```

This loads the saved Excel files.

It does **not** intentionally rebuild the StatsBomb database.

---

## Step 5: Check which leagues are loaded

Run:

```python
sorted(
    all_corners["league"]
    .dropna()
    .astype(str)
    .unique()
)
```

This is useful for confirming which competitions exist in the currently loaded files.

---

## Step 6: Check available seasons

Run:

```python
sorted(
    all_corners["season"]
    .dropna()
    .astype(str)
    .unique()
)
```

This avoids guessing the exact season labels.

---

## Step 7: Run the interactive query

Run:

```python
analysis.interactive_goal_query(all_corners)
```

The notebook will display the prompts.

Answer whichever filters you want and press Enter for the others.

---

# Direct Queries in Jupyter

The interactive prompts are useful for exploring the data, but direct function calls are useful for repeatable analysis.

## Example 1: Champions League

```python
result = analysis.conditional_goal_probability(
    all_corners,
    league="champ"
)

result
```

---

## Example 2: Team

```python
result = analysis.conditional_goal_probability(
    all_corners,
    team="barca"
)

result
```

---

## Example 3: Inswinging corners

```python
result = analysis.conditional_goal_probability(
    all_corners,
    swing_type="inswing"
)

result
```

---

## Example 4: Near-post corners

```python
result = analysis.conditional_goal_probability(
    all_corners,
    delivery_zone="near"
)

result
```

---

## Example 5: Combination of characteristics

```python
result = analysis.conditional_goal_probability(
    all_corners,
    league="champ",
    swing_type="inswing",
    delivery_zone="near",
    delivery_type="into",
    height="high"
)

result
```

This estimates:

**P(Goal | Champions League, Inswinging, Near Post, Into Box, High Pass)**

for the observations available in the dataset.

---

## Example 6: First-touch distance

```python
result = analysis.conditional_goal_probability(
    all_corners,
    min_first_touch_distance=5,
    max_first_touch_distance=15
)

result
```

---

## Example 7: Corner taker

```python
result = analysis.conditional_goal_probability(
    all_corners,
    corner_taker="player name"
)

result
```

Replace `player name` with a player present in the data.

---

## Example 8: Player receiving the delivery

```python
result = analysis.conditional_goal_probability(
    all_corners,
    reached_player="player name"
)

result
```

---

# Direct Query Parameters

The conditional probability function supports the following filters:

```python
analysis.conditional_goal_probability(
    all_corners,

    league=None,
    season=None,
    team=None,

    corner_taker=None,
    reached_player=None,

    swing_type=None,
    delivery_zone=None,
    delivery_type=None,

    height=None,
    foot=None,
    delivery_depth=None,

    min_first_touch_distance=None,
    max_first_touch_distance=None
)
```

Any parameter left as:

```python
None
```

is not used as a filter.

---

# Example Custom Query Template

This can be copied into a Jupyter cell and edited:

```python
my_result = analysis.conditional_goal_probability(
    all_corners,

    league=None,
    season=None,
    team=None,

    corner_taker=None,
    reached_player=None,

    swing_type=None,
    delivery_zone=None,
    delivery_type=None,

    height=None,
    foot=None,
    delivery_depth=None,

    min_first_touch_distance=None,
    max_first_touch_distance=None
)

my_result
```

Only replace the values you want to filter.

For example:

```python
my_result = analysis.conditional_goal_probability(
    all_corners,
    league="premier",
    delivery_zone="far",
    height="high"
)

my_result
```

---

# Inspecting Available Values Before a Query

If a query returns zero matches, it can be useful to inspect the actual values in a column.

For example:

```python
sorted(
    all_corners["delivery_zone"]
    .dropna()
    .astype(str)
    .unique()
)
```

For swing types:

```python
sorted(
    all_corners["swing_type"]
    .dropna()
    .astype(str)
    .unique()
)
```

For teams:

```python
sorted(
    all_corners["team"]
    .dropna()
    .astype(str)
    .unique()
)
```

For players:

```python
sorted(
    all_corners["taker"]
    .dropna()
    .astype(str)
    .unique()
)
```

This is the best way to verify what is actually represented in the saved dataset.

---

# Recommended Jupyter Workflow

A simple notebook can therefore contain these cells in order:

## Cell 1 — Imports

```python
import importlib.util
import sys
```

## Cell 2 — Load analysis code

```python
spec = importlib.util.spec_from_file_location(
    "corner_analysis",
    "440_sim.py"
)

analysis = importlib.util.module_from_spec(spec)
sys.modules["corner_analysis"] = analysis
spec.loader.exec_module(analysis)
```

## Cell 3 — Load data

```python
all_corners = analysis.load_saved_leagues()

print(f"Loaded {len(all_corners):,} corners.")
```

## Cell 4 — Check available data

```python
print(
    sorted(
        all_corners["league"]
        .dropna()
        .astype(str)
        .unique()
    )
)

print(
    sorted(
        all_corners["season"]
        .dropna()
        .astype(str)
        .unique()
    )
)
```

## Cell 5 — Interactive analysis

```python
analysis.interactive_goal_query(all_corners)
```

## Cell 6 — Direct analysis

```python
result = analysis.conditional_goal_probability(
    all_corners,
    league="champ",
    delivery_zone="near"
)

result
```

Additional cells can then be added for different research questions.

---

# Important Interpretation Note

Always consider the number of matching corners when interpreting a conversion rate.

For example:

```text
1 goal / 1 corner = 100%
```

and:

```text
50 goals / 1,000 corners = 5%
```

The first percentage is numerically larger, but it is based on only one observation.

For comparisons among teams, players, or methods, sample size should therefore be considered along with the conversion rate.

---

# What This Analysis Does Not Establish

The analysis identifies patterns and associations in the available StatsBomb corner-kick data.

For example, if near-post corners have a higher observed conversion rate than far-post corners, the analysis can report that relationship.

It does **not**, by itself, establish that choosing a near-post corner causes a team to score more often.

Other factors can differ between teams, players, matches, leagues, and situations.

---

# Summary

The project turns StatsBomb event data into a corner-kick database and provides tools for analyzing:

- corner delivery methods;
- teams;
- corner takers;
- recipients;
- delivery locations;
- first-touch locations;
- goal conversion;
- team and player conversion rates;
- method conversion rates; and
- the relationship between corner success and match outcomes.

The main statistical output is:

**P(Goal | selected corner characteristics)**

For normal use, load the already generated Excel files, choose the desired filters through the interactive prompts or a direct Jupyter query, and interpret the resulting number of matching corners, goals, and goal probability.
