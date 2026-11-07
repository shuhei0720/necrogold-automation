/* NG-G2: the observed-cell planner and the original 73-candidate, single-input
 * motion verifier. Thresholds and Pillow's two-pass integer blur are preserved.
 * No acknowledgement or planned input count is evidence of displacement.
 */
#include "NG2Core.h"
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define W 224
#define H 104
#define N (W*H)
#define CELLS NG2_TILE_COUNT
#define INF_COST 1000000
static const int ddx[5] = {0,-1,1,0,0};
static const int ddy[5] = {0,0,0,-1,1};
/* Python min(tuple) compares direction names, not DIRECTIONS insertion order. */
static const int lexical[5] = {9,1,2,3,0};

static int index_of(int x,int y) {
    return x < -11 || x > 11 || y < -5 || y > 4 ? -1 : (y+5)*23+x+11;
}
static int px(int i) { return i%23-11; }
static int py(int i) { return i/23-5; }
static int tile(const NG2Scene *s,int x,int y) {
    int i=index_of(x,y); return i<0 ? NG2_TILE_UNKNOWN : s->tiles[i];
}
static int protected_at(const NG2Scene *s,int x,int y) {
    int i=index_of(x,y); return i>=0 && s->protected_cells[i]!=0;
}
static int valid_scene(const NG2Scene *s) {
    int i;
    if (!s || s->abi_version!=NG2_ABI_VERSION || s->struct_size!=sizeof(*s)
        || s->state!=NG2_FLOOR || s->goods<NG2_GOODS_UNKNOWN || s->goods>NG2_GOODS_VISIBLE) return 0;
    for (i=0;i<CELLS;++i)
        if (s->tiles[i]>NG2_TILE_ITEM || s->protected_cells[i]>1) return 0;
    return 1;
}
/* Returns the normal to the observed gold bracket. A vertical bracket wins
 * when both orientations exist, exactly as _gates' second assignment does. */
static int gate(const NG2Scene *s,int x,int y) {
    int k=tile(s,x,y),normal=0;
    if (k!=NG2_TILE_FLOOR && k!=NG2_TILE_DIRT && k!=NG2_TILE_STONE && k!=NG2_TILE_DOOR) return 0;
    if (tile(s,x-1,y)==NG2_TILE_GOLD && tile(s,x+1,y)==NG2_TILE_GOLD) normal=NG2_DOWN;
    if (tile(s,x,y-1)==NG2_TILE_GOLD && tile(s,x,y+1)==NG2_TILE_GOLD) normal=NG2_RIGHT;
    return normal;
}
static int gold_count(const NG2Scene *s) {
    int i,n=0; for (i=0;i<CELLS;++i) n+=s->tiles[i]==NG2_TILE_GOLD; return n;
}
typedef struct { int cost,length,first,order,done; } Path;
static void paths(const NG2Scene *s,int weighted,Path out[CELLS]) {
    int i,serial=0,origin=index_of(0,0);
    for (i=0;i<CELLS;++i) { out[i].cost=INF_COST;out[i].length=0;out[i].first=0;out[i].order=INT_MAX;out[i].done=0; }
    out[origin].cost=0;out[origin].order=serial++;
    for (;;) {
        int best=-1,d;
        for (i=0;i<CELLS;++i)
            if (!out[i].done && out[i].cost<INF_COST &&
                (best<0 || out[i].cost<out[best].cost ||
                 (out[i].cost==out[best].cost && out[i].order<out[best].order))) best=i;
        if (best<0) break;
        out[best].done=1;
        for (d=1;d<=4;++d) {
            int x=px(best)+ddx[d],y=py(best)+ddy[d],next=index_of(x,y),k,total;
            if (next<0 || protected_at(s,x,y)) continue;
            k=tile(s,x,y);
            if (k!=NG2_TILE_FLOOR && !(weighted && k==NG2_TILE_DIRT)) continue;
            total=out[best].cost+(k==NG2_TILE_DIRT ? 2 : 1);
            if (total<out[next].cost) {
                out[next].cost=total;out[next].length=out[best].length+1;
                out[next].first=out[best].first ? out[best].first : d;
                out[next].order=serial++;
            }
        }
    }
}
static int lexpoint(int x,int y,int bx,int by) { return x<bx || (x==bx && y<by); }
static void decision(NG2Decision *out,int direction,int reason,int x,int y,const NG2Scene *s) {
    out->direction=direction;out->reason=reason;out->target_x=x;out->target_y=y;
    out->obstacle=direction ? tile(s,ddx[direction],ddy[direction]) : 0;
}
int ng2_choose(const NG2Scene *source,int32_t x,int32_t y,const uint16_t *visits,
               size_t count,const NG2Entrance *entrance,NG2Decision *out) {
    NG2Scene copy;
    const NG2Scene *s=source;
    Path route[CELLS];
    int i,d,passed=-1,best=-1,bestdir=0,bestcost=INF_COST,gx=0,gy=0,nearest=INF_COST,axis;
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!valid_scene(s) || !visits || count!=NG2_VISIT_COUNT || x < -16 || x > 16 || y < -16 || y > 16) return 0;
    if (s->goods==NG2_GOODS_VISIBLE) { out->reason=1;return 0; }
    for (d=0;d<=4;++d) if (protected_at(s,ddx[d],ddy[d])) { out->reason=2;return 0; }
    if (!gold_count(s) || tile(s,0,0)!=NG2_TILE_FLOOR) { out->reason=3;return 0; }
    if (entrance && entrance->valid) {
        int64_t rx=(int64_t)entrance->x-x,ry=(int64_t)entrance->y-y;
        d=entrance->direction;
        if (entrance->valid!=1 || d<1 || d>4 || entrance->x < -16 || entrance->x > 16 || entrance->y < -16 || entrance->y > 16 ||
            rx*ddx[d]+ry*ddy[d]>0) { out->reason=4;return 0; }
        passed=(rx>=-11 && rx<=11 && ry>=-5 && ry<=4) ? index_of((int)rx,(int)ry) : -1;
        copy=*source;s=&copy;
        for (i=0;i<CELLS;++i)
            if (copy.tiles[i]!=NG2_TILE_GOLD && px(i)*ddx[d]+py(i)*ddy[d]<0) copy.tiles[i]=NG2_TILE_UNKNOWN;
    }
    paths(s,1,route);
    /* scan() inserts origin first, then the rest in row-major order. */
    for (i=-1;i<CELLS;++i) {
        int p=i<0 ? index_of(0,0) : i,normal,side;
        if (i==index_of(0,0) || p==passed || s->protected_cells[p]) continue;
        normal=gate(s,px(p),py(p));
        if (!normal) continue;
        for (side=1;side>=-1;side-=2) {
            int nx=px(p)+side*ddx[normal],ny=py(p)+side*ddy[normal],n=index_of(nx,ny);
            if (n<0 || route[n].cost==INF_COST) continue;
            if (!route[n].length) {
                for (d=1;d<=4;++d) if (nx+ddx[d]==px(p) && ny+ddy[d]==py(p)) {
                    decision(out,d,5,px(p),py(p),s);return 1;
                }
            } else {
                int first=route[n].first;
                if (best<0 || route[n].cost<bestcost ||
                    (route[n].cost==bestcost && (lexical[first]<lexical[bestdir] ||
                     (first==bestdir && lexpoint(nx,ny,px(best),py(best)))))) {
                    best=n;bestdir=first;bestcost=route[n].cost;
                }
            }
        }
    }
    if (best>=0) { decision(out,bestdir,tile(s,ddx[bestdir],ddy[bestdir])==NG2_TILE_DIRT ? 6 : 7,px(best),py(best),s);return 1; }
    for (i=0;i<CELLS;++i) if (s->tiles[i]==NG2_TILE_GOLD) {
        int gap=abs(px(i))+abs(py(i));
        if (gap<nearest || (gap==nearest && lexpoint(px(i),py(i),gx,gy))) { nearest=gap;gx=px(i);gy=py(i); }
    }
    axis=abs(gy)>=abs(gx);
    paths(s,0,route);bestcost=INF_COST;
    for (i=0;i<CELLS;++i) {
        int k,gap=INF_COST,seen=0,wx=x+px(i),wy=y+py(i),score,axial,bestaxial;
        if (!route[i].length || route[i].cost==INF_COST || i==passed) continue;
        for (k=0;k<CELLS;++k) if (s->tiles[k]==NG2_TILE_GOLD) {
            int distance=abs(px(i)-px(k))+abs(py(i)-py(k)); if (distance<gap) gap=distance;
        }
        if (wx>=-16 && wx<=16 && wy>=-16 && wy<=16) seen=visits[(wy+16)*33+wx+16];
        score=3*gap+route[i].length+4*seen;
        axial=axis ? abs(py(i)-gy) : abs(px(i)-gx);
        bestaxial=best<0 ? INF_COST : (axis ? abs(py(best)-gy) : abs(px(best)-gx));
        d=route[i].first;
        if (best<0 || score<bestcost || (score==bestcost && (axial<bestaxial ||
            (axial==bestaxial && (lexical[d]<lexical[bestdir] ||
             (d==bestdir && lexpoint(px(i),py(i),px(best),py(best)))))))) {
            best=i;bestdir=d;bestcost=score;
        }
    }
    if (best>=0) { decision(out,bestdir,8,px(best),py(best),s);return 1; }
    return 0;
}

typedef struct { unsigned char normalized[N],texture[N],positive[N]; } View;
typedef struct { double score;int sx,sy; } Candidate;
static int clamp(int v,int high) { return v<0 ? 0 : (v>=high ? high-1 : v); }
static void view(const unsigned char raw[N],View *out) {
    unsigned char horizontal[N];
    int x,y;
    for (y=0;y<H;++y) for (x=0;x<W;++x)
        horizontal[y*W+x]=(unsigned char)((raw[y*W+clamp(x-1,W)]+raw[y*W+x]+raw[y*W+clamp(x+1,W)]+1)/3);
    for (y=0;y<H;++y) for (x=0;x<W;++x) {
        int at=y*W+x,values[9],a,b,n=0,blur,detail,median;
        for (a=-1;a<=1;++a) for (b=-1;b<=1;++b) values[n++]=raw[clamp(y+a,H)*W+clamp(x+b,W)];
        for (a=1;a<9;++a) { int v=values[a];b=a;while (b>0 && values[b-1]>v) {values[b]=values[b-1];--b;}values[b]=v; }
        median=values[4];blur=(horizontal[clamp(y-1,H)*W+x]+horizontal[at]+horizontal[clamp(y+1,H)*W+x]+1)/3;
        detail=(int)raw[at]-blur+128;
        out->normalized[at]=raw[at]<=6 ? 0 : (unsigned char)(detail<0 ? 0 : (detail>255 ? 255 : detail));
        out->texture[at]=(unsigned char)(raw[at]>6 && abs((int)raw[at]-median)>=3);
        out->positive[at]=(unsigned char)((int)raw[at]-median>=3);
    }
}
static int mask(int x,int y,int expanded) {
    if (x<40 || x>=179 || y<20 || y>=79) return 0;
    if (!expanded) return !(x>=90 && x<139 && y>=36);
    return !(x>=103 && x<122 && y>=43 && y<61) && !(x>=115 && x<154 && y>=38 && y<80);
}
static unsigned char even_round(double v) {
    unsigned int n=(unsigned int)v;double f=v-n;
    if (f>.5 || (f==.5 && (n&1u))) ++n;
    return (unsigned char)(n>255 ? 255 : n);
}
static double intensity(const View *a,const View *b,int sx,int sy) {
    uint32_t count=0,sa=0,sb=0,qa=0,qb=0,total=0;
    int x,y;double contrast,ma,mb,gain;unsigned char lut[256];
    for (y=20;y<79;++y) for (x=40;x<179;++x) {
        unsigned int av,bv;
        if (!mask(x,y,0) || !mask(x+sx,y+sy,0)) continue;
        av=a->normalized[y*W+x];bv=b->normalized[(y+sy)*W+x+sx];
        if (av<=6 || bv<=6) continue;
        ++count;sa+=av;sb+=bv;qa+=av*av;qb+=bv*bv;
    }
    if (count<300) return INFINITY;
    contrast=(sqrt(((double)qa-(double)sa*sa/count)/count)+sqrt(((double)qb-(double)sb*sb/count)/count))/2;
    ma=(double)sa/count;mb=(double)sb/count;
    if (contrast<2.5 || ma<6 || mb<6) return INFINITY;
    gain=ma/mb;if (gain<.65) gain=.65;else if (gain>1.55) gain=1.55;
    for (x=0;x<256;++x) { volatile double product=(double)x*gain;lut[x]=even_round(product); }
    for (y=20;y<79;++y) for (x=40;x<179;++x) {
        int av,bv;
        if (!mask(x,y,0) || !mask(x+sx,y+sy,0)) continue;
        av=a->normalized[y*W+x];bv=b->normalized[(y+sy)*W+x+sx];
        if (av>6 && bv>6) total+=(uint32_t)abs(av-(int)lut[bv]);
    }
    return (double)total/count/contrast;
}
static int ranked(const void *left,const void *right) {
    const Candidate *a=(const Candidate *)left,*b=(const Candidate *)right;
    if (a->score<b->score) return -1;
    if (a->score>b->score) return 1;
    return a->sx!=b->sx ? (a->sx<b->sx ? -1 : 1) : (a->sy<b->sy ? -1 : a->sy>b->sy);
}
static void texture_match(const View *a,const View *b,int sx,int sy,int expanded,int *support,int *bad,int regions[3]) {
    int x,y;*support=0;*bad=0;
    if (regions) regions[0]=regions[1]=regions[2]=0;
    for (y=20;y<79;++y) for (x=40;x<179;++x) {
        int old=y*W+x,other;
        if (!mask(x,y,expanded) || !mask(x+sx,y+sy,expanded)) continue;
        other=(y+sy)*W+x+sx;
        if (!a->texture[old] || !b->texture[other]) continue;
        ++*support;*bad+=a->positive[old]!=b->positive[other];
        if (regions) {
            if (y<36) ++regions[0];
            else if (x<90) ++regions[1];
            else if (x>=139) ++regions[2];
        }
    }
}
static int translated_gold(const NG2Scene *a,const NG2Scene *b,int tx,int ty,int exact) {
    int i,ac=gold_count(a),bc=gold_count(b);
    if (exact && ac!=bc) return 0;
    for (i=0;i<CELLS;++i) if (a->tiles[i]==NG2_TILE_GOLD && tile(b,px(i)+tx,py(i)+ty)!=NG2_TILE_GOLD) return 0;
    return 1;
}
static int closed_translation(const NG2Scene *a,const NG2Scene *b,int sx,int sy) {
    int i,tx=sx/9,ty=sy/9;
    if ((sx==0 && sy==0) || sx%9 || sy%9 || gold_count(a)<2 || !translated_gold(a,b,tx,ty,1)) return 0;
    for (i=0;i<CELLS;++i)
        if (a->tiles[i]==NG2_TILE_DOOR && gate(a,px(i),py(i)) &&
            tile(b,px(i)+tx,py(i)+ty)==NG2_TILE_DOOR && gate(b,px(i)+tx,py(i)+ty)) return 1;
    return 0;
}
static int partial_match(const NG2Scene *a,const NG2Scene *b,int tx,int ty) {
    int i,j,gx=0,gy=0,anchors[CELLS],n=0;
    for (i=0;i<CELLS;++i) if (a->tiles[i]==NG2_TILE_GOLD) {gx=px(i);gy=py(i);}
    if (tile(b,gx+tx,gy+ty)!=NG2_TILE_GOLD) return 0;
    for (i=0;i<CELLS;++i) {
        if (a->tiles[i]==NG2_TILE_STONE) {
            int k=tile(b,px(i)+tx,py(i)+ty);
            if (k!=NG2_TILE_STONE && k!=NG2_TILE_UNKNOWN) return 0;
            if (k==NG2_TILE_STONE) anchors[n++]=i;
        }
        if (b->tiles[i]==NG2_TILE_STONE) {
            int k=tile(a,px(i)-tx,py(i)-ty);
            if (k!=NG2_TILE_STONE && k!=NG2_TILE_UNKNOWN) return 0;
        }
    }
    for (i=0;i<n;++i) for (j=i+1;j<n;++j)
        if ((px(anchors[i])-gx)*(py(anchors[j])-gy)!=(py(anchors[i])-gy)*(px(anchors[j])-gx)) return 1;
    return 0;
}
static int partial_translation(const NG2Scene *a,const NG2Scene *b,int sx,int sy) {
    int amount,d,n=0,tx=0,ty=0;
    if (abs(sx)+abs(sy)!=9 || (sx!=0 && sy!=0) || gold_count(a)!=1 || gold_count(b)<=1) return 0;
    if (partial_match(a,b,0,0)) ++n;
    for (amount=1;amount<=2;++amount) for (d=1;d<=4;++d)
        if (partial_match(a,b,amount*ddx[d],amount*ddy[d])) {++n;tx=amount*ddx[d];ty=amount*ddy[d];}
    return n==1 && tx==sx/9 && ty==sy/9;
}
static int unique_gate_translation(const NG2Scene *a,const NG2Scene *b,int sx,int sy) {
    int amount,d,matches=0,tx=0,ty=0;
    if (gold_count(a)<2) return 0;
    for (amount=0;amount<=2;++amount) for (d=1;d<=(amount ? 4 : 1);++d) {
        int x=amount*ddx[d],y=amount*ddy[d],i;
        if (!translated_gold(a,b,x,y,0)) continue;
        for (i=0;i<CELLS;++i) {
            int ak=a->tiles[i],bk=tile(b,px(i)+x,py(i)+y);
            if (gate(a,px(i),py(i)) && gate(b,px(i)+x,py(i)+y) &&
                ((ak==NG2_TILE_DOOR && (bk==NG2_TILE_DOOR || bk==NG2_TILE_FLOOR)) ||
                 (ak==NG2_TILE_FLOOR && bk==NG2_TILE_FLOOR))) {++matches;tx=x;ty=y;break;}
        }
    }
    return matches==1 && sx==tx*9 && sy==ty*9;
}
static int texture_strength(int support,int opposite,int required_percent) {
    return support>=300 && (required_percent==95 ? 20 : 4)*opposite<=support;
}
static int texture_lead(int support,int opposite,int count,int bad) {
    return count<300 || 20*((int64_t)bad*support-(int64_t)opposite*count)>=3*(int64_t)count*support;
}
static int strong_texture(const View *a,const View *b,const Candidate c[73],int expanded,int require_regions) {
    int support,bad,regions[3],k;
    texture_match(a,b,c[0].sx,c[0].sy,expanded,&support,&bad,regions);
    if (!texture_strength(support,bad,95)) return 0;
    if (require_regions && (int)(regions[0]>=100)+(int)(regions[1]>=100)+(int)(regions[2]>=100)<2) return 0;
    for (k=1;k<73;++k) {
        int count,opposite;
        texture_match(a,b,c[k].sx,c[k].sy,expanded,&count,&opposite,NULL);
        if (!texture_lead(support,bad,count,opposite)) return 0;
    }
    return 1;
}
static void evaluate_motion(const NG2Scene *before,const NG2Scene *after,int direction,
                            const View views[2],Candidate candidates[73],NG2Motion *out) {
    int support,bad,sx,sy,amount;
    double best;
    qsort(candidates,73,sizeof(*candidates),ranked);
    best=candidates[0].score;sx=candidates[0].sx;sy=candidates[0].sy;
    if (!isfinite(best) || candidates[1].score-best<.08) return;
    if (best>.45 && !((closed_translation(before,after,sx,sy) || partial_translation(before,after,sx,sy)) &&
                      strong_texture(&views[0],&views[1],candidates,0,1))) return;
    texture_match(&views[0],&views[1],sx,sy,0,&support,&bad,NULL);
    if (support<300) {
        if (best>.45 || !unique_gate_translation(before,after,sx,sy) || !strong_texture(&views[0],&views[1],candidates,1,0)) return;
    } else if (!texture_strength(support,bad,75)) return;
    if (sx==0 && sy==0) {
        int dx=ddx[direction],dy=ddy[direction];
        out->kind=NG2_BLOCKED;
        if (tile(before,dx,dy)==NG2_TILE_DOOR && tile(after,dx,dy)==NG2_TILE_FLOOR && gate(after,dx,dy)) out->kind=NG2_DOOR_OPENED;
        else if (tile(before,dx,dy)==NG2_TILE_DIRT && tile(after,dx,dy)==NG2_TILE_FLOOR &&
                 !protected_at(before,dx,dy) && !protected_at(after,dx,dy)) out->kind=NG2_TERRAIN_OPENED;
    } else if (sx==-9*ddx[direction] && sy==-9*ddy[direction]) {
        out->kind=NG2_MOVED;out->dx=ddx[direction];out->dy=ddy[direction];
    } else {
        out->kind=NG2_UNEXPECTED;
        if (sx%9==0 && sy%9==0) { out->dx=-sx/9;out->dy=-sy/9; }
        for (amount=1;amount<9;++amount)
            if (sx==-amount*ddx[direction] && sy==-amount*ddy[direction]) out->kind=NG2_TWEEN;
    }
}
int ng2_motion(const NG2Scene *before,const NG2Scene *after,int32_t direction,NG2Motion *out) {
    View *views;
    Candidate candidates[73];
    int n=1,amount,d;
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!valid_scene(before) || !valid_scene(after) || direction<1 || direction>4) return 0;
    views=(View *)malloc(2*sizeof(*views));
    if (!views) return 0;
    view(before->signature,&views[0]);view(after->signature,&views[1]);
    candidates[0].sx=0;candidates[0].sy=0;candidates[0].score=intensity(&views[0],&views[1],0,0);
    for (amount=1;amount<=18;++amount) for (d=1;d<=4;++d) {
        candidates[n].sx=amount*ddx[d];candidates[n].sy=amount*ddy[d];
        candidates[n].score=intensity(&views[0],&views[1],candidates[n].sx,candidates[n].sy);++n;
    }
    evaluate_motion(before,after,direction,views,candidates,out);
    free(views);return 1;
}
int ng2_entered_gate(const NG2Scene *before,const NG2Scene *after,int32_t direction,
                     int32_t x,int32_t y,int32_t motion,NG2Entrance *out) {
    int dx,dy;
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!valid_scene(before) || !valid_scene(after) || direction<1 || direction>4 || x < -16 || x > 16 || y < -16 || y > 16) return 0;
    dx=ddx[direction];dy=ddy[direction];
    if (motion!=NG2_MOVED || tile(before,dx,dy)!=NG2_TILE_FLOOR || tile(after,0,0)!=NG2_TILE_FLOOR ||
        !gate(before,dx,dy) || !gate(after,0,0) || protected_at(before,dx,dy) || protected_at(after,0,0)) return 0;
    if (x+dx < -16 || x+dx > 16 || y+dy < -16 || y+dy > 16) return 0;
    out->valid=1;out->x=x+dx;out->y=y+dy;out->direction=direction;return 1;
}
