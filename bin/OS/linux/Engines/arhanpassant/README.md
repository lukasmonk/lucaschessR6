# ArhanPassant

A UCI chess engine and chess library in Rust that keeps getting stronger. Every
new version learns from the engine's own self-play games, and it only replaces
the previous version after beating it in a statistical test over thousands of
games.

**[Play it in your browser](https://arhanpassant.com/play)** ·
**[Play it on Lichess](https://lichess.org/@/arhanpassant)** ·
**[Adaptive puzzle trainer](https://arhanpassant.com/train)** ·
**[Promotion ledger](https://arhanpassant.com/engine)**

## Play it here on GitHub

Everyone plays White, together, against the engine on one shared board. Pick a
move on the [play page](https://github.com/arhancanli/arhanpassant/blob/play/README.md),
press **Submit new issue**, and the engine answers on your issue within a few
minutes.

<p align="center"><a href="https://github.com/arhancanli/arhanpassant/blob/play/README.md"><img src="https://raw.githubusercontent.com/arhancanli/arhanpassant/play/board.svg" width="360" alt="The community game's current position"></a></p>

## Status

**Version 0.13.0.** Its network grew from 0.12 (trained on 381.8M self-play positions) through
four rounds of reinforcement learning: each round fine-tunes the champion on 15 to 25 million
fresh self-play positions, and the result must beat the champion before it replaces it. The
four rounds gained +27.3, +20.5, +16.0 and +6.7 Elo in 1,032 to 5,714 paired games at 5+0.05.
Three search changes that passed the same test together (+11.7 Elo) are now defaults:
evaluation correction by minor pieces, detecting a forced repetition ahead of time, and capture
futility pruning. Every promotion and every test, including the failures, is recorded in
[`forge/ledger.json`](forge/ledger.json) and [`forge/tests.json`](forge/tests.json), and on the
[engine page](https://arhanpassant.com/engine).

**Measured strength: about 3,500 on the CCRL Blitz scale.** In 900 games at 10+0.1 against nine
engines with published CCRL Blitz ratings (Stockfish 19 and 17.1, Koivisto 9.0, Ethereal 12,
Laser 1.7, Stash 34 and 37, Weiss 1.4 and 2.0), a fit to the five opponents it scored 20-80%
against gave 3,507 (95% interval 3,472 to 3,541, game statistics only). Against the same nine
engines, with the same openings and settings, it scored 70.6 Elo better than version 0.12. These
are our own matches, not an official CCRL rating.

New in 0.13.0 besides strength: Chess960 (`UCI_Chess960`, X-FEN and Shredder-FEN), hash tables
up to 1 TB cleared in parallel, and ARM Linux builds.

## What is inside

- **Move generation**: legal moves from magic bitboards, matching 21 published
  perft results, including the 706,045,033-position test from the Chess
  Programming Wiki and Martin Sedlak's en passant and castling edge cases.
- **Search**: iterative deepening, aspiration windows, principal variation
  search, quiescence search, a lock-free shared hash table and lazy SMP threads;
  null-move, reverse futility, futility, late-move and static-exchange pruning;
  late-move reductions; singular extensions; history, continuation-history,
  killer and counter-move ordering.
- **Evaluation**: an NNUE, (768 inputs × 8 king buckets → 512) × 2 → 8 output
  buckets, with squared clipped ReLU, int16 quantised and updated incrementally
  (NEON, AVX2 and WebAssembly SIMD paths); tapered piece-square tables as the
  baseline.
- **Interfaces**: UCI, a Rust library (FEN, legal moves, SAN, perft) and a
  WebAssembly build that runs in browsers.
- **Self-improvement tooling**: self-play data generation, an NNUE trainer and a
  match runner with a calibrated sequential test.

## Install

- **Download** a build for Windows, Linux (x86-64 or ARM) or macOS from the
  [latest release](https://github.com/arhancanli/arhanpassant/releases/latest). On a PC,
  pick the `avx2` build unless the computer is older than about 2013 (then the plain one).
- **Homebrew** (macOS and Linux): `brew install arhancanli/tap/arhanpassant`
- **Docker**: `docker run -i --rm ghcr.io/arhancanli/arhanpassant`
- **Cargo**: `cargo install --git https://github.com/arhancanli/arhanpassant arhanpassant`

## Quick start

```sh
cargo build --release
./target/release/arhanpassant bench
```

Add `target/release/arhanpassant` to any UCI chess GUI (Cute Chess, Arena,
Banksia, En Croissant). Options:

| Option          | Default      | Meaning                                          |
| --------------- | ------------ | ------------------------------------------------ |
| `Hash`          | 16           | Hash table size in MB (up to 1,048,576)          |
| `Threads`       | 1            | Search threads (up to 512)                       |
| `Move Overhead` | 30           | Milliseconds kept in reserve per move            |
| `EvalFile`      | `<embedded>` | Network file, or `<none>` for the hand-written evaluation |
| `SyzygyPath`    | `<empty>`    | Folders of Syzygy tablebase files, separated by `:` |
| `SyzygyProbeLimit` | 7         | Largest piece count probed during search         |
| `UCI_Chess960`  | false        | Chess960: castling as king-takes-rook, X-FEN and Shredder-FEN |

With tablebases loaded, the engine plays only moves that keep the tables'
result at the root (the fastest wins, the slowest losses) and scores
positions the tables cover right after a capture or pawn move.

## As a library

```rust
use arhanpassant::Position;

let pos = Position::from_fen("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3").unwrap();
for m in pos.legal_moves().iter() {
    println!("{} {}", m.to_uci(), pos.san(m));
}
assert_eq!(arhanpassant::perft(&Position::startpos(), 5), 4_865_609);
```

## How it gets stronger

1. **Self-play.** `arhanpassant datagen` plays games at a fixed number of nodes
   per move and stores every quiet position with its search score and the game
   result (32 bytes per position).
2. **Training.** `trainer/train.py` trains a network on those positions.
   `trainer/check_pipeline.py` proves the engine evaluates the exported network
   exactly as an integer re-implementation does, and that a scrambled export is
   caught.
3. **The gate.** `arena` plays the candidate against the champion in pairs of
   games (same opening, colours swapped) and runs a pentanomial sequential
   probability ratio test with bounds [0, 5] Elo and α = β = 0.05.
4. **Promotion.** Versions that pass are released and logged in the ledger, and
   become the opponent for the next round.

The gate is checked before it is trusted: on 600 simulated matches of known
strength it passes 5.0% of no-better versions and 95.2% of versions that really
are 5 Elo stronger (50.7% halfway between), an engine against an identical copy
measures exactly 0 Elo, and a deliberately broken likelihood ratio fails the
calibration test.

```sh
# a candidate network against the current engine
./target/release/arena \
  --engine name=candidate cmd=./target/release/arhanpassant opt.EvalFile=new.nnue \
  --engine name=champion  cmd=./target/release/arhanpassant \
  --tc 8+0.08 --book UHO_4060_v4.epd --concurrency 8 --games 40000 --sprt 0,5
```

## Repository

On macOS, keep self-play, training, network gates and the queued search
experiments running under a supervised service:

```sh
python3 forge/macbook.py install --cpu-budget 18 --min-new 80000000 --train-hidden 512
python3 forge/macbook.py status
python3 forge/test_queue.py add NAME "change description" parameter=value
python3 forge/macbook.py stop
python3 forge/macbook.py start
```

The current owner's profile uses an 18-core budget, 512 hidden units and starts a
new training round after 80 million fresh positions. If a search gate already has completed
pairs, it finishes that gate before training can change the network; a queued
test that has not started does not delay training. Other Macs can choose their own budget;
omitting it reserves two cores. While search tests
are pending, half the budget generates self-play and the rest plays test
games. Network gates pause self-play and use the full budget; training uses
Metal when available and eight parallel record decoders. Local gates save
completed pairs every 64 games and resume after a restart. A build, network,
book, settings or execution profile change starts a separate gate. Only a passed gate promotes
a network or accepts search settings; the settings also apply to self-play.

Self-play rotates into chunks of about one million positions. The controller
limits generated data to 14 GiB and pauses generation below 8 GiB of free
disk space. It retires only complete generated chunks that were included in
a successful training round, preserving untrained data, networks and match
evidence. The service restarts after a crash and starts at login. It prevents
idle sleep with a macOS assertion owned by the controller; stopping the service
releases it, and the display can still sleep. Pass `--allow-idle-sleep` when
installing to omit this assertion. Manual sleep and closing the lid can still
pause work. `status` reports idle-sleep protection, its current phase, fresh
positions, pending tests and saved gate results.

Milestone matches cover every version in the existing opponent suite plus
full-strength Stockfish 19: Stockfish 17.1, Koivisto 9.0, Demolito 2021,
Ethereal 12.00, Laser 1.7, Stash 28/31/34/37 and Weiss 1.2/1.3/1.4/2.0.
Prepare them on the Mac with the forge stopped, then reinstall its profile:

```sh
python3 forge/macbook.py stop
python3 forge/opponents.py --jobs 18
python3 forge/macbook.py install --cpu-budget 18 --min-new 20000000
```

The verified catalog enables milestone testing automatically. Each changed
champion network, executable or accepted settings creates a saved snapshot.
The controller alternates external batches with search batches within the
same CPU budget, using one thread and 64 MB hash on both sides. Each opponent
plays 200 games at 10+0.1 and 100 at 60+0.6, with colours reversed per opening.
Completed batches and game records survive restarts; a later promotion keeps
earlier unfinished suites. Results live in `DATA/forge/milestones/`, with
pair-based conservative 95% score intervals. These matches measure outside
opposition; the existing SPRT gates decide promotions. Historical cloud ratings
are not extrapolated from these Mac results.

Rejected or interrupted external batches keep their summary and game records
in numbered `NNNN-attempts/` archives before a retry reuses the output paths.
The adjacent `NNNN.attempts.json` records commands and errors. A batch gets at
most three attempts across restarts, including an interrupted launch. Exhausted
batches are listed in `blocked_matches`; other opponents and search tests keep
running. If only exhausted batches remain, the suite reports `needs_attention`
and stops scheduling games until the cause is investigated. Failed attempts
never enter the accepted game counts or score intervals.

Local SPRT batches use the same three-attempt rule and now write game records
so a failed game's losing side can be inspected. Their archives are under
`GATE.json.batch-attempts/SEED/`. An exhausted search gate keeps its original
checkpoint and queue entry and reports `search_retry_failure` in service status;
external matches continue. Resolve the recorded cause before allowing more
attempts. Accepted temporary records are removed after their aggregate commits.

Analyse saved losses with `forge/blunders.py` using the dependencies in
`forge/requirements-analysis.txt`. It compares Stockfish's preferred move
with the played move from the same position, at equal node limits and with
fresh search state. A preferred move has zero estimated loss; restricted
searches that disagree with the recommendation are counted separately.
Saved reports include input hashes and the reference build. These diagnostics
guide experiments; they do not establish a strength gain or replace match gates.
After every opponent has a completed initial batch, and again after the full
suite finishes, the controller reviews up to 32 saved losses with Stockfish 19.
The review replaces one external batch slot and uses its available cores beside
self-play. It freezes game records, the reference binary and the analysis code;
completed reviews survive restarts. Reports and bounded failure retries live in
the milestone's `diagnostics/` folder. Pass `--loss-analysis-sample 0` to the loop
to disable reviews, or another sample size to change their budget.

For a network-capacity experiment, append `--train-hidden 1024` when installing
the Mac profile. Training rounds use that width and the normal gate
compares the candidate with the current champion before any promotion. Omit
the option to choose capacity from the retained dataset size. This makes larger
models testable without expanding the self-play storage budget.

Training carries partial record buffers into the next batch and visits every
frozen training and validation row exactly once per pass. It uses one final
partial batch, weights losses and throughput by actual record counts, and sizes
the learning-rate schedule from the resulting number of optimizer steps. A
shortened frozen input or incomplete epoch fails the round instead of silently
reducing its dataset. Appended records remain outside the frozen prefix.

For an isolated fine-tuning study, provide both `--init-checkpoint model.nnue.pt`
and `--init-network model.nnue` to `trainer/train.py`, with the matching hidden
width and bucket counts. The checkpoint must re-export byte for byte to that
NNUE before training starts. Output files cannot overwrite either input, and
input hashes are checked again after training. Fine-tuning defaults to a
learning rate of `1e-5`; training from scratch keeps its `1e-3` default. The
`.init.json` sidecar records initialization, settings and selected checkpoint
hashes. This option does not change the supervised controller's training policy
or promote a model; a fresh strength gate remains required.

When a completed training round exports exactly the champion's network bytes,
the controller records its trained-data progress and skips the duplicate gate.
With an explicit champion file, an identical NNUE cannot create a new champion
version, even if a separately requested statistical test returns H1. Search and executable comparisons still
use their normal gates with the same network on both sides.

For a multicore search experiment, pass `common.Threads=3` to `test_queue.py add`
(saved as `"common_options": {"Threads": "3"}`). Both engines receive these options, and the controller
reduces concurrent games to fit their threads within the remaining CPU budget.
Common options are recorded with the evidence and are never promoted as tuned
settings. `smp_vote=1` is an experimental vote among completed main and helper
searches; its shipped default is zero until a strength test passes.

To compare executable changes locally, a queue entry can set `candidate_engine`
and `baseline_engine` (also accepted by `test_queue.py add`). Both sides use
the same champion network and accepted settings. The result records the hash
of each executable, and changing either starts a separate test. The Apple
Silicon neural output kernel uses NEON with exact i64 reduction; full evaluation
retains the scalar reference, and other architectures use the portable path.

| Path       | Contents                                             |
| ---------- | ---------------------------------------------------- |
| `engine/`  | The engine and library (`arhanpassant` crate)        |
| `arena/`   | Match runner and SPRT gate                           |
| `wasm/`    | WebAssembly interface for browsers                   |
| `trainer/` | NNUE training and pipeline checks                    |
| `forge/`   | Cloud self-play fleet scripts                        |

## License

Licensed under either of [Apache License, Version 2.0](LICENSE-APACHE) or
[MIT license](LICENSE-MIT) at your option.
