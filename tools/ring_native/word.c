/* Fixed numeric word ink only, generated from target_ring_features.json.
 * SHA256 202322326d86f600b300713ca8572b592f3beb59ceff6e6f6e58ef9cb3b728b4
 * This file reads no original image and performs no pixel mutation or I/O. */
#include "ring.h"

#include "word_features.h"

static unsigned pop32(uint32_t value) {
    value -= (value >> 1) & UINT32_C(0x55555555);
    value = (value & UINT32_C(0x33333333)) + ((value >> 2) & UINT32_C(0x33333333));
    value = (value + (value >> 4)) & UINT32_C(0x0f0f0f0f);
    return (unsigned)((value * UINT32_C(0x01010101)) >> 24);
}

static unsigned pop64(uint64_t value) {
    return pop32((uint32_t)value) + pop32((uint32_t)(value >> 32));
}

static void window84(const uint64_t row[RING_WORDS], int x, uint64_t bits[2]) {
    unsigned word = (unsigned)x >> 6;
    unsigned shift = (unsigned)x & 63;
    bits[0] = row[word] >> shift;
    bits[1] = row[word+1] >> shift;
    if (shift) {
        bits[0] |= row[word+1] << (64-shift);
        if (word+2 < RING_WORDS) bits[1] |= row[word+2] << (64-shift);
    }
    bits[1] &= UINT64_C(0xfffff);
}

int ring_word(const RingObservation *observation, int cx, int sy, int slot, RingWord *out) {
    if (!observation || !out || cx < 0 || cx >= RING_W || sy < 0 || sy >= RING_HH || slot < 0 || slot > 2) return -1;
    int y0 = sy-20 > 0 ? sy-20 : 0;
    int y1 = sy+35 < RING_HH-11 ? sy+35 : RING_HH-11;
    int x0 = cx-60 > 0 ? cx-60 : 0;
    int x1 = cx-24 < RING_W-84 ? cx-24 : RING_W-84;
    if (y0 > y1 || x0 > x1) return 1;
    int found = 0;
    double best_iou = 0.0, best_coverage = 0.0;
    int best_x = x0, best_y = y0;
    for (int y=y0; y<=y1; y++) {
        for (int x=x0; x<=x1; x++) {
            unsigned intersection = 0, total_union = 0;
            for (int dy=0; dy<11; dy++) {
                uint64_t observed[2];
                window84(observation->white[y+dy], x, observed);
                intersection += pop64(word_reference[dy][0] & observed[0]);
                intersection += pop64(word_reference[dy][1] & observed[1]);
                total_union += pop64(word_reference[dy][0] | observed[0]);
                total_union += pop64(word_reference[dy][1] | observed[1]);
            }
            double iou = ring_div((double)intersection, (double)(total_union ? total_union : 1));
            double coverage = ring_div((double)intersection, 239.0);
            if (!found || iou > best_iou || (iou == best_iou && coverage > best_coverage)) {
                found = 1; best_iou = iou; best_coverage = coverage;
                best_x = x; best_y = y;
            }
        }
    }
    out->slot = slot; out->iou = best_iou; out->coverage = best_coverage;
    out->box[0] = best_x; out->box[1] = best_y; out->box[2] = 84; out->box[3] = 11;
    return 0;
}
