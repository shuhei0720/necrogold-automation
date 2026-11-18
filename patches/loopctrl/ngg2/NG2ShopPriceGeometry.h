/* Read-only fixed-view merchandise geometry. No target/catalog authority. */
#ifndef NG2_SHOP_PRICE_GEOMETRY_H
#define NG2_SHOP_PRICE_GEOMETRY_H
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int left,sy,lower_slot;
    int boxes[3][4],ink[3];
} NG2ShopPriceGeometry;

static inline int ng2_spg_hud(int x,int y){
    static const int areas[][4]={{0,0,143,140},{663,0,896,80},{717,315,896,414},
        {405,321,485,414},{0,380,896,414},{429,0,465,45},{866,45,896,290}};
    for(unsigned i=0;i<sizeof(areas)/sizeof(areas[0]);++i)
        if(x>=areas[i][0]&&x<areas[i][2]&&y>=areas[i][1]&&y<areas[i][3])return 1;
    return 0;
}
static inline int ng2_spg_white(const unsigned char *rgba,int x,int y){
    const unsigned char *p=rgba+4*((size_t)y*896+x);
    int low=p[0]<p[1]?p[0]:p[1],high=p[0]>p[1]?p[0]:p[1];
    if(p[2]<low)low=p[2];
    if(p[2]>high)high=p[2];
    return low>140&&high-low<40;
}
static inline int ng2_spg_window(const unsigned char *rgba,int cx,int sy,int offset){
    int count=0;
    for(int y=sy+69+offset;y<sy+78+offset;++y)
        for(int x=cx-11;x<cx+12;++x)count+=ng2_spg_white(rgba,x,y);
    return count;
}
/* The caller already has an observed full face. Prices are independent
 * connected x-groups, not fixed numeric amounts or an item's white trim. */
static inline int ng2_spg_price_row(const unsigned char *rgba,int left,int sy,
                                  NG2ShopPriceGeometry *out){
    if(left-54<143||left+126>663||sy+24<45||sy+91>315)return 0;
    NG2ShopPriceGeometry value={0};value.left=left;value.sy=sy;value.lower_slot=-1;
    int common[3][12]={{0}},bright[3]={0},all_baseline=0;
    for(int s=0;s<3;++s){
        int cx=left+36*s;
        for(int k=0;k<12;++k)common[s][k]=ng2_spg_window(rgba,cx,sy,k);
        for(int y=sy+24;y<sy+66;++y)for(int x=cx-17;x<cx+18;++x){
            const unsigned char *p=rgba+4*((size_t)y*896+x);
            bright[s]+=((19595u*p[0]+38470u*p[1]+7471u*p[2]+32768u)>>16)>55;
        }
        if(bright[s]<24)return 0;
    }
    for(int k=0;k<12;++k)all_baseline|=common[0][k]>=18&&common[1][k]>=18&&common[2][k]>=18;
    if(all_baseline)return 0; /* The old observer owns this ordinary row. */
    int first=-1,last=-1000,groups=0;
    for(int x=left-54;x<=left+126;++x){
        int ink=0;
        if(x<left+126)for(int y=sy+69;y<sy+91;++y)ink|=ng2_spg_white(rgba,x,y);
        if(ink){if(first<0)first=x;last=x;}
        if(first>=0&&((!ink&&x-last>3)||x==left+126)){
            int count=0,top=414,bottom=-1,slot=-1,perimeter=0;
            for(int y=sy+69;y<sy+91;++y)for(int xx=first;xx<=last;++xx)
                if(ng2_spg_white(rgba,xx,y)){++count;if(y<top)top=y;if(y>bottom)bottom=y;}
            if(count>=18){
                for(int s=0;s<3;++s)
                    if(first>=left+36*s-11&&last<left+36*s+12)slot=s;
                if(slot<0||value.boxes[slot][2]||bottom-top+1<7||bottom-top+1>9)return 0;
                for(int xx=first;xx<=last;++xx)
                    perimeter|=ng2_spg_white(rgba,xx,top-1)||ng2_spg_white(rgba,xx,bottom+1);
                if(perimeter)return 0;
                int box[4]={first,top,last-first+1,bottom-top+1};
                memcpy(value.boxes[slot],box,sizeof(box));value.ink[slot]=count;++groups;
            }
            first=-1;
        }
    }
    if(groups!=3)return 0;
    int choices=0;
    for(int lower=0;lower<3;++lower){
        const int *late=value.boxes[lower];int top=414,bottom=0,baseline=0;
        if(late[1]<sy+82||late[1]+late[3]>sy+91)continue;
        for(int s=0;s<3;++s)if(s!=lower){
            const int *box=value.boxes[s];
            if(box[1]<top)top=box[1];
            if(box[1]+box[3]>bottom)bottom=box[1]+box[3];
        }
        if(top<sy+69||bottom>sy+89||bottom-top>9||late[1]+late[3]<=bottom)continue;
        for(int k=0;k<12;++k){
            int both=1;for(int s=0;s<3;++s)if(s!=lower)both&=common[s][k]>=18;
            baseline|=both;
        }
        if(baseline){value.lower_slot=lower;++choices;}
    }
    if(choices!=1)return 0;
    *out=value;return 1;
}
/* Find the same canonical full SIGN in Perception and Ring. Work buffers
 * live on the heap; OOM is lack of new geometry, never a partial fallback
 * into input or absence authority. All original pixels remain untouched. */
static inline int ng2_shop_lower_price_geometry(const unsigned char *rgba,size_t bytes,
                                              size_t stride,NG2ShopPriceGeometry *out){
    const size_t count=(size_t)896*414;
    if(!rgba||!out||bytes!=count*4||stride!=896*4)return 0;
    unsigned char *mask=calloc(count,1);uint32_t *queue=malloc(count*sizeof(*queue));
    if(!mask||!queue){free(mask);free(queue);return 0;}
    int signs=0,cx=0,sy=0,full=0;
    for(int y=0;y<414;++y)for(int x=0;x<896;++x){
        size_t at=(size_t)y*896+x;const unsigned char *p=rgba+4*at;
        int limit=(p[0]*1050+999)/1000;if(limit>255)limit=255;
        if(p[3]!=255){free(mask);free(queue);return 0;}
        mask[at]=(unsigned char)(p[0]>57&&p[1]>p[0]*865/1000&&p[1]<limit
            &&p[2]<(p[1]*240+999)/1000&&!ng2_spg_hud(x,y));
    }
    for(size_t at=0;at<count;++at)if(mask[at]){
        size_t head=0,tail=0;int ink=0,x0=896,y0=414,x1=0,y1=0;
        mask[at]=0;queue[tail++]=(uint32_t)at;
        while(head<tail){
            uint32_t pos=queue[head++];int x=(int)(pos%896),y=(int)(pos/896);
            ++ink;if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y;
            int neighbours[4]={x?(int)pos-1:-1,x+1<896?(int)pos+1:-1,
                y?(int)pos-896:-1,y+1<414?(int)pos+896:-1};
            for(int k=0;k<4;++k)if(neighbours[k]>=0&&mask[neighbours[k]]){
                mask[neighbours[k]]=0;queue[tail++]=(uint32_t)neighbours[k];
            }
        }
        int width=x1-x0+1,height=y1-y0+1;
        if(ink>=150&&width>=18&&width<=48&&height>=16&&height<=40){
            ++signs;cx=(x0+x1+1)/2;sy=(y0+y1+1)/2;full=height==29&&width<=36;
            if(signs>1){free(mask);free(queue);return 0;}
        }
    }
    free(mask);free(queue);
    if(signs!=1||!full)return 0;
    NG2ShopPriceGeometry selected={0};int matches=0;
    for(int side=0;side<2;++side){
        NG2ShopPriceGeometry value;
        if(ng2_spg_price_row(rgba,cx-72*side,sy,&value)){selected=value;++matches;}
    }
    if(matches!=1)return 0;
    *out=selected;return 1;
}
#endif
