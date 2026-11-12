#ifndef RING_H
#define RING_H
#include <stdint.h>
#include <stddef.h>
#define RING_W 896
#define RING_HH 414
#define RING_WORDS 14
#define RING_FILTERED ((size_t)RING_HH*(RING_W*4+1))
#define RING_RGBA ((size_t)RING_HH*RING_W*4)
typedef struct {int left,sy;} RingRow;
typedef struct {uint64_t white[RING_HH][RING_WORDS];RingRow rows[4];int count;} RingObservation;
typedef struct {int slot;double iou,coverage;int box[4];} RingWord;
static inline double ring_div(double a,double b){volatile double r=a/b;return r;}
int ring_observe(const unsigned char *rgba,RingObservation *out);
int ring_word(const RingObservation *observation,int cx,int sy,int slot,RingWord *out);
int ring_unfilter(const unsigned char *filtered,unsigned char *rgba);
const char *ring_feature_sha256(void);
int ring_icon(const unsigned char *rgba,size_t bytes,int cx,int sy,int mode,int (*cancelled)(void),double *raw_best,int box[4]);
#endif
