#ifndef IRINA_H
#define IRINA_H

typedef struct
{
   unsigned from      : 6;
   unsigned to        : 6;
   unsigned piece     : 4;
   unsigned capture   : 4;
   unsigned promotion : 4;
   unsigned is_ep     : 1;
   unsigned is_2p     : 1;
   unsigned is_castle : 2;
} MoveBin;

void init_board(void);
void fen_board(char *fen);
int movegen(void);
int pgn2pv(char *pgn, char * pv);
int make_nummove(int resp);
int num_moves( void );
void get_move( int num, char * pv );

char *board_fen(char *fen);
char *board_fenM2(char *fen);

int num_base_move( void );
int search_move( char *desde, char *hasta, char * promotion );
void get_move_ex( int num, char * info );
char * to_san(int num, char *sanMove);
char incheck(void);

void pgn_start(int depth);
void pgn_stop( void );
int pgn_read(char * body, char * fen);
char * pgn_pv(void);
int pgn_raw(void);
char * pgn_fen(int num);
int pgn_numfens(void);

int parse_body( char * fen, char * body, char * resp );

int parse_pgn(char * pgn, char * resp );

unsigned long long hash_from_fen(char *fen);

void write_integer(int size, unsigned long long n);
unsigned int move_from_string(char move_s[6]);
int move_to_string(char move_s[6], unsigned int move);

void open_poly_w(char * name);
void close_poly(void);

void pv_xpv_c(const char* pv, char* res);

int cpu_flags_to_string(char *buffer, int size);

#endif
