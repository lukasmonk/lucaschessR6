#include "protos.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>

#if defined(_MSC_VER)
    #include <intrin.h>
    static void cpuid(int info[4], int leaf, int subleaf) {
        __cpuidex(info, leaf, subleaf);
    }
#else
    #include <cpuid.h>
    static void cpuid(int info[4], int leaf, int subleaf) {
        __cpuid_count(leaf, subleaf, info[0], info[1], info[2], info[3]);
    }
#endif

enum {
    FLAG_SSE3       = 1ULL << 0,
    FLAG_SSSE3      = 1ULL << 1,
    FLAG_SSE4_1     = 1ULL << 2,
    FLAG_POPCNT     = 1ULL << 3,
    FLAG_AVX2       = 1ULL << 4,
    FLAG_BMI2       = 1ULL << 5,
    FLAG_AVXVNNI    = 1ULL << 6,
    FLAG_AVX512F    = 1ULL << 7,
    FLAG_AVX512VL   = 1ULL << 8,
    FLAG_AVX512VNNI = 1ULL << 9,
    FLAG_AVX512DQ   = 1ULL << 10,
    FLAG_AVX512BW   = 1ULL << 11,
};

static uint64_t detect_cpu_flags(void) {
    uint64_t flags = 0;
    int info[4] = {0};

    cpuid(info, 0, 0);
    int max_leaf = info[0];

    if (max_leaf >= 1) {
        cpuid(info, 1, 0);
        int ecx = info[2];
        if (ecx & (1 << 0))  flags |= FLAG_SSE3;
        if (ecx & (1 << 9))  flags |= FLAG_SSSE3;
        if (ecx & (1 << 19)) flags |= FLAG_SSE4_1;
        if (ecx & (1 << 23)) flags |= FLAG_POPCNT;
    }

    if (max_leaf >= 7) {
        cpuid(info, 7, 0);
        int ebx = info[1];
        int ecx7 = info[2];
        int max_sub7 = info[0];

        if (ebx & (1 << 5))   flags |= FLAG_AVX2;
        if (ebx & (1 << 8))   flags |= FLAG_BMI2;
        if (ebx & (1 << 16))  flags |= FLAG_AVX512F;
        if (ebx & (1 << 17))  flags |= FLAG_AVX512DQ;
        if (ebx & (1 << 30))  flags |= FLAG_AVX512BW;
        if (ebx & (1u << 31)) flags |= FLAG_AVX512VL;
        if (ecx7 & (1 << 11)) flags |= FLAG_AVX512VNNI;

        if (max_sub7 >= 1) {
            cpuid(info, 7, 1);
            if (info[0] & (1 << 4)) flags |= FLAG_AVXVNNI;
        }
    }

    return flags;
}

int cpu_flags_to_string(char *buffer, int size) {
    uint64_t flags = detect_cpu_flags();
    struct { const char *name; uint64_t bit; } table[] = {
        {"sse3", FLAG_SSE3}, {"ssse3", FLAG_SSSE3}, {"sse4_1", FLAG_SSE4_1},
        {"popcnt", FLAG_POPCNT}, {"avx2", FLAG_AVX2}, {"bmi2", FLAG_BMI2},
        {"avxvnni", FLAG_AVXVNNI}, {"avx512f", FLAG_AVX512F},
        {"avx512vl", FLAG_AVX512VL}, {"avx512vnni", FLAG_AVX512VNNI},
        {"avx512dq", FLAG_AVX512DQ}, {"avx512bw", FLAG_AVX512BW},
    };
    buffer[0] = '\0';
    int written = 0;
    int first = 1;
    for (size_t i = 0; i < sizeof(table) / sizeof(table[0]); i++) {
        if (flags & table[i].bit) {
            int n = snprintf(buffer + written, size - written, "%s%s",
                              first ? "" : ",", table[i].name);
            if (n < 0 || written + n >= size) break;
            written += n;
            first = 0;
        }
    }
    return written;
}