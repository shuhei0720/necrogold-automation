/* TEST-015: fixed 896 x 414 RGB; no allocation, imports or floating point.
 * Build from repository root (GCC 13.3.0 used for the bundled artifact):
 * gcc -m32 -march=i386 -mno-sse -mno-sse2 -O2 -fPIC -ffreestanding \
 *   -fno-stack-protector -fno-builtin -shared -nostdlib -Wl,--build-id=none \
 *   necroprobe/gold_scan_native.c -o necroprobe/gold_scan_i386.so
 * The Python loader pins the SHA-256 of that exact artifact.
 */
#define WIDTH 896
#define HEIGHT 414
#define RGB_LENGTH (WIDTH * HEIGHT * 3)
#define RADIUS 13
#define WINDOW 27
#define OUTPUT_LENGTH 49

/* One horizontal BoxBlur pass with constant extension at either edge.
 * Mask inequalities are exactly the integer LUT inequalities in gold_scan.py.
 */
static void horizontal_row(const unsigned char *rgb, int y, unsigned char *out) {
    unsigned char mask[WIDTH];
    unsigned int sum;
    int x;
    for (x = 0; x < WIDTH; ++x) {
        unsigned int r = rgb[x * 3], g = rgb[x * 3 + 1], b = rgb[x * 3 + 2];
        int excluded = (x < 143 && y < 54) || (x >= 663 && y < 80) ||
            (x >= 717 && y >= 315) || (x >= 405 && x < 485 && y >= 321) ||
            y >= 380;
        mask[x] = !excluded && r > 52 && 1000 * g > 685 * r &&
            100 * g < 92 * r && 100 * b > 7 * g && 100 * b < 58 * g ? 255 : 0;
    }
    sum = (RADIUS + 1) * mask[0];
    for (x = 1; x <= RADIUS; ++x) sum += mask[x];
    for (x = 0; x < WIDTH; ++x) {
        int leaving = x - RADIUS, entering = x + RADIUS + 1;
        out[x] = (unsigned char)((sum + RADIUS) / WINDOW);
        if (leaving < 0) leaving = 0;
        if (entering >= WIDTH) entering = WIDTH - 1;
        sum = sum - mask[leaving] + mask[entering];
    }
}

/* output[0] = gold peak, output[1..48] = terrain fingerprint.
 * Invalid pointers/lengths are rejected before reading input or writing output.
 * As with any C byte API, supplied non-null pointers must own their stated size.
 */
int necro_gold_scan(const unsigned char *rgb, unsigned int rgb_len,
                    unsigned char *output, unsigned int output_len) {
    unsigned char horizontal[WINDOW][WIDTH];
    unsigned int vertical[WIDTH];
    unsigned int peak = 0;
    int row, col, x, y;
    if (!rgb || !output || rgb_len != RGB_LENGTH || output_len != OUTPUT_LENGTH)
        return -1;

    for (row = 0; row < 6; ++row) {
        for (col = 0; col < 8; ++col) {
            unsigned int sum = 0, mean, remainder;
            int index = 1 + row * 8 + col;
            if (col >= 2 && col <= 5 && row >= 2 && row <= 4) {
                output[index] = 0;
                continue;
            }
            for (y = 70 + row * 48; y < 118 + row * 48; ++y) {
                const unsigned char *pixel = rgb + (y * WIDTH + 224 + col * 56) * 3;
                for (x = 0; x < 56; ++x, pixel += 3)
                    sum += (19595u * pixel[0] + 38470u * pixel[1] +
                            7471u * pixel[2] + 32768u) >> 16;
            }
            mean = sum / (56 * 48);
            remainder = sum % (56 * 48);
            /* ImageStat mean then Python round: exact halves go to even. */
            if (remainder > 56 * 24 || (remainder == 56 * 24 && (mean & 1))) ++mean;
            output[index] = (unsigned char)mean;
        }
    }

    for (x = 0; x < WIDTH; ++x) vertical[x] = 0;
    /* A 27-row ring keeps per-call stack use below 32 KiB, with no shared
     * mutable state. Row zero contributes 14 times to the first window.
     * The final 13 iterations extend the bottom row, as Pillow does.
     */
    for (y = 0; y < HEIGHT + RADIUS; ++y) {
        unsigned char *incoming;
        if (y > RADIUS) {
            const unsigned char *leaving = horizontal[y < WINDOW ? 0 : (y - WINDOW) % WINDOW];
            for (x = 0; x < WIDTH; ++x) vertical[x] -= leaving[x];
        }
        if (y < HEIGHT) {
            incoming = horizontal[y % WINDOW];
            horizontal_row(rgb + y * WIDTH * 3, y, incoming);
        } else {
            incoming = horizontal[(HEIGHT - 1) % WINDOW];
        }
        for (x = 0; x < WIDTH; ++x) {
            unsigned int value;
            vertical[x] += incoming[x] * (y == 0 ? RADIUS + 1 : 1);
            if (y < RADIUS) continue;
            /* Pillow rounds the horizontal pass before the vertical pass. */
            value = (vertical[x] + RADIUS) / WINDOW;
            if (value > peak) peak = value;
        }
        if (peak == 255) break;
    }
    output[0] = (unsigned char)peak;
    return 0;
}
