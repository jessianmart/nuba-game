#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

static inline uint32_t get_bits(const uint8_t *src, int *in_pos, uint64_t *bit_buf, int *bits_left, int n) {
    while (*bits_left < n) {
        if (*in_pos >= 16) {
            *bit_buf = (*bit_buf << 8) | src[*in_pos];
            (*in_pos)--;
        } else {
            *bit_buf = (*bit_buf << 8);
        }
        *bits_left += 8;
    }
    *bits_left -= n;
    uint32_t val = (uint32_t)((*bit_buf >> *bits_left) & ((1ULL << n) - 1));
    *bit_buf &= (1ULL << *bits_left) - 1;
    return val;
}

EXPORT int decompress_crilayla_c(const uint8_t *src, int src_len, uint8_t *out, int max_out_len) {
    if (src_len < 16 || memcmp(src, "CRILAYLA", 8) != 0) {
        return -1;
    }
    uint32_t uncomp_size = *(const uint32_t*)(src + 8);
    uint32_t comp_size = *(const uint32_t*)(src + 12);
    int total_out = (int)uncomp_size + 0x100;
    if (total_out > max_out_len) {
        return -2;
    }
    if ((int)(16 + comp_size + 0x100) > src_len) {
        return -3;
    }

    memcpy(out, src + 16 + comp_size, 0x100);

    int in_pos = 16 + comp_size - 1;
    uint64_t bit_buf = 0;
    int bits_left = 0;
    int out_pos = 0x100 + (int)uncomp_size - 1;
    const int vle_lens[4] = {2, 3, 5, 8};

    while (out_pos >= 0x100) {
        if (get_bits(src, &in_pos, &bit_buf, &bits_left, 1)) {
            int offset = out_pos + get_bits(src, &in_pos, &bit_buf, &bits_left, 13) + 3;
            int length = 3;
            int done_vle = 0;
            for (int i = 0; i < 4; i++) {
                int vle = vle_lens[i];
                int this_level = get_bits(src, &in_pos, &bit_buf, &bits_left, vle);
                length += this_level;
                if (this_level != ((1 << vle) - 1)) {
                    done_vle = 1;
                    break;
                }
            }
            if (!done_vle) {
                while (1) {
                    int this_level = get_bits(src, &in_pos, &bit_buf, &bits_left, 8);
                    length += this_level;
                    if (this_level != 255) break;
                }
            }
            for (int i = 0; i < length; i++) {
                out[out_pos] = out[offset];
                out_pos--;
                offset--;
                if (out_pos < 0x100) break;
            }
        } else {
            out[out_pos] = (uint8_t)get_bits(src, &in_pos, &bit_buf, &bits_left, 8);
            out_pos--;
        }
    }
    return total_out;
}
