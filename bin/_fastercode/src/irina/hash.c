#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "defs.h"
#include "protos.h"
#include "hash.h"
#include "globals.h"

Bitmap HASH_keys[64][16];
Bitmap HASH_ep[64];
Bitmap HASH_wk = 0;
Bitmap HASH_wq;
Bitmap HASH_bk;
Bitmap HASH_bq;
Bitmap HASH_side;

Bitmap register_max;

static Bitmap splitmix_state;

static Bitmap splitmix_next(void) {
    Bitmap z = (splitmix_state += 0x9e3779b97f4a7c15);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9;
    z = (z ^ (z >> 27)) * 0x94d049bb133111eb;
    return z ^ (z >> 31);
}

Bitmap rand64()
{
    return splitmix_next();
}

void init_hash()
{
    int i, j;

    splitmix_state = (Bitmap)time(NULL) ^ ((Bitmap)clock() << 16);

    for (i = 0; i < 64; i++)
    {
        HASH_ep[i] = rand64();
        for (j = 0; j < 16; j++)
        {
            HASH_keys[i][j] = rand64();
        }
    }
    HASH_side = rand64();
    HASH_wk = rand64();
    HASH_wq = rand64();
    HASH_bk = rand64();
    HASH_bq = rand64();

}
