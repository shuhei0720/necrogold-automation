/* TEST-020: exact 224x104 grayscale motion signatures, 73 candidates.
 * Reproducible i386 build (GCC 14.2.0):
 * gcc -m32 -march=i386 -mno-sse -mno-sse2 -O2 -fPIC -ffreestanding \
 *   -fno-stack-protector -fno-builtin -shared -nostdlib -Wl,--build-id=none \
 *   necroprobe/motion_stats.c -o necroprobe/motion_stats_i386.so
 * All length arguments are bytes. Stats: count,sum_a,sum_b,square_a,square_b.
 * Order: (0,0), then left,right,up,down for each amount 1..18.
 * No allocation, floating point, imports or shared mutable state.
 */
#define SIGNATURE_LENGTH (224u * 104u)
#define CANDIDATES 73u
#define STATS_LENGTH (CANDIDATES * 5u * 4u)
#define LUT_LENGTH (CANDIDATES * 256u)
#define DIFF_LENGTH (CANDIDATES * 4u)

/* Both samples must lie in the same old Pillow valid mask. Intersect its
 * outer rectangle first; test the player/instructions cutout per sample.
 */
static void displacement(unsigned int candidate, int *sx, int *sy) {
    unsigned int direction;
    int amount;
    *sx=0; *sy=0;
    if (!candidate) return;
    amount=(int)(((candidate-1u)>>2)+1u);
    direction=(candidate-1u)&3u;
    if (direction==0) *sx=-amount;
    else if (direction==1) *sx=amount;
    else if (direction==2) *sy=-amount;
    else *sy=amount;
}

int necro_motion_stats(const unsigned char *before, unsigned int before_len,
                       const unsigned char *after, unsigned int after_len,
                       unsigned int *out, unsigned int out_len) {
    unsigned int k;
    if (!before || !after || !out || before_len!=SIGNATURE_LENGTH ||
        after_len!=SIGNATURE_LENGTH || out_len!=STATS_LENGTH) return -1;
    for (k=0;k<CANDIDATES;++k) {
        int sx,sy,x,y,left,right,top,bottom;
        unsigned int count=0,sum_a=0,sum_b=0,square_a=0,square_b=0;
        displacement(k,&sx,&sy);
        left=sx<0?40-sx:40; right=sx>0?179-sx:179;
        top=sy<0?20-sy:20; bottom=sy>0?79-sy:79;
        for (y=top;y<bottom;++y) {
            const unsigned char *a=before+y*224;
            const unsigned char *b=after+(y+sy)*224+sx;
            for (x=left;x<right;++x) {
                unsigned int av,bv;
                if ((y>=36 && x>=90 && x<139) ||
                    (y+sy>=36 && x+sx>=90 && x+sx<139)) continue;
                av=a[x]; bv=b[x];
                if (av<=6 || bv<=6) continue;
                ++count; sum_a+=av; sum_b+=bv;
                square_a+=av*av; square_b+=bv*bv;
            }
        }
        out[5*k]=count; out[5*k+1]=sum_a; out[5*k+2]=sum_b;
        out[5*k+3]=square_a; out[5*k+4]=square_b;
    }
    return 0;
}

int necro_motion_diffs(const unsigned char *before, unsigned int before_len,
                       const unsigned char *after, unsigned int after_len,
                       const unsigned char *luts, unsigned int luts_len,
                       unsigned int *out, unsigned int out_len) {
    unsigned int k;
    if (!before || !after || !luts || !out || before_len!=SIGNATURE_LENGTH ||
        after_len!=SIGNATURE_LENGTH || luts_len!=LUT_LENGTH || out_len!=DIFF_LENGTH) return -1;
    for (k=0;k<CANDIDATES;++k) {
        int sx,sy,x,y,left,right,top,bottom;
        unsigned int total=0;
        const unsigned char *lut=luts+k*256;
        displacement(k,&sx,&sy);
        left=sx<0?40-sx:40; right=sx>0?179-sx:179;
        top=sy<0?20-sy:20; bottom=sy>0?79-sy:79;
        for (y=top;y<bottom;++y) {
            const unsigned char *a=before+y*224;
            const unsigned char *b=after+(y+sy)*224+sx;
            for (x=left;x<right;++x) {
                unsigned int av,bv;
                if ((y>=36 && x>=90 && x<139) ||
                    (y+sy>=36 && x+sx>=90 && x+sx<139)) continue;
                av=a[x]; bv=b[x];
                if (av<=6 || bv<=6) continue;
                bv=lut[bv]; total+=av>bv?av-bv:bv-av;
            }
        }
        out[k]=total;
    }
    return 0;
}
