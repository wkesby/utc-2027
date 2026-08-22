"""The 20 UTC competitions: display name, feed, season window, and how the comp is ordered."""
SPORTS = {
 "nfl":     ("NFL",                           "espn:football/nfl@2026",        "Sep 2026 – Feb 2027", "playoff depth > seed > record"),
 "epl":     ("EPL",                           "espn:soccer/eng.1@2026",        "Aug 2026 – May 2027", "final table"),
 "bund":    ("Bundesliga",                    "espn:soccer/ger.1@2026",        "Aug 2026 – May 2027", "final table"),
 "ucl":     ("UEFA Champions League",         "espn:soccer/uefa.champions@2026","Sep 2026 – Jun 2027", "knockout depth > league-phase position"),
 "nba":     ("NBA",                           "espn:basketball/nba@2027",      "Oct 2026 – Jun 2027", "playoff depth > conference seed > record"),
 "nhl":     ("NHL",                           "espn:hockey/nhl@2027",          "Oct 2026 – Jun 2027", "playoff depth > seed > points"),
 "afl":     ("AFL",                           "squiggle:2027",                 "Mar – Sep 2027",      "finals depth > ladder"),
 "nrl":     ("NRL",                           "manual",                        "Mar – Oct 2027",      "finals depth > ladder"),
 "mlb":     ("MLB",                           "espn:baseball/mlb@2027",        "Apr – Nov 2027",      "playoff depth > league seed > record"),
 "cycling": ("Cycling (UCI WorldTour teams)", "manual",                        "Jan – Oct 2027",      "UCI WorldTour team ranking"),
 "f1":      ("Formula 1",                     "espn:racing/f1@2027",           "Mar – Nov 2027",      "drivers' championship points"),
 "motogp":  ("MotoGP",                        "manual",                        "Mar – Nov 2027",      "riders' championship points"),
 "v8":      ("V8 Supercars",                  "manual",                        "Feb – Dec 2027",      "drivers' championship points"),
 "tennisM": ("Men's Tennis (ATP Race)",       "manual",                        "Jan – Nov 2027",      "ATP Race points, excl. Finals"),
 "tennisW": ("Women's Tennis (Grand Slams)",  "manual",                        "Jan – Sep 2027",      "per-slam round points x4, +1 per slam won"),
 "golf":    ("Golf (4 majors)",               "manual",                        "Apr – Jul 2027",      "per-major finish points x4, +1 per major won"),
 "wsl":     ("World Surf League",             "manual",                        "Apr – Dec 2027",      "final CT rankings"),
 "nascar":  ("NASCAR",                        "espn:racing/nascar-premier@2027","Feb – Nov 2027",     "final standings"),
 "ncaa":    ("NCAA Football",                 "espn:football/college-football@2026","Aug 2026 – Jan 2027", "playoff depth > seed > final AP poll"),
 "rugby":   ("European Rugby Champions Cup",  "manual",                        "Oct 2026 – May 2027", "knockout depth > pool position"),
}
PER_EVENT = {"golf", "tennisW"}   # scored per tournament; bonus is +1 per win rather than +2
