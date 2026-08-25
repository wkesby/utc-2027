"""The 20 UTC competitions: display name, feed, season window, how the comp is ordered, and the
month it starts. Listed in start order — that order flows through to the tabs on the page.
`start` is month granularity (competitions starting the same month keep the order below)."""
SPORTS = {
 # --- spring/autumn 2026 starts ---
 "epl":     ("EPL",                           "espn:soccer/eng.1@2026",             "Aug 2026 – May 2027", "final table",                             "2026-08"),
 "bund":    ("Bundesliga",                    "espn:soccer/ger.1@2026",             "Aug 2026 – May 2027", "final table",                             "2026-08"),
 "ncaa":    ("NCAA Football",                 "espn:football/college-football@2026","Aug 2026 – Jan 2027", "playoff depth > seed > final AP poll",     "2026-08"),
 "nfl":     ("NFL",                           "espn:football/nfl@2026",             "Sep 2026 – Feb 2027", "playoff depth > seed > record",            "2026-09"),
 "ucl":     ("UEFA Champions League",         "espn:soccer/uefa.champions@2026",    "Sep 2026 – Jun 2027", "knockout depth > league-phase position",   "2026-09"),
 "nhl":     ("NHL",                           "espn:hockey/nhl@2027",               "Oct 2026 – Jun 2027", "playoff depth > seed > points",            "2026-10"),
 "nba":     ("NBA",                           "espn:basketball/nba@2027",           "Oct 2026 – Jun 2027", "playoff depth > conference seed > record", "2026-10"),
 "rugby":   ("European Rugby Champions Cup",  "manual",                             "Oct 2026 – May 2027", "knockout depth > pool position",           "2026-10"),
 # --- 2027 calendar-year starts ---
 "cycling": ("Cycling (UCI WorldTour teams)", "manual",                             "Jan – Oct 2027",      "UCI WorldTour team ranking",               "2027-01"),
 "tennisM": ("Men's Tennis (ATP Race)",       "manual",                             "Jan – Nov 2027",      "ATP Race points, excl. Finals",            "2027-01"),
 "tennisW": ("Women's Tennis (Grand Slams)",  "manual",                             "Jan – Sep 2027",      "per-slam round points x4, +1 per slam won", "2027-01"),
 "nascar":  ("NASCAR",                        "espn:racing/nascar-premier@2027",    "Feb – Nov 2027",      "final standings",                          "2027-02"),
 "v8":      ("V8 Supercars",                  "manual",                             "Feb – Dec 2027",      "drivers' championship points",             "2027-02"),
 "f1":      ("Formula 1",                     "espn:racing/f1@2027",                "Mar – Nov 2027",      "drivers' championship points",             "2027-03"),
 "motogp":  ("MotoGP",                        "manual",                             "Mar – Nov 2027",      "riders' championship points",              "2027-03"),
 "nrl":     ("NRL",                           "manual",                             "Mar – Oct 2027",      "finals depth > ladder",                    "2027-03"),
 "afl":     ("AFL",                           "squiggle:2027",                      "Mar – Sep 2027",      "finals depth > ladder",                    "2027-03"),
 "mlb":     ("MLB",                           "espn:baseball/mlb@2027",             "Apr – Nov 2027",      "playoff depth > league seed > record",      "2027-04"),
 "golf":    ("Golf (4 majors)",               "manual",                             "Apr – Jul 2027",      "per-major finish points x4, +1 per major won", "2027-04"),
 "wsl":     ("World Surf League",             "manual",                             "Apr – Dec 2027",      "final CT rankings",                        "2027-04"),
}
PER_EVENT = {"golf", "tennisW"}   # scored per tournament; bonus is +1 per win rather than +2
