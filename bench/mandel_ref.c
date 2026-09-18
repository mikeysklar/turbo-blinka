// C reference for turbo's pixels.py mandel_row + _turbo_bench: the compiled ceiling.
#include <stdio.h>
#include <stdint.h>
#include <time.h>
static void mandel_row(uint8_t *out, int width, int dx, int cy, int max_iter) {
    for (int px = 0; px < width; px++) {
        int cx = px * dx - (2 << 12), x = 0, y = 0, i = 0;
        while (i < max_iter) {
            int x2 = (x * x) >> 12, y2 = (y * y) >> 12;
            if (x2 + y2 > (4 << 12)) break;
            y = ((x * y) >> 11) + cy;
            x = x2 - y2 + cx;
            i++;
        }
        out[px] = i;
    }
}
int main(void) {
    enum { W = 160, H = 120, IT = 64 };
    uint8_t row[W]; double best = 1e9; long total = 0;
    for (int t = 0; t < 8; t++) {
        struct timespec a, b; clock_gettime(CLOCK_MONOTONIC, &a);
        total = 0; int dx = (3 << 12) / W;
        for (int r = 0; r < H; r++) {
            mandel_row(row, W, dx, ((r * 2) << 12) / H - (1 << 12), IT);
            for (int k = 0; k < W; k++) total += row[k];
        }
        clock_gettime(CLOCK_MONOTONIC, &b);
        double ms = (b.tv_sec - a.tv_sec) * 1e3 + (b.tv_nsec - a.tv_nsec) / 1e6;
        if (ms < best) best = ms;
    }
    printf("C -O2 best of 8: %.3f ms, value %ld\n", best, total);
}
