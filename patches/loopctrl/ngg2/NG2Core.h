#ifndef NG2_CORE_H
#define NG2_CORE_H
#include <stdint.h>
#include <stddef.h>
#define NG2_ABI_VERSION 1u
#define NG2_WIDTH 896
#define NG2_HEIGHT 414
#define NG2_TILE_COUNT 230
#define NG2_SIGNATURE_LENGTH 23296
#define NG2_VISIT_COUNT 1089
enum { NG2_UNKNOWN=0, NG2_PAUSE=1, NG2_FLOOR=2 };
enum { NG2_GOLD_UNKNOWN=0, NG2_GOLD_CLEAR=1, NG2_GOLD_CANDIDATE=2,
       NG2_GOLD_EDGE_DOWN=3 };
enum { NG2_GOODS_UNKNOWN=0, NG2_GOODS_PARTIAL=1, NG2_GOODS_VISIBLE=2 };
enum { NG2_TILE_UNKNOWN=0, NG2_TILE_FLOOR=1, NG2_TILE_GOLD=2, NG2_TILE_STONE=3,
       NG2_TILE_DIRT=4, NG2_TILE_DOOR=5, NG2_TILE_ITEM=6 };
enum { NG2_DIR_NONE=0, NG2_LEFT=1, NG2_RIGHT=2, NG2_UP=3, NG2_DOWN=4 };
typedef struct {
    uint32_t abi_version, struct_size;
    int32_t state, restart_label, gold_state, gold_peak, goods;
    uint8_t tiles[NG2_TILE_COUNT], protected_cells[NG2_TILE_COUNT];
    uint8_t signature[NG2_SIGNATURE_LENGTH], fingerprint[48];
    int32_t beat_valid;
    double beat_remaining, beat_spacing, beat_center;
} NG2Scene;
typedef struct { int32_t valid, x, y, direction; } NG2Entrance;
typedef struct { int32_t direction, reason, target_x, target_y, obstacle; } NG2Decision;
enum { NG2_MOTION_UNKNOWN=0, NG2_MOVED=1, NG2_BLOCKED=2, NG2_DOOR_OPENED=3,
       NG2_TERRAIN_OPENED=4, NG2_GATE_ENTERED=5, NG2_UNEXPECTED=6, NG2_TWEEN=7 };
typedef struct { int32_t kind, dx, dy; } NG2Motion;
typedef struct {
    uint64_t start_ns, end_ns, midpoint_ns;
    double half_width_ns, q, spacing, center;
} NG2BeatSample;
typedef struct {
    uint64_t period_ns, epoch_ns, first_ns, last_ns, gap_ns, prediction_span_ns;
    int32_t sample_count, mode, candidate_count;
    double residual, maximum, alternate, alias_gap, half_width_max_ns, tracking_error, extrapolation_budget;
} NG2BeatModel;
/* Packed RGBA8 integer orientation, matching the Raster EXIF maps. Dimensions
 * are 1..4096, at most 8,000,000 pixels; orientation is 1..8. Both lengths
 * must equal width*height*4 and buffers must not overlap. RGB is copied and
 * output alpha is 255. Returns copied pixels, or zero before any write on
 * invalid arguments. No allocation or shared mutable state. */
size_t ng2_orient_rgba(const uint8_t *source, size_t source_length,
                       int32_t width, int32_t height, int32_t orientation,
                       uint8_t *destination, size_t destination_length);
/* rgba is sRGB opaque RGBA8, length exactly stride*414, stride 3584..7680.
 * Padding is ignored. Input is immutable for this call. Output is copied and
 * initialized to unknown on failure. No global mutable state. */
int ng2_analyze_rgba(const uint8_t *rgba, size_t length, size_t stride, NG2Scene *out);
int ng2_fingerprint_changed(const uint8_t *before, const uint8_t *after);
/* tiles index = (y+5)*23+x+11; visits world index = (y+16)*33+x+16. */
int ng2_choose(const NG2Scene *scene, int32_t x, int32_t y,
               const uint16_t *visits, size_t visit_count, const NG2Entrance *entrance, NG2Decision *out);
/* Initial no-gold room side passages: bits0..4=(k,-3), bits5..9=(-3,k),
 * k=-2..2. No synthetic GOLD or permission to enter an unobserved cell. */
uint32_t ng2_passage_candidates(const NG2Scene *scene);
/* mouth is fixed in initial world coordinates. A positive return is the
 * shortest observed-FLOOR path length to the chosen local vantage; the
 * decision target is that actual vantage relative to the current player.
 * The one-cell-outside goal and arrival are tracked by the caller. */
int ng2_choose_passage(const NG2Scene *scene, int32_t x, int32_t y,
                      int32_t mouth_x, int32_t mouth_y, NG2Decision *out);
int ng2_motion(const NG2Scene *before, const NG2Scene *after, int32_t direction, NG2Motion *out);
int ng2_entered_gate(const NG2Scene *before, const NG2Scene *after, int32_t direction,
                     int32_t x, int32_t y, int32_t motion, NG2Entrance *out);
int ng2_make_sample(double q, double spacing, double center, uint64_t start, uint64_t end, NG2BeatSample *out);
int ng2_beat_fit(const NG2BeatSample *samples, size_t count, NG2BeatModel *out);
int ng2_beat_track(const NG2BeatModel *old, const NG2BeatSample *samples, size_t count, NG2BeatModel *out);
int ng2_beat_model_valid(const NG2BeatModel *model);
uint64_t ng2_next_target(const NG2BeatModel *model, uint64_t now, uint64_t lead);
#endif
