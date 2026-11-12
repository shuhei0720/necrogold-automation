/* Exact fixed-geometry translation of the Python observation stage.
 * No input, file, network, or device authority. Caller owns cancellation.
 */
#include "ring.h"
#include <stdlib.h>
#include <string.h>

#define PIXELS ((size_t)RING_W*RING_HH)
typedef struct {int count,cx,sy;} Component;
typedef struct {int left,sy,price,count;} Candidate;

static int hud(int x0,int y0,int x1,int y1){
    static const int areas[][4]={{0,0,143,140},{663,0,896,80},{717,315,896,414},
        {405,321,485,414},{0,380,896,414},{429,0,465,45},{866,45,896,290}};
    size_t i;
    for(i=0;i<sizeof(areas)/sizeof(areas[0]);i++)
        if(x0<areas[i][2]&&areas[i][0]<x1&&y0<areas[i][3]&&areas[i][1]<y1)return 1;
    return 0;
}

static int pop32(uint32_t value){
    value=value-((value>>1)&UINT32_C(0x55555555));
    value=(value&UINT32_C(0x33333333))+((value>>2)&UINT32_C(0x33333333));
    value=(value+(value>>4))&UINT32_C(0x0f0f0f0f);
    value=value+(value>>8);value=value+(value>>16);
    return (int)(value&63);
}

static int white23(const RingObservation *out,int y,int x){
    int word=x/64,shift=x%64;
    uint64_t bits=out->white[y][word]>>shift;
    if(shift>41)bits|=out->white[y][word+1]<<(64-shift);
    return pop32((uint32_t)bits&UINT32_C(0x7fffff));
}

/* Python's sorted(component tuples, reverse=True). Equal records keep order. */
static int component_before(Component a,Component b){
    if(a.count!=b.count)return a.count>b.count;
    if(a.cx!=b.cx)return a.cx>b.cx;
    return a.sy>b.sy;
}

static void keep_component(Component top[12],int *length,Component value){
    int at=0,i,old=*length;
    while(at<old&&!component_before(value,top[at]))at++;
    if(at>=12)return;
    if(*length<12)(*length)++;
    for(i=*length-1;i>at;i--)top[i]=top[i-1];
    top[at]=value;
}

static void save_candidate(Candidate rows[24],int *length,Candidate value){
    int i;
    /* Python dict assignment replaces the value without replacing the key. */
    for(i=0;i<*length;i++)if(rows[i].left==value.left&&rows[i].sy==value.sy){
        rows[i]=value;return;
    }
    rows[(*length)++]=value;
}

/* Python row key (-price, -count, sy, left), in ascending order. */
static int row_before(Candidate a,Candidate b){
    if(a.price!=b.price)return a.price>b.price;
    if(a.count!=b.count)return a.count>b.count;
    if(a.sy!=b.sy)return a.sy<b.sy;
    return a.left<b.left;
}

int ring_observe(const unsigned char *rgba,RingObservation *out){
    unsigned char *signs;
    uint32_t *queue;
    Component top[12];Candidate rows[24];
    int top_length=0,row_length=0,x,y,i,j;
    size_t at;
    if(!rgba||!out)return -1;
    memset(out,0,sizeof(*out));
    signs=(unsigned char *)calloc(PIXELS,1);
    queue=(uint32_t *)malloc(PIXELS*sizeof(*queue));
    if(!signs||!queue){free(signs);free(queue);return -2;}
    for(y=0;y<RING_HH;y++)for(x=0;x<RING_W;x++){
        int r,g,b,minimum,maximum,green_limit;
        at=(size_t)y*RING_W+x;
        r=rgba[4*at];g=rgba[4*at+1];b=rgba[4*at+2];
        minimum=r<g?r:g;minimum=minimum<b?minimum:b;
        maximum=r>g?r:g;maximum=maximum>b?maximum:b;
        if(r>140&&g>140&&b>140&&maximum-minimum<40)
            out->white[y][x/64]|=UINT64_C(1)<<(x%64);
        green_limit=(r*1050+999)/1000;if(green_limit>255)green_limit=255;
        if(r>57&&g>r*865/1000&&g<green_limit&&b<(g*240+999)/1000&&!hud(x,y,x+1,y+1))
            signs[at]=1;
    }
    for(at=0;at<PIXELS;at++){
        size_t head=0,tail=0;
        int count=0,x0=RING_W,y0=RING_HH,x1=0,y1=0;
        if(!signs[at])continue;
        signs[at]=0;queue[tail++]=(uint32_t)at;
        while(head<tail){
            uint32_t position=queue[head++];int neighbours[4];
            x=(int)(position%RING_W);y=(int)(position/RING_W);count++;
            if(x<x0)x0=x;
            if(x>x1)x1=x;
            if(y<y0)y0=y;
            if(y>y1)y1=y;
            neighbours[0]=x?(int)position-1:-1;
            neighbours[1]=x+1<RING_W?(int)position+1:-1;
            neighbours[2]=y?(int)position-RING_W:-1;
            neighbours[3]=y+1<RING_HH?(int)position+RING_W:-1;
            for(i=0;i<4;i++)if(neighbours[i]>=0&&signs[neighbours[i]]){
                signs[neighbours[i]]=0;queue[tail++]=(uint32_t)neighbours[i];
            }
        }
        if(count>=150&&x1-x0+1>=18&&x1-x0+1<=48&&y1-y0+1>=16&&y1-y0+1<=40){
            Component value={count,(x0+x1+1)/2,(y0+y1+1)/2};
            keep_component(top,&top_length,value);
        }
    }
    free(signs);free(queue);
    for(i=0;i<top_length;i++)for(j=0;j<2;j++){
        int left=top[i].cx-(j?72:0),sy=top[i].sy,start=sy+69;
        int slot,k,price=0,minimum_bright=RING_W*RING_HH;
        if(left<18||left+72>=878||start<0||start+20>=RING_HH||hud(left-18,sy+24,left+90,start+20))continue;
        for(k=0;k<12;k++){
            int minimum=RING_W*RING_HH;
            for(slot=0;slot<3;slot++){
                int count=0;
                for(y=start+k;y<start+k+9;y++)count+=white23(out,y,left+36*slot-11);
                if(count<minimum)minimum=count;
            }
            if(minimum>price)price=minimum;
        }
        if(price<18)continue;
        for(slot=0;slot<3;slot++){
            int value=0;
            for(y=sy+24;y<sy+66;y++)for(x=left+36*slot-17;x<left+36*slot+18;x++){
                uint32_t luma;
                at=4*((size_t)y*RING_W+x);
                luma=(UINT32_C(19595)*rgba[at]+UINT32_C(38470)*rgba[at+1]+UINT32_C(7471)*rgba[at+2]+UINT32_C(32768))>>16;
                value+=luma>55;
            }
            if(value<minimum_bright)minimum_bright=value;
        }
        if(minimum_bright>=24){Candidate value={left,sy,price,top[i].count};save_candidate(rows,&row_length,value);}
    }
    for(i=1;i<row_length;i++){
        Candidate value=rows[i];j=i;
        while(j>0&&row_before(value,rows[j-1])){rows[j]=rows[j-1];j--;}
        rows[j]=value;
    }
    out->count=row_length<4?row_length:4;
    for(i=0;i<out->count;i++){out->rows[i].left=rows[i].left;out->rows[i].sy=rows[i].sy;}
    return 0;
}
