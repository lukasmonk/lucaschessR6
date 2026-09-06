#ifndef IRINA_PROTOS_H
#define IRINA_PROTOS_H

#include "defs.h"
#include "hash.h"

// util.c
unsigned int first_one(Bitmap bitmap);
int ah_pos(char *ah);

// data.c
void init_data(void);

// board.c
void init_board(void);
void board_reset(void);
void fen_board(char *fen);
void bitmap_pz(unsigned pz[], Bitmap bm, int piece);
char *board_fen(char *fen);
char *board_fenM2(char *fen);
Bitmap board_hashkey(void);

// movegen.c
int movegen(void);
void addMove(MoveBin move);
bool isAttacked(Bitmap targetBitmap, int fromSide);
bool incheck(void);

int movegen_piece_to(int piece, unsigned xto);

// makemove.c
void make_move(MoveBin move);
void unmake_move(void);

// hash.c
Bitmap rand64();
void init_hash();

// lc.c
int pgn2pv(char *pgn, char * pv);
int make_nummove(int num);

// parser.c
int parse_body( char * fen, char * body, char * resp );
int parse_pgn( char * pgn, char * resp );

// pgn.c
void pgn_start(int depth);
void pgn_stop( void );
int pgn_read(char * body, char * fen);
char * pgn_pv(void);
int pgn_raw(void);
char * pgn_fen(int num);
int pgn_numfens(void);

// polyglot.c
Bitmap hash_from_fen(char *fen);
void open_poly_w(char * name);
void close_poly();
void write_integer(int size, unsigned long long n);
unsigned int move_from_string(char move_s[6]);
int move_to_string(char move_s[6], unsigned int move);

// cpu_flags.c
int cpu_flags_to_string(char *buffer, int size);


#endif