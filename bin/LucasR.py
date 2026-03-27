#!/usr/bin/env python
# ==============================================================================
# Author : Lucas Monge, lukasmonk@gmail.com
# Web : https://lucaschess.pythonanywhere.com/
# Blog : https://lucaschess.blogspot.com
# Licence : GPL 3.0
# ==============================================================================
import sys

import warnings

warnings.simplefilter("ignore")

if __debug__:
    import faulthandler

    faulthandler.enable()

n_args = len(sys.argv)
if n_args == 1:
    import Code.Main.Init

    Code.Main.Init.init()

elif n_args >= 2:
    arg = sys.argv[1].lower()
    if arg.endswith((".pgn", ".lcdb", ".lcsb", ".bmt", ".shortcut")) or arg in ("-play", "-playagainst"):
        import Code.Main.Init

        Code.Main.Init.init()

    elif arg == "-kibitzer":
        import Code.Kibitzers.RunKibitzer

        Code.Kibitzers.RunKibitzer.run(sys.argv[2])

    elif arg == "-translate":
        from Code.Translations import RunTranslate
        RunTranslate.run_wtranslation(sys.argv[2])

    elif arg == "-tournament":
        import Code.Tournaments.RunTournament

        user = sys.argv[3] if len(sys.argv) >= 4 else ""
        Code.Tournaments.RunTournament.run(user, sys.argv[2])

    elif arg == "-league":
        import Code.Leagues.RunLeague

        user = sys.argv[3] if len(sys.argv) >= 4 else ""
        Code.Leagues.RunLeague.run(user, sys.argv[2])

    elif arg == "-swiss":
        import Code.Swiss.RunSwiss

        user = sys.argv[3] if len(sys.argv) >= 4 else ""
        Code.Swiss.RunSwiss.run(user, sys.argv[2])

    elif arg == "-analysis":
        import Code.Analysis.RunAnalysis

        Code.Analysis.RunAnalysis.run(sys.argv[2])

    elif arg == "-healthcheck":
        sys.exit(0)

