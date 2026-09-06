#ifndef IRINA_GLOBALS_H
#define IRINA_GLOBALS_H

extern Board  board;
extern Bitmap BITSET[64];
extern Bitmap FREEWAY[64][64];
extern Bitmap WHITE_PAWN_ATTACKS[64];
extern Bitmap WHITE_PAWN_POSTATTACKS[64];
extern Bitmap WHITE_PAWN_MOVES[64];
extern Bitmap WHITE_PAWN_DOUBLE_MOVES[64];
extern Bitmap BLACK_PAWN_ATTACKS[64];
extern Bitmap BLACK_PAWN_POSTATTACKS[64];
extern Bitmap BLACK_PAWN_MOVES[64];
extern Bitmap BLACK_PAWN_DOUBLE_MOVES[64];
extern Bitmap KNIGHT_ATTACKS[64];
extern Bitmap KING_ATTACKS[64];
extern Bitmap LINE_ATTACKS[64];
extern Bitmap DIAG_ATTACKS[64];

extern Bitmap HASH_keys[64][16];
extern Bitmap HASH_ep[64];
extern Bitmap HASH_wk;
extern Bitmap HASH_wq;
extern Bitmap HASH_bk;
extern Bitmap HASH_bq;
extern Bitmap HASH_side;

extern char *POS_AH[64];
extern char NAMEPZ[16];


#endif