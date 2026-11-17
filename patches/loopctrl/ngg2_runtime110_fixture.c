/* Procedural incomplete classifier result only. The actual production Runtime
 * worker still hashes and calls the actual kernel on its retained RGBA. */
#include "ngg2_cycle_runtime_fixture.h"
void ng2_fixture_partial_unknown110(const NG2Scene *scene,uint64_t start,uint64_t end,NG2RingResult *out){
    int i;ng2_fixture_cycle_result(scene,start,end,NG2_RING_UNKNOWN,out);
    out->coverage=NG2_RING_COVERAGE_INCOMPLETE;out->partial_safe_no_positive=1;
    out->row_count=1;out->selected_row=0;
    out->rows[0].left=300;out->rows[0].sy=90;out->rows[0].word_slot=-1;
    for(i=0;i<3;++i){NG2RingSlot *s=&out->rows[0].slots[i];
        s->cx=300+36*i;s->sy=90;s->slot=i;s->icon_score=s->icon_upper_bound=.1;
    }
}

/* Masks are extracted by the host driver from the exact compiled Perception
 * source into a temporary header. No independent feature bank is forked. */
#include "runtime110_masks.h"
#include "ngg2/NG2Templates.h"
#include <string.h>
static void fixture110_box(uint8_t *p,int l,int t,int w,int h,int r,int g,int b){
    for(int y=t;y<t+h;++y)for(int x=l;x<l+w;++x){
        if(x<0||x>=896||y<0||y>=414)continue;
        size_t at=((size_t)y*896u+(size_t)x)*4u;p[at]=r;p[at+1]=g;p[at+2]=b;p[at+3]=255;
    }
}
static void fixture110_glyph(uint8_t *p,const NG2Template *t,int grey){
    for(int y=0;y<t->h;++y)for(int x=0;x<t->w;++x)
        if((t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1u)
            fixture110_box(p,t->x+x,t->y+y,1,1,grey,grey,grey);
}
int ng2_fixture_irregular110(uint8_t *p,size_t length,int mode,int direction,int hearts){
    if(!p||length!=896u*414u*4u)return 0;
#if NG2_RUNTIME110_MASKS
    if(mode==1||mode==2){
        fixture110_box(p,312,312,270,24,mode==1?0:255,mode==1?0:200,mode==1?0:80);
        fixture110_glyph(p,&ng2_template_death,200);
        if(mode==1)for(int n=0;n<3;++n){int cx=695+29*n;
            fixture110_box(p,cx-12,6,25,25,0,0,0);
            for(int y=0;y<25;++y)for(int x=0;x<25;++x)
                if((ng2_depleted_rows[y]>>x)&1u)fixture110_box(p,cx-12+x,6+y,1,1,90,0,0);
        }
        return 1;
    }
    if(mode==3){
        memset(p,0,length);for(size_t at=3;at<length;at+=4)p[at]=255;
        fixture110_glyph(p,&ng2_template_restart,200);return 1;
    }
    if(mode==4&&direction>=1&&direction<=4&&hearts>=1&&hearts<=3){
        static const int dx[]={0,-1,1,0,0},dy[]={0,0,0,-1,1};
        int cx=448+36*dx[direction],cy=207+36*dy[direction];
        fixture110_box(p,cx-14,cy-9,29,24,40,140,40);
        for(int n=0;n<hearts;++n){int l=cx-7-9*(hearts-1)+18*n,t=cy-31;
            for(int y=0;y<13;++y)for(int x=0;x<15;++x)
                if((ng2_actor_heart_rows[y]>>x)&1u)fixture110_box(p,l+x,t+y,1,1,200,0,0);
        }
        return 1;
    }
#else
    (void)mode;(void)direction;(void)hearts;
#endif
    return 0;
}
