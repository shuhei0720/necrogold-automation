#ifndef NG2_RING_H
#define NG2_RING_H
#include <stddef.h>
#include <stdint.h>
#include "NG2Core.h"

#define NG2_RING_ABI 1u
#define NG2_RING_MAX_ROWS 4
#define NG2_RING_MAX_SLOTS 3
#define NG2_RING_MAX_PARTIAL 12

enum { NG2_RING_UNKNOWN=0, NG2_RING_CANDIDATE=1, NG2_RING_TARGET=2, NG2_RING_NEGATIVE=3 };
#define NG2_RING_NON_TARGET 3u
#define NG2_RING_IGNORED_CONTAINER 4u
#define NG2_RING_GENERIC_NON_TARGET 3u
enum { NG2_RING_MODE_LEGACY=0, NG2_RING_MODE_COMPENSATED=1, NG2_RING_MODE_TARGET_ONLY=2 };
enum { NG2_RING_OK=0, NG2_RING_CANCELLED=1, NG2_RING_DEADLINE=2,
       NG2_RING_INVALID=3, NG2_RING_ALLOCATION=4, NG2_RING_KERNEL=5 };
enum { NG2_RING_COVERAGE_UNKNOWN=0, NG2_RING_COVERAGE_INCOMPLETE=1,
       NG2_RING_COVERAGE_COMPLETE=2 };
enum { NG2_RING_NO_ROW=0, NG2_RING_NO_TARGET_EVIDENCE=1,
       NG2_RING_ICON_ONLY=2, NG2_RING_ICON_AND_NAME=3, NG2_RING_EXPOSED_TARGET_ABSENT=4 };
enum { NG2_RING_COV_SCENE=1u, NG2_RING_COV_BOARD=2u, NG2_RING_COV_GLYPH=4u,
       NG2_RING_COV_MERCHANT=8u, NG2_RING_COV_ENDCAP=16u, NG2_RING_COV_IDENTITY=32u,
       NG2_RING_COV_PRICE=64u, NG2_RING_COV_ITEM=128u, NG2_RING_COV_ROWS=256u,
       NG2_RING_COV_BOUNDS=512u, NG2_RING_COV_EXTRA_BOARD=1024u };

typedef uint64_t (*NG2RingClock)(void *context);
typedef int (*NG2RingCancelled)(void *context);
typedef struct {
    uint32_t abi, size;
    int32_t mode;
    uint32_t reserved;
    uint64_t deadline_ns;
    NG2RingClock now_ns;
    NG2RingCancelled cancelled;
    void *context;
    const NG2Scene *scene;
    uint32_t fast;
} NG2RingOptions;

typedef struct {
    int32_t cx, sy, slot, word_present;
    double icon_score, word_iou, word_coverage;
    int32_t icon_box[4], word_box[4];
    uint32_t icon_score_exact;
    double icon_upper_bound;
    uint32_t outcome, non_target_id;
    double non_target_icon_score, non_target_name_iou, non_target_name_coverage;
    int32_t non_target_icon_box[4], non_target_name_box[4];
    uint32_t non_target_conflict;
    uint32_t kind, ignored_container_id;
    double ignored_icon_score, ignored_gold_iou, ignored_gold_coverage, ignored_dark_iou, ignored_dark_coverage;
    int32_t ignored_icon_box[4];
} NG2RingSlot;
typedef struct {
    int32_t left, sy, word_slot;
    uint32_t outcome, reason;
    NG2RingSlot slots[NG2_RING_MAX_SLOTS];
} NG2RingRow;
typedef struct {
    int32_t box[4], r, g, b, spread, black_count, count;
    int32_t bright_count, price_ink_count, floor_full, floor_upper, floor_lower;
} NG2RingEndcap;
typedef struct {
    uint32_t layout_version;
    int32_t accepted_rows, observed_items, observed_prices, unmatched_items, unmatched_prices;
    int32_t scene_state, scene_goods, actual_gold_cells, row[2], strip_box[4];
    int32_t merchant_box[4], sign_boxes[2][4];
    double merchant_score, merchant_coverage, sign_iou[2], sign_coverage[2];
    NG2RingEndcap endcaps[2];
    int32_t item_boxes[3][4], name_boxes[3][4], price_boxes[3][4];
    uint32_t policy_version, failure_flags;
    int32_t row_index, non_target_items, ignored_containers, unmatched_boards;
    int32_t board_boxes[2][4], board_counts[2];
    int32_t board_edge_counts[2][4], board_corner_counts[2][4];
    int32_t board_exterior_count[2];
    uint32_t board_mode;
} NG2RingCoverage;
typedef struct {
    uint32_t abi, size, status, outcome, coverage, reason;
    int32_t row_count, selected_row, partial_count, selected_partial;
    uint32_t partial_safe_no_positive;
    uint64_t started_ns, finished_ns, checks;
    NG2RingRow rows[NG2_RING_MAX_ROWS];
    NG2RingSlot partial[NG2_RING_MAX_PARTIAL];
    NG2RingCoverage certificate;
} NG2RingResult;

/* Immutable fixed 896x414 opaque RGBA. No input, I/O, or caller identity authority.
 * The caller binds this result to owner/run/level/prefix/capture/SHA at commit.
 * A non-OK status is a failed job, never a completed UNKNOWN or NEGATIVE. */
int ng2_ring_assess_rgba(const unsigned char *rgba, size_t bytes, size_t stride,
                         const NG2RingOptions *options, NG2RingResult *result);
const char *ng2_ring_classifier_version(void);
const char *ng2_ring_feature_sha256(void);
const char *ng2_ring_bank_sha256(void);
const char *ng2_ring_coverage_sha256(void);
const char *ng2_ring_coverage_version(void);
const char *ng2_ring_policy_version(void);
const char *ng2_ring_target_only_policy_version(void);

/* Pure bounded raw-row aggregation, also used by the pixel entry point.
 * Input fields must be finite; outputs use Python's binary64 round(...,9). */
int ng2_ring_aggregate(NG2RingResult *result);
double ng2_ring_round9(double value);
/* Validate only this bounded numeric/image certificate. Source identity,
 * prefix, cancellation, generation and all input authority remain external. */
int ng2_ring_negative_certificate(const NG2RingResult *result);
#endif
