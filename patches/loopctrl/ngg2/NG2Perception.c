/* Portable RGBA perception, matching gold_scan, shop_navigation and
 * beat_sync.extract. TEST057 calibrates only the bright-floor lower B boundary.
 * No image scaling, interpolation, shared mutable state or external assets. */
#include "NG2Core.h"
#include "NG2Templates.h"
#include "NG2ShopPriceGeometry.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define W NG2_WIDTH
#define H NG2_HEIGHT
#define PIXELS ((size_t)W*H)
static const int ng2_hud[][4]={{0,0,143,140},{663,0,896,80},{717,315,896,414},
    {405,321,485,414},{0,380,896,414},{429,0,465,45},{866,45,896,290}};
static int ng2_min(int a,int b){return a<b?a:b;}
static int ng2_max(int a,int b){return a>b?a:b;}
static int ng2_overlap(int x0,int y0,int x1,int y1,const int *b){
    return x0<b[2] && b[0]<x1 && y0<b[3] && b[1]<y1;
}
static int ng2_hud_overlap(int x0,int y0,int x1,int y1){
    size_t k;for(k=0;k<sizeof(ng2_hud)/sizeof(ng2_hud[0]);++k)
        if(ng2_overlap(x0,y0,x1,y1,ng2_hud[k]))return 1;
    return 0;
}
static int ng2_index(int x,int y){return x>=-11&&x<=11&&y>=-5&&y<=4?(y+5)*23+x+11:-1;}
static unsigned char ng2_gray(const unsigned char *p){
    return (unsigned char)((19595u*p[0]+38470u*p[1]+7471u*p[2]+32768u)>>16);
}
static int ng2_neutral(const unsigned char *p){
    return 2*ng2_min(p[0],ng2_min(p[1],p[2]))>=ng2_max(p[0],ng2_max(p[1],p[2]));
}
static int ng2_template_bit(const NG2Template *t,int x,int y){
    return (t->mask[y*((t->w+7)/8)+x/8]>>(7-x%8))&1;
}
static int ng2_match(const unsigned char *rgba,size_t stride,const unsigned char *gray,
                     const NG2Template *t,int neutral){
    int x,y,inter=0,uni=0;
    for(y=0;y<t->h;++y)for(x=0;x<t->w;++x){
        int observed=gray[(t->y+y)*W+t->x+x]>=t->cutoff;
        int ref=ng2_template_bit(t,x,y);
        if(neutral)observed=observed&&ng2_neutral(rgba+(t->y+y)*stride+4*(t->x+x));
        inter+=observed&&ref;uni+=observed||ref;
    }
    return inter>=t->minimum*ng2_max(1,uni);
}
static int ng2_icon_overlap(const unsigned char *mask){
    int x,y,inter=0,uni=0;const NG2Template *t=&ng2_template_icon;
    for(y=0;y<36;++y)for(x=0;x<36;++x){int a=mask[y*36+x],b=ng2_template_bit(t,x,y);
        inter+=a&&b;uni+=a||b;}
    return inter>=t->minimum*ng2_max(1,uni);
}
/* Long, one-pixel name strokes can survive the vertical-only openings.
 * Require an observed3x9 bar rectangle instead. Zero padding and symmetric
 * erosion/dilation keep the result a subset of the full original mask; the
 * caller still checks the entire36x36 reference and union at the old IoU. */
static void ng2_icon_rect3x9(const unsigned char *mask,unsigned char *eroded,unsigned char *opened){
    int x,y,dx,dy;
    for(y=0;y<36;++y)for(x=0;x<36;++x){int value=1;
        for(dy=-4;dy<=4;++dy)for(dx=-1;dx<=1;++dx)
            if(y+dy<0||y+dy>=36||x+dx<0||x+dx>=36||!mask[(y+dy)*36+x+dx])value=0;
        eroded[y*36+x]=(unsigned char)value;
    }
    for(y=0;y<36;++y)for(x=0;x<36;++x){int value=0;
        for(dy=-4;dy<=4;++dy)for(dx=-1;dx<=1;++dx)
            if(y+dy>=0&&y+dy<36&&x+dx>=0&&x+dx<36&&eroded[(y+dy)*36+x+dx])value=1;
        opened[y*36+x]=(unsigned char)value;
    }
}
static int ng2_pause_icon(const unsigned char *rgba,size_t stride,const unsigned char *gray){
    unsigned char masks[2][1296],eroded[1296],opened[1296];int k,x,y,dy,radius;
    for(k=0;k<2;++k){
        for(y=0;y<36;++y)for(x=0;x<36;++x)
            masks[k][y*36+x]=(unsigned char)(gray[(y+6)*W+x+429]>=(k?85:55)
                &&ng2_neutral(rgba+(y+6)*stride+4*(x+429)));
        if(ng2_icon_overlap(masks[k]))return 1;
    }
    /* Keep the original 13px and 11px openings first. Compressed bars under
     * item labels may also retain 9px runs. Every opening uses the full
     * reference/0.8 IoU, without filling gaps or clipping padding. */
    for(radius=6;radius>=4;--radius)for(k=0;k<2;++k){
        for(y=0;y<36;++y)for(x=0;x<36;++x){int value=1;
            for(dy=-radius;dy<=radius;++dy)if(y+dy<0||y+dy>=36||!masks[k][(y+dy)*36+x])value=0;
            eroded[y*36+x]=(unsigned char)value;
        }
        for(y=0;y<36;++y)for(x=0;x<36;++x){int value=0;
            for(dy=-radius;dy<=radius;++dy)if(y+dy>=0&&y+dy<36&&eroded[(y+dy)*36+x])value=1;
            opened[y*36+x]=(unsigned char)value;
        }
        if(ng2_icon_overlap(opened))return 1;
    }
    for(k=0;k<2;++k){
        ng2_icon_rect3x9(masks[k],eroded,opened);
        if(ng2_icon_overlap(opened))return 1;
    }
    return 0;
}
static int ng2_gold_pixel(const unsigned char *p){
    unsigned r=p[0],g=p[1],b=p[2];
    return r>52&&1000*g>685*r&&100*g<92*r&&100*b>7*g&&100*b<58*g;
}
static int ng2_sign_pixel(const unsigned char *p){
    unsigned r=p[0],g=p[1],b=p[2],high=(r*1050+999)/1000;
    if(high>255)high=255;
    return r>57&&g>r*865/1000&&g<high&&b<(g*240+999)/1000;
}
/* Pillow's BoxBlur rounds each separable integer pass and extends edges. */
static int ng2_blur(const unsigned char *src,unsigned char *dst,int radius){
    unsigned char *ring=(unsigned char*)malloc((size_t)(2*radius+1)*W);
    unsigned sums[W];int x,y,xx,window=2*radius+1;
    if(!ring)return -1;
    memset(sums,0,sizeof(sums));
    for(y=0;y<H+radius;++y){
        unsigned char *incoming;
        if(y>radius){const unsigned char *leaving=ring+(y<window?0:(y-window)%window)*W;
            for(x=0;x<W;++x)sums[x]-=leaving[x];}
        if(y<H){unsigned sum=(unsigned)(radius+1)*src[y*W];
            incoming=ring+(y%window)*W;
            for(xx=1;xx<=radius;++xx)sum+=src[y*W+xx];
            for(x=0;x<W;++x){int leaving=ng2_max(0,x-radius),entering=ng2_min(W-1,x+radius+1);
                incoming[x]=(unsigned char)((sum+(unsigned)radius)/(unsigned)window);
                sum=sum-src[y*W+leaving]+src[y*W+entering];}
        }else incoming=ring+((H-1)%window)*W;
        for(x=0;x<W;++x){sums[x]+=(unsigned)incoming[x]*(unsigned)(y==0?radius+1:1);
            if(y>=radius)dst[(y-radius)*W+x]=(unsigned char)((sums[x]+(unsigned)radius)/(unsigned)window);}
    }
    free(ring);return 0;
}
static int ng2_gold(const unsigned char *rgba,size_t stride,const unsigned char *gray,
                    unsigned char *work,unsigned char *density,NG2Scene *out){
    int x,y,row,col;unsigned peak=0;
    for(y=0;y<H;++y)for(x=0;x<W;++x){
        int excluded=(x<143&&y<54)||(x>=663&&y<80)||(x>=717&&y>=315)
            ||(x>=405&&x<485&&y>=321)||y>=380;
        work[y*W+x]=(unsigned char)(!excluded&&ng2_gold_pixel(rgba+y*stride+4*x)?255:0);
    }
    if(ng2_blur(work,density,13))return -1;
    for(y=0;y<H;++y)for(x=0;x<W;++x)if(density[y*W+x]>peak)peak=density[y*W+x];
    out->gold_peak=(int32_t)peak;
    out->gold_state=peak>=135?NG2_GOLD_CANDIDATE:peak<100?NG2_GOLD_CLEAR:NG2_GOLD_UNKNOWN;
    for(row=0;row<6;++row)for(col=0;col<8;++col){unsigned sum=0,mean,remainder;
        if(col>=2&&col<=5&&row>=2&&row<=4)continue;
        for(y=70+row*48;y<118+row*48;++y)for(x=224+col*56;x<280+col*56;++x)sum+=gray[y*W+x];
        mean=sum/(56*48);remainder=sum%(56*48);
        if(remainder>56*24||(remainder==56*24&&(mean&1)))++mean;
        out->fingerprint[row*8+col]=(unsigned char)mean;
    }
    return 0;
}
typedef struct { int r,g,b,spread,black,count; } NG2MaterialSample;
static NG2MaterialSample ng2_material_sample(const unsigned char *rgba,size_t stride,
    int left,int top,int width,int height){
    unsigned hist[3][256]={{0}},sum[3]={0},squares[3]={0};
    NG2MaterialSample out={0};int med[3],x,y,c,v,n=width*height;
    out.count=n;
    for(y=top;y<top+height;++y)for(x=left;x<left+width;++x){
        const unsigned char *p=rgba+y*stride+4*x;
        out.black+=p[0]<6||p[1]<3;
        for(c=0;c<3;++c){v=p[c];++hist[c][v];sum[c]+=(unsigned)v;squares[c]+=(unsigned)(v*v);}
    }
    for(c=0;c<3;++c){unsigned count=0;
        for(v=0;v<256;++v){count+=hist[c][v];if(count>(unsigned)n/2)break;}
        med[c]=v;
        if((uint64_t)n*squares[c]-(uint64_t)sum[c]*sum[c]>=(uint64_t)4*n*n)out.spread=1;
    }
    out.r=med[0];out.g=med[1];out.b=med[2];return out;
}
static int ng2_material_floor(NG2MaterialSample a){
    int r=a.r,g=a.g,b=a.b;
    return r>=6&&g>=3&&a.spread&&((r<=38&&44*r<=100*b&&100*b<=90*r&&40*r<=100*g&&100*g<=90*r
        &&abs(g-b)<=fmax(2,.18*r))||(38<r&&r<=52&&55*r<=100*b+155&&100*b<=70*r
        &&45*r<=100*g&&100*g<=68*r&&abs(g-b)<=fmax(2,.12*r)));
}
static int ng2_material_stone(NG2MaterialSample a){
    return a.spread&&a.r>40&&100*a.b>53*a.r&&100*a.g>69*a.r;
}
static void ng2_material_proofs(const unsigned char *rgba,size_t stride,NG2Scene *out){
    for(int j=-5;j<5;++j)for(int i=-11;i<12;++i){
        int idx=ng2_index(i,j),cx=448+36*i,cy=207+36*j,gap;
        NG2MaterialSample full,upper,lower,ur,ll;
        if(out->tiles[idx]!=NG2_TILE_DIRT)continue;
        full=ng2_material_sample(rgba,stride,cx-12,cy-12,25,25);
        if(!full.spread)continue;
        if(38<full.r&&full.r<=52){
            gap=55*full.r-(100*full.b+155);
            if(1<=gap&&gap<=77&&100*full.b<=70*full.r&&45*full.r<=100*full.g
                &&100*full.g<=68*full.r&&abs(full.g-full.b)<=fmax(2,.12*full.r)){
                upper=ng2_material_sample(rgba,stride,cx-12,cy-12,25,12);
                lower=ng2_material_sample(rgba,stride,cx-12,cy,25,13);
                ur=ng2_material_sample(rgba,stride,cx,cy-12,13,12);
                ll=ng2_material_sample(rgba,stride,cx-12,cy,12,13);
                if((ng2_material_floor(upper)&&ng2_material_floor(lower))
                    ||(ng2_material_floor(ur)&&ng2_material_floor(ll))){out->tiles[idx]=NG2_TILE_FLOOR;continue;}
            }
        }
        if(6<=full.r&&full.r<=12){
            upper=ng2_material_sample(rgba,stride,cx-12,cy-12,25,12);
            lower=ng2_material_sample(rgba,stride,cx-12,cy,25,13);
            if(100*upper.black>=95*upper.count&&100*(lower.count-lower.black)>=90*lower.count
                &&16<=lower.r&&lower.r<=52&&ng2_material_floor(lower)){
                out->tiles[idx]=NG2_TILE_FLOOR;continue;
            }
        }
        gap=53*full.r-100*full.b;
        if(full.r>40&&100*full.g>69*full.r&&0<=gap&&gap<=76){
            ur=ng2_material_sample(rgba,stride,cx,cy-12,13,12);
            ll=ng2_material_sample(rgba,stride,cx-12,cy,12,13);
            if(ng2_material_stone(ur)&&ng2_material_stone(ll))out->tiles[idx]=NG2_TILE_STONE;
        }
    }
}

/* A separately observed lower floor may coexist with a black upper half.
 * Require current pixel colour/texture, never infer it from a passage shape. */
static void ng2_black_entry_floor(const unsigned char *rgba,size_t stride,NG2Scene *out){
    for(int j=-5;j<5;++j)for(int i=-11;i<12;++i){
        int idx=ng2_index(i,j),cx=448+36*i,cy=207+36*j;
        NG2MaterialSample full,upper,lower;
        if(out->tiles[idx]!=NG2_TILE_UNKNOWN||ng2_hud_overlap(cx-12,cy-12,cx+13,cy+13))continue;
        full=ng2_material_sample(rgba,stride,cx-12,cy-12,25,25);
        if(!full.spread||(full.r>=6&&full.g>=3)||full.r>12||full.g>12||full.b>12)continue;
        upper=ng2_material_sample(rgba,stride,cx-12,cy-12,25,12);
        lower=ng2_material_sample(rgba,stride,cx-12,cy,25,13);
        if(100*upper.black>=95*upper.count&&100*(lower.count-lower.black)>=90*lower.count
            &&16<=lower.r&&lower.r<=52&&ng2_material_floor(lower))out->tiles[idx]=NG2_TILE_FLOOR;
    }
}

/* Recover observed floor around a narrow occlusion using two fixed, disjoint
 * bands in one 36px tile. HUD exclusion covers all 750 sampled pixels. */
static void ng2_separated_floor_bands(const unsigned char *rgba,size_t stride,NG2Scene *out){
    for(int j=-5;j<5;++j)for(int i=-11;i<12;++i){
        int idx=ng2_index(i,j),cx=448+36*i,cy=207+36*j;
        NG2MaterialSample full,upper,lower;
        if(out->tiles[idx]!=NG2_TILE_DIRT||ng2_hud_overlap(cx-12,cy-12,cx+13,cy+18))continue;
        full=ng2_material_sample(rgba,stride,cx-12,cy-12,25,25);
        if(!full.spread||full.r<39||full.r>52||100*full.g<45*full.r||100*full.g>68*full.r
            ||100*full.b<=25*full.r||100*full.b>=44*full.r)continue;
        upper=ng2_material_sample(rgba,stride,cx-12,cy-12,25,12);
        lower=ng2_material_sample(rgba,stride,cx-12,cy+13,25,5);
        if(upper.r>=16&&lower.r>=16&&ng2_material_floor(upper)&&ng2_material_floor(lower))
            out->tiles[idx]=NG2_TILE_FLOOR;
    }
}

static void ng2_tiles(const unsigned char *rgba,size_t stride,NG2Scene *out){
    int i,j,x,y,c,v,k;unsigned hist[3][256],sum[3],squares[3];
    for(j=-5;j<5;++j)for(i=-11;i<12;++i){
        int med[3],spread=0,gold=0,idx=ng2_index(i,j),r,g,b;int cx=448+36*i,cy=207+36*j;
        if(i==0&&j==0){out->tiles[idx]=NG2_TILE_FLOOR;continue;}
        if(ng2_hud_overlap(cx-12,cy-12,cx+13,cy+13))continue;
        memset(hist,0,sizeof(hist));memset(sum,0,sizeof(sum));memset(squares,0,sizeof(squares));
        for(y=cy-12;y<cy+13;++y)for(x=cx-12;x<cx+13;++x){const unsigned char *p=rgba+y*stride+4*x;
            gold+=ng2_gold_pixel(p);
            for(c=0;c<3;++c){v=p[c];++hist[c][v];sum[c]+=(unsigned)v;squares[c]+=(unsigned)(v*v);}}
        if(gold>=280){out->tiles[idx]=NG2_TILE_GOLD;continue;}
        for(c=0;c<3;++c){unsigned count=0;for(v=0;v<256;++v){count+=hist[c][v];if(count>312)break;}
            med[c]=v;if((uint64_t)625*squares[c]-(uint64_t)sum[c]*sum[c]>=(uint64_t)4*625*625)spread=1;}
        r=med[0];g=med[1];b=med[2];if(r<6||g<3)continue;
        if(spread&&((r<=38&&44*r<=100*b&&100*b<=90*r&&40*r<=100*g&&100*g<=90*r
                    &&abs(g-b)<=fmax(2,.18*r))||(38<r&&r<=52&&55*r<=100*b+155&&100*b<=70*r
                    &&45*r<=100*g&&100*g<=68*r&&abs(g-b)<=fmax(2,.12*r))))out->tiles[idx]=NG2_TILE_FLOOR;
        else if(r>40&&100*b>53*r&&100*g>69*r)out->tiles[idx]=NG2_TILE_STONE;
        else if(100*b<55*r&&100*g>42*r)out->tiles[idx]=NG2_TILE_DIRT;
        else if(35<=r&&r<=140&&g>=8&&18*r<=100*g&&100*g<=42*r&&100*b<=25*r&&spread)out->tiles[idx]=7; /* temporary wood */
    }
    /* Gates depend on original gold neighbours; replacement does not alter them. */
    for(j=-5;j<5;++j)for(i=-11;i<12;++i){int idx=ng2_index(i,j),a,b,t=out->tiles[idx];
        if(t!=NG2_TILE_DIRT&&t!=NG2_TILE_STONE&&t!=7)continue;
        a=ng2_index(i-1,j);b=ng2_index(i+1,j);
        k=a>=0&&b>=0&&out->tiles[a]==NG2_TILE_GOLD&&out->tiles[b]==NG2_TILE_GOLD;
        a=ng2_index(i,j-1);b=ng2_index(i,j+1);
        if(k||(a>=0&&b>=0&&out->tiles[a]==NG2_TILE_GOLD&&out->tiles[b]==NG2_TILE_GOLD))out->tiles[idx]=NG2_TILE_DOOR;
        else if(t==7)out->tiles[idx]=NG2_TILE_UNKNOWN;
    }
}
/* The narrow, edge-on iron leaf can occupy too little of the 25x25 material
 * sample to change its FLOOR median. Recover only that observed vertical
 * leaf between an existing upper/lower GOLD bracket. An opened, rotated panel
 * has upper-band pixels but no matching lower stripe; it stays FLOOR. */
static void ng2_thin_gate_doors(const unsigned char *rgba,size_t stride,NG2Scene *out){
    int i,j;
    if(out->state!=NG2_FLOOR||out->gold_state!=NG2_GOLD_CANDIDATE||out->goods!=NG2_GOODS_UNKNOWN)return;
    for(j=-5;j<5;++j)for(i=-11;i<12;++i){
        int idx=ng2_index(i,j),above=ng2_index(i,j-1),below=ng2_index(i,j+1);
        int cx=448+36*i,cy=207+36*j,column,row,qualified=0,protected=0;
        if((!i&&!j)||out->tiles[idx]!=NG2_TILE_FLOOR||out->protected_cells[idx]
            ||above<0||below<0||out->tiles[above]!=NG2_TILE_GOLD||out->tiles[below]!=NG2_TILE_GOLD
            ||out->protected_cells[above]||out->protected_cells[below]
            ||cx-8<0||cx-4>W||cy-23<0||cy+2>H
            ||ng2_hud_overlap(cx-8,cy-23,cx-4,cy+2))continue;
        for(row=0;row<25&&!protected;++row)for(column=0;column<4;++column){
            int x=cx-8+column,y=cy-23+row;
            int sample=ng2_index((x-34)/36-11,(y-9)/36-5);
            if(sample<0||out->protected_cells[sample]){protected=1;break;}
        }
        if(protected)continue;
        for(column=0;column<4;++column){
            int upper=0,lower=0;
            for(row=0;row<25;++row){
                const unsigned char *p=rgba+(cy-23+row)*stride+4*(cx-8+column);
                int low=ng2_min(p[0],ng2_min(p[1],p[2]));
                int high=ng2_max(p[0],ng2_max(p[1],p[2]));
                if(low>=45&&high-low<=45){if(row<12)++upper;else ++lower;}
            }
            qualified+=upper+lower>=20&&upper>=8&&lower>=8;
        }
        if(qualified>=3)out->tiles[idx]=NG2_TILE_DOOR;
    }
}
static int ng2_even_round(double value){
    double lower=floor(value),fraction=value-lower;
    return (int)(lower+(fraction>.5||(fraction==.5&&fmod(lower,2)!=0)));
}
static int ng2_white(const unsigned char *rgba,size_t stride,int x,int y){
    const unsigned char *p;int low,high;
    if(x<0||x>=W||y<0||y>=H)return 0;
    p=rgba+y*stride+4*x;low=ng2_min(p[0],ng2_min(p[1],p[2]));high=ng2_max(p[0],ng2_max(p[1],p[2]));
    return low>140&&high-low<40;
}
static void ng2_protect(NG2Scene *out,const unsigned char *items){
    int x,y,d;static const int delta[5][2]={{0,0},{-1,0},{1,0},{0,-1},{0,1}};
    /* An item just outside the tile array can still protect an edge tile. */
    for(y=-6;y<=7;++y)for(x=-13;x<=13;++x)if(items[(y+6)*27+x+13]){
        int idx=ng2_index(x,y);if(idx>=0)out->tiles[idx]=NG2_TILE_ITEM;
        for(d=0;d<5;++d){idx=ng2_index(x+delta[d][0],y+delta[d][1]);if(idx>=0)out->protected_cells[idx]=1;}
    }
}
static int ng2_merchandise(const unsigned char *rgba,size_t stride,const unsigned char *gray,
                          unsigned char *work,unsigned char *density,NG2Scene *out){
    unsigned char partial[27*14]={0},visible[27*14];int x,y,n,high,px,py,offset,dy,any=0;
    for(y=0;y<H;++y)for(x=0;x<W;++x)work[y*W+x]=(unsigned char)(
        !ng2_hud_overlap(x,y,x+1,y+1)&&ng2_sign_pixel(rgba+y*stride+4*x)?255:0);
    if(ng2_blur(work,density,14))return -1;
    for(n=0;n<12;++n){high=0;px=py=0;
        for(y=0;y<H;++y)for(x=0;x<W;++x)if(density[y*W+x]>high){high=density[y*W+x];px=x;py=y;}
        if(high<96)break;
        for(y=ng2_max(0,py-23);y<ng2_min(H,py+24);++y)for(x=ng2_max(0,px-23);x<ng2_min(W,px+24);++x)density[y*W+x]=0;
        for(offset=0;offset<=72;offset+=72){int left=px-offset;
            if(left<18||left+72>=878)continue;
            for(dy=-4;dy<=6;dy+=2){int sy=py+dy,start=sy+69,prices[3][12]={{0}},item_count=0,price_count=0,slot,k;
                memset(visible,0,sizeof(visible));
                for(slot=0;slot<3;++slot){int cx=left+36*slot;
                    int tx=ng2_even_round((cx-448)/36.0),ty=ng2_even_round((sy+48-207)/36.0);
                    if(tx>=-13&&tx<=13&&ty>=-6&&ty<=7){partial[(ty+6)*27+tx+13]=1;visible[(ty+6)*27+tx+13]=1;any=1;}
                }
                if(start<0||start+20>=H)continue;
                for(slot=0;slot<3;++slot){int cx=left+36*slot,bright=0;
                    for(k=0;k<12;++k)for(y=start+k;y<start+k+9;++y)for(x=cx-11;x<cx+12;++x)prices[slot][k]+=ng2_white(rgba,stride,x,y);
                    for(y=sy+24;y<sy+66;++y)for(x=cx-17;x<cx+18;++x)
                        if(x>=0&&x<W&&y>=0&&y<H&&gray[y*W+x]>55)++bright;
                    item_count+=bright>=24;
                }
                for(k=0;k<12;++k){int count=0;for(slot=0;slot<3;++slot)count+=prices[slot][k]>=18;if(count>price_count)price_count=count;}
                if(price_count==3&&item_count==3&&!ng2_hud_overlap(left-18,sy+24,left+90,start+20)){
                    out->goods=NG2_GOODS_VISIBLE;ng2_protect(out,visible);return 0;}
            }
        }
    }
    if(any){
        NG2ShopPriceGeometry price_row;
        if(ng2_shop_lower_price_geometry(rgba,(size_t)W*H*4,stride,&price_row)){
            memset(visible,0,sizeof(visible));
            for(int slot=0;slot<3;++slot){
                int tx=ng2_even_round((price_row.left+36*slot-448)/36.0);
                int ty=ng2_even_round((price_row.sy+48-207)/36.0);
                visible[(ty+6)*27+tx+13]=1;
            }
            out->goods=NG2_GOODS_VISIBLE;ng2_protect(out,visible);return 0;
        }
        out->goods=NG2_GOODS_PARTIAL;ng2_protect(out,partial);
    }
    return 0;
}
/* Raw paired gold can extend below the map or behind its coarse HUD mask.
 * An external row is a hint only; never shift its cells into the map. An
 * in-map pair is restored only at its actual, previously masked coordinates.
 * Gold color/count, global density and the original HUD masks stay intact. */
static void ng2_lower_fringe(const unsigned char *rgba,size_t stride,NG2Scene *out){
    unsigned counts[3][23];int i,j,x,y,k,pairs=0,chosen_x=0,chosen_y=0;
    if(out->state!=NG2_FLOOR||out->goods!=NG2_GOODS_UNKNOWN)return;
    for(k=0;k<NG2_TILE_COUNT;++k)
        if(out->tiles[k]==NG2_TILE_GOLD||out->protected_cells[k])return;
    for(j=3;j<=5;++j)for(i=-11;i<=11;++i){
        int cx=448+36*i,cy=207+36*j;unsigned count=0;
        for(y=cy-12;y<cy+13;++y)for(x=cx-12;x<cx+13;++x)
            count+=(unsigned)ng2_gold_pixel(rgba+y*stride+4*x);
        counts[j-3][i+11]=count;
    }
    for(j=3;j<=5;++j)for(i=-10;i<=10;++i){
        if(counts[j-3][i+10]<280||counts[j-3][i+12]<280||counts[j-3][i+11]>=280)continue;
        if(j<5){
            int a=ng2_index(i-1,j),b=ng2_index(i+1,j);
            int left=448+36*(i-1),right=448+36*(i+1),cy=207+36*j;
            if(a<0||b<0||out->tiles[a]!=NG2_TILE_UNKNOWN||out->tiles[b]!=NG2_TILE_UNKNOWN
                ||!ng2_hud_overlap(left-12,cy-12,left+13,cy+13)
                ||!ng2_hud_overlap(right-12,cy-12,right+13,cy+13))continue;
        }
        ++pairs;chosen_x=i;chosen_y=j;
    }
    if(pairs!=1)return;
    if(chosen_y==5)out->gold_state=NG2_GOLD_EDGE_DOWN;
    else {
        int a=ng2_index(chosen_x-1,chosen_y),b=ng2_index(chosen_x+1,chosen_y);
        if(a<0||b<0)return;
        out->tiles[a]=NG2_TILE_GOLD;out->tiles[b]=NG2_TILE_GOLD;
        out->gold_state=NG2_GOLD_CANDIDATE;
    }
}
static int ng2_double_compare(const void *a,const void *b){double x=*(const double*)a,y=*(const double*)b;return (x>y)-(x<y);}
static double ng2_median(double *values,int count){qsort(values,(size_t)count,sizeof(*values),ng2_double_compare);return count%2?values[count/2]:(values[count/2-1]+values[count/2])/2;}
static double ng2_mod1(double v){double r=fmod(v,1);return r<0?r+1:r;}
static double ng2_distance(double a,double b){return ng2_mod1(a-b+.5)-.5;}
static int ng2_circle(const double *v,int n,double *out){
    double real=0,imag=0,tau=2*3.14159265358979323846;int k;
    for(k=0;k<n;++k){real+=cos(tau*v[k]);imag+=sin(tau*v[k]);}
    if(hypot(real,imag)<.5*n)return 0;
    *out=ng2_mod1(atan2(imag,real)/tau);return 1;
}
static void ng2_beat_extract(const unsigned char *rgba,size_t stride,NG2Scene *out){
    /* Accepted groups occupy >=2px and are separated by >=4px: their means
     * differ by >=5px. A 24px pair-sum band has at most5 partners per group,
     * and each side has fewer than86 groups, so 856 centers is conservative. */
    int x,y,active[856],count=0,k,start;double left[428],right[428],gaps[856],adjacent[856],centers[856];
    double phases[856],spacing,center,ql,qr,q;int nl=0,nr=0,ng=0,na=0,nc=0;
    for(x=20;x<876;++x){int hits=0;if(x>=418&&x<=474)continue;
        for(y=350;y<387;++y){const unsigned char *p=rgba+y*stride+4*x;int r=p[0],g=p[1],b=p[2];
            hits+=g>=75&&b>=60&&g>ng2_min(255,r+35)&&b>ng2_min(255,r+25);}
        if(hits>=18)active[count++]=x;
    }
    for(start=0;start<count;){int end=start+1,sum=active[start];double pos;
        while(end<count&&active[end]-active[end-1]<=3){sum+=active[end];++end;}
        if(active[end-1]-active[start]+1>=2&&active[end-1]-active[start]+1<=10){pos=(double)sum/(end-start);
            if(pos<418)left[nl++]=pos;else if(pos>474)right[nr++]=pos;}
        start=end;
    }
    if(nl<2||nr<2)return;
    for(k=1;k<nl;++k)gaps[ng++]=left[k]-left[k-1];
    for(k=1;k<nr;++k)gaps[ng++]=right[k]-right[k-1];
    for(k=0;k<ng;++k)if(gaps[k]>=90&&gaps[k]<=120)adjacent[na++]=gaps[k];
    if(na<2)return;
    spacing=ng2_median(adjacent,na);
    for(k=0;k<ng;++k)if(fabs(gaps[k]/spacing-ng2_even_round(gaps[k]/spacing))>.045)return;
    for(x=0;x<nl;++x)for(y=0;y<nr;++y){double c=(left[x]+right[y])/2;if(c>=440&&c<=452)centers[nc++]=c;}
    if(nc<2)return;
    center=ng2_median(centers,nc);
    for(k=0;k<nc;++k)if(fabs(centers[k]-center)>2.5)return;
    for(k=0;k<nl;++k)phases[k]=ng2_mod1((center-left[k])/spacing);
    for(k=0;k<nr;++k)phases[nl+k]=ng2_mod1((right[k]-center)/spacing);
    if(!ng2_circle(phases,nl,&ql)||!ng2_circle(phases+nl,nr,&qr)||fabs(ng2_distance(ql,qr))>.045)return;
    if(!ng2_circle(phases,nl+nr,&q))return;
    for(k=0;k<nl+nr;++k)if(fabs(ng2_distance(phases[k],q))>.045)return;
    out->beat_valid=1;out->beat_remaining=q;out->beat_spacing=spacing;out->beat_center=center;
}
int ng2_analyze_rgba(const uint8_t *rgba,size_t length,size_t stride,NG2Scene *out){
    unsigned char *gray,*work,*density;int x,y,result=0;
    if(!out)return -1;
    memset(out,0,sizeof(*out));out->abi_version=NG2_ABI_VERSION;out->struct_size=sizeof(*out);
    if(!rgba||stride<W*4u||stride>7680u||length!=stride*H)return -1;
    /* Entire image must be opaque, even HUD/ignored pixels. Padding is ignored. */
    for(y=0;y<H;++y)for(x=0;x<W;++x)if(rgba[y*stride+4*x+3]!=255)return -1;
    gray=(unsigned char*)malloc(PIXELS*3);
    if(!gray)return -1;
    work=gray+PIXELS;density=work+PIXELS;
    for(y=0;y<H;++y)for(x=0;x<W;++x)gray[y*W+x]=ng2_gray(rgba+y*stride+4*x);
    if(ng2_match(rgba,stride,gray,&ng2_template_continue,0)){
        out->state=NG2_PAUSE;out->restart_label=ng2_match(rgba,stride,gray,&ng2_template_restart,0);
    }else if(ng2_pause_icon(rgba,stride,gray)&&ng2_match(rgba,stride,gray,&ng2_template_footer,1)
        &&ng2_match(rgba,stride,gray,&ng2_template_zone_one,1)&&ng2_match(rgba,stride,gray,&ng2_template_floor_one,1)
        &&!ng2_match(rgba,stride,gray,&ng2_template_death,0)){
        out->state=NG2_FLOOR;
        if(ng2_gold(rgba,stride,gray,work,density,out))result=-1;
        else {ng2_tiles(rgba,stride,out);ng2_material_proofs(rgba,stride,out);ng2_black_entry_floor(rgba,stride,out);ng2_separated_floor_bands(rgba,stride,out);result=ng2_merchandise(rgba,stride,gray,work,density,out);}
        if(!result){ng2_thin_gate_doors(rgba,stride,out);ng2_lower_fringe(rgba,stride,out);
            for(y=0;y<H;y+=4)for(x=0;x<W;x+=4)out->signature[(y/4)*224+x/4]=gray[y*W+x];
            ng2_beat_extract(rgba,stride,out);}
    }
    free(gray);
    if(result){memset(out,0,sizeof(*out));out->abi_version=NG2_ABI_VERSION;out->struct_size=sizeof(*out);}
    return result;
}
size_t ng2_orient_rgba(const uint8_t *source,size_t source_length,
                       int32_t width,int32_t height,int32_t orientation,
                       uint8_t *destination,size_t destination_length){
    size_t pixels,packed,copied=0;
    uintptr_t source_address,destination_address,source_end,destination_end;
    int32_t output_width,output_height,x,y;
    if(!source||!destination||width<1||height<1||width>4096||height>4096
        ||orientation<1||orientation>8)return 0;
    pixels=(size_t)width*(size_t)height;
    if(pixels>8000000u||pixels>SIZE_MAX/4u)return 0;
    packed=pixels*4u;
    if(source_length!=packed||destination_length!=packed)return 0;
    source_address=(uintptr_t)source;destination_address=(uintptr_t)destination;
    if(source_length>UINTPTR_MAX-source_address
        ||destination_length>UINTPTR_MAX-destination_address)return 0;
    source_end=source_address+source_length;destination_end=destination_address+destination_length;
    if(source_address<destination_end&&destination_address<source_end)return 0;
    output_width=orientation>=5?height:width;
    output_height=orientation>=5?width:height;
    for(y=0;y<output_height;++y){
        for(x=0;x<output_width;++x){
            int32_t sx,sy;size_t a,b;
            switch(orientation){
                case 2:sx=width-1-x;sy=y;break;
                case 3:sx=width-1-x;sy=height-1-y;break;
                case 4:sx=x;sy=height-1-y;break;
                case 5:sx=y;sy=x;break;
                case 6:sx=y;sy=height-1-x;break;
                case 7:sx=width-1-y;sy=height-1-x;break;
                case 8:sx=width-1-y;sy=x;break;
                default:sx=x;sy=y;break;
            }
            a=((size_t)sy*(size_t)width+(size_t)sx)*4u;
            b=((size_t)y*(size_t)output_width+(size_t)x)*4u;
            destination[b]=source[a];destination[b+1]=source[a+1];
            destination[b+2]=source[a+2];destination[b+3]=255;
        }
        copied+=(size_t)output_width;
    }
    return copied;
}
int ng2_fingerprint_changed(const uint8_t *before,const uint8_t *after){
    int k,count=0;unsigned cols=0,rows=0;if(!before||!after)return 0;
    for(k=0;k<48;++k)if(abs((int)before[k]-after[k])>=12){++count;cols|=1u<<(k%8);rows|=1u<<(k/8);}
    if(count<6)return 0;
    count=0;for(k=0;k<8;++k)count+=(cols>>k)&1u;if(count<3)return 0;
    count=0;for(k=0;k<6;++k)count+=(rows>>k)&1u;return count>=2;
}

/* Separate positive irregular observations. Neither these immutable shape
 * masks nor the companion change ng2_analyze_rgba's Scene/terrain output.
 * Depleted HUD shape382bits: existing immutable R12 death reference.
 * Miniheart137bits: generic health marker calibrated on TEST109 fe54/244;
 * only this derived binary glyph is stored, never the private frame. */
static const uint32_t ng2_depleted_rows[25]={
    0x0u,0x1fc3f8u,0x3fe7fcu,0x7ffffeu,0x7ffffeu,0xffffffu,0xffffffu,
    0xffffffu,0xffffffu,0xffffffu,0xffffffu,0x7ffffeu,0x7ffffeu,0x3ffffcu,
    0x1ffff8u,0xffff0u,0xffff0u,0x7ffe0u,0x3ffc0u,0x1ff80u,0x7e00u,
    0x3c00u,0x1800u,0x0u,0x0u};
static const uint16_t ng2_actor_heart_rows[13]={
    0x3c3cu,0x7f7eu,0x7fffu,0x7fffu,0x7fffu,0x7fffu,0x7ffeu,
    0x3ffcu,0x1ff8u,0xff0u,0x7e0u,0x3c0u,0x180u};
static int ng2_irregular_red(const unsigned char *p,int bright){
    return bright?p[0]>=125&&p[0]>=p[1]+45&&p[0]>=p[2]+45:
        p[0]>=40&&p[0]>=p[1]+25&&p[0]>=p[2]+25;
}
static void ng2_irregular_template(const unsigned char *rgba,size_t stride,
    const unsigned char *gray,const NG2Template *t,int neutral,int *intersection,int *uni){
    int x,y;*intersection=0;*uni=0;
    for(y=0;y<t->h;++y)for(x=0;x<t->w;++x){
        int a=gray[(t->y+y)*W+t->x+x]>=t->cutoff
            &&(!neutral||ng2_neutral(rgba+(t->y+y)*stride+4*(t->x+x)));
        int b=ng2_template_bit(t,x,y);*intersection+=a&&b;*uni+=a||b;
    }
}
static void ng2_irregular_health(const unsigned char *rgba,size_t stride,
    NG2IrregularObservation *out){
    int s,x,y;
    for(s=0;s<3;++s){int cx=695+29*s,inter=0,uni=0,red=0,dark=0,bright=0;
        for(y=0;y<25;++y)for(x=0;x<25;++x){
            const unsigned char *p=rgba+(6+y)*stride+4*(cx-12+x);
            int a=ng2_irregular_red(p,0),b=(ng2_depleted_rows[y]>>x)&1u;
            inter+=a&&b;uni+=a||b;
        }
        for(y=10;y<28;++y)for(x=cx-8;x<cx+9;++x){
            const unsigned char *p=rgba+y*stride+4*x;
            int a=ng2_irregular_red(p,0);red+=a;dark+=a&&p[0]<=124;
            bright+=ng2_irregular_red(p,1);
        }
        out->heart_inter[s]=inter;out->heart_union[s]=uni;
        out->heart_red[s]=red;out->heart_dark[s]=dark;out->heart_bright[s]=bright;
        out->empty_hearts+=100*inter>=90*uni&&100*inter>=95*382
            &&red>=225&&dark>=192&&bright<=48;
    }
}
/* 136x39 is a maximality guard, not a cropped candidate box. A centered
 * three-heart bar ends within32.5px; its fourth aligned neighbor ends within
 *51.5px. The complete fourth component therefore cannot hide at this edge. */
#define NG2_ACTOR_GUARD_W 136
#define NG2_ACTOR_GUARD_H 39
#define NG2_ACTOR_GUARD_PIXELS (NG2_ACTOR_GUARD_W*NG2_ACTOR_GUARD_H)
typedef struct {int left,top,inter,uni,label;} NG2ActorMarker;
typedef struct {int left,top,width,height,count,label;} NG2ActorFragment;
/* A rejected fourth marker must not disappear from a maximal three-bar.
 * Only a complete connected fragment, with a full glyph axis and at least
 *56 supported reference pixels, is positive partial-marker evidence.56 is
 * the smallest ink count among the four geometric halves of the137bit glyph.
 * Ordinary brown floor pixels and a separately placed bat are not fragments
 * cropped into the expected next slot. This veto grants no new input. */
static int ng2_actor_partial_extension(const uint16_t *labels,int guard_left,int guard_top,
    const NG2ActorFragment *fragments,int count,const NG2ActorMarker *markers,
    const int *members,int total){
    int side,step,dy,k,j;
    for(side=0;side<2;++side){NG2ActorMarker end=markers[members[side?total-1:0]];
        for(step=17;step<=19;++step)for(dy=-1;dy<=1;++dy){
            int left=end.left+(side?step:-step),top=end.top+dy;
            for(k=0;k<count;++k){NG2ActorFragment f=fragments[k];int adopted=0,inter=0,x,y;
                if(f.left<left||f.left+f.width>left+15||f.top<top||f.top+f.height>top+13)continue;
                for(j=0;j<total;++j)adopted|=f.label==markers[members[j]].label;
                if(adopted)continue;
                for(y=f.top;y<f.top+f.height;++y)for(x=f.left;x<f.left+f.width;++x)
                    if(labels[(y-guard_top)*NG2_ACTOR_GUARD_W+x-guard_left]==f.label)
                        inter+=(ng2_actor_heart_rows[y-top]>>(x-left))&1u;
                if(inter>=56&&100*inter>=90*f.count)return 1;
            }
        }
    }
    return 0;
}
static int ng2_irregular_actor(const unsigned char *rgba,size_t stride,
    const unsigned char *gray,int direction,NG2IrregularObservation *out){
    static const int dx[4]={-1,1,0,0},dy[4]={0,0,-1,1};
    unsigned char grouped[64]={0};uint16_t mask[NG2_ACTOR_GUARD_PIXELS];
    uint16_t stack[NG2_ACTOR_GUARD_PIXELS];
    NG2ActorMarker markers[64];NG2ActorFragment fragments[96];
    int n=0,fragment_count=0,next_label=2,cx=448+36*dx[direction],cy=207+36*dy[direction];
    int left=cx-68,top=cy-43,x,y,k,body_luma=0,body_sat=0;
    for(y=0;y<NG2_ACTOR_GUARD_H;++y)for(x=0;x<NG2_ACTOR_GUARD_W;++x)
        mask[y*NG2_ACTOR_GUARD_W+x]=(uint16_t)ng2_irregular_red(rgba+(top+y)*stride+4*(left+x),1);
    for(k=0;k<NG2_ACTOR_GUARD_PIXELS;++k)if(mask[k]==1){
        int count=0,used=0,label=next_label++,x0=NG2_ACTOR_GUARD_W,x1=0,y0=NG2_ACTOR_GUARD_H,y1=0;
        stack[used++]=(uint16_t)k;mask[k]=(uint16_t)label;
        while(used){int at=stack[--used],xx=at%NG2_ACTOR_GUARD_W,yy=at/NG2_ACTOR_GUARD_W,a,b;
            ++count;x0=ng2_min(x0,xx);x1=ng2_max(x1,xx+1);y0=ng2_min(y0,yy);y1=ng2_max(y1,yy+1);
            for(b=-1;b<=1;++b)for(a=-1;a<=1;++a){int nx=xx+a,ny=yy+b,pos;
                if(nx<0||nx>=NG2_ACTOR_GUARD_W||ny<0||ny>=NG2_ACTOR_GUARD_H)continue;
                pos=ny*NG2_ACTOR_GUARD_W+nx;
                if(mask[pos]==1){
                    if(used>=NG2_ACTOR_GUARD_PIXELS)return -1;
                    mask[pos]=(uint16_t)label;stack[used++]=(uint16_t)pos;
                }
            }
        }
        if(count>=56&&count<=152&&x1-x0<=15&&y1-y0<=13&&(x1-x0==15||y1-y0==13)){
            /* At least56 distinct pixels per complete component: at most94
             * fit in5304pixels. Preserve all, and fail closed on overflow. */
            NG2ActorFragment *f;if(fragment_count>=96)return -1;
            f=&fragments[fragment_count++];f->left=left+x0;f->top=top+y0;
            f->width=x1-x0;f->height=y1-y0;f->count=count;f->label=label;
        }
        if(x1-x0==15&&y1-y0==13&&count>=128){int inter=0,uni=0;
            for(y=0;y<13;++y)for(x=0;x<15;++x){
                int a=ng2_irregular_red(rgba+(top+y0+y)*stride+4*(left+x0+x),1);
                int b=(ng2_actor_heart_rows[y]>>x)&1u;inter+=a&&b;uni+=a||b;
            }
            if(100*inter>=90*uni&&100*inter>=93*137){
                /* Each full qualified component has>=128 distinct pixels:
                 * at most41 fit the5304pixel guard. Never truncate on overflow. */
                if(n>=64)return -1;
                markers[n].left=left+x0;markers[n].top=top+y0;
                markers[n].inter=inter;markers[n].uni=uni;markers[n].label=label;++n;
            }
        }
    }
    for(y=cy-9;y<cy+15;++y)for(x=cx-14;x<cx+15;++x){
        const unsigned char *p=rgba+y*stride+4*x;
        body_luma+=gray[y*W+x]>=70;
        body_sat+=ng2_max(p[0],ng2_max(p[1],p[2]))-ng2_min(p[0],ng2_min(p[1],p[2]))>=40;
    }
    out->enemy_body_luma[direction]=body_luma;out->enemy_body_saturation[direction]=body_sat;
    for(k=0;k<n;++k)if(!grouped[k]){
        int queue[64],members[64],used=1,total=0,j,a,b,l=W,r=0,t=H,bottom=0,inter=0,uni=0;
        queue[0]=k;grouped[k]=1;
        while(used){int at=queue[--used];members[total++]=at;
            for(j=0;j<n;++j)if(!grouped[j]
                &&abs(markers[j].left-markers[at].left)>=17&&abs(markers[j].left-markers[at].left)<=19
                &&abs(markers[j].top-markers[at].top)<=1){
                if(used>=64)return -1;
                grouped[j]=1;queue[used++]=j;
            }
        }
        if(total<1||total>3)continue;
        for(j=0;j<total;++j){NG2ActorMarker m=markers[members[j]];
            l=ng2_min(l,m.left);r=ng2_max(r,m.left+15);t=ng2_min(t,m.top);bottom=ng2_max(bottom,m.top+13);
        }
        if(bottom-t>14||abs(l+r-2*cx)>12||t+bottom-2*cy<-64||t+bottom-2*cy>-24)continue;
        /* Maximal graph components are retained before these global checks.
         * Reject staircases/branches, rather than extracting a passing subset. */
        for(a=0;a<total;++a)for(b=a+1;b<total;++b)
            if(markers[members[b]].left<markers[members[a]].left){int tmp=members[a];members[a]=members[b];members[b]=tmp;}
        for(j=1;j<total;++j)if(markers[members[j]].left-markers[members[j-1]].left<17
            ||markers[members[j]].left-markers[members[j-1]].left>19)break;
        if(j<total)continue;
        for(y=t;y<bottom;++y)for(x=l;x<r;++x){int observed=ng2_irregular_red(rgba+y*stride+4*x,1),reference=0;
            for(j=0;j<total;++j){NG2ActorMarker m=markers[members[j]];
                if(x>=m.left&&x<m.left+15&&y>=m.top&&y<m.top+13)
                    reference|=(ng2_actor_heart_rows[y-m.top]>>(x-m.left))&1u;
            }
            inter+=observed&&reference;uni+=observed||reference;
        }
        if(uni-137*total>64||100*inter<90*uni||100*inter<93*137*total||body_luma<48||body_sat<96)continue;
        if(!out->enemy_matches[direction]){
            out->enemy_inter[direction]=inter;out->enemy_union[direction]=uni;
            out->enemy_left[direction]=l;out->enemy_top[direction]=t;
            out->enemy_red_outside[direction]=uni-137*total;out->enemy_heart_count[direction]=total;
            out->enemy_width[direction]=r-l;out->enemy_height[direction]=bottom-t;
        }
        if(ng2_actor_partial_extension(mask,left,top,fragments,fragment_count,markers,members,total))
            out->enemy_matches[direction]=2;
        else out->enemy_matches[direction]=ng2_min(2,out->enemy_matches[direction]+1);
    }
    if(out->enemy_matches[direction]==1)out->enemy_mask|=1u<<direction;
    return 0;
}
/* Exact full-window white counts reject most positions before the sparse
 *223-bit intersection. Max108108 windows, no resize, crop or global state. */
static int ng2_irregular_restart(const unsigned char *rgba,size_t stride,
    const unsigned char *gray,NG2IrregularObservation *out){
    enum {RW=576,RH=300,PITCH=577};
    uint32_t *integral=(uint32_t*)calloc((size_t)PITCH*(RH+1),sizeof(uint32_t));
    int refx[223],refy[223],count=0,x,y,found=0,best_i=0,best_u=1,best_x=0,best_y=0;
    int min_x=W,max_x=0,min_y=H,max_y=0;const NG2Template *t=&ng2_template_restart;
    if(!integral)return -1;
    for(y=0;y<28;++y)for(x=0;x<181;++x)if(ng2_template_bit(t,x,y)){
        if(count>=223){free(integral);return -1;}
        refx[count]=x;refy[count]=y;++count;
    }
    if(count!=223){free(integral);return -1;}
    for(y=0;y<RH;++y)for(x=0;x<RW;++x){
        int a=gray[(y+60)*W+x+160]>=180&&ng2_neutral(rgba+(y+60)*stride+4*(x+160));
        integral[(y+1)*PITCH+x+1]=(uint32_t)a+integral[y*PITCH+x+1]
            +integral[(y+1)*PITCH+x]-integral[y*PITCH+x];
    }
    for(y=0;y<=RH-28;++y)for(x=0;x<=RW-181;++x){int i=0,u,j,observed;
        observed=(int)(integral[(y+28)*PITCH+x+181]-integral[y*PITCH+x+181]
            -integral[(y+28)*PITCH+x]+integral[y*PITCH+x]);
        if(observed<212||observed>237)continue;
        for(j=0;j<count;++j){int xx=x+160+refx[j],yy=y+60+refy[j];
            i+=gray[yy*W+xx]>=180&&ng2_neutral(rgba+yy*stride+4*xx);
        }
        u=223+observed-i;if(100*i<94*u||100*i<95*223)continue;
        min_x=ng2_min(min_x,x);max_x=ng2_max(max_x,x);min_y=ng2_min(min_y,y);max_y=ng2_max(max_y,y);
        if(!found||i*best_u>best_i*u||(i*best_u==best_i*u&&i>best_i)){
            best_i=i;best_u=u;best_x=x;best_y=y;
        }
        found=1;
    }
    free(integral);
    if(found){out->glyph_intersection=best_i;out->glyph_union=best_u;
        out->left=best_x+160;out->top=best_y+60;out->width=181;out->height=28;
        out->matches=best_x-min_x<=2&&max_x-best_x<=2&&best_y-min_y<=2&&max_y-best_y<=2?1:2;
        if(out->matches==1)out->kind=NG2_IRREGULAR_IMAGE_RESTART;
    }
    return 0;
}
int ng2_analyze_irregular_rgba(const uint8_t *rgba,size_t length,size_t stride,
    uint32_t flags,NG2IrregularObservation *out){
    unsigned char *gray;int x,y,inter,uni,pause,death,glyph_death,k,result=0;
    if(!out)return -1;
    memset(out,0,sizeof(*out));out->abi_version=NG2_IRREGULAR_ABI_VERSION;out->struct_size=sizeof(*out);
    if(!rgba||stride<W*4u||stride>7680u||length!=stride*H||flags>NG2_IRREGULAR_SCAN_RESTART)return -1;
    for(y=0;y<H;++y)for(x=0;x<W;++x)if(rgba[y*stride+4*x+3]!=255)return -1;
    gray=(unsigned char*)malloc(PIXELS);if(!gray)return -1;
    for(y=0;y<H;++y)for(x=0;x<W;++x)gray[y*W+x]=ng2_gray(rgba+y*stride+4*x);
    out->hud_mask=ng2_match(rgba,stride,gray,&ng2_template_footer,1)
        +2*ng2_match(rgba,stride,gray,&ng2_template_zone_one,1)
        +4*ng2_match(rgba,stride,gray,&ng2_template_floor_one,1)
        +8*ng2_pause_icon(rgba,stride,gray);
    pause=ng2_match(rgba,stride,gray,&ng2_template_continue,0);
    death=ng2_match(rgba,stride,gray,&ng2_template_death,0);
    ng2_irregular_health(rgba,stride,out);
    ng2_irregular_template(rgba,stride,gray,&ng2_template_death,1,&inter,&uni);
    glyph_death=100*inter>=64*uni&&100*inter>=90*522;
    if(glyph_death){
        /* A visible full prompt vetoes live/menu input even when the HUD is
         * incomplete. Preserve its support as NONE; only the stronger
         * three-heart/HUD certificate below grants DEATH_CONTINUE authority. */
        out->glyph_intersection=inter;out->glyph_union=uni;
        out->matches=1;out->left=312;out->top=312;out->width=270;out->height=24;
    }else if(death){
        /* The old non-neutral mask is a conservative UI veto even below the
         * new90% coverage. Preserve that distinct support, never action
         * authority: strong DEATH still requires matches1 and all HUD hearts. */
        ng2_irregular_template(rgba,stride,gray,&ng2_template_death,0,&inter,&uni);
        out->glyph_intersection=inter;out->glyph_union=uni;
        out->matches=2;out->left=312;out->top=312;out->width=270;out->height=24;
    }
    if(glyph_death&&out->hud_mask==15&&!pause&&out->empty_hearts==3)
        out->kind=NG2_IRREGULAR_IMAGE_DEATH;
    else if(!death&&!glyph_death){
        if(flags&NG2_IRREGULAR_SCAN_RESTART)result=ng2_irregular_restart(rgba,stride,gray,out);
        if(!result&&out->kind==NG2_IRREGULAR_IMAGE_NONE&&out->hud_mask==15&&!pause){
            for(k=0;k<4;++k)if(ng2_irregular_actor(rgba,stride,gray,k,out)){result=-1;break;}
            if(out->enemy_mask)out->kind=NG2_IRREGULAR_IMAGE_ENEMY;
        }
    }
    free(gray);
    if(result){memset(out,0,sizeof(*out));out->abi_version=NG2_IRREGULAR_ABI_VERSION;out->struct_size=sizeof(*out);}
    return result;
}
