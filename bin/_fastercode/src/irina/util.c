#include <string.h>
#include "defs.h"
#include "protos.h"
#include "globals.h"

/**
 * @author Kim Walisch (2012)
 * @param bb bitboard to scan
 * @precondition bb != 0
 * @return index (0..63) of least significant one bit
 */
unsigned int first_one(Bitmap bb) {
    static const int index64[64] ={
        0, 47, 1, 56, 48, 27, 2, 60,
        57, 49, 41, 37, 28, 16, 3, 61,
        54, 58, 35, 52, 50, 42, 21, 44,
        38, 32, 29, 23, 17, 11, 4, 62,
        46, 55, 26, 59, 40, 36, 15, 53,
        34, 51, 20, 43, 31, 22, 10, 45,
        25, 39, 14, 33, 19, 30, 9, 24,
        13, 18, 8, 12, 7, 6, 5, 63
    };
    static const Bitmap debruijn64 = 0x03f79d71b4cb0a89;

    return index64[((bb ^ (bb - 1)) * debruijn64) >> 58];
}


int ah_pos(char *ah) {
    if ((ah[0] < 'a') || (ah[0] > 'h') || (ah[1] < '0') || (ah[1] > '9')) {
        return 0;
    }
    return (int) (ah[0] - 'a') + 8 * (int) (ah[1] - '1');
}


/**
 * Reduce una partida en formato "e2e4 d7d5..." a nomenclatura compacta xpv.
 * @param pv Cadena de entrada (movimientos separados por espacio).
 * @param res Buffer de salida (debe tener al menos el mismo tamaño que pv).
 */
void pv_xpv_c(const char* pv, char* res) {
    int i = 0; // Índice lectura
    int r = 0; // Índice escritura

    while (pv[i] != '\0') {
        // Saltar espacios
        if (pv[i] == ' ') {
            i++;
            continue;
        }

        // Procesar origen (pv[i], pv[i+1])
        // a1_pos: (fila - '1') * 8 + (col - 'a')
        int src = (pv[i+1] - 49) * 8 + (pv[i] - 97);
        res[r++] = (char)(src + 58);

        // Procesar destino (pv[i+2], pv[i+3])
        int dst = (pv[i+3] - 49) * 8 + (pv[i+2] - 97);
        res[r++] = (char)(dst + 58);

        i += 4;

        // Verificar si hay promoción (ej: e7e8q)
        if (pv[i] != '\0' && pv[i] != ' ') {
            char prom = pv[i];
            if (prom == 'q' || prom == 'Q') res[r++] = 50;
            else if (prom == 'r' || prom == 'R') res[r++] = 51;
            else if (prom == 'b' || prom == 'B') res[r++] = 52;
            else if (prom == 'n' || prom == 'N') res[r++] = 53;

            // Avanzar hasta el siguiente espacio o fin
            while (pv[i] != '\0' && pv[i] != ' ') {
                i++;
            }
        }
    }
    res[r] = '\0'; // Terminación nula del string resultante
}