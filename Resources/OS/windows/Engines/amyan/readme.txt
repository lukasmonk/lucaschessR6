       *******************************************************************************
       *     ______     ___        ___  ___    ____    ______    ____        ____    *
       *    /      \   |   \      /   | |  |   |   |  /      \   |   \       |   |   *
       *   |        \  |    \    /    | |  |   |   | |        \  |    \      |   |   *
       *   |   __   |  |     \  /     | |   \_/    | |   __   |  |     \     |   |   *
       *   |  |  |  |  |      \/      |  \        /  |  |  |  |  |      \    |   |   *
       *   |  |__|  |  |              |   \      /   |  |__|  |  |       \   |   |   *
       *   |        |  |              |    \    /    |        |  |   |\   \  |   |   *
       *   |  ___   |  |   |\_  _/|   |    |   |     |  ___   |  |   | \   \ |   |   *
       *   |  |  |  |  |   |  \/  |   |    |   |     |  |  |  |  |   |  \   \|   |   *
       *   |  |  |  |  |   |      |   |    |   |     |  |  |  |  |   |   \       |   *
       *   |  |  |  |  |   |      |   |    |   |     |  |  |  |  |   |    \      |   *
       *   \__/  \__/  |___|      |___|    |___|     \__/  \__/  |___|     \_____|   *
       *                                                                             *
       *******************************************************************************

Version : 1.72
Web     : http://www.pincha.cl/amyan


My chess program Amyan! ( compatible with Winboard and UCI protocols. )
-----------------------------------------------------------------------

Hi! this is a chess engine (no interface included), compatible with WINBOARD and UCI protocols, 
so you need a Winboard or Uci compatible chess interface.

Strength?? pretty strong, altough not as strong as the top chess programs.

Some of the strongest free chess engines are:
Rybka 2.2, StockFish, Bright, etc. just take a look at the various rating lists available.


The files style.ini and ics.ini only are read when running as a Winboard engine.


Respect to Winboard GUI
-----------------------

Amyan supports base-inc time controls and the x moves in y minutes.
He support also the "sd" command to set depth of thinking, for example press Alt+1 then write
"sd 1"(without the marks) to win cheating. This is reset if you start a new game or send "sd 0".

It does support "Edit Position", "Analisis Mode", "Move Now"...

It always claims draw by repetition and almost always the fifty move rule(infinite lazyness.)

It doesn't ponder yet...

Amyan has a default hash table of 32 MB of size, you better change that setting in the style.ini 
file for optimal perfomance in case you have enough RAM or will play long games.


Respect to UCI
--------------

Amyan supports part of UCI protocol.
Amyan does ponder under UCI.
It does support assign an ELO level (if the GUI supports it as well)
It does support multipv, and the show refutations option.
It has a very small default hash size, you better change that setting in its configuration for optimal performance.

**************************


Openning book:
--------------

Amyan comes with a small opening book with some hundreds of moves written by me, and some 
others taken from amyan's own games.
If you run Amyan in some interfaces, like Arena, it may be possible to use another book, surely 
bigger, and more importantly, with more opennings.


Search :
--------

Basically,

-Several killers are used.
-My move ordering is mainly killer based. Static tables only get me a 5% speedup or so.
-few extensions (only up to 1 per line currently except check escape.)
-some futility prunning.
-null-move usage (with r=2 only.)
-reductions usage.
-qsearch with only some captures and check escapes, only sometimes more in a few
threats (but as that's is considered an extension=>only 1 per line)
-for ordering captures, mainly, it uses mvv/lva, and prunes a bit.
-nothing of things like etc and iid, because I didn't managed to make a difference with them.


Evaluation :
-------------

Basically, it considers,

-No complex terms.
-Minor pieces development, doubled and isolated pawns depending on file, pawn storms 
especially towards the enemy king, pawns relative to the center, passed pawns depending 
on rank(if connected, obstructed, attacked or supported by rook etc.)
-King positioning, considering 3 phases for the game and pawns protecting it.
-King hunting, considering pieces attacking near him, material and the previous term.
-Much mobility, specially near the enemy king and the center.
-Rook on (half-)open files, the 7th(8th) file issue.
-Piece on square tables for knights, bishops and queens. Good squares for knights.
-Scoring for some pins, various special fool bonuses, etc.

All the values are tunned by hand and trying to do correct stuff and make amyan play fun at the same time.
Almost all the values that must depend of the material on the board, do, at least in a poor way.
I think Amyan's eval is good enough. It can detect most strong King attacks.
Pawns storms is characteristic of its playing style, I like that very much.
If you think amyan's eval is very bad for a particular position send me an email.

Others :
--------

For board representation, basically an array for the board and arrays for each piece type 
are used. No special tricks. In the board array, index 11 is A1 and 88 is H8, isn't it intuitive enough?
Usage of bitboards mainly for pawns.

There are a "normal" hash table(including qsearch), an eval hash and a pawn hash. History heuristic is not active yet. Anyway killers and history prunning concepts can converge.
It doesn't uses endgames tables yet but I will implement them soon.

We could say Amyan is a slow searcher, this is not only because it may have a slow eval, actually the whole program is relatively inefficient.

BTW I don't study other people source codes. For the sake of curiosity I still take a look mainly to some other program's eval tough..


Thanks to :
-----------

*Arturo Ochoa.
(because the pretty logo, it's PERFECT)
*Telmo Escobar.
(because helping me with some moves for the little book and make good comment about amyan)
*Dann Corbit.
(basically for answering some of my fool emails)
*Daniel Torres.
(helped me starting to translate my program from java to c++)
*Nicolás Carrasco.
(helped me starting to translate my program from java to c++)
*Tom Kerrigan.
(TSCP helped me to get my thing runing with Winboard more quickly)
*Thomas Mayer.(->Dan Homman->Robert Hyatt->Tim Mann)
(because sending me a piece of code to read input without wait)
*Lars Hollerstorm, Leo Dijkman, Alex Schmidt, Patrick Buchmann, George Lyapko, Steffen Basting, 
Roger Brown, Andy, Tony, etc.
(for testing chess engines, including mine.)
*many more
(because using Amyan)

and to the CCC, and to all the winboard and chess programming community.


--------------------------------------------------------------------------
Amyan account at FICS (www.freechess.org), is with nick: Amyan.
Myself am a very weak player.

Please excuse my english.


Written by and being written by Antonio Dieguez, from Chile.

Send good comments, congratulations, complimments, etc. to zodiamoon@yahoo.com :)


bye bye, love and peace, etc.


Some of the anime series I like: yea I do really watch this!

Angelic Layer
Avenger
Card Captor Sakura
Claymore
Gantz
.Hack//SIGN
Hikaru No Go
HunterXHunter
Rurouni Kenshin
Saint Seiya
Tokyo Babylon - X
