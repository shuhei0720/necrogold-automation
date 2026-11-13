/* Direct-RGBA aggregation over the canonical tools/ring_native kernel.
 * Pixel algorithms are copied byte-for-byte by apply_ngg2, not forked here. */
#include "NG2Ring.h"
#if __has_include("NG2RingKernel/ring.h")
#include "NG2RingKernel/ring.h"
#include "NG2RingKernel/features.h"
#include "NG2RingKernel/word_features.h"
#else
#include "../../../tools/ring_native/ring.h"
#include "../../../tools/ring_native/features.h"
#include "../../../tools/ring_native/word_features.h"
#endif
#include <string.h>
#include <math.h>
#include <fenv.h>
#include <stdlib.h>
#if __has_include("NG2RingBank.h")
#include "NG2RingBank.h"
#include "NG2RingCoverage.h"
#define NG2_HAS_RING_BANK 1
#else
#define NG2_HAS_RING_BANK 0
#endif

const char *ng2_ring_classifier_version(void) { return "ngg2-ring-assessment-095-v1"; }
const char *ng2_ring_feature_sha256(void) { return ring_feature_sha256(); }
const char *ng2_ring_bank_sha256(void) {
#if NG2_HAS_RING_BANK
    return R94_BANK_SHA256;
#else
    return "";
#endif
}
const char *ng2_ring_coverage_sha256(void) {
#if NG2_HAS_RING_BANK
    return R94_COVERAGE_SHA256;
#else
    return "";
#endif
}
const char *ng2_ring_policy_version(void){return "exposed_cursering_v1";}
const char *ng2_ring_target_only_policy_version(void){return "exposed_cursering_target_only_v2";}
const char *ng2_ring_coverage_version(void){return R94_COVERAGE_AUTHORITY_VERSION;}
/* Python round(x,9) rounds the exact binary64 input to a decimal quantum.
 * Multiplying by 1e9 first loses the threshold's low bits. 5^9 fits in 21
 * bits, so an exact binary numerator fits in 74 bits for bounded scores. */
double ng2_ring_round9(double value) {
    int exponent;
    if (!isfinite(value)||value<0.0||value>2.0) return NAN;
    if (value==0.0) return value;
    double fraction=frexp(value,&exponent);
    uint64_t mantissa=(uint64_t)ldexp(fraction,53);
    __uint128_t numerator=(__uint128_t)mantissa*UINT64_C(1953125);
    int shift=53-exponent-9;
    if (shift>=128) return 0.0;
    __uint128_t whole=numerator>>shift;
    __uint128_t remainder=numerator-(whole<<shift);
    __uint128_t half=(__uint128_t)1<<(shift-1);
    if (remainder>half||(remainder==half&&(whole&1))) whole++;
    volatile double rounded=(double)(uint64_t)whole/1000000000.0;
    return rounded;
}
static int valid_slot(const NG2RingSlot *slot) {
    return isfinite(slot->icon_score)&&slot->icon_score>=0.0&&slot->icon_score<=1.000001
        &&(slot->word_present==0||slot->word_present==1)
        &&(!slot->word_present||(isfinite(slot->word_iou)&&slot->word_iou>=0.0&&slot->word_iou<=1.0
             &&isfinite(slot->word_coverage)&&slot->word_coverage>=0.0&&slot->word_coverage<=1.0));
}
static int target_slot(const NG2RingSlot *slot) {
    return slot->icon_score>=.88&&slot->word_present&&slot->word_iou>=.82&&slot->word_coverage>=.90;
}
static void round_slot(NG2RingSlot *slot) {
    slot->icon_score=ng2_ring_round9(slot->icon_score<1.0?slot->icon_score:1.0);
    if(slot->word_present) {
        slot->word_iou=ng2_ring_round9(slot->word_iou);
        slot->word_coverage=ng2_ring_round9(slot->word_coverage);
    }
    memset((unsigned char *)slot+offsetof(NG2RingSlot,non_target_id),0,
           sizeof(*slot)-offsetof(NG2RingSlot,non_target_id));
    slot->outcome=target_slot(slot)?NG2_RING_TARGET:
        slot->icon_score>=.80?NG2_RING_CANDIDATE:NG2_RING_UNKNOWN;
}
static int better_word(const NG2RingSlot *a,const NG2RingSlot *b) {
    if(target_slot(a)!=target_slot(b))return target_slot(a)>target_slot(b);
    if(a->word_iou!=b->word_iou)return a->word_iou>b->word_iou;
    if(a->word_coverage!=b->word_coverage)return a->word_coverage>b->word_coverage;
    return a->icon_score>b->icon_score;
}
int ng2_ring_aggregate(NG2RingResult *result) {
    if (!result) return NG2_RING_INVALID;
    result->status=NG2_RING_INVALID;
    result->outcome=NG2_RING_UNKNOWN;
    result->coverage=NG2_RING_COVERAGE_UNKNOWN;
    result->selected_row=-1;
    result->selected_partial=-1;
    result->reason=NG2_RING_NO_ROW;
    result->partial_safe_no_positive=0;
    memset(&result->certificate,0,sizeof(result->certificate));
    if(result->abi!=NG2_RING_ABI||result->size!=sizeof(*result)||fegetround()!=FE_TONEAREST
        ||result->row_count<0||result->row_count>NG2_RING_MAX_ROWS
        ||result->partial_count<0||result->partial_count>NG2_RING_MAX_PARTIAL)return NG2_RING_INVALID;
    for(int r=0;r<result->row_count;r++)for(int s=0;s<3;s++)
        if(!valid_slot(&result->rows[r].slots[s]))return NG2_RING_INVALID;
    for(int s=0;s<result->partial_count;s++)if(!valid_slot(&result->partial[s]))return NG2_RING_INVALID;
    double best_max=-1.0;
    for(int r=0;r<result->row_count;r++) {
        NG2RingRow *row=&result->rows[r];double maximum=0.0;
        row->word_slot=-1;
        for(int s=0;s<3;s++) {
            NG2RingSlot *slot=&row->slots[s];round_slot(slot);
            if(slot->icon_score>maximum)maximum=slot->icon_score;
            if(slot->icon_score>=.80&&slot->word_present&&(row->word_slot<0
                ||better_word(slot,&row->slots[row->word_slot])))row->word_slot=s;
        }
        row->outcome=row->word_slot>=0&&target_slot(&row->slots[row->word_slot])?
            NG2_RING_TARGET:maximum>=.80?NG2_RING_CANDIDATE:NG2_RING_UNKNOWN;
        row->reason=row->outcome==NG2_RING_TARGET?NG2_RING_ICON_AND_NAME:
            row->outcome==NG2_RING_CANDIDATE?NG2_RING_ICON_ONLY:NG2_RING_NO_TARGET_EVIDENCE;
        if(result->selected_row<0||row->outcome==NG2_RING_TARGET||maximum>best_max) {
            result->selected_row=r;best_max=maximum;
            result->outcome=row->outcome;result->reason=row->reason;
        }
        if(row->outcome==NG2_RING_TARGET)break;
    }
    for(int s=0;s<result->partial_count;s++) {
        NG2RingSlot *slot=&result->partial[s];round_slot(slot);
        if(result->outcome==NG2_RING_TARGET)continue;
        if(slot->outcome==NG2_RING_TARGET||slot->icon_score>best_max) {
            result->selected_partial=s;result->selected_row=-1;best_max=slot->icon_score;
            result->outcome=slot->outcome;
            result->reason=slot->outcome==NG2_RING_TARGET?NG2_RING_ICON_AND_NAME:
                slot->outcome==NG2_RING_CANDIDATE?NG2_RING_ICON_ONLY:NG2_RING_NO_TARGET_EVIDENCE;
        }
    }
    result->status=NG2_RING_OK;
    return NG2_RING_OK;
}
static int checkpoint(const NG2RingOptions *options,NG2RingResult *result) {
    result->checks++;
    if(options&&options->cancelled&&options->cancelled(options->context))return NG2_RING_CANCELLED;
    if(options&&options->now_ns) {
        uint64_t now=options->now_ns(options->context);
        if(now<result->started_ns)return NG2_RING_INVALID;
        result->finished_ns=now;
        if(options->deadline_ns&&now>=options->deadline_ns)return NG2_RING_DEADLINE;
    }
    return NG2_RING_OK;
}
static double probe_add(double a,double b){volatile double value=a+b;return value;}
static double probe_sub(double a,double b){volatile double value=a-b;return value;}
static double probe_mul(double a,double b){volatile double value=a*b;return value;}
static double probe_div(double a,double b){volatile double value=a/b;return value;}
static double probe_sqrt(double a){volatile double value=sqrt(a);return value;}
/* Every original match/outline count is bounded by its fixed sample count.
 * Replacing both counts by those maxima bounds each original binary64 score
 * by monotonic nonnegative operations, with the identical NCC calculation.
 * The extra 1e-12 margin and decimal round9 force boundary cases to exact C.
 * Pruning is permitted only when EVERY sprite/position stays below .80. */
static int candidate_probe(const unsigned char *rgba,int cx,int sy,const NG2RingOptions *options,
                           NG2RingResult *result,int *potential,double *upper,int box[4]) {
    *potential=0;*upper=0.0;int status;
    for(size_t s=0;s<sizeof(sprites)/sizeof(sprites[0]);s++) {
        const Sprite *sp=&sprites[s];double count=sp->count,dark=sp->dark_count;
        int y0=sy+24>0?sy+24:0,y1=sy+57<RING_HH-sp->height?sy+57:RING_HH-sp->height;
        int x0=cx-sp->width/2-8>0?cx-sp->width/2-8:0;
        int x1=cx-sp->width/2+8<RING_W-sp->width?cx-sp->width/2+8:RING_W-sp->width;
        for(int y=y0;y<=y1;y++) {
            if((status=checkpoint(options,result)))return status;
            for(int x=x0;x<=x1;x++) {
                int32_t total=0,square=0,cross=0,dot=0;
                uint16_t observed_sum[344];unsigned char observed_green[344];
                for(int k=0;k<sp->count;k++) {
                    const Bright *p=&sp->bright[k];size_t at=4*((size_t)(y+p->dy)*RING_W+x+p->dx);
                    int r=rgba[at],g=rgba[at+1],b=rgba[at+2],v=r+g+b;
                    observed_sum[k]=(uint16_t)v;observed_green[k]=(unsigned char)g;
                    dot+=r*p->r+g*p->g+b*p->b;
                    total+=v;square+=v*v;cross+=v*(p->r+p->g+p->b);
                }
                double product=probe_mul(probe_sub(square,probe_div((double)((int64_t)total*total),count)),sp->target_var);
                double norm=probe_sqrt(product>0.0?product:0.0);
                double shape=probe_div(probe_sub(cross,probe_div((double)((int64_t)total*sp->target_sum),count)),norm>9.0?norm:9.0);
                if(shape<0.0)shape=0.0;
                double value=probe_mul(probe_add(probe_div(probe_mul(.55,count),count),probe_mul(.45,shape)),
                                       probe_add(.80,probe_div(probe_mul(.20,dark),dark)));
                if(value>=.799999999) {
                    int outline=0,possible=0;
                    for(int k=0;k<sp->dark_count;k++) {
                        const Dark *p=&sp->dark[k];size_t at=4*((size_t)(y+p->dy)*RING_W+x+p->dx);
                        outline+=rgba[at]+rgba[at+1]+rgba[at+2]<144;
                    }
                    double gain=probe_div(dot,sp->energy);if(gain<.37)gain=.37;if(gain>1.3)gain=1.3;
                    double tolerance=probe_mul(3.0,probe_add(13.0,probe_mul(15.0,gain)));
                    /* Triangle inequality: an RGB match necessarily satisfies
                     * both total-channel and each individual-channel error.
                     * Terms stay below 1024; <16 rounded operations have total
                     * absolute error <2e-12, covered conservatively by 1e-9.
                     * Thus these tests only overcount possible exact matches. */
                    double limit=probe_add(tolerance,1e-9);
                    for(int k=0;k<sp->count;k++) {
                        const Bright *p=&sp->bright[k];
                        double total_error=fabs(probe_sub(observed_sum[k],probe_mul(gain,p->r+p->g+p->b)));
                        double green_error=fabs(probe_sub(observed_green[k],probe_mul(gain,p->g)));
                        possible+=total_error<limit&&green_error<limit;
                    }
                    value=probe_mul(probe_add(probe_div(probe_mul(.55,possible),count),probe_mul(.45,shape)),
                                    probe_add(.80,probe_div(probe_mul(.20,outline),dark)));
                }
                value=probe_add(value,1e-12);if(value>1.0)value=1.0;
                value=ng2_ring_round9(value);
                if(value>*upper) {
                    *upper=value;box[0]=x;box[1]=y;box[2]=sp->width;box[3]=sp->height;
                }
                if(value>=.80){*potential=1;*upper=1.0;return NG2_RING_OK;}
            }
        }
    }
    return checkpoint(options,result);
}
#if NG2_HAS_RING_BANK
static int binary_slot_word(const RingObservation *observation,int cx,int sy,
                            const NG2RingOptions *options,NG2RingResult *result,NG2RingSlot *slot);
#endif
static int score_slot(const unsigned char *rgba,const RingObservation *observation,
                      int cx,int sy,int index,const NG2RingOptions *options,
                      NG2RingResult *result,NG2RingSlot *slot) {
    RingWord word;int box[4]={cx-16,sy+24,33,28};double score=0.0,upper=0.0;int status,potential=1;
    if((status=checkpoint(options,result)))return status;
    if(options&&options->fast) {
        status=candidate_probe(rgba,cx,sy,options,result,&potential,&upper,box);
        if(status)return status;
    }
    if(potential) {
        status=ring_icon(rgba,RING_RGBA,cx,sy,options&&options->mode==1?1:0,NULL,&score,box);
        if(status)return NG2_RING_KERNEL;
        if(!(options&&options->fast))upper=score;
    } else score=upper;
    if((status=checkpoint(options,result)))return status;
    slot->cx=cx;slot->sy=sy;slot->slot=index;slot->icon_score=score;
    slot->icon_score_exact=(uint32_t)potential;slot->icon_upper_bound=upper;
    for(int k=0;k<4;k++)slot->icon_box[k]=box[k];
#if NG2_HAS_RING_BANK
    if(options&&options->mode==NG2_RING_MODE_TARGET_ONLY)
        return binary_slot_word(observation,cx,sy,options,result,slot);
#endif
    /* Raw word work is intentionally unconditional, even below .80 icon.
     * A geometrically empty name window remains an explicit null. */
    status=ring_word(observation,cx,sy,index,&word);
    if(status<0)return NG2_RING_KERNEL;
    if(!status) {
        slot->word_present=1;slot->word_iou=word.iou;slot->word_coverage=word.coverage;
        for(int k=0;k<4;k++)slot->word_box[k]=word.box[k];
    }
    return checkpoint(options,result);
}
typedef struct { int count,cx,sy,x0,y0,x1,y1; } NG2RingSign;
static int partial_hud(int x0,int y0,int x1,int y1) {
    static const int areas[][4]={{0,0,143,140},{663,0,896,80},{717,315,896,414},
        {405,321,485,414},{0,380,896,414},{429,0,465,45},{866,45,896,290}};
    for(size_t i=0;i<sizeof(areas)/sizeof(areas[0]);i++)
        if(x0<areas[i][2]&&areas[i][0]<x1&&y0<areas[i][3]&&areas[i][1]<y1)return 1;
    return 0;
}
static int partial_exists(const NG2RingResult *result,int cx,int sy) {
    for(int r=0;r<result->row_count;r++)for(int s=0;s<3;s++)
        if(result->rows[r].slots[s].cx==cx&&result->rows[r].slots[s].sy==sy)return 1;
    for(int s=0;s<result->partial_count;s++)
        if(result->partial[s].cx==cx&&result->partial[s].sy==sy)return 1;
    return 0;
}
/* A nonempty icon below an independently observed SHOP sign can
 * locate one item even when adjacent goods are clipped. This adapter grants
 * positive evidence only; its count never proves complete shop coverage. */
static int partial_slots(const unsigned char *rgba,const RingObservation *observation,
                         const NG2RingOptions *options,NG2RingResult *result,
                         NG2RingSign observed_signs[12],int *sign_count) {
    const size_t pixels=(size_t)RING_W*RING_HH;
    unsigned char *signs=calloc(pixels,1);
    uint32_t *queue=malloc(pixels*sizeof(*queue));
    NG2RingSign top[12];int length=0,components=0,status=NG2_RING_OK;
    if(!signs||!queue){free(signs);free(queue);return NG2_RING_ALLOCATION;}
    for(int y=0;y<RING_HH;y++) {
        if((status=checkpoint(options,result)))goto done;
        for(int x=0;x<RING_W;x++) {
            size_t at=(size_t)y*RING_W+x;int r=rgba[4*at],g=rgba[4*at+1],b=rgba[4*at+2];
            int limit=(r*1050+999)/1000;if(limit>255)limit=255;
            if(r>57&&g>r*865/1000&&g<limit&&b<(g*240+999)/1000
                &&!partial_hud(x,y,x+1,y+1))signs[at]=1;
        }
    }
    for(size_t at=0;at<pixels;at++) {
        if(!(at%1024)&&(status=checkpoint(options,result)))goto done;
        if(!signs[at])continue;
        size_t head=0,tail=0;int count=0,x0=RING_W,y0=RING_HH,x1=0,y1=0;
        signs[at]=0;queue[tail++]=(uint32_t)at;
        while(head<tail) {
            if(!(head%1024)&&(status=checkpoint(options,result)))goto done;
            uint32_t position=queue[head++];int x=(int)(position%RING_W),y=(int)(position/RING_W);
            count++;if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y;
            int neighbours[4]={x?(int)position-1:-1,x+1<RING_W?(int)position+1:-1,
                y?(int)position-RING_W:-1,y+1<RING_HH?(int)position+RING_W:-1};
            for(int k=0;k<4;k++)if(neighbours[k]>=0&&signs[neighbours[k]]) {
                signs[neighbours[k]]=0;queue[tail++]=(uint32_t)neighbours[k];
            }
        }
        if(count<150||x1-x0+1<18||x1-x0+1>48||y1-y0+1<16||y1-y0+1>40)continue;
        if(++components>12){status=NG2_RING_KERNEL;goto done;}
        NG2RingSign value={count,(x0+x1+1)/2,(y0+y1+1)/2,x0,y0,x1+1,y1+1};int where=0;
        while(where<length&&(top[where].count>value.count
            ||(top[where].count==value.count&&(top[where].cx>value.cx
                ||(top[where].cx==value.cx&&top[where].sy>=value.sy)))))where++;
        if(where>=12)continue;
        if(length<12)length++;
        for(int j=length-1;j>where;j--)top[j]=top[j-1];
        top[where]=value;
    }
    *sign_count=length;memcpy(observed_signs,top,(size_t)length*sizeof(*top));
    for(int i=0;i<length;i++)for(int offset=-2;offset<=2;offset++) {
        int cx=top[i].cx+36*offset,sy=top[i].sy;
        if(cx<18||cx>=878||sy<0||sy+66>=RING_HH
            ||partial_hud(cx-17,sy+24,cx+18,sy+66)||partial_exists(result,cx,sy))continue;
        int bright=0;
        for(int y=sy+24;y<sy+66;y++)for(int x=cx-17;x<cx+18;x++) {
            size_t at=4*((size_t)y*RING_W+x);
            uint32_t luma=(UINT32_C(19595)*rgba[at]+UINT32_C(38470)*rgba[at+1]
                +UINT32_C(7471)*rgba[at+2]+UINT32_C(32768))>>16;
            bright+=luma>55;
        }
        if(bright<24)continue;
        if(result->partial_count>=NG2_RING_MAX_PARTIAL) {status=NG2_RING_KERNEL;goto done;}
        NG2RingSlot *slot=&result->partial[result->partial_count++];
        if((status=score_slot(rgba,observation,cx,sy,0,options,result,slot)))goto done;
    }
done:
    free(signs);free(queue);return status;
}
#if NG2_HAS_RING_BANK
static double bank_add(double a,double b){volatile double value=a+b;return value;}
static double bank_sub(double a,double b){volatile double value=a-b;return value;}
static double bank_mul(double a,double b){volatile double value=a*b;return value;}
static double bank_div(double a,double b){volatile double value=a/b;return value;}
static double bank_sqrt(double a){volatile double value=sqrt(a);return value;}
static int bank_min(int a,int b){return a<b?a:b;}
static int bank_max(int a,int b){return a>b?a:b;}
static unsigned bank_pop(uint64_t bits){return (unsigned)__builtin_popcountll(bits);}
typedef struct {uint64_t gold[RING_HH][RING_WORDS],dark[RING_HH][RING_WORDS];} NG2ContainerMasks;
static void bank_window(const uint64_t row[RING_WORDS],int x,int width,uint64_t bits[2]) {
    int word=x/64,shift=x%64;
    bits[0]=row[word]>>shift;bits[1]=word+1<RING_WORDS?row[word+1]>>shift:0;
    if(shift) {
        if(word+1<RING_WORDS)bits[0]|=row[word+1]<<(64-shift);
        if(word+2<RING_WORDS)bits[1]|=row[word+2]<<(64-shift);
    }
    if(width<=64) {if(width<64)bits[0]&=(UINT64_C(1)<<width)-1;bits[1]=0;}
    else bits[1]&=(UINT64_C(1)<<(width-64))-1;
}
static int bank_word(const RingObservation *observation,int cx,int sy,int width,int height,int ink,
                     const uint64_t (*reference)[2],int full_name,const NG2RingOptions *options,NG2RingResult *result,
                     double *best_iou,double *best_coverage,int32_t box[4]) {
    if(width<1||width>96||height<1||height>12||ink<1||!reference)return NG2_RING_KERNEL;
    int x0=bank_max(0,cx-width/2-18),x1=bank_min(RING_W-width,cx-width/2+18);
    int y0=bank_max(0,sy-20),y1=bank_min(RING_HH-height,sy+35),found=0,status;
    *best_iou=0.0;*best_coverage=0.0;
    for(int y=y0;y<=y1;y++) {
        if((status=checkpoint(options,result)))return status;
        for(int x=x0;x<=x1;x++) {
            if(full_name) {
                int clean=x>=8&&x+width+8<=RING_W;
                if(clean&&partial_hud(x-8,y,x+width+8,y+height))clean=0;
                for(int dy=0;clean&&dy<height;dy++)for(int margin=1;margin<=8;margin++) {
                    int left=x-margin,right=x+width-1+margin;
                    if(((observation->white[y+dy][left/64]>>(left%64))&1)
                       ||((observation->white[y+dy][right/64]>>(right%64))&1)){clean=0;break;}
                }
                if(!clean)continue;
            }
            unsigned intersection=0,total_union=0;
            for(int dy=0;dy<height;dy++) {
                uint64_t observed[2];bank_window(observation->white[y+dy],x,width,observed);
                for(int k=0;k<2;k++) {
                    intersection+=bank_pop(reference[dy][k]&observed[k]);
                    total_union+=bank_pop(reference[dy][k]|observed[k]);
                }
            }
            double iou=bank_div(intersection,total_union?total_union:1),coverage=bank_div(intersection,ink);
            if(!found||iou>*best_iou||(iou==*best_iou&&coverage>*best_coverage)) {
                found=1;*best_iou=iou;*best_coverage=coverage;
                box[0]=x;box[1]=y;box[2]=width;box[3]=height;
            }
        }
    }
    *best_iou=ng2_ring_round9(*best_iou);*best_coverage=ng2_ring_round9(*best_coverage);
    return NG2_RING_OK;
}
/* Same bounded RGB/shape/outline arithmetic as the original numeric scorer,
 * with a separate finite bank and larger proven int32 moment bounds. */
static int bank_icon(const unsigned char *rgba,int cx,int sy,const R94BankIcon *sp,
                     const NG2RingOptions *options,NG2RingResult *result,
                     double *best,double *foreground,int32_t box[4],int merchant) {
    _Static_assert(INT64_C(1296)*765*765<=INT32_MAX,"bank moment bounds");
    int count=sp->count,dark_count=sp->dark_count,status;
    if(count<1||count>1296||dark_count<1||dark_count>1296||sp->width<1||sp->width>36
       ||sp->height<1||sp->height>36||sp->energy<=0||!sp->bright||!sp->dark
       ||!isfinite(sp->target_var)||sp->target_var<=0.0)return NG2_RING_KERNEL;
    double dc=count,dd=dark_count;*best=0.0;*foreground=0.0;
    int y0=merchant==1?sy-39:merchant==2?sy:sy+24;
    int y1=merchant==1?sy-33:merchant==2?sy:sy+57,radius=merchant==1?3:merchant==2?0:8;
    for(int y=bank_max(0,y0);y<=bank_min(RING_HH-sp->height,y1);y++) {
        if((status=checkpoint(options,result)))return status;
        for(int x=bank_max(0,cx-sp->width/2-radius);x<=bank_min(RING_W-sp->width,cx-sp->width/2+radius);x++) {
            unsigned char observed[1296][3];int32_t dot=0,total=0,square=0,cross=0;
            for(int k=0;k<count;k++) {
                const R94BankBright *p=&sp->bright[k];
                if(p->dx>=sp->width||p->dy>=sp->height)return NG2_RING_KERNEL;
                size_t at=4*((size_t)(y+p->dy)*RING_W+x+p->dx);
                int a=rgba[at],b=rgba[at+1],c=rgba[at+2],v=a+b+c;
                observed[k][0]=(unsigned char)a;observed[k][1]=(unsigned char)b;observed[k][2]=(unsigned char)c;
                dot+=a*p->r+b*p->g+c*p->b;total+=v;square+=v*v;cross+=v*(p->r+p->g+p->b);
            }
            double product=bank_mul(bank_sub(square,bank_div((double)((int64_t)total*total),dc)),sp->target_var);
            double norm=bank_sqrt(product>0.0?product:0.0);
            double shape=bank_div(bank_sub(cross,bank_div((double)((int64_t)total*sp->target_sum),dc)),norm>9.0?norm:9.0);
            if(shape<0.0)shape=0.0;
            double upper=bank_mul(bank_add(bank_div(bank_mul(.55,dc),dc),bank_mul(.45,shape)),
                                  bank_add(.80,bank_div(bank_mul(.20,dd),dd)));
            if(merchant!=1&&upper<=*best)continue;
            double gain=bank_div(dot,sp->energy);if(gain<.37)gain=.37;if(gain>1.3)gain=1.3;
            double tolerance=bank_mul(3.0,bank_add(13.0,bank_mul(15.0,gain))),scaled[256];
            for(int k=0;k<256;k++)scaled[k]=bank_mul(gain,k);
            int matches=0,outline=0;
            for(int k=0;k<count;k++) {
                const R94BankBright *p=&sp->bright[k];
                double values[3]={fabs(bank_sub(observed[k][0],scaled[p->r])),
                    fabs(bank_sub(observed[k][1],scaled[p->g])),fabs(bank_sub(observed[k][2],scaled[p->b]))};
                double error=0.0,correction=0.0;
                for(int channel=0;channel<3;channel++) {
                    double v=values[channel],next=bank_add(error,v);
                    if(options&&options->mode==1)correction=bank_add(correction,fabs(error)>=fabs(v)?
                        bank_add(bank_sub(error,next),v):bank_add(bank_sub(v,next),error));
                    error=next;
                }
                if(options&&options->mode==1&&correction!=0.0)error=bank_add(error,correction);
                matches+=error<tolerance;
            }
            for(int k=0;k<dark_count;k++) {
                const R94BankDark *p=&sp->dark[k];
                if(p->dx>=sp->width||p->dy>=sp->height)return NG2_RING_KERNEL;
                size_t at=4*((size_t)(y+p->dy)*RING_W+x+p->dx);
                outline+=rgba[at]+rgba[at+1]+rgba[at+2]<144;
            }
            double score=bank_mul(bank_add(bank_div(bank_mul(.55,matches),dc),bank_mul(.45,shape)),
                                  bank_add(.80,bank_div(bank_mul(.20,outline),dd)));
            double fg=bank_div(matches,dc),value=merchant==1?shape:score;
            int qualifies=fg>=.95&&value>=.94,old_qualifies=*foreground>=.95&&*best>=.94;
            if((merchant==1&&qualifies!=old_qualifies)?qualifies:value>*best) {
                *best=value;*foreground=fg;
                box[0]=x;box[1]=y;box[2]=sp->width;box[3]=sp->height;
            }
        }
    }
    *best=ng2_ring_round9(*best<1.0?*best:1.0);*foreground=ng2_ring_round9(*foreground);
    return checkpoint(options,result);
}
static int container_masks(const unsigned char *rgba,const NG2RingOptions *options,
                           NG2RingResult *result,NG2ContainerMasks *out) {
    memset(out,0,sizeof(*out));int status;
    for(int y=0;y<RING_HH;y++) {
        if((status=checkpoint(options,result)))return status;
        for(int x=0;x<RING_W;x++) {
            const unsigned char *p=rgba+4*((size_t)y*RING_W+x);int r=p[0],g=p[1],b=p[2];
            if(r>85&&g>45&&2*b<g&&100*g>=50*r&&100*g<=110*r)out->gold[y][x/64]|=UINT64_C(1)<<(x%64);
            if(r<40&&g<40&&b<40)out->dark[y][x/64]|=UINT64_C(1)<<(x%64);
        }
    }
    return NG2_RING_OK;
}
static int container_structure(const NG2ContainerMasks *observed,const R94ContainerShape *shape,
                               int x,int y,double scores[4]) {
    if(!shape||shape->width<1||shape->width>36||shape->height<1||shape->height>36
       ||!shape->gold_ink||!shape->dark_ink||!shape->gold_rows||!shape->dark_rows)return 0;
    unsigned intersection[2]={0},total_union[2]={0};
    for(int dy=0;dy<shape->height;dy++) {
        uint64_t gold[2],dark[2];
        bank_window(observed->gold[y+dy],x,shape->width,gold);
        bank_window(observed->dark[y+dy],x,shape->width,dark);
        for(int k=0;k<2;k++) {
            intersection[0]+=bank_pop(gold[k]&shape->gold_rows[dy][k]);
            total_union[0]+=bank_pop(gold[k]|shape->gold_rows[dy][k]);
            intersection[1]+=bank_pop(dark[k]&shape->dark_rows[dy][k]);
            total_union[1]+=bank_pop(dark[k]|shape->dark_rows[dy][k]);
        }
    }
    scores[0]=ng2_ring_round9(bank_div(intersection[0],total_union[0]?total_union[0]:1));
    scores[1]=ng2_ring_round9(bank_div(intersection[0],shape->gold_ink));
    scores[2]=ng2_ring_round9(bank_div(intersection[1],total_union[1]?total_union[1]:1));
    scores[3]=ng2_ring_round9(bank_div(intersection[1],shape->dark_ink));
    return scores[0]>=.94&&scores[1]>=.95&&scores[2]>=.94&&scores[3]>=.95;
}
static int container_slot(const unsigned char *rgba,const NG2ContainerMasks *observed,
                          const R94BankEntry *item,const NG2RingOptions *options,
                          NG2RingResult *result,NG2RingSlot *slot) {
    const R94ContainerShape *shape=item->container_shape;int status;
    if(!shape)return NG2_RING_KERNEL;
    for(unsigned icon=0;icon<item->icon_count;icon++) {
        const R94BankIcon *sp=&item->icons[icon];
        if(sp->width!=shape->width||sp->height!=shape->height)return NG2_RING_KERNEL;
        for(int y=bank_max(0,slot->sy+24);y<=bank_min(RING_HH-sp->height,slot->sy+57);y++) {
            if((status=checkpoint(options,result)))return status;
            for(int x=bank_max(0,slot->cx-sp->width/2-8);x<=bank_min(RING_W-sp->width,slot->cx-sp->width/2+8);x++) {
                double metrics[4],score,foreground;int32_t box[4]={0};
                if(!container_structure(observed,shape,x,y,metrics))continue;
                status=bank_icon(rgba,x+sp->width/2,y,sp,options,result,&score,&foreground,box,2);
                if(status)return status;
                if(score<.94)continue;
                if(slot->non_target_id||(slot->ignored_container_id&&slot->ignored_container_id!=item->id)) {
                    slot->non_target_conflict=1;slot->non_target_id=0;slot->ignored_container_id=0;
                    slot->outcome=NG2_RING_UNKNOWN;slot->kind=0;return NG2_RING_OK;
                }
                if(slot->ignored_container_id&&score<=slot->ignored_icon_score)continue;
                slot->ignored_container_id=item->id;slot->ignored_icon_score=score;slot->kind=R94_BANK_IGNORED_CONTAINER;
                slot->ignored_gold_iou=metrics[0];slot->ignored_gold_coverage=metrics[1];
                slot->ignored_dark_iou=metrics[2];slot->ignored_dark_coverage=metrics[3];
                memcpy(slot->ignored_icon_box,box,sizeof(box));slot->outcome=NG2_RING_IGNORED_CONTAINER;
            }
        }
    }
    return NG2_RING_OK;
}
static int bank_slot(const unsigned char *rgba,const RingObservation *observation,
                     const NG2ContainerMasks *containers,const NG2RingOptions *options,
                     NG2RingResult *result,NG2RingSlot *slot) {
    _Static_assert(R94_BANK_COUNT>0&&R94_BANK_COUNT<=16,"finite exposed-item bank");
    if(slot->outcome==NG2_RING_TARGET||slot->outcome==NG2_RING_CANDIDATE)return NG2_RING_OK;
    for(size_t entry=0;entry<R94_BANK_COUNT;entry++) {
        const R94BankEntry *item=&r94_bank_entries[entry];
        if(item->kind==R94_BANK_IGNORED_CONTAINER) {
            int status=container_slot(rgba,containers,item,options,result,slot);
            if(status)return status;
            if(slot->non_target_conflict)return NG2_RING_OK;
            continue;
        }
        if(item->kind!=R94_BANK_NONTARGET)return NG2_RING_KERNEL;
        double iou=0.0,coverage=0.0;int32_t name_box[4]={0};
        int status=bank_word(observation,slot->cx,slot->sy,item->word_width,item->word_height,
            item->word_ink,item->word_rows,1,options,result,&iou,&coverage,name_box);
        if(status)return status;
        if(iou<.94||coverage<.95)continue;
        double best=0.0;int32_t best_box[4]={0};
        for(unsigned icon=0;icon<item->icon_count;icon++) {
            double score,foreground;int32_t box[4]={0};
            status=bank_icon(rgba,slot->cx,slot->sy,&item->icons[icon],options,result,&score,&foreground,box,0);
            if(status)return status;
            if(score>best){best=score;memcpy(best_box,box,sizeof(box));}
        }
        if(best<.94)continue;
        if((slot->non_target_id&&slot->non_target_id!=item->id)||slot->ignored_container_id) {
            slot->non_target_conflict=1;slot->non_target_id=0;slot->ignored_container_id=0;
            slot->outcome=NG2_RING_UNKNOWN;slot->kind=0;
            return NG2_RING_OK;
        }
        slot->non_target_id=item->id;slot->non_target_icon_score=best;
        slot->non_target_name_iou=iou;slot->non_target_name_coverage=coverage;
        memcpy(slot->non_target_icon_box,best_box,sizeof(best_box));
        memcpy(slot->non_target_name_box,name_box,sizeof(name_box));
        slot->outcome=NG2_RING_NON_TARGET;slot->kind=R94_BANK_NONTARGET;
    }
    return NG2_RING_OK;
}
static int box_valid(const int32_t box[4]) {
    return box[0]>=0&&box[1]>=0&&box[2]>0&&box[3]>0
        &&box[2]<=RING_W&&box[3]<=RING_HH&&box[0]<=RING_W-box[2]&&box[1]<=RING_HH-box[3]
        &&!partial_hud(box[0],box[1],box[0]+box[2],box[1]+box[3]);
}
static int box_contains(const int32_t box[4],int x,int y) {
    return box[2]>0&&box[3]>0&&x>=box[0]&&y>=box[1]&&x<box[0]+box[2]&&y<box[1]+box[3];
}
static int glyph_auth(const unsigned char *rgba,int cx,int sy,const NG2RingOptions *options,
                      NG2RingResult *result,double *best_iou,double *best_cov,int32_t box[4]) {
    *best_iou=0.0;*best_cov=0.0;int status;
    for(int phase=0;phase<R94_SHOP_GLYPH_COUNT;phase++) {
        const R94CoverageGlyph *glyph=&r94_shop_glyphs[phase];
        for(int y=sy-6;y<=sy;y++) {
            if((status=checkpoint(options,result)))return status;
            for(int x=cx-15;x<=cx-9;x++) {
                int32_t candidate[4]={x,y,glyph->width,glyph->height};
                if(!box_valid(candidate))continue;
                unsigned intersection=0,total_union=0;
                for(int dy=0;dy<glyph->height;dy++)for(int dx=0;dx<glyph->width;dx++) {
                    size_t at=4*((size_t)(y+dy)*RING_W+x+dx);
                    int observed=rgba[at]<60&&rgba[at+1]<60&&rgba[at+2]<60;
                    int reference=(int)((glyph->rows[dy][dx/64]>>(dx%64))&1);
                    intersection+=observed&&reference;total_union+=observed||reference;
                }
                double iou=ng2_ring_round9(bank_div(intersection,total_union?total_union:1));
                double coverage=ng2_ring_round9(bank_div(intersection,glyph->ink));
                int qualifies=iou>=.94&&coverage>=.95,old=*best_iou>=.94&&*best_cov>=.95;
                if((qualifies!=old)?qualifies:(iou>*best_iou||(iou==*best_iou&&coverage>*best_cov))) {
                    *best_iou=iou;*best_cov=coverage;memcpy(box,candidate,sizeof(candidate));
                }
            }
        }
    }
    return NG2_RING_OK;
}
static int board_pixel(const unsigned char *p) {
    int r=p[0],g=p[1],b=p[2],high=(r*1050+999)/1000;if(high>255)high=255;
    int sign=r>57&&g>r*865/1000&&g<high&&b<(g*240+999)/1000;
    int gold=r>52&&1000*g>685*r&&100*g<92*r&&100*b>7*g&&100*b<58*g;
    return sign||gold;
}
/* Fixed before the 326 frame evaluation: the common price-row anchor locates
 * a fully observed 36x40 search ROI, not the truncated yellow seed's center.
 * Only existing GOLD|SIGN predicates reveal the physical exterior. */
static int board_frame(const unsigned char *rgba,const NG2RingSign *seed,int cx,int sy,
                       NG2RingSign *physical,int32_t edges[4],int32_t corners[4]) {
    int32_t roi[4]={cx-18,sy-20,36,40};
    if(!box_valid(roi)||seed->count<150||seed->x1-seed->x0<18||seed->x1-seed->x0>48
       ||seed->y1-seed->y0<16||seed->y1-seed->y0>40||abs(seed->cx-cx)>2||abs(seed->sy-sy)>10
       ||seed->x0<roi[0]||seed->x1>roi[0]+36||seed->y0<roi[1]||seed->y1>roi[1]+40)return 0;
    unsigned char mask[40][36];int x0=36,y0=40,x1=-1,y1=-1;
    for(int y=0;y<40;y++)for(int x=0;x<36;x++) {
        mask[y][x]=(unsigned char)board_pixel(rgba+4*((size_t)(roi[1]+y)*RING_W+roi[0]+x));
        if(mask[y][x]){if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y;}
    }
    int width=x1-x0+1,height=y1-y0+1;
    if(width<18||width>48||height<16||height>40)return 0;
    int pcx=(roi[0]+x0+roi[0]+x1+1)/2,pcy=(roi[1]+y0+roi[1]+y1+1)/2;
    if(abs(pcx-cx)>2||abs(pcy-sy)>2)return 0;
    memset(edges,0,4*sizeof(*edges));memset(corners,0,4*sizeof(*corners));
    for(int x=x0;x<=x1;x++){edges[0]+=mask[y0][x];edges[1]+=mask[y1][x];}
    for(int y=y0;y<=y1;y++){edges[2]+=mask[y][x0];edges[3]+=mask[y][x1];}
    for(int dy=0;dy<2;dy++)for(int dx=0;dx<2;dx++) {
        corners[0]+=mask[y0+dy][x0+dx];corners[1]+=mask[y0+dy][x1-1+dx];
        corners[2]+=mask[y1-1+dy][x0+dx];corners[3]+=mask[y1-1+dy][x1-1+dx];
    }
    if(4*edges[0]<3*width||4*edges[1]<3*width||4*edges[2]<3*height||4*edges[3]<3*height)return 0;
    for(int corner=0;corner<4;corner++)if(!corners[corner])return 0;
    physical->count=seed->count;physical->cx=pcx;physical->sy=pcy;
    physical->x0=roi[0]+x0;physical->x1=roi[0]+x1+1;physical->y0=roi[1]+y0;physical->y1=roi[1]+y1+1;
    return 1;
}
static int board_exterior(const unsigned char *rgba,const NG2RingSign *board,const int32_t merchant[4]) {
    int32_t exterior[4]={board->x0-1,board->y0-1,board->x1-board->x0+2,board->y1-board->y0+2};
    if(!box_valid(exterior))return -1;
    int count=0;
    for(int y=board->y0-1;y<=board->y1;y++)for(int x=board->x0-1;x<=board->x1;x++) {
        if(x!=board->x0-1&&x!=board->x1&&y!=board->y0-1&&y!=board->y1)continue;
        if(box_contains(merchant,x,y))continue;
        count+=board_pixel(rgba+4*((size_t)y*RING_W+x));
    }
    return count;
}
/* These material predicates deliberately retain the exact existing
 * NG2Perception.c ng2_material_sample/floor formulas and 90% visibility bound.
 * They report raw evidence only and do not relabel any Scene cell. */
static NG2RingEndcap material_sample(const unsigned char *rgba,int left,int top,int width,int height) {
    NG2RingEndcap out={0};unsigned hist[3][256]={{0}},sum[3]={0},squares[3]={0};
    int med[3],count=width*height;out.count=count;
    out.box[0]=left;out.box[1]=top;out.box[2]=width;out.box[3]=height;
    for(int y=top;y<top+height;y++)for(int x=left;x<left+width;x++) {
        const unsigned char *p=rgba+4*((size_t)y*RING_W+x);
        out.black_count+=p[0]<6||p[1]<3;
        uint32_t luma=(UINT32_C(19595)*p[0]+UINT32_C(38470)*p[1]+UINT32_C(7471)*p[2]+32768)>>16;
        out.bright_count+=luma>55;
        for(int c=0;c<3;c++){int v=p[c];hist[c][v]++;sum[c]+=(unsigned)v;squares[c]+=(unsigned)(v*v);}
    }
    for(int c=0;c<3;c++) {
        unsigned total=0;int v;
        for(v=0;v<256;v++){total+=hist[c][v];if(total>(unsigned)count/2)break;}
        med[c]=v;
        if((uint64_t)count*squares[c]-(uint64_t)sum[c]*sum[c]>=(uint64_t)4*count*count)out.spread=1;
    }
    out.r=med[0];out.g=med[1];out.b=med[2];return out;
}
static int material_floor(NG2RingEndcap a) {
    int r=a.r,g=a.g,b=a.b;
    return r>=6&&g>=3&&a.spread&&((r<=38&&44*r<=100*b&&100*b<=90*r&&40*r<=100*g&&100*g<=90*r
        &&abs(g-b)<=fmax(2,.18*r))||(38<r&&r<=52&&55*r<=100*b+155&&100*b<=70*r
        &&45*r<=100*g&&100*g<=68*r&&abs(g-b)<=fmax(2,.12*r)));
}
static int white_count(const RingObservation *observation,int cx,int sy,int offset) {
    int count=0;
    for(int y=sy+69+offset;y<sy+78+offset;y++)for(int x=cx-11;x<cx+12;x++)
        count+=(int)((observation->white[y][x/64]>>(x%64))&1);
    return count;
}
static int endcap_witness(const unsigned char *rgba,const RingObservation *observation,
                          int cx,int sy,NG2RingEndcap *out) {
    int32_t box[4]={cx-12,sy+36,25,25},price[4]={cx-11,sy+69,23,20};
    if(!box_valid(box)||!box_valid(price))return 0;
    *out=material_sample(rgba,box[0],box[1],25,25);
    out->floor_full=material_floor(*out);
    out->floor_upper=material_floor(material_sample(rgba,box[0],box[1],25,12));
    out->floor_lower=material_floor(material_sample(rgba,box[0],box[1]+12,25,13));
    for(int k=0;k<12;k++){int count=white_count(observation,cx,sy,k);if(count>out->price_ink_count)out->price_ink_count=count;}
    return out->floor_full&&out->floor_upper&&out->floor_lower
        &&100*(out->count-out->black_count)>=90*out->count&&out->bright_count<24&&out->price_ink_count<18;
}
static int price_white(const RingObservation *observation,const NG2RingCoverage *out,int x,int y) {
    for(int s=0;s<3;s++)if(box_contains(out->item_boxes[s],x,y))return 0;
    return (int)((observation->white[y][x/64]>>(x%64))&1);
}
static void price_witness(const RingObservation *observation,const NG2RingRow *row,NG2RingCoverage *out) {
    int left=row->left,sy=row->sy;
    int last=-1000,start=-1,x0=left-54,x1=left+126,baseline=0;
    int y_end=sy+(out->ignored_containers?91:89);
    for(int k=0;k<12;k++) {
        int all=1;for(int s=0;s<3;s++)if(row->slots[s].kind!=R94_BANK_IGNORED_CONTAINER)
            all&=white_count(observation,left+36*s,sy,k)>=18;
        if(all){baseline=1;break;}
    }
    for(int x=x0;x<=x1;x++) {
        int ink=0;
        if(x<x1)for(int y=sy+69;y<y_end;y++)ink|=price_white(observation,out,x,y);
        if(ink) {if(start<0)start=x;last=x;}
        if(start>=0&&((!ink&&x-last>3)||x==x1)) {
            int matched=-1,y0=RING_HH,y1=0;
            for(int y=sy+69;y<y_end;y++)for(int xx=start;xx<=last;xx++)
                if(price_white(observation,out,xx,y)){if(y<y0)y0=y;if(y>y1)y1=y;}
            out->observed_prices++;
            for(int s=0;s<3;s++)if(start>=left+36*s-11&&last<left+36*s+12)matched=s;
            if(matched<0||out->price_boxes[matched][2]>0)out->unmatched_prices++;
            else {
                int32_t box[4]={start,y0,last-start+1,y1-y0+1};
                memcpy(out->price_boxes[matched],box,sizeof(box));
                if(row->slots[matched].kind==R94_BANK_IGNORED_CONTAINER) {
                    int count=0,perimeter=0,cx=left+36*matched;
                    for(int y=sy+82;y<=sy+90;y++)for(int xx=cx-11;xx<cx+12;xx++) {
                        int value=price_white(observation,out,xx,y);
                        count+=value;if(y==sy+82||y==sy+90)perimeter+=value;
                    }
                    if(y0<sy+83||y1>=sy+90||count<18||perimeter)out->unmatched_prices++;
                } else if(y0<sy+69||y1>=sy+89)out->unmatched_prices++;
            }
            start=-1;
        }
    }
    if(!baseline)out->unmatched_prices++;
}
static void item_witness(const unsigned char *rgba,const NG2RingRow *row,NG2RingCoverage *out) {
    unsigned char mask[180*67]={0};uint16_t queue[180*67];int height=out->strip_box[3];
    int prefix[181*68]={0};
    for(int s=0;s<3;s++) {
        int cx=row->left+36*s,count=0;
        for(int y=row->sy+24;y<row->sy+66;y++)for(int x=cx-18;x<cx+18;x++) {
            const unsigned char *p=rgba+4*((size_t)y*RING_W+x);
            count+=((19595u*p[0]+38470u*p[1]+7471u*p[2]+32768u)>>16)>55;
        }
        out->observed_items+=count>=24;
    }
    for(int dy=0;dy<height;dy++)for(int dx=0;dx<180;dx++) {
        int x=out->strip_box[0]+dx,y=out->strip_box[1]+dy,known=0;
        for(int s=0;s<3;s++)known|=box_contains(out->item_boxes[s],x,y)
            ||box_contains(out->name_boxes[s],x,y)||box_contains(out->price_boxes[s],x,y);
        if(known)continue;
        const unsigned char *p=rgba+4*((size_t)y*RING_W+x);
        if(((19595u*p[0]+38470u*p[1]+7471u*p[2]+32768u)>>16)>55)mask[dy*180+dx]=1;
    }
    for(int y=0;y<height;y++) {
        int row_total=0;
        for(int x=0;x<180;x++) {
            row_total+=mask[y*180+x];
            prefix[(y+1)*181+x+1]=prefix[y*181+x+1]+row_total;
        }
    }
    int local_item=0;
    /* The existing 35x42 / 24 bright-pixel item-presence contract also catches
     * disconnected sprite fragments. Widely separated floor/AA specks do not
     * combine into an invented fourth item across the whole shop strip. */
    for(int y=0;y+42<=height&&!local_item;y++)for(int x=0;x+35<=180;x++) {
        int count=prefix[(y+42)*181+x+35]-prefix[y*181+x+35]
            -prefix[(y+42)*181+x]+prefix[y*181+x];
        if(count>=24){local_item=1;break;}
    }
    for(int at=0;at<180*height;at++)if(mask[at]) {
        int head=0,tail=0;mask[at]=0;queue[tail++]=(uint16_t)at;
        while(head<tail) {
            int position=queue[head++],x=position%180,y=position/180;
            int neighbours[4]={x?position-1:-1,x+1<180?position+1:-1,y?position-180:-1,y+1<height?position+180:-1};
            for(int k=0;k<4;k++)if(neighbours[k]>=0&&mask[neighbours[k]]) {
                mask[neighbours[k]]=0;queue[tail++]=(uint16_t)neighbours[k];
            }
        }
        out->unmatched_items+=tail>=24;
    }
    if(local_item&&!out->unmatched_items)out->unmatched_items=1;
}
/* Policy2 searches only the requested target. The supported normal 1-1 shop
 * has three 36px offer cells; one cell of observed floor on each side forms
 * B=[left-54,sy+24,180,67]. Every integer top-left of EVERY canonical primary
 * template wholly contained in B is visited. This is not arbitrary-world
 * absence, and no product name/catalog identity is needed for a negative. */
static double binary_pose_bound(const unsigned char *rgba,const Sprite *sp,int x,int y) {
    double count=sp->count,dark=sp->dark_count;
    int32_t total=0,square=0,cross=0,dot=0;
    uint16_t sums[344];unsigned char greens[344];
    for(int k=0;k<sp->count;k++) {
        const Bright *p=&sp->bright[k];const unsigned char *q=rgba+4*((size_t)(y+p->dy)*RING_W+x+p->dx);
        int v=q[0]+q[1]+q[2];sums[k]=(uint16_t)v;greens[k]=q[1];
        dot+=q[0]*p->r+q[1]*p->g+q[2]*p->b;
        total+=v;square+=v*v;cross+=v*(p->r+p->g+p->b);
    }
    double product=probe_mul(probe_sub(square,probe_div((double)((int64_t)total*total),count)),sp->target_var);
    double norm=probe_sqrt(product>0.0?product:0.0);
    double shape=probe_div(probe_sub(cross,probe_div((double)((int64_t)total*sp->target_sum),count)),norm>9.0?norm:9.0);
    if(shape<0.0)shape=0.0;
    double value=probe_mul(probe_add(probe_div(probe_mul(.55,count),count),probe_mul(.45,shape)),
                           probe_add(.80,probe_div(probe_mul(.20,dark),dark)));
    if(value>=.799999999) {
        int outline=0,possible=0;
        for(int k=0;k<sp->dark_count;k++) {
            const Dark *p=&sp->dark[k];const unsigned char *q=rgba+4*((size_t)(y+p->dy)*RING_W+x+p->dx);
            outline+=q[0]+q[1]+q[2]<144;
        }
        double gain=probe_div(dot,sp->energy);if(gain<.37)gain=.37;if(gain>1.3)gain=1.3;
        double limit=probe_add(probe_mul(3.0,probe_add(13.0,probe_mul(15.0,gain))),1e-9);
        for(int k=0;k<sp->count;k++) {
            const Bright *p=&sp->bright[k];
            possible+=fabs(probe_sub(sums[k],probe_mul(gain,p->r+p->g+p->b)))<limit
                &&fabs(probe_sub(greens[k],probe_mul(gain,p->g)))<limit;
        }
        value=probe_mul(probe_add(probe_div(probe_mul(.55,possible),count),probe_mul(.45,shape)),
                         probe_add(.80,probe_div(probe_mul(.20,outline),dark)));
    }
    value=probe_add(value,1e-12);return ng2_ring_round9(value<1.0?value:1.0);
}
typedef struct {int cx,sy,ready;double maximum;int32_t pose[4];} NG2BinaryProbe;
static int binary_primary(const unsigned char *rgba,const NG2RingOptions *options,
                          NG2RingResult *result,NG2RingRow *row) {
    NG2BinaryProbe probes[30];NG2RingSlot cells[5];int count=0,status;
    memset(cells,0,sizeof(cells));
    for(int cell=0;cell<5;cell++) {
        int cx=row->left+36*(cell-1);NG2RingSlot *slot=&cells[cell];
        slot->cx=cx;slot->sy=row->sy;slot->slot=cell>0&&cell<4?cell-1:0;
        slot->kind=NG2_RING_GENERIC_NON_TARGET;slot->outcome=NG2_RING_NON_TARGET;
        int32_t box[4]={cx-18,row->sy+24,36,67};memcpy(slot->non_target_icon_box,box,sizeof(box));
        for(int dy=0;dy<=6;dy+=6)for(int dx=-16;dx<=16;dx+=16)
            probes[count++]=(NG2BinaryProbe){cx+dx,row->sy+dy,0,0.0,{0}};
    }
    for(size_t s=0;s<sizeof(sprites)/sizeof(sprites[0]);s++) {
        const Sprite *sp=&sprites[s];
        for(int y=row->sy+24;y<=row->sy+91-sp->height;y++) {
            if((status=checkpoint(options,result)))return status;
            for(int x=row->left-54;x<=row->left+126-sp->width;x++) {
                int cell=(x+sp->width/2-(row->left-54))/36;
                if(cell<0||cell>=5)return NG2_RING_KERNEL;
                double bound=binary_pose_bound(rgba,sp,x,y);int cached=-1;
                for(int p=0;p<30;p++)if(x>=probes[p].cx-sp->width/2-8
                    &&x<=probes[p].cx-sp->width/2+8&&y>=probes[p].sy+24&&y<=probes[p].sy+57) {
                    if(cached<0||probes[p].ready)cached=p;
                    if(probes[p].ready)break;
                }
                if(cached<0)return NG2_RING_KERNEL;
                NG2BinaryProbe *probe=&probes[cached];
                if(bound>=.80&&!probe->ready) {
                    if((status=checkpoint(options,result)))return status;
                    if(ring_icon(rgba,RING_RGBA,probe->cx,probe->sy,0,NULL,&probe->maximum,probe->pose))return NG2_RING_KERNEL;
                    probe->maximum=ng2_ring_round9(probe->maximum<1.0?probe->maximum:1.0);probe->ready=1;
                    if((status=checkpoint(options,result)))return status;
                }
                if(probe->ready&&probe->maximum<bound)bound=probe->maximum;
                if(bound>=.80) {
                    int at=result->partial_count<NG2_RING_MAX_PARTIAL?result->partial_count++:0;
                    NG2RingSlot *evidence=&result->partial[at];memset(evidence,0,sizeof(*evidence));
                    evidence->cx=probe->cx;evidence->sy=probe->sy;evidence->icon_score=probe->maximum;
                    evidence->icon_upper_bound=probe->maximum;evidence->icon_score_exact=1;
                    evidence->outcome=NG2_RING_CANDIDATE;memcpy(evidence->icon_box,probe->pose,sizeof(probe->pose));
                    result->selected_partial=at;result->selected_row=-1;
                    result->outcome=NG2_RING_CANDIDATE;result->reason=NG2_RING_ICON_ONLY;
                    result->coverage=NG2_RING_COVERAGE_INCOMPLETE;return NG2_RING_OK;
                }
                NG2RingSlot *slot=&cells[cell];
                if(bound>slot->icon_upper_bound||!slot->icon_box[2]) {
                    slot->icon_score=slot->icon_upper_bound=bound;
                    int32_t pose[4]={x,y,sp->width,sp->height};memcpy(slot->icon_box,pose,sizeof(pose));
                }
            }
        }
    }
    for(int s=0;s<3;s++)row->slots[s]=cells[s+1];
    result->partial_count=2;result->partial[0]=cells[0];result->partial[1]=cells[4];
    return checkpoint(options,result);
}
static int binary_word_window(const RingObservation *observation,int x0,int x1,int y0,int y1,
                              const NG2RingOptions *options,NG2RingResult *result,NG2RingSlot *slot) {
    double best=0.0,coverage=0.0;int32_t best_box[4]={0};int status,found=0;
    /* Both every original partial window and the complete-strip name union
     * filter full visibility and qualifying thresholds BEFORE maximization. */
    for(int y=y0;y<=y1;y++) {
        if((status=checkpoint(options,result)))return status;
        for(int x=x0;x<=x1;x++) {
            int32_t box[4]={x,y,84,11};if(!box_valid(box))continue;
            unsigned intersection=0,total_union=0;
            for(int dy=0;dy<11;dy++) {
                uint64_t observed[2];bank_window(observation->white[y+dy],x,84,observed);
                for(int k=0;k<2;k++) {
                    intersection+=bank_pop(word_reference[dy][k]&observed[k]);
                    total_union+=bank_pop(word_reference[dy][k]|observed[k]);
                }
            }
            double iou=ng2_ring_round9(bank_div(intersection,total_union?total_union:1));
            double cov=ng2_ring_round9(bank_div(intersection,239));
            int qualifies=iou>=.82&&cov>=.90,old=best>=.82&&coverage>=.90;
            if(!found||((qualifies!=old)?qualifies:(iou>best||(iou==best&&cov>coverage)))) {
                found=1;best=iou;coverage=cov;memcpy(best_box,box,sizeof(box));
            }
        }
    }
    if(found) {
        slot->word_present=1;slot->word_iou=best;slot->word_coverage=coverage;
        memcpy(slot->word_box,best_box,sizeof(best_box));
    }
    return checkpoint(options,result);
}
static int binary_slot_word(const RingObservation *observation,int cx,int sy,
                            const NG2RingOptions *options,NG2RingResult *result,NG2RingSlot *slot) {
    return binary_word_window(observation,cx-60,cx-24,sy-20,sy+35,options,result,slot);
}
static int binary_word_veto(const RingObservation *observation,const NG2RingOptions *options,
                            NG2RingResult *result,NG2RingRow *row) {
    NG2RingSlot word={0};
    int status=binary_word_window(observation,row->left-112,row->left+100,row->sy-20,row->sy+41,
                                  options,result,&word);
    if(status)return status;
    if(word.word_present&&word.word_iou>=.82&&word.word_coverage>=.90) {
        NG2RingSlot *slot=&row->slots[0];slot->word_present=1;slot->word_iou=word.word_iou;slot->word_coverage=word.word_coverage;
        memcpy(slot->word_box,word.word_box,sizeof(word.word_box));slot->outcome=NG2_RING_CANDIDATE;
        result->outcome=NG2_RING_CANDIDATE;result->reason=NG2_RING_ICON_ONLY;
    }
    return checkpoint(options,result);
}
static void binary_preserve_observed_words(NG2RingResult *result) {
    if(result->outcome!=NG2_RING_UNKNOWN)return;
    for(int r=0;r<result->row_count;r++)for(int s=0;s<3;s++) {
        NG2RingSlot *slot=&result->rows[r].slots[s];
        if(slot->word_present&&slot->word_iou>=.82&&slot->word_coverage>=.90&&box_valid(slot->word_box)) {
            slot->outcome=NG2_RING_CANDIDATE;result->outcome=NG2_RING_CANDIDATE;
            result->reason=NG2_RING_ICON_ONLY;result->selected_row=r;result->selected_partial=-1;return;
        }
    }
    for(int s=0;s<result->partial_count;s++) {
        NG2RingSlot *slot=&result->partial[s];
        if(slot->word_present&&slot->word_iou>=.82&&slot->word_coverage>=.90&&box_valid(slot->word_box)) {
            slot->outcome=NG2_RING_CANDIDATE;result->outcome=NG2_RING_CANDIDATE;
            result->reason=NG2_RING_ICON_ONLY;result->selected_row=-1;result->selected_partial=s;return;
        }
    }
}
static int binary_coverage(const unsigned char *rgba,const RingObservation *observation,
                           const NG2RingOptions *options,NG2RingResult *result,int selected) {
    NG2RingCoverage *out=&result->certificate;NG2RingRow *row=&result->rows[selected];
    int32_t strip[4]={row->left-54,row->sy+24,180,67};memcpy(out->strip_box,strip,sizeof(strip));
    out->policy_version=2;
    if(!box_valid(strip)){out->failure_flags|=NG2_RING_COV_BOUNDS;return NG2_RING_OK;}
    int status=binary_primary(rgba,options,result,row);if(status||result->outcome!=NG2_RING_UNKNOWN)return status;
    status=binary_word_veto(observation,options,result,row);if(status||result->outcome!=NG2_RING_UNKNOWN)return status;
    int complete=endcap_witness(rgba,observation,row->left-36,row->sy,&out->endcaps[0]);
    complete&=endcap_witness(rgba,observation,row->left+108,row->sy,&out->endcaps[1]);
    if(!complete)out->failure_flags|=NG2_RING_COV_ENDCAP;
    /* Raw prices are read before the primary coverage cell boxes are stored:
     * a detector union is never used as a price/extraneous-object mask. */
    price_witness(observation,row,out);
    if(out->observed_prices!=3||out->unmatched_prices){complete=0;out->failure_flags|=NG2_RING_COV_PRICE;}
    for(int s=0;s<3;s++) {
        memcpy(out->item_boxes[s],row->slots[s].non_target_icon_box,sizeof(out->item_boxes[s]));
        memset(out->name_boxes[s],0,sizeof(out->name_boxes[s]));
    }
    item_witness(rgba,row,out);
    if(out->observed_items!=3||out->unmatched_items){complete=0;out->failure_flags|=NG2_RING_COV_ITEM;}
    if(out->unmatched_boards){complete=0;out->failure_flags|=NG2_RING_COV_EXTRA_BOARD;}
    out->non_target_items=3;out->ignored_containers=0;
    if(complete){result->coverage=NG2_RING_COVERAGE_COMPLETE;result->selected_row=selected;result->selected_partial=-1;}
    return checkpoint(options,result);
}
/* Policy3 is a separate finite normal-shop layout proof. Pixel identities of
 * SHOP or the singer are not authority here. All target pixels remain intact;
 * the exact policy2 dense sweep and word veto are used without a text mask. */
static int structural_cell(int pixel,int origin,int *cell) {
    int delta=pixel-origin,whole=delta/36,remainder=delta%36;
    if(remainder==18||remainder==-18)return 0;
    if(remainder>18)whole++;else if(remainder<-18)whole--;
    *cell=whole;return 1;
}
static int structural_row_cells(int left,int sy,int *ax,int *ay) {
    return left>=54&&left<=RING_W-126&&sy>=0&&sy<=RING_HH-91
        &&structural_cell(left,448,ax)&&structural_cell(sy+48,207,ay)
        &&*ax-2>=-11&&*ax+4<=11&&*ay-1>=-5&&*ay+3<=4;
}
static int structural_tile(const NG2Scene *scene,int x,int y) {
    return x>=-11&&x<=11&&y>=-5&&y<=4?scene->tiles[(y+5)*23+x+11]:NG2_TILE_UNKNOWN;
}
static int structural_scene_row(const NG2Scene *scene,int left,int sy) {
    int ax,ay,gold=0;
    if(!scene||scene->abi_version!=NG2_ABI_VERSION||scene->struct_size!=sizeof(*scene)
       ||scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE
       ||(scene->gold_state!=NG2_GOLD_CANDIDATE&&scene->gold_state!=NG2_GOLD_EDGE_DOWN)
       ||!structural_row_cells(left,sy,&ax,&ay))return 0;
    for(int i=0;i<NG2_TILE_COUNT;i++)gold+=scene->tiles[i]==NG2_TILE_GOLD;
    if(gold<12)return 0;
    for(int x=ax;x<=ax+2;x++)if(structural_tile(scene,x,ay)!=NG2_TILE_ITEM)return 0;
    if(structural_tile(scene,ax-1,ay)!=NG2_TILE_FLOOR||structural_tile(scene,ax+3,ay)!=NG2_TILE_FLOOR)return 0;
    for(int mirror=0;mirror<2;mirror++) {
        int wall=mirror?ax+4:ax-2,gate=mirror?ax-2:ax+4,valid=1;
        for(int y=ay-1;y<=ay+3;y++)valid&=structural_tile(scene,wall,y)==NG2_TILE_GOLD;
        for(int x=ax-2+mirror;x<=ax+3+mirror;x++)valid&=structural_tile(scene,x,ay+3)==NG2_TILE_GOLD;
        valid&=structural_tile(scene,gate,ay)==NG2_TILE_GOLD;
        valid&=structural_tile(scene,gate,ay+2)==NG2_TILE_GOLD;
        int opening=structural_tile(scene,gate,ay+1);
        valid&=opening==NG2_TILE_FLOOR||opening==NG2_TILE_DOOR;
        if(valid)return 1;
    }
    return 0;
}
static int structural_face(const NG2RingSign *face,int cx,int sy) {
    int32_t roi[4]={cx-18,sy-20,36,40};
    int32_t box[4]={face->x0,face->y0,face->x1-face->x0,face->y1-face->y0};
    return box_valid(roi)&&box_valid(box)&&box[2]>=18&&box[2]<=36&&box[3]>=16&&box[3]<=40
        &&face->count>=150&&face->count<=box[2]*box[3]
        &&box[0]>=roi[0]&&box[1]>=roi[1]&&box[0]+box[2]<=roi[0]+36&&box[1]+box[3]<=roi[1]+40
        &&abs(face->cx-cx)<=2&&abs(face->sy-sy)<=2
        &&abs(box[0]+box[2]/2-cx)<=2&&abs(box[1]+box[3]/2-sy)<=2;
}
static int structural_coverage(const unsigned char *rgba,const RingObservation *observation,
                               const NG2RingSign signs[12],int sign_count,
                               const NG2RingOptions *options,NG2RingResult *result,int *handled) {
    *handled=0;
    if(!options||options->mode!=NG2_RING_MODE_TARGET_ONLY)return NG2_RING_OK;
    int selected=-1,selected_pair[2]={-1,-1},accepted=0;
    for(int r=0;r<result->row_count;r++) {
        const NG2RingRow *row=&result->rows[r];int pair[2]={-1,-1},hits[2]={0,0};
        if(!structural_scene_row(options->scene,row->left,row->sy))continue;
        for(int side=0;side<2;side++)for(int i=0;i<sign_count;i++)
            if(structural_face(&signs[i],row->left+72*side,row->sy)){pair[side]=i;hits[side]++;}
        if(hits[0]!=1||hits[1]!=1||pair[0]==pair[1]
           ||abs(signs[pair[1]].cx-signs[pair[0]].cx-72)>2||abs(signs[pair[1]].sy-signs[pair[0]].sy)>2)continue;
        accepted++;
        if(selected<0){selected=r;selected_pair[0]=pair[0];selected_pair[1]=pair[1];}
    }
    if(!accepted)return NG2_RING_OK; /* Exact old policy2 fallback remains below. */
    *handled=1;
    NG2RingCoverage *out=&result->certificate;NG2RingRow *row=&result->rows[selected];
    memset(out,0,sizeof(*out));out->layout_version=1;out->policy_version=3;out->board_mode=3;
    out->accepted_rows=accepted;out->row_index=selected;out->row[0]=row->left;out->row[1]=row->sy;
    out->scene_state=options->scene->state;out->scene_goods=options->scene->goods;
    for(int i=0;i<NG2_TILE_COUNT;i++)out->actual_gold_cells+=options->scene->tiles[i]==NG2_TILE_GOLD;
    result->coverage=NG2_RING_COVERAGE_INCOMPLETE;
    for(int side=0;side<2;side++) {
        const NG2RingSign *face=&signs[selected_pair[side]];
        int32_t box[4]={face->x0,face->y0,face->x1-face->x0,face->y1-face->y0};
        memcpy(out->board_boxes[side],box,sizeof(box));out->board_counts[side]=face->count;
    }
    /* The canonical observation stage already admits 18..48px SIGN faces.
     * Only the selected pair uses the narrower complete 36px pose ROI. */
    for(int i=0;i<sign_count;i++)if(i!=selected_pair[0]&&i!=selected_pair[1])out->unmatched_boards++;
    if(accepted!=1){out->failure_flags|=NG2_RING_COV_ROWS;return NG2_RING_OK;}
    if(out->unmatched_boards){out->failure_flags|=NG2_RING_COV_EXTRA_BOARD;return NG2_RING_OK;}
    int32_t strip[4]={row->left-54,row->sy+24,180,67};memcpy(out->strip_box,strip,sizeof(strip));
    if(!box_valid(strip)){out->failure_flags|=NG2_RING_COV_BOUNDS;return NG2_RING_OK;}
    int status=binary_primary(rgba,options,result,row);if(status||result->outcome!=NG2_RING_UNKNOWN)return status;
    status=binary_word_veto(observation,options,result,row);if(status||result->outcome!=NG2_RING_UNKNOWN)return status;
    int complete=endcap_witness(rgba,observation,row->left-36,row->sy,&out->endcaps[0]);
    complete&=endcap_witness(rgba,observation,row->left+108,row->sy,&out->endcaps[1]);
    if(!complete)out->failure_flags|=NG2_RING_COV_ENDCAP;
    price_witness(observation,row,out);
    if(out->observed_prices!=3||out->unmatched_prices){complete=0;out->failure_flags|=NG2_RING_COV_PRICE;}
    for(int s=0;s<3;s++)memcpy(out->item_boxes[s],row->slots[s].non_target_icon_box,sizeof(out->item_boxes[s]));
    item_witness(rgba,row,out);
    /* This raw diagnostic is not an object/word classifier. The finite three
     * offer premise plus the unmasked all-position target sweep is authority. */
    if(out->observed_items!=3){complete=0;out->failure_flags|=NG2_RING_COV_ITEM;}
    out->non_target_items=3;
    if(complete){result->coverage=NG2_RING_COVERAGE_COMPLETE;result->selected_row=selected;result->selected_partial=-1;}
    return checkpoint(options,result);
}
/* Coverage and item identity are separate witnesses. Neither a low target
 * score nor the legacy three-price row alone can authorize NEGATIVE. */
static int coverage_witness(const unsigned char *rgba,const RingObservation *observation,
                            const NG2RingSign signs[12],int sign_count,
                            const NG2RingOptions *options,NG2RingResult *result) {
    if(!options||!options->scene)return NG2_RING_OK;
    int handled=0,structural=structural_coverage(rgba,observation,signs,sign_count,options,result,&handled);
    if(structural||handled)return structural;
    const NG2Scene *scene=options->scene;NG2RingCoverage *out=&result->certificate;
    if(scene->abi_version!=NG2_ABI_VERSION||scene->struct_size!=sizeof(*scene))return NG2_RING_INVALID;
    out->scene_state=scene->state;out->scene_goods=scene->goods;out->layout_version=1;
    out->policy_version=options->mode==NG2_RING_MODE_TARGET_ONLY?2:1;out->row_index=-1;
    for(int k=0;k<NG2_TILE_COUNT;k++)out->actual_gold_cells+=scene->tiles[k]==NG2_TILE_GOLD;
    if(scene->state!=NG2_FLOOR||scene->goods!=NG2_GOODS_VISIBLE||!out->actual_gold_cells) {
        out->failure_flags=NG2_RING_COV_SCENE;return NG2_RING_OK;
    }
    result->coverage=NG2_RING_COVERAGE_INCOMPLETE;
    int selected=-1,status;
    for(int r=0;r<result->row_count;r++) {
        NG2RingRow *row=&result->rows[r];int pair[2]={-1,-1};NG2RingSign physical[2];
        int32_t edge_counts[2][4]={{0}},corner_counts[2][4]={{0}};
        int mode=1;
        /* The original connected SIGN component witnesses its own visible
         * yellow face. It does not claim completion of a black/gold exterior.
         * The independently observed SHOP glyph and merchant authenticate
         * this finite layout; item coverage is proved separately below. */
        for(int i=0;i<sign_count;i++)for(int side=0;side<2;side++) {
            int32_t box[4]={signs[i].x0,signs[i].y0,signs[i].x1-signs[i].x0,signs[i].y1-signs[i].y0};
            if(pair[side]<0&&abs(signs[i].cx-row->left-72*side)<=2&&abs(signs[i].sy-row->sy)<=2&&box_valid(box)) {
                pair[side]=i;physical[side]=signs[i];
            }
        }
        if(pair[0]<0||pair[1]<0||pair[0]==pair[1]
           ||abs(physical[1].cx-physical[0].cx-72)>2||abs(physical[1].sy-physical[0].sy)>2) {
            mode=2;pair[0]=pair[1]=-1;
            for(int i=0;i<sign_count;i++)for(int side=0;side<2;side++)
                if(pair[side]<0&&board_frame(rgba,&signs[i],row->left+72*side,row->sy,&physical[side],edge_counts[side],corner_counts[side]))pair[side]=i;
        }
        if(selected<0) {
            out->board_mode=(uint32_t)mode;
            out->row_index=r;out->row[0]=row->left;out->row[1]=row->sy;
            for(int side=0;side<2;side++)if(pair[side]>=0) {
                const NG2RingSign *sign=&physical[side];
                out->board_boxes[side][0]=sign->x0;out->board_boxes[side][1]=sign->y0;
                out->board_boxes[side][2]=sign->x1-sign->x0;out->board_boxes[side][3]=sign->y1-sign->y0;
                out->board_counts[side]=sign->count;
            }
        }
        if(pair[0]<0||pair[1]<0||pair[0]==pair[1]){out->failure_flags|=NG2_RING_COV_BOARD;continue;}
        const NG2RingSign *a=&physical[0],*b=&physical[1];
        if(abs(b->cx-a->cx-72)>2||abs(b->sy-a->sy)>2){out->failure_flags|=NG2_RING_COV_BOARD;continue;}
        int valid=1;double iou[2],cov[2];int32_t glyph_boxes[2][4]={{0}};
        for(int side=0;side<2;side++) {
            const NG2RingSign *sign=&physical[side];
            int32_t board[4]={sign->x0,sign->y0,sign->x1-sign->x0,sign->y1-sign->y0};
            valid&=box_valid(board);
            status=glyph_auth(rgba,row->left+72*side,row->sy,options,result,&iou[side],&cov[side],glyph_boxes[side]);
            if(status)return status;
        }
        if(selected<0) {
            memcpy(out->sign_boxes,glyph_boxes,sizeof(glyph_boxes));
            memcpy(out->sign_iou,iou,sizeof(iou));memcpy(out->sign_coverage,cov,sizeof(cov));
            memcpy(out->board_edge_counts,edge_counts,sizeof(edge_counts));
            memcpy(out->board_corner_counts,corner_counts,sizeof(corner_counts));
        }
        if(!valid){out->failure_flags|=NG2_RING_COV_BOUNDS;continue;}
        if(!((iou[0]>=.94&&cov[0]>=.95)||(iou[1]>=.94&&cov[1]>=.95))) {
            out->failure_flags|=NG2_RING_COV_GLYPH;continue;
        }
        double merchant=0.0,foreground=0.0;int32_t merchant_box[4]={0};
        for(int phase=0;phase<R94_MERCHANT_COUNT;phase++) {
            double score,fg;int32_t box[4]={0};
            status=bank_icon(rgba,row->left+36,row->sy,&r94_merchants[phase],options,result,&score,&fg,box,1);
            if(status)return status;
            int qualifies=score>=.94&&fg>=.95,old=merchant>=.94&&foreground>=.95;
            if((qualifies!=old)?qualifies:score>merchant) {
                merchant=score;foreground=fg;memcpy(merchant_box,box,sizeof(box));
            }
        }
        if(selected<0) {
            out->merchant_score=merchant;out->merchant_coverage=foreground;
            memcpy(out->merchant_box,merchant_box,sizeof(merchant_box));
        }
        if(merchant<.94||foreground<.95||!box_valid(merchant_box)) {
            out->failure_flags|=NG2_RING_COV_MERCHANT;continue;
        }
        int32_t exterior[2]={0,0};
        if(mode==2) {
            exterior[0]=board_exterior(rgba,&physical[0],merchant_box);
            exterior[1]=board_exterior(rgba,&physical[1],merchant_box);
        }
        if(selected<0)memcpy(out->board_exterior_count,exterior,sizeof(exterior));
        if(exterior[0]||exterior[1]){out->failure_flags|=NG2_RING_COV_BOARD;continue;}
        out->accepted_rows++;
        if(selected<0) {
            selected=r;out->row_index=r;out->row[0]=row->left;out->row[1]=row->sy;
            out->failure_flags=0;
            out->merchant_score=merchant;out->merchant_coverage=foreground;
            memcpy(out->merchant_box,merchant_box,sizeof(merchant_box));
            memcpy(out->sign_boxes,glyph_boxes,sizeof(glyph_boxes));
            memcpy(out->sign_iou,iou,sizeof(iou));memcpy(out->sign_coverage,cov,sizeof(cov));
            for(int i=0;i<sign_count;i++)if(i!=pair[0]&&i!=pair[1]) {
                double extra_iou,extra_cov;int32_t extra_box[4]={0};
                status=glyph_auth(rgba,signs[i].cx,signs[i].sy,options,result,&extra_iou,&extra_cov,extra_box);
                if(status)return status;
                if(extra_iou>=.94&&extra_cov>=.95)out->unmatched_boards++;
            }
        }
    }
    if(out->accepted_rows!=1){out->failure_flags|=NG2_RING_COV_ROWS;return NG2_RING_OK;}
    out->failure_flags=0;
    NG2RingRow *row=&result->rows[selected];
    if(options->mode==NG2_RING_MODE_TARGET_ONLY)return binary_coverage(rgba,observation,options,result,selected);
    int has_container=0;for(int s=0;s<3;s++)has_container|=row->slots[s].kind==R94_BANK_IGNORED_CONTAINER;
    int32_t strip[4]={row->left-54,row->sy+24,180,has_container?67:65};memcpy(out->strip_box,strip,sizeof(strip));
    if(!box_valid(strip)){out->failure_flags|=NG2_RING_COV_BOUNDS;return NG2_RING_OK;}
    int complete=1;
    int endcaps=endcap_witness(rgba,observation,row->left-36,row->sy,&out->endcaps[0]);
    endcaps&=endcap_witness(rgba,observation,row->left+108,row->sy,&out->endcaps[1]);
    if(!endcaps){complete=0;out->failure_flags|=NG2_RING_COV_ENDCAP;}
    for(int s=0;s<3;s++) {
        NG2RingSlot *slot=&row->slots[s];
        int known=slot->non_target_id>0&&!slot->non_target_conflict&&slot->outcome==NG2_RING_NON_TARGET
            &&slot->kind==R94_BANK_NONTARGET;
        int ignored=slot->ignored_container_id>0&&!slot->non_target_conflict&&slot->outcome==NG2_RING_IGNORED_CONTAINER
            &&slot->kind==R94_BANK_IGNORED_CONTAINER;
        if(ignored) {
            out->ignored_containers++;
            memcpy(out->item_boxes[s],slot->ignored_icon_box,sizeof(slot->ignored_icon_box));
        } else if(known) {
            out->non_target_items++;
            memcpy(out->item_boxes[s],slot->non_target_icon_box,sizeof(slot->non_target_icon_box));
            memcpy(out->name_boxes[s],slot->non_target_name_box,sizeof(slot->non_target_name_box));
        } else {complete=0;out->failure_flags|=NG2_RING_COV_IDENTITY;}
        if(!box_valid(out->item_boxes[s])||(!ignored&&!box_valid(out->name_boxes[s]))) {
            complete=0;out->failure_flags|=NG2_RING_COV_BOUNDS;
        }
        const int32_t *pose=out->item_boxes[s];int bottom=row->sy+(ignored?90:89);
        if(pose[2]>36||pose[3]>36||pose[0]<slot->cx-pose[2]/2-8||pose[0]>slot->cx-pose[2]/2+8
           ||pose[1]<slot->sy+24||pose[1]>slot->sy+57||pose[1]+pose[3]>bottom
           ||pose[0]<strip[0]||pose[0]+pose[2]>strip[0]+strip[2]) {
            complete=0;out->failure_flags|=NG2_RING_COV_BOUNDS;
        }
        for(int previous=0;previous<s;previous++) {
            const int32_t *a=out->item_boxes[s],*b=out->item_boxes[previous];
            if(a[0]<b[0]+b[2]&&b[0]<a[0]+a[2]&&a[1]<b[1]+b[3]&&b[1]<a[1]+a[3]) {
                complete=0;out->failure_flags|=NG2_RING_COV_IDENTITY;
            }
            if(!ignored&&!memcmp(out->name_boxes[s],out->name_boxes[previous],sizeof(out->name_boxes[s]))) {
                complete=0;out->failure_flags|=NG2_RING_COV_IDENTITY;
            }
        }
    }
    price_witness(observation,row,out);
    item_witness(rgba,row,out);
    if(out->observed_prices!=3||out->unmatched_prices){complete=0;out->failure_flags|=NG2_RING_COV_PRICE;}
    if(out->observed_items!=3||out->unmatched_items){complete=0;out->failure_flags|=NG2_RING_COV_ITEM;}
    if(out->unmatched_boards){complete=0;out->failure_flags|=NG2_RING_COV_EXTRA_BOARD;}
    if(complete) {
        result->coverage=NG2_RING_COVERAGE_COMPLETE;result->selected_row=selected;result->selected_partial=-1;
    }
    return checkpoint(options,result);
}
static int proof_score(double value,double lower){return isfinite(value)&&value>=lower&&value<=1.000001;}
static int proof_no_candidate(const NG2RingSlot *slot) {
    if(slot->outcome==NG2_RING_TARGET||slot->outcome==NG2_RING_CANDIDATE||slot->outcome>NG2_RING_IGNORED_CONTAINER
       ||slot->icon_score_exact>1||!proof_score(slot->icon_score,0.0)||!proof_score(slot->icon_upper_bound,0.0)
       ||slot->word_present<0||slot->word_present>1
       ||(slot->word_present&&(!proof_score(slot->word_iou,0.0)||!proof_score(slot->word_coverage,0.0))))return 0;
    if(slot->icon_score_exact)return slot->icon_score<.80;
    return slot->icon_upper_bound<.80&&slot->icon_score<=slot->icon_upper_bound;
}
static int binary_no_candidate(const NG2RingSlot *slot) {
    return proof_no_candidate(slot)&&!(slot->word_present&&slot->word_iou>=.82&&slot->word_coverage>=.90);
}
static int binary_cell_certificate(const NG2RingSlot *slot,int cx,int sy,int index,const int32_t strip[4]) {
    if(slot->cx!=cx||slot->sy!=sy||slot->slot!=index||slot->kind!=NG2_RING_GENERIC_NON_TARGET
       ||slot->outcome!=NG2_RING_NON_TARGET||slot->icon_score_exact||!binary_no_candidate(slot)
       ||slot->icon_score!=slot->icon_upper_bound||slot->non_target_id||slot->ignored_container_id
       ||slot->non_target_conflict||slot->non_target_icon_score||slot->non_target_name_iou
       ||slot->non_target_name_coverage||slot->ignored_icon_score||slot->ignored_gold_iou
       ||slot->ignored_gold_coverage||slot->ignored_dark_iou||slot->ignored_dark_coverage)return 0;
    const int32_t *pose=slot->icon_box,*cell=slot->non_target_icon_box;
    if(!box_valid(pose)||!((pose[2]==32&&pose[3]==28)||(pose[2]==33&&pose[3]==28)
       ||(pose[2]==34&&pose[3]==29))||pose[0]<strip[0]||pose[1]<strip[1]
       ||pose[0]+pose[2]>strip[0]+strip[2]||pose[1]+pose[3]>strip[1]+strip[3]
       ||pose[0]+pose[2]/2<cx-18||pose[0]+pose[2]/2>=cx+18
       ||cell[0]!=cx-18||cell[1]!=sy+24||cell[2]!=36||cell[3]!=67)return 0;
    for(int k=0;k<4;k++)if(slot->non_target_name_box[k]||slot->ignored_icon_box[k])return 0;
    return 1;
}
static int structural_negative_certificate(const NG2RingResult *result) {
    if(result->abi!=NG2_RING_ABI||result->size!=sizeof(*result)||result->status!=NG2_RING_OK
       ||(result->outcome!=NG2_RING_UNKNOWN&&result->outcome!=NG2_RING_NEGATIVE)
       ||result->coverage!=NG2_RING_COVERAGE_COMPLETE||result->row_count<1||result->row_count>4
       ||result->partial_count!=2||result->selected_row<0||result->selected_row>=result->row_count
       ||result->selected_partial!=-1||result->partial_safe_no_positive)return 0;
    const NG2RingCoverage *w=&result->certificate;const NG2RingRow *row=&result->rows[result->selected_row];int ax,ay;
    if(!structural_row_cells(row->left,row->sy,&ax,&ay)||w->layout_version!=1||w->policy_version!=3
       ||w->board_mode!=3||w->failure_flags||w->accepted_rows!=1||w->row_index!=result->selected_row
       ||w->row[0]!=row->left||w->row[1]!=row->sy||w->scene_state!=NG2_FLOOR
       ||w->scene_goods!=NG2_GOODS_VISIBLE||w->actual_gold_cells<12||w->actual_gold_cells>NG2_TILE_COUNT
       ||w->observed_items!=3||w->observed_prices!=3||w->unmatched_prices||w->unmatched_boards
       ||w->unmatched_items<0||w->unmatched_items>(180*67)/24||w->non_target_items!=3||w->ignored_containers
       ||!box_valid(w->strip_box)||w->strip_box[0]!=row->left-54||w->strip_box[1]!=row->sy+24
       ||w->strip_box[2]!=180||w->strip_box[3]!=67||w->merchant_score||w->merchant_coverage)return 0;
    for(int k=0;k<4;k++)if(w->merchant_box[k])return 0;
    for(int side=0;side<2;side++) {
        int cx=row->left+72*side;const int32_t *board=w->board_boxes[side];const NG2RingEndcap *end=&w->endcaps[side];
        int32_t roi[4]={cx-18,row->sy-20,36,40};
        if(!box_valid(roi)||!box_valid(board)||board[2]<18||board[2]>36||board[3]<16||board[3]>40
           ||w->board_counts[side]<150||w->board_counts[side]>board[2]*board[3]
           ||board[0]<roi[0]||board[1]<roi[1]||board[0]+board[2]>roi[0]+36||board[1]+board[3]>roi[1]+40
           ||abs(board[0]+board[2]/2-cx)>2||abs(board[1]+board[3]/2-row->sy)>2
           ||w->sign_iou[side]||w->sign_coverage[side]||w->board_exterior_count[side]
           ||!box_valid(end->box)||end->box[0]!=row->left+(side?96:-48)||end->box[1]!=row->sy+36
           ||end->box[2]!=25||end->box[3]!=25||end->count!=625||end->black_count<0||end->black_count>62
           ||end->bright_count<0||end->bright_count>=24||end->price_ink_count<0||end->price_ink_count>=18
           ||end->r<0||end->r>255||end->g<0||end->g>255||end->b<0||end->b>255||end->spread!=1
           ||end->floor_full!=1||end->floor_upper!=1||end->floor_lower!=1||!material_floor(*end))return 0;
        for(int k=0;k<4;k++)if(w->sign_boxes[side][k]||w->board_edge_counts[side][k]||w->board_corner_counts[side][k])return 0;
    }
    if(abs(w->board_boxes[1][0]+w->board_boxes[1][2]/2-w->board_boxes[0][0]-w->board_boxes[0][2]/2-72)>2
       ||abs(w->board_boxes[1][1]+w->board_boxes[1][3]/2-w->board_boxes[0][1]-w->board_boxes[0][3]/2)>2)return 0;
    for(int r=0;r<result->row_count;r++)for(int s=0;s<3;s++)if(!binary_no_candidate(&result->rows[r].slots[s]))return 0;
    for(int s=0;s<3;s++) {
        if(!binary_cell_certificate(&row->slots[s],row->left+36*s,row->sy,s,w->strip_box)
           ||memcmp(w->item_boxes[s],row->slots[s].non_target_icon_box,sizeof(w->item_boxes[s]))
           ||!box_valid(w->price_boxes[s])||w->price_boxes[s][0]<row->left+36*s-11
           ||w->price_boxes[s][0]+w->price_boxes[s][2]>row->left+36*s+12
           ||w->price_boxes[s][1]<row->sy+69||w->price_boxes[s][1]+w->price_boxes[s][3]>row->sy+89)return 0;
        for(int k=0;k<4;k++)if(w->name_boxes[s][k])return 0;
    }
    return binary_cell_certificate(&result->partial[0],row->left-36,row->sy,0,w->strip_box)
        &&binary_cell_certificate(&result->partial[1],row->left+108,row->sy,0,w->strip_box);
}
int ng2_ring_negative_certificate(const NG2RingResult *result) {
    if(result&&result->certificate.policy_version==3)return structural_negative_certificate(result);
    if(!result||result->abi!=NG2_RING_ABI||result->size!=sizeof(*result)||result->status!=NG2_RING_OK
       ||(result->outcome!=NG2_RING_UNKNOWN&&result->outcome!=NG2_RING_NEGATIVE)
       ||result->coverage!=NG2_RING_COVERAGE_COMPLETE||result->row_count<1||result->row_count>4
       ||result->partial_count<0||result->partial_count>12||result->selected_row<0
       ||result->selected_row>=result->row_count||result->selected_partial!=-1||result->partial_safe_no_positive)return 0;
    const NG2RingCoverage *w=&result->certificate;const NG2RingRow *row=&result->rows[result->selected_row];
    int binary=w->policy_version==2;
    if(row->left<54||row->left>RING_W-126||row->sy<0||row->sy>RING_HH-91
       ||w->layout_version!=1||(w->policy_version!=1&&!binary)||w->failure_flags||w->accepted_rows!=1
       ||w->row_index!=result->selected_row||w->row[0]!=row->left||w->row[1]!=row->sy
       ||w->observed_items!=3||w->observed_prices!=3||w->unmatched_items||w->unmatched_prices||w->unmatched_boards
       ||w->non_target_items<0||w->non_target_items>3||w->ignored_containers<0||w->ignored_containers>3
       ||w->non_target_items+w->ignored_containers!=3
       ||w->scene_state!=NG2_FLOOR||w->scene_goods!=NG2_GOODS_VISIBLE||w->actual_gold_cells<1
       ||w->actual_gold_cells>NG2_TILE_COUNT||(w->board_mode!=1&&w->board_mode!=2)
       ||!box_valid(w->strip_box)||w->strip_box[0]!=row->left-54||w->strip_box[1]!=row->sy+24
       ||w->strip_box[2]!=180||w->strip_box[3]!=(binary||w->ignored_containers?67:65)
       ||!box_valid(w->merchant_box)||!proof_score(w->merchant_score,.94)||!proof_score(w->merchant_coverage,.95))return 0;
    int shop=0;
    for(int side=0;side<2;side++) {
        if(!proof_score(w->sign_iou[side],0.0)||!proof_score(w->sign_coverage[side],0.0))return 0;
        if(w->sign_iou[side]>=.94&&w->sign_coverage[side]>=.95&&box_valid(w->sign_boxes[side]))shop=1;
        const int32_t *board=w->board_boxes[side];const NG2RingEndcap *end=&w->endcaps[side];
        if(!box_valid(board)||w->board_counts[side]<150||w->board_counts[side]>48*40
           ||w->board_counts[side]>board[2]*board[3]||board[2]<18||board[2]>48||board[3]<16||board[3]>40
           ||abs(board[0]+board[2]/2-row->left-72*side)>2||abs(board[1]+board[3]/2-row->sy)>2
           ||!box_valid(end->box)||end->box[0]!=row->left+(side?96:-48)||end->box[1]!=row->sy+36
           ||end->box[2]!=25||end->box[3]!=25||end->count!=625||end->black_count<0||end->black_count>62
           ||end->bright_count<0||end->bright_count>=24||end->price_ink_count<0||end->price_ink_count>=18
           ||end->r<0||end->r>255||end->g<0||end->g>255||end->b<0||end->b>255||end->spread!=1
           ||end->floor_full!=1||end->floor_upper!=1||end->floor_lower!=1||!material_floor(*end))return 0;
        if(w->board_mode==2) {
            if(w->board_exterior_count[side])return 0;
            for(int edge=0;edge<4;edge++) {
                int dimension=edge<2?board[2]:board[3],count=w->board_edge_counts[side][edge];
                if(count<0||count>dimension||4*count<3*dimension
                   ||w->board_corner_counts[side][edge]<1||w->board_corner_counts[side][edge]>4)return 0;
            }
        }
    }
    if(!shop||abs(w->board_boxes[1][0]+w->board_boxes[1][2]/2-w->board_boxes[0][0]-w->board_boxes[0][2]/2-72)>2
       ||abs(w->board_boxes[1][1]+w->board_boxes[1][3]/2-w->board_boxes[0][1]-w->board_boxes[0][3]/2)>2)return 0;
    for(int r=0;r<result->row_count;r++)for(int s=0;s<3;s++)if(!proof_no_candidate(&result->rows[r].slots[s]))return 0;
    for(int s=0;s<result->partial_count;s++)if(!proof_no_candidate(&result->partial[s]))return 0;
    if(binary) {
        if(w->non_target_items!=3||w->ignored_containers||result->partial_count!=2)return 0;
        for(int r=0;r<result->row_count;r++)for(int s=0;s<3;s++)if(!binary_no_candidate(&result->rows[r].slots[s]))return 0;
        for(int s=0;s<3;s++) {
            if(!binary_cell_certificate(&row->slots[s],row->left+36*s,row->sy,s,w->strip_box)
               ||memcmp(w->item_boxes[s],row->slots[s].non_target_icon_box,sizeof(w->item_boxes[s]))
               ||!box_valid(w->price_boxes[s])||w->price_boxes[s][0]<row->left+36*s-11
               ||w->price_boxes[s][0]+w->price_boxes[s][2]>row->left+36*s+12
               ||w->price_boxes[s][1]<row->sy+69||w->price_boxes[s][1]+w->price_boxes[s][3]>row->sy+89)return 0;
            for(int k=0;k<4;k++)if(w->name_boxes[s][k])return 0;
        }
        return binary_cell_certificate(&result->partial[0],row->left-36,row->sy,0,w->strip_box)
            &&binary_cell_certificate(&result->partial[1],row->left+108,row->sy,0,w->strip_box);
    }
    int named=0,ignored=0;
    for(int s=0;s<3;s++) {
        const NG2RingSlot *slot=&row->slots[s];const int32_t *pose;
        if(slot->cx!=row->left+36*s||slot->sy!=row->sy||slot->slot!=s||slot->non_target_conflict
           ||!box_valid(w->item_boxes[s])||!box_valid(w->price_boxes[s]))return 0;
        if(slot->kind==R94_BANK_NONTARGET&&slot->outcome==NG2_RING_NON_TARGET&&slot->non_target_id>0
           &&slot->non_target_id<=8&&!slot->ignored_container_id&&proof_score(slot->non_target_icon_score,.94)
           &&proof_score(slot->non_target_name_iou,.94)&&proof_score(slot->non_target_name_coverage,.95)
           &&box_valid(slot->non_target_name_box)&&!memcmp(w->name_boxes[s],slot->non_target_name_box,sizeof(w->name_boxes[s]))) {
            named++;pose=slot->non_target_icon_box;
        } else if(slot->kind==R94_BANK_IGNORED_CONTAINER&&slot->outcome==NG2_RING_IGNORED_CONTAINER&&!slot->non_target_id
            &&(slot->ignored_container_id==9||slot->ignored_container_id==10)&&proof_score(slot->ignored_icon_score,.94)
            &&proof_score(slot->ignored_gold_iou,.94)&&proof_score(slot->ignored_gold_coverage,.95)
            &&proof_score(slot->ignored_dark_iou,.94)&&proof_score(slot->ignored_dark_coverage,.95)) {
            ignored++;pose=slot->ignored_icon_box;
            for(int k=0;k<4;k++)if(w->name_boxes[s][k])return 0;
        } else return 0;
        int bottom=row->sy+(slot->kind==R94_BANK_IGNORED_CONTAINER?90:89);
        const int32_t *price=w->price_boxes[s];
        if(!box_valid(pose)||memcmp(w->item_boxes[s],pose,sizeof(w->item_boxes[s]))||pose[2]>36||pose[3]>36
           ||pose[0]<slot->cx-pose[2]/2-8||pose[0]>slot->cx-pose[2]/2+8||pose[1]<row->sy+24||pose[1]>row->sy+57
           ||pose[0]<w->strip_box[0]||pose[0]+pose[2]>w->strip_box[0]+180||pose[1]+pose[3]>bottom
           ||price[0]<slot->cx-11||price[0]+price[2]>slot->cx+12
           ||price[1]<row->sy+(slot->kind==R94_BANK_IGNORED_CONTAINER?83:69)||price[1]+price[3]>bottom)return 0;
        for(int previous=0;previous<s;previous++) {
            const int32_t *other=w->item_boxes[previous];
            if(pose[0]<other[0]+other[2]&&other[0]<pose[0]+pose[2]&&pose[1]<other[1]+other[3]&&other[1]<pose[1]+pose[3])return 0;
            if(!memcmp(price,w->price_boxes[previous],sizeof(w->price_boxes[s])))return 0;
            if(slot->kind==R94_BANK_NONTARGET&&row->slots[previous].kind==R94_BANK_NONTARGET
               &&!memcmp(w->name_boxes[s],w->name_boxes[previous],sizeof(w->name_boxes[s])))return 0;
        }
    }
    return named==w->non_target_items&&ignored==w->ignored_containers;
}
#endif
#if !NG2_HAS_RING_BANK
int ng2_ring_negative_certificate(const NG2RingResult *result){(void)result;return 0;}
#endif
int ng2_ring_assess_rgba(const unsigned char *rgba,size_t bytes,size_t stride,
                         const NG2RingOptions *options,NG2RingResult *result) {
    if (!result) return NG2_RING_INVALID;
    memset(result,0,sizeof(*result));
    result->abi=NG2_RING_ABI;result->size=sizeof(*result);
    result->status=NG2_RING_INVALID;result->selected_row=-1;result->selected_partial=-1;
    if(!rgba||bytes!=RING_RGBA||stride!=RING_W*4||fegetround()!=FE_TONEAREST
       ||(options&&(options->abi!=NG2_RING_ABI||options->size!=sizeof(*options)
            ||options->reserved||options->mode<0||options->mode>NG2_RING_MODE_TARGET_ONLY||options->fast>1
            ||(options->deadline_ns&&!options->now_ns))))return result->status;
    if(options&&options->now_ns)result->started_ns=options->now_ns(options->context);
    result->finished_ns=result->started_ns;
    int status=checkpoint(options,result);
    if(status)goto done;
    for(int y=0;y<RING_HH;y++) {
        if((status=checkpoint(options,result)))goto done;
        for(int x=0;x<RING_W;x++)if(rgba[4*((size_t)y*RING_W+x)+3]!=255) {
            status=NG2_RING_INVALID;goto done;
        }
    }
    RingObservation observation;
    status=ring_observe(rgba,&observation);
    if(status) {status=status==-2?NG2_RING_ALLOCATION:NG2_RING_KERNEL;goto done;}
    if((status=checkpoint(options,result)))goto done;
    result->row_count=observation.count;
    for(int r=0;r<observation.count;r++) {
        NG2RingRow *row=&result->rows[r];
        row->left=observation.rows[r].left;row->sy=observation.rows[r].sy;
        for(int s=0;s<3;s++) {
            status=score_slot(rgba,&observation,row->left+36*s,row->sy,s,options,result,&row->slots[s]);
            if(status)goto done;
        }
    }
    NG2RingSign observed_signs[12];int sign_count=0;
    status=partial_slots(rgba,&observation,options,result,observed_signs,&sign_count);
    if(status)goto done;
    status=ng2_ring_aggregate(result);
#if NG2_HAS_RING_BANK
    if(!status&&options&&options->mode==NG2_RING_MODE_TARGET_ONLY)binary_preserve_observed_words(result);
    NG2ContainerMasks containers;
    if(!status&&result->outcome==NG2_RING_UNKNOWN&&(!options||options->mode!=NG2_RING_MODE_TARGET_ONLY))status=container_masks(rgba,options,result,&containers);
    if(!status&&result->outcome==NG2_RING_UNKNOWN&&(!options||options->mode!=NG2_RING_MODE_TARGET_ONLY))for(int r=0;r<result->row_count;r++) {
        for(int s=0;s<3;s++) {
            status=bank_slot(rgba,&observation,&containers,options,result,&result->rows[r].slots[s]);
            if(status)goto done;
        }
    }
    if(!status&&result->outcome==NG2_RING_UNKNOWN)
        status=coverage_witness(rgba,&observation,observed_signs,sign_count,options,result);
#endif
    if(!status)status=checkpoint(options,result);
    if(!status&&options&&options->scene&&options->scene->abi_version==NG2_ABI_VERSION
       &&options->scene->struct_size==sizeof(NG2Scene)&&options->scene->state==NG2_FLOOR
       &&options->scene->goods==NG2_GOODS_PARTIAL) {
        result->coverage=NG2_RING_COVERAGE_INCOMPLETE;
        result->partial_safe_no_positive=result->outcome==NG2_RING_UNKNOWN
            &&(result->partial_count>0||result->row_count>0);
    }
    if(!status&&result->coverage==NG2_RING_COVERAGE_COMPLETE) {
        if(!ng2_ring_negative_certificate(result)){status=NG2_RING_KERNEL;goto done;}
        result->outcome=NG2_RING_NEGATIVE;result->reason=NG2_RING_EXPOSED_TARGET_ABSENT;
        result->rows[result->selected_row].outcome=NG2_RING_NEGATIVE;
        result->rows[result->selected_row].reason=NG2_RING_EXPOSED_TARGET_ABSENT;
        status=checkpoint(options,result);
    }
done:
    result->status=(uint32_t)status;
    if(status) {
        result->outcome=NG2_RING_UNKNOWN;result->coverage=NG2_RING_COVERAGE_UNKNOWN;
        result->selected_row=-1;result->selected_partial=-1;
        result->partial_safe_no_positive=0;
    }
    return status;
}
